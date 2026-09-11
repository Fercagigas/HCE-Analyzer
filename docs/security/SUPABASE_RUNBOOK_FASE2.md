# Runbook Supabase - Fase 2

Ejecuta este procedimiento por entorno como Owner. No copies valores de claves ni JWTs en el SQL Editor, Git o capturas. Conserva la evidencia en el repositorio protegido del proyecto.

## 1. Preparar

1. En Supabase Dashboard abre el proyecto correcto y **SQL Editor > New query**.
2. Confirma que no hay una clave `service_role` en el runtime. El backend necesitara una clave publishable/anon y los JWT de usuarios.
3. Guarda el resultado de esta consulta de inventario (sin filas clinicas):

```sql
select n.nspname, c.relname, c.relrowsecurity
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname in ('public', 'mimiciv_hosp', 'mimiciv_icu') and c.relkind in ('r', 'p')
order by 1, 2;
```

## 2. Aplicar migraciones, en este orden

1. Copia y ejecuta completo `db/migrations/0001_clinical_aggregates_v1.sql`.
2. Copia y ejecuta completo `db/migrations/0002_revoke_execute_readonly_query.sql`.
3. Copia y ejecuta completo `db/migrations/0003_drop_exec_sql.sql`.
4. Copia y ejecuta completo `db/migrations/0004_harden_security_definer_functions.sql`.
5. Copia y ejecuta completo `db/migrations/0005_rls_usuario_paciente_y_clinical_readonly.sql`.
6. Copia y ejecuta completo `db/migrations/0006_rbac_abac_relacion_asistencial.sql`.
7. Copia y ejecuta completo `db/migrations/0007_rag_governance.sql`.

Si una migracion falla, detente; no ejecutes los pasos posteriores parcialmente y registra el error sin secretos.

La numeración ejecutable es consistente de `0001` a `0005`. `0003_rag_search_functions_snapshot.sql` conserva un snapshot heredado sin DDL ejecutable: **no lo ejecutes** ni lo intercales en la secuencia. La migración RLS fue renumerada a `0005` para evitar la colisión que habría tenido con `0004_harden_security_definer_functions.sql`.

Verifica las funciones y la retirada de SQL libre:

```sql
select n.nspname, p.proname, p.prosecdef
from pg_proc p join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname in ('clinical_dataset_summary_v1', 'clinical_key_is_readonly_v1', 'execute_readonly_query', 'exec_sql')
order by p.proname;
```

El resultado debe incluir las dos funciones `clinical_*` y no incluir `execute_readonly_query` ni `exec_sql`.

## 3. Asignar pacientes y comprobar RLS

La nueva tabla empieza vacia: el owner debe conceder cada relacion usuario-paciente antes de que una cuenta pueda consultar ese paciente. Sustituye los placeholders por UUID e identificador autorizados:

```sql
insert into public.user_patient_access (user_id, tenant_id, subject_id, service_id, valid_from, granted_by)
values ('<AUTH_USER_UUID>', '<TENANT_ID>', <MIMIC_SUBJECT_ID>, '<SERVICE_ID>', now(), '<OWNER_AUTH_USER_UUID>')
on conflict (user_id, tenant_id, subject_id, service_id) do update set valid_from = excluded.valid_from, valid_until = null;

select user_id, tenant_id, subject_id, service_id, valid_from, valid_until
from public.user_patient_access
where user_id = '<AUTH_USER_UUID>' and tenant_id = '<TENANT_ID>' and subject_id = <MIMIC_SUBJECT_ID>;
```

Antes de iniciar la API, asigna en `auth.users.raw_app_meta_data` (mediante el endpoint administrativo o proceso de identidad aprobado) `tenant_id` no vacío y una lista `roles` formada solo por `clinician`, `reviewer`, `admin`, `auditor`, `knowledge_manager` o `researcher`. No uses `public.users.role` ni `user_metadata` como fuente de permisos.

Comprueba que no quedan policies heredadas permisivas y que RLS esta activo:

