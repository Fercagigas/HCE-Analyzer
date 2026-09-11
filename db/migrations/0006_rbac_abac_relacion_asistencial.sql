-- 0006_rbac_abac_relacion_asistencial.sql
-- Fase 2: atributos de tenant, servicio y vigencia para la relacion usuario-paciente.
-- Los roles viven exclusivamente en auth.users.raw_app_meta_data (tenant_id, roles);
-- nunca en el cuerpo de una peticion ni en public.users.

begin;

alter table public.user_patient_access
  add column if not exists tenant_id text not null default 'default',
  add column if not exists service_id text not null default 'default',
  add column if not exists valid_from timestamptz not null default now(),
  add column if not exists valid_until timestamptz null;

-- 0005 usaba (user_id, subject_id); una misma persona puede atender al paciente
-- desde varios servicios o tenants, cada uno con una vigencia independiente.
alter table public.user_patient_access drop constraint if exists user_patient_access_pkey;
alter table public.user_patient_access
  add constraint user_patient_access_pkey primary key (user_id, tenant_id, subject_id, service_id),
  add constraint user_patient_access_valid_window check (valid_until is null or valid_until > valid_from),
  add constraint user_patient_access_tenant_not_blank check (length(trim(tenant_id)) > 0),
  add constraint user_patient_access_service_not_blank check (length(trim(service_id)) > 0);

create index if not exists user_patient_access_active_lookup_idx
  on public.user_patient_access (user_id, tenant_id, subject_id, service_id, valid_from, valid_until);

-- Mantiene el RLS de 0005 para lectura propia. Las escrituras administrativas se
-- hacen mediante el backend con service key tras el check RBAC de la API; no se
-- concede INSERT/UPDATE/DELETE a authenticated.
revoke insert, update, delete on public.user_patient_access from authenticated;

commit;
