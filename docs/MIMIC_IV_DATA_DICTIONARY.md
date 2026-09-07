# Diccionario de datos — MIMIC-IV Clinical Demo 2.2 (en ChatHCE)

**Fuente:** MIMIC-IV Clinical Database Demo 2.2 (PhysioNet, 100 pacientes, datos anonimizados).
**Backend:** Supabase (PostgreSQL) — esquemas `mimiciv_hosp` y `mimiciv_icu`.
**Verificado contra `information_schema` el 1 de septiembre de 2026.**

Este documento describe el **subconjunto clínico curado** realmente cargado en el sistema (18 tablas). Es la referencia canónica del esquema; para el porqué de la migración y los cambios de código, ver [MIGRACION_MIMIC_IV.md](MIGRACION_MIMIC_IV.md).

> Tipos: `int` = integer, `smallint`, `float` = double precision, `varchar` = character varying, `text`, `ts` = timestamp, `date`. Todas las columnas son *nullable* salvo las marcadas **NOT NULL**.

---

## 1. Modelo de identificadores

| ID | Significado | Tabla origen |
|---|---|---|
| `subject_id` | Paciente único | `mimiciv_hosp.patients` |
| `hadm_id` | Admisión hospitalaria (episodio); un paciente puede tener varias | `mimiciv_hosp.admissions` |
| `stay_id` | Estancia en UCI | `mimiciv_icu.icustays` |
| `transfer_id` | Traslado entre unidades | `mimiciv_hosp.transfers` |
| `pharmacy_id` | Orden de farmacia | `mimiciv_hosp.pharmacy` |
| `itemid` | Ítem de laboratorio o de UCI (se resuelve con diccionarios) | `d_labitems` / `d_items` |
| `icd_code` + `icd_version` | Código de diagnóstico/procedimiento (se resuelve con diccionarios) | `d_icd_diagnoses` / `d_icd_procedures` |

Relaciones para obtener texto legible:
- Diagnóstico/procedimiento → título: `JOIN d_icd_diagnoses` / `d_icd_procedures` **ON (icd_code, icd_version)**.
- Laboratorio → nombre del test: `JOIN d_labitems` **ON itemid**.
- Chart UCI → nombre de la medición: `JOIN d_items` **ON itemid**.

---

## 2. Esquema `mimiciv_hosp` (módulo hospitalario)

### patients — 100 filas
Demografía del paciente. No hay fecha de nacimiento exacta (anonimización); la edad es `anchor_age`.

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | PK. Paciente |
| gender | varchar | M / F |
| anchor_age | int | Edad en `anchor_year` |
| anchor_year | int | Año de referencia (desplazado) |
| anchor_year_group | varchar | Rango trienal (p. ej. 2011-2013) |
| dod | date | Fecha de defunción, si consta |

### admissions — 275 filas
Admisiones hospitalarias. Eje del episodio (`hadm_id`).

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int **NOT NULL** | PK. Admisión |
| admittime / dischtime / deathtime | ts | Ingreso / alta / defunción |
| admission_type | varchar | Urgente, electiva, etc. |
| admit_provider_id | varchar | Proveedor que admite |
| admission_location / discharge_location | varchar | Origen / destino |
| insurance / language / marital_status / race | varchar | Datos administrativos/demográficos |
| edregtime / edouttime | ts | Paso por urgencias (si aplica) |
| hospital_expire_flag | smallint | 1 = fallece en el ingreso |

### transfers — 1190 filas
Traslados entre unidades durante el ingreso.

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int | Admisión (nullable) |
| transfer_id | int **NOT NULL** | PK |
| eventtype | varchar | admit / transfer / discharge |
| careunit | varchar | Unidad |
| intime / outtime | ts | Entrada / salida de la unidad |

### services — 319 filas
Servicio clínico responsable durante el ingreso.

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int **NOT NULL** | Admisión |
| transfertime | ts | Momento del cambio |
| prev_service / curr_service | varchar | Servicio previo / actual |

