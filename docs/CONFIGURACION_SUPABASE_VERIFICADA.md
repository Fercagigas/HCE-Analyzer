# Configuración de Supabase

> Actualizado al cierre de Fase 1. Datos: **MIMIC-IV Clinical Demo 2.2** (ver `docs/MIGRACION_MIMIC_IV.md`). Verificación operativa y de seguridad: `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md` (ADR 0070).

## Esquemas

- **`public`**: tablas de aplicación (`users`, `chat_sessions`, `chat_messages`, `clinical_documents`, `analyses`, `user_preferences`, `rag_chunks`) y funciones RPC.
- **`mimiciv_hosp`** (15 tablas) y **`mimiciv_icu`** (3 tablas): datos clínicos. El esquema `mimic_ed` fue eliminado.
- PostgREST expone `public, graphql_public, mimiciv_hosp, mimiciv_icu`.

### Conteos de referencia

| Esquema | Tabla | Filas |
|---|---|---:|
| mimiciv_hosp | patients | 100 |
| mimiciv_hosp | admissions | 275 |
| mimiciv_hosp | transfers | 1190 |
| mimiciv_hosp | services | 319 |
| mimiciv_hosp | diagnoses_icd | 4506 |
| mimiciv_hosp | d_icd_diagnoses | 109775 |
| mimiciv_hosp | procedures_icd | 722 |
| mimiciv_hosp | d_icd_procedures | 85257 |
| mimiciv_hosp | labevents | 107727 |
| mimiciv_hosp | d_labitems | 1622 |
| mimiciv_hosp | microbiologyevents | 2899 |
| mimiciv_hosp | omr | 2964 |
| mimiciv_hosp | prescriptions | 18087 |
| mimiciv_hosp | pharmacy | 15306 |
| mimiciv_hosp | emar | 35835 |
| mimiciv_icu | icustays | 140 |
| mimiciv_icu | chartevents | 668862 |
| mimiciv_icu | d_items | 4014 |

## Funciones RPC

| Función | Estado | Fichero |
|---|---|---|
| `clinical_dataset_summary_v1()` | Requerida (Fase 1) | `db/migrations/0001_clinical_aggregates_v1.sql` |
| `clinical_top_diagnoses_v1(p_limit, p_icd_version)` | Requerida | idem |
| `clinical_top_drugs_v1(p_limit)` | Requerida | idem |
| `clinical_admission_type_distribution_v1()` | Requerida | idem |
| `execute_readonly_query(text)` | **Debe eliminarse** | `db/migrations/0002_revoke_execute_readonly_query.sql` |
| `hybrid_search`, `vector_search` (RAG) | Existentes, sin versionar | plantilla `db/migrations/0003_rag_search_functions_snapshot.sql` |

Las RPC `clinical_*_v1` son `LANGUAGE sql STABLE SECURITY INVOKER`, con `search_path` fijo, `statement_timeout` de 10 s y límite acotado a 200. La RPC de SQL libre ya no tiene ningún consumidor en el código; su eliminación cierra el riesgo en la base de datos. Ambas migraciones se aplican en el SQL Editor (ver `db/README.md`).

## Patrón de acceso desde la aplicación

El runtime **no** usa el cliente Supabase directamente para datos clínicos. Todo pasa por `chathce.adapters.supabase.MimicClinicalDataProvider`, que:

- usa `.schema("mimiciv_hosp"|"mimiciv_icu").table(...)` con `select` explícito;
- añade siempre `.eq("subject_id", ctx.patient_id)` (defensa en profundidad además de `ScopeGuard`);
- pide `limit + 1` para marcar `truncated`;
- resuelve etiquetas contra diccionarios (`d_labitems`, `d_items`, `d_icd_*`) cacheados en memoria;
- llama a las RPC `clinical_*_v1` para agregados, solo con `purpose=research`.

Los scripts (`scripts/load_mimiciv.py`, `scripts/record_mimic_fixtures.py`) sí usan el cliente directamente, con `SUPABASE_SERVICE_ROLE_KEY` o `SUPABASE_KEY`, y nunca forman parte del runtime.

## Claves por función

| Variable | Rol | Uso |
|---|---|---|
| `SUPABASE_KEY` | hoy `service_role` (objetivo: bajo privilegio) | Auth, `public.*`, RAG |
| `SUPABASE_CLINICAL_KEY` | rol de solo lectura sobre `mimiciv_*` (pendiente de crear) | `MimicClinicalDataProvider` |
| `SUPABASE_SERVICE_ROLE_KEY` | `service_role` | Solo scripts de carga |

## Seguridad

- RLS habilitado en `mimiciv_hosp` / `mimiciv_icu`; política `SELECT` para `authenticated`; escritura revocada a `anon`/`authenticated`.
- El aislamiento por paciente lo aplica la aplicación (`ScopeGuard`, ADR 0090); RLS por usuario/paciente queda para Fase 2 (ADR 0100).
- El `service_role` ignora RLS: por eso el objetivo es separar claves por función y sustituir `SUPABASE_KEY` por una clave de bajo privilegio (checklist, item de rotación).

## Verificación rápida

```powershell
conda activate HCE ; python scripts/load_mimiciv.py --verify-only
conda activate HCE ; $env:HCE_RUN_INTEGRATION="1" ; python -m pytest tests/integration/test_mimic_provider_live.py -q
```

El segundo comando ejecuta el provider real en solo lectura; los tests de agregados se saltan hasta que `0001` esté aplicada.
