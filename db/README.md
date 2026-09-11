# Base de datos: migraciones versionadas

Las funciones SQL que usa ChatHCE viven aqui para que el esquema de Supabase sea
reproducible y auditable. Se aplican manualmente en el **SQL Editor** de Supabase
(rol `postgres`); el repositorio no ejecuta DDL.

| Fichero | Contenido | Cuando aplicar |
| --- | --- | --- |
| `0001_clinical_aggregates_v1.sql` | 4 RPC de agregados fijos (`clinical_*_v1`), `SECURITY INVOKER`, `statement_timeout 10s`, limite <= 200 | Antes de usar `get_dataset_statistics` / visualizaciones de frecuencias (WP3) |
| `0002_revoke_execute_readonly_query.sql` | Elimina la RPC de SQL libre `execute_readonly_query` | Despues de desplegar el runtime sin `custom_query` (WP4) |
| `0003_drop_exec_sql.sql` | Elimina la segunda RPC de SQL libre `exec_sql` | Despues de `0002` |
| `0003_rag_search_functions_snapshot.sql` | Snapshot heredado no ejecutable de `hybrid_search` / `vector_search` | No aplicar; pendiente de definiciones reales |
| `0004_harden_security_definer_functions.sql` | Endurece funciones SECURITY DEFINER y retira su EXECUTE de la API REST | Despues de `0003` |
| `0005_rls_usuario_paciente_y_clinical_readonly.sql` | RLS por ownership, concesiones usuario-paciente y rol clinico readonly | Despues de `0004` y antes de exponer datos de producto |

## Procedimiento

1. Abrir el proyecto en Supabase > SQL Editor.
2. Pegar el contenido del fichero y ejecutar. Todos los scripts son idempotentes.
3. Verificar con las consultas indicadas al final de cada fichero.
4. Anotar la aplicacion en `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md`.

## Claves por funcion (ADR 0010 §10)

- `SUPABASE_KEY`: credencial de Auth heredada y de bajo privilegio; no usar `service_role` en
  el runtime.
- `SUPABASE_ANON_KEY`/`SUPABASE_PUBLISHABLE_KEY`: clave publica usada con el JWT por peticion
  para los repositorios protegidos por RLS.
- `SUPABASE_CLINICAL_KEY`: JWT del rol `clinical_readonly` sobre `mimiciv_hosp.*` y
  `mimiciv_icu.*`, usado exclusivamente por `MimicClinicalDataProvider`.
- `SUPABASE_SERVICE_ROLE_KEY`: solo scripts de carga (`scripts/load_mimiciv.py`, `scripts/clear_rag.py`,
  `scripts/record_mimic_fixtures.py`). Nunca en el runtime.

## Emulacion local

`chathce.adapters.memory.postgrest_client.register_clinical_aggregate_rpcs` reproduce las
cuatro RPC sobre tablas en memoria (tests y perfil `CLINICAL_PROVIDER=memory`).