### diagnoses_icd — 4506 filas
Diagnósticos codificados de la admisión. Solo códigos; el título está en `d_icd_diagnoses`.

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int **NOT NULL** | Admisión |
| seq_num | int **NOT NULL** | Orden del diagnóstico |
| icd_code | varchar | Código ICD-9/10 |
| icd_version | int | 9 o 10 |

### d_icd_diagnoses — 109775 filas (diccionario)
| Columna | Tipo | Notas |
|---|---|---|
| icd_code | varchar **NOT NULL** | PK compuesta con icd_version |
| icd_version | int **NOT NULL** | 9 o 10 |
| long_title | text | Descripción del diagnóstico |

### procedures_icd — 722 filas
| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int **NOT NULL** | Admisión |
| seq_num | int **NOT NULL** | Orden |
| chartdate | ts | Fecha del procedimiento |
| icd_code | varchar | Código |
| icd_version | int | 9 o 10 |

### d_icd_procedures — 85257 filas (diccionario)
Igual estructura que `d_icd_diagnoses` (icd_code, icd_version, long_title).

### labevents — 107727 filas
Resultados de laboratorio. Solo `itemid`; el nombre está en `d_labitems`.

| Columna | Tipo | Notas |
|---|---|---|
| labevent_id | int **NOT NULL** | PK |
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int | Admisión (nullable: puede ser ambulatorio) |
| specimen_id | int | Muestra |
| itemid | int | Test (→ d_labitems) |
| order_provider_id | varchar | Proveedor |
| charttime / storetime | ts | Toma / registro |
| value | text | Valor textual |
| valuenum | float | Valor numérico |
| valueuom | varchar | Unidad |
| ref_range_lower / ref_range_upper | float | Rango de referencia |
| flag | varchar | `abnormal` si fuera de rango |
| priority | varchar | STAT / ROUTINE |
| comments | text | Comentarios |

### d_labitems — 1622 filas (diccionario)
| Columna | Tipo | Notas |
|---|---|---|
| itemid | int **NOT NULL** | PK |
| label | text | Nombre del test |
| fluid | text | Fluido (sangre, orina...) |
| category | text | Categoría |

### microbiologyevents — 2899 filas
Cultivos y antibiogramas.

| Columna | Tipo | Notas |
|---|---|---|
| microevent_id | int **NOT NULL** | PK |
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int | Admisión |
| micro_specimen_id | int | Muestra |
| order_provider_id | varchar | Proveedor |
| chartdate / charttime | ts | Fecha/hora |
| spec_itemid / spec_type_desc | int / varchar | Tipo de muestra |
| test_seq | int | Secuencia |
| storedate / storetime | ts | Registro |
| test_itemid / test_name | int / varchar | Prueba |
| org_itemid / org_name | int / varchar | Organismo aislado |
| isolate_num | smallint | Nº de aislado |
| quantity | varchar | Cantidad |
| ab_itemid / ab_name | int / varchar | Antibiótico probado |
| dilution_text / dilution_comparison / dilution_value | varchar / varchar / float | Dilución |
| interpretation | varchar | S/I/R (sensibilidad) |
| comments | text | Comentarios |

### omr — 2964 filas
Online Medical Record: mediciones ambulatorias (peso, talla, IMC, TA...).

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| chartdate | date | Fecha |
| seq_num | int | Secuencia |
| result_name | varchar | Nombre de la medición |
| result_value | text | Valor |

### prescriptions — 18087 filas
Prescripciones farmacológicas del ingreso.

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int **NOT NULL** | Admisión |
| pharmacy_id | int | Orden de farmacia |
| poe_id / poe_seq | varchar / int | Orden POE |
| order_provider_id | varchar | Proveedor |
| starttime / stoptime | ts | Inicio / fin |
| drug_type | varchar | MAIN / BASE / ADDITIVE |
| drug | varchar | **Nombre del fármaco** |
| formulary_drug_cd | varchar | Código de formulario |
| gsn / ndc | varchar | Códigos de fármaco |
| prod_strength | varchar | Concentración |
| form_rx | varchar | Forma prescrita |
| dose_val_rx / dose_unit_rx | varchar | Dosis / unidad |
| form_val_disp / form_unit_disp | varchar | Dispensación |
| doses_per_24_hrs | float | Dosis/día |
| route | varchar | Vía |

