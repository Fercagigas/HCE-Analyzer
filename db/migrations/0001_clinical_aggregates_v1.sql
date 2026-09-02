-- 0001_clinical_aggregates_v1.sql
-- Agregados fijos del dataset MIMIC-IV Demo para ChatHCE (ADR 0050).
-- Sustituyen al SQL libre: el modelo solo puede invocar estas funciones, con
-- parametros acotados y sin devolver identificadores de paciente.
--
-- Aplicar en el SQL Editor de Supabase (rol postgres). Idempotente.

create or replace function public.clinical_dataset_summary_v1()
returns table (
  patients bigint,
  admissions bigint,
  icu_stays bigint,
  diagnoses bigint,
  lab_events bigint,
  prescriptions bigint
)
language sql
stable
security invoker
set search_path = mimiciv_hosp, mimiciv_icu, pg_temp
set statement_timeout = '10s'
as $$
  select
    (select count(*) from mimiciv_hosp.patients),
    (select count(*) from mimiciv_hosp.admissions),
    (select count(*) from mimiciv_icu.icustays),
    (select count(*) from mimiciv_hosp.diagnoses_icd),
    (select count(*) from mimiciv_hosp.labevents),
    (select count(*) from mimiciv_hosp.prescriptions);
$$;

create or replace function public.clinical_top_diagnoses_v1(p_limit integer, p_icd_version integer default null)
returns table (
  icd_code text,
  icd_version integer,
  long_title text,
  n bigint
)
language sql
stable
security invoker
set search_path = mimiciv_hosp, pg_temp
set statement_timeout = '10s'
as $$
  select d.icd_code::text, d.icd_version::integer, t.long_title::text, count(*) as n
  from mimiciv_hosp.diagnoses_icd d
  left join mimiciv_hosp.d_icd_diagnoses t
    on t.icd_code = d.icd_code and t.icd_version = d.icd_version
  where p_icd_version is null or d.icd_version = p_icd_version
  group by d.icd_code, d.icd_version, t.long_title
  order by n desc, d.icd_code
  limit least(greatest(coalesce(p_limit, 20), 1), 200);
$$;

create or replace function public.clinical_top_drugs_v1(p_limit integer)
returns table (
  drug text,
  n bigint
)
language sql
stable
security invoker
set search_path = mimiciv_hosp, pg_temp
set statement_timeout = '10s'
as $$
  select p.drug::text, count(*) as n
  from mimiciv_hosp.prescriptions p
  where p.drug is not null
  group by p.drug
  order by n desc, p.drug
  limit least(greatest(coalesce(p_limit, 20), 1), 200);
$$;

create or replace function public.clinical_admission_type_distribution_v1()
returns table (
  admission_type text,
  n bigint
)
language sql
stable
security invoker
set search_path = mimiciv_hosp, pg_temp
set statement_timeout = '10s'
as $$
  select a.admission_type::text, count(*) as n
  from mimiciv_hosp.admissions a
  group by a.admission_type
  order by n desc, a.admission_type;
$$;

-- Permisos: solo roles autenticados de la aplicacion.
revoke all on function public.clinical_dataset_summary_v1() from public, anon;
revoke all on function public.clinical_top_diagnoses_v1(integer, integer) from public, anon;
revoke all on function public.clinical_top_drugs_v1(integer) from public, anon;
revoke all on function public.clinical_admission_type_distribution_v1() from public, anon;

grant execute on function public.clinical_dataset_summary_v1() to authenticated, service_role;
grant execute on function public.clinical_top_diagnoses_v1(integer, integer) to authenticated, service_role;
grant execute on function public.clinical_top_drugs_v1(integer) to authenticated, service_role;
grant execute on function public.clinical_admission_type_distribution_v1() to authenticated, service_role;

-- Verificacion:
--   select proname from pg_proc where proname like 'clinical_%_v1' order by 1;
--   select * from public.clinical_top_diagnoses_v1(5, null);