```sql
select c.relname, c.relrowsecurity, p.policyname, p.cmd, p.qual, p.with_check
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join pg_policies p on p.schemaname = n.nspname and p.tablename = c.relname
where n.nspname = 'public'
  and c.relname in ('user_patient_access','chat_sessions','chat_messages','analyses','user_preferences','clinical_documents','rag_chunks')
order by c.relname, p.policyname;
```

Todos los objetos existentes deben tener `relrowsecurity = true`; las policies de sesiones, analisis y preferencias deben referirse a `auth.uid()`. Prueba positiva y negativa desde dos cuentas de prueba distintas mediante la API: A crea una sesion y B recibe lista vacia/404 al pedirla. No uses una clave de servicio para esa prueba.

Para RAG, el claim de tenant debe estar en `tenant_id` o `app_metadata.tenant_id` del JWT. Comprueba que la migración dejó los documentos heredados en `draft` y que no hay resultados de otro tenant, retirados ni fuera de vigencia. Revisa y aprueba manualmente cada documento heredado antes de volverlo consultable; no promociones hashes legacy vacíos.

## 4. Crear la clave clinica de solo lectura

1. La migracion crea el rol PostgreSQL sin login `clinical_readonly` y solo le concede `USAGE`/`SELECT` en `mimiciv_hosp` y `mimiciv_icu`.
2. En el mecanismo de emision de JWT de tu proyecto, crea una credencial de backend cuyo claim `role` sea exactamente `clinical_readonly`, tenga expiracion y rotacion documentadas, y guardala solo en el gestor de secretos como `SUPABASE_CLINICAL_KEY`. No uses `anon`, `authenticated`, `service_role` ni una clave secret para esta variable.
3. Verifica como owner los grants efectivos:

```sql
select has_schema_privilege('clinical_readonly', 'mimiciv_hosp', 'USAGE') as hosp_usage,
       has_table_privilege('clinical_readonly', 'mimiciv_hosp.patients', 'SELECT') as can_select,
       has_table_privilege('clinical_readonly', 'mimiciv_hosp.patients', 'INSERT') as can_insert,
       has_table_privilege('clinical_readonly', 'mimiciv_icu.chartevents', 'UPDATE') as can_update,
       has_function_privilege('clinical_readonly', 'public.clinical_key_is_readonly_v1()', 'EXECUTE') as can_verify;
```

El unico resultado aceptable es `true, true, false, false, true`. El provider bloquea toda consulta clinica si la RPC de verificacion detecta escritura o no puede verificarse.

## 5. Configurar el runtime y validar

En el gestor de secretos (o `.env` local no versionado) configura placeholders, nunca valores reales en este documento:

```dotenv
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_KEY=<AUTH_KEY_EXISTENTE_DE_BAJO_PRIVILEGIO>
SUPABASE_ANON_KEY=<PUBLISHABLE_O_ANON_KEY>
SUPABASE_CLINICAL_KEY=<JWT_ROLE_CLINICAL_READONLY>
```

`SUPABASE_KEY` se conserva para Auth heredada; los repositorios de producto construyen un cliente con `SUPABASE_ANON_KEY` y el Bearer JWT de cada `RequestContext`. La ausencia de JWT o clave publica falla cerrada para persistencia protegida.

Reinicia el backend y verifica:

```sql
select * from public.clinical_key_is_readonly_v1();
```

Ejecuta despues las pruebas offline locales:

```powershell
$env:HCE_DISABLE_DOTENV='1'; python -m pytest
```

Después, desde un entorno autorizado con `ANTHROPIC_API_KEY`, `SUPABASE_URL` y claves de bajo privilegio configuradas fuera del repositorio, ejecuta la evaluación live de seguridad:

```powershell
python -m Evaluation.run_security_tests --output Evaluation/results
```

Para validar `SEC-IND-001`, siembra primero un documento de prueba inocuo y aislado del corpus productivo y ejecuta:

```powershell
python -m Evaluation.run_security_tests --include-indirect-fixture --output Evaluation/results
```

El gate de la oleada 1 exige cero violaciones `critical`. Conserva el resultado y la evidencia de la siembra en el repositorio protegido del proyecto, sin PHI ni secretos, y registra los checks completados en `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md`.