### pharmacy — 15306 filas
Detalle de farmacia (una fila por `pharmacy_id`).

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int **NOT NULL** | Admisión |
| pharmacy_id | int **NOT NULL** | PK |
| poe_id | varchar | Orden POE |
| starttime / stoptime | ts | Inicio / fin |
| medication | text | **Nombre del medicamento** |
| proc_type | varchar | Tipo |
| status | varchar | Estado |
| entertime / verifiedtime | ts | Registro / verificación |
| route / frequency / disp_sched | varchar | Vía / frecuencia / pauta |
| infusion_type / sliding_scale | varchar | Infusión / escala móvil |
| lockout_interval | varchar | Intervalo de bloqueo |
| basal_rate | float | Ritmo basal |
| one_hr_max | varchar | Máx/hora |
| doses_per_24_hrs | float | Dosis/día |
| duration / duration_interval | float / varchar | Duración |
| expiration_value / expiration_unit / expirationdate | int / varchar / ts | Caducidad |
| dispensation | varchar | Dispensación |
| fill_quantity | varchar | Cantidad |

### emar — 35835 filas
eMAR: registro de **administración** de medicamentos.

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int | Admisión |
| emar_id | varchar **NOT NULL** | PK |
| emar_seq | int | Secuencia |
| poe_id / pharmacy_id | varchar / int | Enlaces a orden/farmacia |
| enter_provider_id | varchar | Proveedor |
| charttime | ts | Momento de la administración |
| medication | text | **Nombre del medicamento** |
| event_txt | varchar | Administered / Not Given, etc. |
| scheduletime / storetime | ts | Programado / registrado |

---

## 3. Esquema `mimiciv_icu` (módulo UCI)

### icustays — 140 filas
Estancias en UCI.

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int **NOT NULL** | Admisión |
| stay_id | int **NOT NULL** | PK. Estancia UCI |
| first_careunit / last_careunit | varchar | Unidad inicial / final |
| intime / outtime | ts | Entrada / salida |
| los | float | Días de estancia |

### chartevents — 668862 filas
Mediciones monitorizadas en UCI (signos vitales, etc.). Tabla más grande. Solo `itemid`; el nombre está en `d_items`.

| Columna | Tipo | Notas |
|---|---|---|
| subject_id | int **NOT NULL** | Paciente |
| hadm_id | int **NOT NULL** | Admisión |
| stay_id | int **NOT NULL** | Estancia UCI |
| caregiver_id | int | Cuidador |
| charttime / storetime | ts | Medición / registro |
| itemid | int **NOT NULL** | Medición (→ d_items) |
| value | text | Valor textual |
| valuenum | float | Valor numérico |
| valueuom | varchar | Unidad |
| warning | smallint | Aviso del monitor |

### d_items — 4014 filas (diccionario)
| Columna | Tipo | Notas |
|---|---|---|
| itemid | int **NOT NULL** | PK |
| label | text | Nombre de la medición |
| abbreviation | text | Abreviatura |
| linksto | varchar | Tabla a la que enlaza |
| category | varchar | Categoría |
| unitname | varchar | Unidad |
| param_type | varchar | Numérico / texto |
| lownormalvalue / highnormalvalue | float | Rango normal |

---

## 4. Consultas de ejemplo (SELECT, sin punto y coma)

