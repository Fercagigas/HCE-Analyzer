-- 0005_rls_usuario_paciente_y_clinical_readonly.sql
-- Fase 2: RLS para datos de producto y rol dedicado de lectura clinica.
-- Aplicar como owner despues de 0004_harden_security_definer_functions.sql;
-- no modifica ni concede EXECUTE sobre sus funciones SECURITY DEFINER.

begin;

-- RLS suma policies permisivas con OR. Por eso se retiran primero las policies
-- heredadas de estas tablas; conservar una antigua ``using (true)`` anularia el
-- aislamiento nuevo.
do $$
declare p record;
begin
  for p in
    select policyname, tablename from pg_policies
    where schemaname = 'public'
      and tablename in ('user_patient_access', 'chat_sessions', 'chat_messages', 'analyses',
                        'user_preferences', 'clinical_documents', 'rag_chunks')
  loop
    execute format('drop policy if exists %I on public.%I', p.policyname, p.tablename);
  end loop;
end $$;

-- La asignacion explicita es el punto de control para acceso clinico por paciente.
create table if not exists public.user_patient_access (
  user_id uuid not null references auth.users(id) on delete cascade,
  subject_id bigint not null,
  granted_at timestamptz not null default now(),
  granted_by uuid null references auth.users(id),
  primary key (user_id, subject_id)
);
alter table public.user_patient_access enable row level security;
alter table public.user_patient_access force row level security;
revoke all on public.user_patient_access from public, anon, authenticated;
grant select on public.user_patient_access to authenticated;
create policy user_patient_access_own_select on public.user_patient_access for select to authenticated
  using (user_id = auth.uid());

-- Quita policies historicas permisivas y deja ownership comprobado por auth.uid().
-- Los DO dinamicos toleran instalaciones antiguas que aun no tengan todas las tablas.
do $$
declare t text;
begin
  foreach t in array array['chat_sessions', 'analyses', 'user_preferences'] loop
    if to_regclass('public.' || t) is not null then
      execute format('alter table public.%I enable row level security', t);
      execute format('alter table public.%I force row level security', t);
      execute format('revoke all on public.%I from anon', t);
      execute format('grant select, insert, update, delete on public.%I to authenticated', t);
      execute format('create policy fase2_owner_all on public.%I for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid())', t);
    end if;
  end loop;
end $$;

-- Los mensajes no llevan user_id: la propiedad se deriva siempre de su sesion.
alter table if exists public.chat_messages enable row level security;
alter table if exists public.chat_messages force row level security;
revoke all on table public.chat_messages from anon;
grant select, insert, update, delete on table public.chat_messages to authenticated;
create policy fase2_session_owner_all on public.chat_messages for all to authenticated
  using (exists (select 1 from public.chat_sessions s where s.id = session_id and s.user_id = auth.uid()))
  with check (exists (select 1 from public.chat_sessions s where s.id = session_id and s.user_id = auth.uid()));

-- El corpus es compartido solo para usuarios autenticados. La administracion sigue
-- reservada a un rol de JWT, no a una clave de servicio. No se conceden escrituras.
do $$
declare t text;
begin
  foreach t in array array['clinical_documents', 'rag_chunks'] loop
    if to_regclass('public.' || t) is not null then
      execute format('alter table public.%I enable row level security', t);
      execute format('alter table public.%I force row level security', t);
      execute format('revoke all on public.%I from anon', t);
      execute format('grant select on public.%I to authenticated', t);
      execute format('create policy fase2_authenticated_read on public.%I for select to authenticated using (auth.uid() is not null)', t);
    end if;
  end loop;
end $$;

-- Rol sin LOGIN para un JWT/API key clinica dedicada. No concede INSERT/UPDATE/DELETE.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'clinical_readonly') then
    create role clinical_readonly nologin noinherit;
  end if;
end $$;
grant usage on schema mimiciv_hosp, mimiciv_icu to clinical_readonly;
grant select on all tables in schema mimiciv_hosp, mimiciv_icu to clinical_readonly;
alter default privileges in schema mimiciv_hosp grant select on tables to clinical_readonly;
alter default privileges in schema mimiciv_icu grant select on tables to clinical_readonly;
revoke insert, update, delete, truncate, references, trigger on all tables in schema mimiciv_hosp, mimiciv_icu from clinical_readonly;

-- La funcion no revela filas: el provider la consulta antes de cualquier operacion.
create or replace function public.clinical_key_is_readonly_v1()
returns table (is_readonly boolean)
language sql stable security invoker
set search_path = pg_catalog
as $$
  select not exists (
    select 1
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname in ('mimiciv_hosp', 'mimiciv_icu') and c.relkind in ('r', 'p', 'v', 'm')
      and (has_table_privilege(current_user, c.oid, 'INSERT')
        or has_table_privilege(current_user, c.oid, 'UPDATE')
        or has_table_privilege(current_user, c.oid, 'DELETE')
        or has_table_privilege(current_user, c.oid, 'TRUNCATE'));
$$;
revoke all on function public.clinical_key_is_readonly_v1() from public;
grant execute on function public.clinical_key_is_readonly_v1() to clinical_readonly;

commit;
