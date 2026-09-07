# Base de datos: migraciones versionadas

Las funciones SQL que usa ChatHCE viven aqui para que el esquema de Supabase sea
reproducible y auditable. Se aplican manualmente en el **SQL Editor** de Supabase
(rol `postgres`); el repositorio no ejecuta DDL.

| Fichero | Contenido | Cuando aplicar |
| --- | --- | --- |
| `0001_clinical_aggregates_v1.sql` | 4 RPC de agregados fijos (`clinical_*_v1`), `SECURITY INVOKER`, `statement_timeout 10s`, limite <= 200 | Antes de usar `get_dataset_statistics` / visualizaciones de frecuencias (WP3) |
| `0002_revoke_execute_readonly_query.sql` | Elimina la RPC de SQL libre `execute_readonly_query` | Despues de desplegar el runtime sin `custom_query` (WP4) |
| `0003_rag_search_functions_snapshot.sql` | Plantilla para versionar `hybrid_search` / `vector_search` | Cuando el propietario exporte las definiciones |

## Procedimiento

1. Abrir el proyecto en Supabase > SQL Editor.
2. Pegar el contenido del fichero y ejecutar. Todos los scripts son idempotentes.
3. Verificar con las consultas indicadas al final de cada fichero.
4. Anotar la aplicacion en `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md`.

## Claves por funcion (ADR 0010 §10)

- `SUPABASE_KEY`: clave general de la aplicacion (auth, `public.*`). Hoy es `service_role`; ese
  rol ignora RLS. Ver checklist para el plan de sustitucion.
- `SUPABASE_CLINICAL_KEY` (opcional, recomendado): clave de un rol de solo lectura sobre
  `mimiciv_hosp.*` y `mimiciv_icu.*`, usada exclusivamente por `MimicClinicalDataProvider`.
- `SUPABASE_SERVICE_ROLE_KEY`: solo scripts de carga (`scripts/load_mimiciv.py`, `scripts/clear_rag.py`,
  `scripts/record_mimic_fixtures.py`). Nunca en el runtime.

## Emulacion local

`chathce.adapters.memory.postgrest_client.register_clinical_aggregate_rpcs` reproduce las
cuatro RPC sobre tablas en memoria (tests y perfil `CLINICAL_PROVIDER=memory`).
