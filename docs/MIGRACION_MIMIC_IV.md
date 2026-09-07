# Migración de MIMIC-IV-ED a MIMIC-IV Clinical Demo 2.2

> **Nota (Fase 1, sep 2026).** Las referencias a `DatabaseService`, `custom_query` y a la RPC `execute_readonly_query` describen el estado en el momento de la migracion. Desde Fase 1 el acceso clinico es exclusivamente por `chathce.adapters.supabase.MimicClinicalDataProvider` (ADR 0050) y la RPC de SQL libre se elimina con `db/migrations/0002`.

**Fecha:** 1 de septiembre de 2026
**Estado:** Completada y verificada

> Para el detalle columna a columna de cada tabla, ver el diccionario de datos: [MIMIC_IV_DATA_DICTIONARY.md](MIMIC_IV_DATA_DICTIONARY.md).

## Resumen

Se migró la fuente de datos clínicos del prototipo desde **MIMIC-IV-ED** (schema `mimic_ed`, 6 tablas de urgencias) a la **MIMIC-IV Clinical Database Demo 2.2** (historia clínica hospitalaria completa, 100 pacientes). Esta migración está alineada con la decisión DP-03 del intended purpose ("MIMIC-IV-ED es un adapter transitorio... se prevé migrar o ampliar la fuente a MIMIC general") y con el ADR 0010.

El dataset antiguo (`mimic_ed`) fue **eliminado** de Supabase tras cargar y verificar la nueva fuente.

## Esquemas nuevos

Se siguió la convención oficial de MIMIC-IV con dos esquemas (adapter fiel y mapeable a FHIR):

### `mimiciv_hosp` (módulo hospitalario)

| Tabla | Filas | Contenido |
|---|---:|---|
| patients | 100 | Demografía (subject_id, gender, anchor_age, dod) |
| admissions | 275 | Admisiones hospitalarias (hadm_id, tiempos, tipo, alta) |
| transfers | 1190 | Traslados entre unidades |
| services | 319 | Servicios asignados durante la admisión |
| diagnoses_icd | 4506 | Diagnósticos (códigos ICD) |
| d_icd_diagnoses | 109775 | Diccionario de títulos de diagnóstico |
| procedures_icd | 722 | Procedimientos (códigos ICD) |
| d_icd_procedures | 85257 | Diccionario de títulos de procedimiento |
| labevents | 107727 | Resultados de laboratorio |
| d_labitems | 1622 | Diccionario de tests de laboratorio |
| microbiologyevents | 2899 | Microbiología |
| omr | 2964 | Mediciones ambulatorias (BMI, TA...) |
| prescriptions | 18087 | Prescripciones |
| pharmacy | 15306 | Farmacia |
| emar | 35835 | Administración de medicamentos (eMAR) |

### `mimiciv_icu` (módulo UCI)

| Tabla | Filas | Contenido |
|---|---:|---|
| icustays | 140 | Estancias en UCI (stay_id) |
| chartevents | 668862 | Signos vitales y mediciones monitorizadas |
| d_items | 4014 | Diccionario de ítems de chart |

**Total: ~1,48M filas** en 18 tablas.

## Subconjunto curado

Se cargó un **subconjunto clínico curado** (no las 31 tablas del dataset). Se omitieron tablas operativas de bajo valor para las capabilities v1, respetando el principio de *minimum necessary data*: `provider`, `caregiver`, `poe`/`poe_detail`, `emar_detail`, `hcpcsevents`/`d_hcpcs`, `drgcodes`, `datetimeevents`, `inputevents`, `outputevents`, `procedureevents`, `ingredientevents`.

## Identificadores clave (cambio de modelo)

- **subject_id**: paciente (igual que antes)
- **hadm_id**: admisión hospitalaria (nuevo eje del episodio; sustituye al `stay_id` de urgencias)
- **stay_id**: ahora identifica una **estancia UCI** (`mimiciv_icu.icustays`), no una estancia de urgencias

Diferencia importante respecto a MIMIC-IV-ED:
- Los diagnósticos ya no incluyen `icd_title`; el título se obtiene con JOIN a `d_icd_diagnoses`/`d_icd_procedures` por `(icd_code, icd_version)`.
- Labs y chartevents guardan solo `itemid`; el nombre está en `d_labitems`/`d_items`.
- Ya no existen `edstays`, `triage`, `vitalsign`, `medrecon`, `pyxis` ni la columna `chiefcomplaint`/`acuity`.

## Seguridad (igual que la posición previa)

- RLS habilitado en todas las tablas nuevas.
- Política `SELECT` para el rol `authenticated`; escritura revocada para `anon`/`authenticated`.
- Esquemas expuestos vía PostgREST (`pgrst.db_schemas`).
- RPC `execute_readonly_query` con `search_path` a `public, mimiciv_hosp, mimiciv_icu` (SELECT-only).

> Nota de roadmap: el SQL libre (`custom_query`) sigue existiendo como activo de investigación. Su eliminación y sustitución por un `ClinicalDataProvider` tipado es trabajo de Fase 1/2, fuera del alcance de esta migración de datos.

## Cambios de código

- `config/settings.py`: `allowed_schemas = ["mimiciv_hosp", "mimiciv_icu"]`.
- `services/medical_agent/services/database_service.py`: reescrito. Mapa `TABLE_SCHEMA` (tabla→esquema), operaciones clínicas nuevas (`get_patient_summary`, `get_admission_details`, `get_lab_results`, `get_icu_chartevents`, `get_medication_history`, `get_patient_diagnoses`, `get_admission_diagnoses`, `search_diagnoses`), enriquecimiento de diagnósticos con títulos ICD.
- `services/unified_chat/tools/database_tool.py`: nuevo esquema documentado para el LLM, query types `patient_summary | admission_details | diagnoses | medications | labs | icu_vitals | custom`, validador de SQL/columnas actualizado.
- `services/medical_agent/prompt_manager.py`: identidad, contexto, esquema y ejemplos reescritos para MIMIC-IV clinical.
- `services/medical_agent/tools/visualization_collaboration_tool.py`: fuentes de datos y agregados actualizados (labevents, chartevents, diagnoses_icd, prescriptions, admissions).
- `services/connection_pool_manager.py`: health check contra `mimiciv_hosp.patients`.
- `utils/validators/mimic_validator.py`: conteos, columnas e integridad para el nuevo modelo.
- `scripts/load_mimiciv.py`: cargador idempotente de los CSV.gz a Supabase (service_role).

## Cómo recargar los datos

```powershell
conda activate HCE ; python scripts/load_mimiciv.py            # todo
conda activate HCE ; python scripts/load_mimiciv.py --only chartevents
conda activate HCE ; python scripts/load_mimiciv.py --verify-only
```

El cargador lee de `_mimic_iv_extract/mimic-iv-clinical-database-demo-2.2/` (descomprimir el zip del dataset ahí) y requiere `SUPABASE_URL`/`SUPABASE_KEY` (service_role) en `.env`.

## Verificación realizada

- Conteos por tabla coinciden exactamente con los CSV origen.
- Integridad referencial: 0 admisiones huérfanas, 0 diagnósticos sin diccionario, 0 chartevents sin item.
- Smoke test del data service + tool: patient_summary, labs, diagnoses (con títulos), custom query por RPC y rechazo del esquema antiguo `mimic_ed`.
