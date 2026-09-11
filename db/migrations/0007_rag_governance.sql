-- 0007_rag_governance.sql
-- Gobierno documental del RAG: tenant, version, aprobacion y vigencia.
-- Aplicar despues de 0005. Los registros heredados quedan como draft y por
-- tanto no son recuperables hasta que un responsable los revise y apruebe.

begin;

create extension if not exists pgcrypto;

do $$
declare t text;
begin
  foreach t in array array['clinical_documents', 'rag_chunks'] loop
    if to_regclass('public.' || t) is not null then
      execute format('alter table public.%I add column if not exists tenant_id text not null default ''default''', t);
      execute format('alter table public.%I add column if not exists document_key text', t);
      execute format('alter table public.%I add column if not exists version text not null default ''legacy-unapproved''', t);
      execute format('alter table public.%I add column if not exists effective_from date not null default date ''1970-01-01''', t);
      execute format('alter table public.%I add column if not exists effective_to date', t);
      execute format('alter table public.%I add column if not exists status text not null default ''draft''', t);
      execute format('alter table public.%I add column if not exists approved_by text', t);
      execute format('alter table public.%I add column if not exists approved_at timestamptz', t);
      execute format('alter table public.%I add column if not exists content_hash text not null default ''''', t);
      execute format('alter table public.%I drop constraint if exists %I', t, t || '_governance_status_ck');
      execute format('alter table public.%I add constraint %I check (status in (''draft'', ''approved'', ''retired''))', t, t || '_governance_status_ck');
      execute format('alter table public.%I drop constraint if exists %I', t, t || '_governance_dates_ck');
      execute format('alter table public.%I add constraint %I check (effective_to is null or effective_to >= effective_from)', t, t || '_governance_dates_ck');
      execute format('alter table public.%I drop constraint if exists %I', t, t || '_governance_approval_ck');
      execute format($sql$
        alter table public.%I add constraint %I check (
          status <> 'approved' or (
            approved_by is not null and approved_at is not null
            and content_hash ~ '^[0-9a-f]{64}$'
          )
        )
      $sql$, t, t || '_governance_approval_ck');
    end if;
  end loop;
end $$;

-- Solo los chunks pueden reconstruir de forma fiable el hash historico. Aun
-- asi se mantienen draft: nunca se promociona contenido heredado sin revision.
update public.rag_chunks
set content_hash = encode(digest(content, 'sha256'), 'hex'),
    document_key = coalesce(nullif(document_key, ''), filename),
    status = 'draft'
where true;

update public.clinical_documents
set document_key = coalesce(nullif(document_key, ''), title, filename),
    content_hash = coalesce(nullif(content_hash, ''), metadata ->> 'content_hash', ''),
    status = 'draft'
where true;

create index if not exists rag_chunks_governed_retrieval_idx
  on public.rag_chunks (tenant_id, status, effective_from, effective_to, document_key, version)
  where is_parent = false;
create index if not exists rag_chunks_governed_document_idx
  on public.rag_chunks (tenant_id, document_id, status);
create index if not exists clinical_documents_governed_lookup_idx
  on public.clinical_documents (tenant_id, status, document_key, version, effective_from);
create unique index if not exists clinical_documents_tenant_hash_uq
  on public.clinical_documents (tenant_id, content_hash)
  where content_hash <> '';

-- RLS no confia en un tenant enviado por el cliente: lo compara contra el JWT.
create or replace function public.rag_current_tenant_id()
returns text language sql stable security invoker
set search_path = pg_catalog
as $$
  select coalesce(auth.jwt() ->> 'tenant_id', auth.jwt() -> 'app_metadata' ->> 'tenant_id');
$$;
revoke all on function public.rag_current_tenant_id() from public;
grant execute on function public.rag_current_tenant_id() to authenticated;

do $$
declare p record;
begin
  for p in
    select policyname, tablename from pg_policies
    where schemaname = 'public' and tablename in ('clinical_documents', 'rag_chunks')
  loop
    execute format('drop policy if exists %I on public.%I', p.policyname, p.tablename);
  end loop;

  if to_regclass('public.clinical_documents') is not null then
    alter table public.clinical_documents enable row level security;
    alter table public.clinical_documents force row level security;
    revoke all on public.clinical_documents from anon;
    grant select on public.clinical_documents to authenticated;
    create policy rag_documents_tenant_select on public.clinical_documents for select to authenticated
      using (tenant_id = public.rag_current_tenant_id());
  end if;
  if to_regclass('public.rag_chunks') is not null then
    alter table public.rag_chunks enable row level security;
    alter table public.rag_chunks force row level security;
    revoke all on public.rag_chunks from anon;
    grant select on public.rag_chunks to authenticated;
    create policy rag_chunks_tenant_select on public.rag_chunks for select to authenticated
      using (tenant_id = public.rag_current_tenant_id());
  end if;
end $$;

-- El contrato de RPC ahora obliga tenant y fecha de consulta. SECURITY INVOKER
-- permite que RLS sea una segunda barrera frente a un parametro manipulado.
drop function if exists public.hybrid_search(vector, text, integer, integer);
drop function if exists public.vector_search(vector, integer);

create function public.vector_search(
  query_embedding vector,
  match_count integer,
  query_tenant_id text,
  query_as_of date default current_date
)
returns table (
  content text, similarity double precision, metadata jsonb, parent_id text,
  filename text, chunk_id text, tenant_id text, document_key text, version text,
  effective_from date, effective_to date, status text, approved_by text,
  approved_at timestamptz, content_hash text
)
language sql stable security invoker
set search_path = public, pg_catalog
as $$
  with eligible_documents as (
    select distinct on (coalesce(nullif(document_key, ''), filename))
      document_id, coalesce(nullif(document_key, ''), filename) as logical_key, version
    from public.rag_chunks
    where not is_parent
      and tenant_id = query_tenant_id
      and status = 'approved'
      and effective_from <= query_as_of
      and (effective_to is null or effective_to >= query_as_of)
    order by coalesce(nullif(document_key, ''), filename), effective_from desc, version desc, approved_at desc nulls last
  )
  select c.content, (1 - (c.embedding <=> query_embedding))::double precision,
         c.metadata, c.parent_id, c.filename, c.chunk_id, c.tenant_id, c.document_key,
         c.version, c.effective_from, c.effective_to, c.status, c.approved_by,
         c.approved_at, c.content_hash
  from public.rag_chunks c
  join eligible_documents d on d.document_id = c.document_id and d.version = c.version
  where not c.is_parent and c.tenant_id = query_tenant_id and c.status = 'approved'
  order by c.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;

create function public.hybrid_search(
  query_embedding vector,
  query_text text,
  match_count integer,
  rrf_k integer,
  query_tenant_id text,
  query_as_of date default current_date
)
returns table (
  content text, rrf_score double precision, metadata jsonb, parent_id text,
  filename text, chunk_id text, tenant_id text, document_key text, version text,
  effective_from date, effective_to date, status text, approved_by text,
  approved_at timestamptz, content_hash text
)
language sql stable security invoker
set search_path = public, pg_catalog
as $$
  with eligible_documents as (
    select distinct on (coalesce(nullif(document_key, ''), filename))
      document_id, coalesce(nullif(document_key, ''), filename) as logical_key, version
    from public.rag_chunks
    where not is_parent and tenant_id = query_tenant_id and status = 'approved'
      and effective_from <= query_as_of and (effective_to is null or effective_to >= query_as_of)
    order by coalesce(nullif(document_key, ''), filename), effective_from desc, version desc, approved_at desc nulls last
  ), ranked as (
    select c.*, row_number() over (order by c.embedding <=> query_embedding) as vector_rank,
           row_number() over (order by ts_rank_cd(to_tsvector('simple', c.content), plainto_tsquery('simple', query_text)) desc) as text_rank
    from public.rag_chunks c
    join eligible_documents d on d.document_id = c.document_id and d.version = c.version
    where not c.is_parent and c.tenant_id = query_tenant_id and c.status = 'approved'
  )
  select content,
         ((1.0 / (greatest(rrf_k, 1) + vector_rank)) + (1.0 / (greatest(rrf_k, 1) + text_rank)))::double precision,
         metadata, parent_id, filename, chunk_id, tenant_id, document_key, version,
         effective_from, effective_to, status, approved_by, approved_at, content_hash
  from ranked
  order by ((1.0 / (greatest(rrf_k, 1) + vector_rank)) + (1.0 / (greatest(rrf_k, 1) + text_rank))) desc
  limit greatest(match_count, 1);
$$;

revoke all on function public.vector_search(vector, integer, text, date) from public, anon;
revoke all on function public.hybrid_search(vector, text, integer, integer, text, date) from public, anon;
grant execute on function public.vector_search(vector, integer, text, date) to authenticated;
grant execute on function public.hybrid_search(vector, text, integer, integer, text, date) to authenticated;

commit;