```sql
-- Pacientes únicos
SELECT subject_id, gender, anchor_age FROM mimiciv_hosp.patients ORDER BY subject_id

-- Admisiones de un paciente
SELECT hadm_id, admittime, dischtime, admission_type, discharge_location
FROM mimiciv_hosp.admissions WHERE subject_id = 10000032 ORDER BY admittime

-- Diagnósticos de una admisión con título
SELECT x.seq_num, x.icd_code, d.long_title
FROM mimiciv_hosp.diagnoses_icd x
JOIN mimiciv_hosp.d_icd_diagnoses d ON d.icd_code = x.icd_code AND d.icd_version = x.icd_version
WHERE x.hadm_id = 22595853 ORDER BY x.seq_num

-- Serie temporal de un laboratorio de un paciente
SELECT l.charttime, di.label, l.valuenum, l.valueuom, l.flag
FROM mimiciv_hosp.labevents l
JOIN mimiciv_hosp.d_labitems di ON di.itemid = l.itemid
WHERE l.subject_id = 10000032 ORDER BY l.charttime

-- Top 10 diagnósticos más frecuentes del dataset
SELECT d.long_title, COUNT(*) AS n
FROM mimiciv_hosp.diagnoses_icd x
JOIN mimiciv_hosp.d_icd_diagnoses d ON d.icd_code = x.icd_code AND d.icd_version = x.icd_version
GROUP BY d.long_title ORDER BY n DESC LIMIT 10

-- Signos vitales UCI de una estancia (por ítem)
SELECT c.charttime, i.label, c.valuenum, c.valueuom
FROM mimiciv_icu.chartevents c
JOIN mimiciv_icu.d_items i ON i.itemid = c.itemid
WHERE c.stay_id = 30057454 ORDER BY c.charttime
```

Acceso desde la aplicacion (Fase 1): exclusivamente mediante operaciones allowlisted de `ClinicalDataProvider` (`chathce/adapters/supabase/mimic_clinical_data_provider.py`) con filtro obligatorio por `subject_id`, y agregados mediante las RPC fijas `clinical_*_v1` (`db/migrations/0001`). La antigua RPC `execute_readonly_query` no tiene consumidores y se elimina con `db/migrations/0002` (ADR 0050).

---

## 5. Acceso desde el código

El agente NO recibe nombres de esquema/tabla como parámetros libres: usa operaciones tipadas de `DatabaseService` (`get_patient_summary`, `get_admission_details`, `get_lab_results`, `get_icu_chartevents`, `get_medication_history`, `get_patient_diagnoses`, `get_admission_diagnoses`, `search_diagnoses`). El mapa tabla→esquema vive en `DatabaseService.TABLE_SCHEMA`. La tool `query_mimic_database` expone los query types `patient_summary | admission_details | diagnoses | medications | labs | icu_vitals | custom`.

Acceso directo (Python client):
```python
supabase.schema('mimiciv_hosp').table('admissions').select('*').eq('subject_id', 10000032).execute()
supabase.schema('mimiciv_icu').table('chartevents').select('*').eq('stay_id', 30057454).execute()
```

---

## 6. Seguridad y notas

- RLS habilitado en las 18 tablas; política `SELECT` para `authenticated`; escritura revocada a `anon`/`authenticated`.
- Esquemas expuestos vía PostgREST (`pgrst.db_schemas`).
- Dataset **anonimizado**, de demostración (100 pacientes), para investigación/educación. Sin notas de texto libre.
- Tablas del dataset NO cargadas (subconjunto curado): `provider`, `caregiver`, `poe`/`poe_detail`, `emar_detail`, `hcpcsevents`/`d_hcpcs`, `drgcodes`, `datetimeevents`, `inputevents`, `outputevents`, `procedureevents`, `ingredientevents`.

---

## 7. Recarga y verificación

```powershell
conda activate HCE ; python scripts/load_mimiciv.py --verify-only   # conteos actuales
conda activate HCE ; python scripts/load_mimiciv.py                 # recarga completa (idempotente)
conda activate HCE ; python -m utils.validators.mimic_validator     # validación de conteos/columnas/integridad
```
