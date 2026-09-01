# ✅ Configuración de Supabase - Verificada

> Actualizado tras la migración a **MIMIC-IV Clinical Demo 2.2**. Ver `docs/MIGRACION_MIMIC_IV.md`.

## 📋 Resumen de Configuración

### Esquemas de Base de Datos
- **Esquema `public`:** Tablas de aplicación (usuarios, sesiones, chat, RAG)
- **Esquema `mimiciv_hosp`:** Módulo hospitalario de MIMIC-IV (datos médicos)
- **Esquema `mimiciv_icu`:** Módulo UCI de MIMIC-IV
- **Función RPC:** `execute_readonly_query(text)` en esquema `public` (SELECT-only)
- **IMPORTANTE:** Las tablas clínicas están en `mimiciv_hosp` / `mimiciv_icu`, NO en `public`. El esquema `mimic_ed` fue eliminado.

### Tablas Disponibles

#### Esquema `mimiciv_hosp`
| Tabla | Filas |
|---|---:|
| patients | 100 |
| admissions | 275 |
| transfers | 1190 |
| services | 319 |
| diagnoses_icd | 4506 |
| d_icd_diagnoses | 109775 |
| procedures_icd | 722 |
| d_icd_procedures | 85257 |
| labevents | 107727 |
| d_labitems | 1622 |
| microbiologyevents | 2899 |
| omr | 2964 |
| prescriptions | 18087 |
| pharmacy | 15306 |
| emar | 35835 |

#### Esquema `mimiciv_icu`
| Tabla | Filas |
|---|---:|
| icustays | 140 |
| chartevents | 668862 |
| d_items | 4014 |

#### Esquema `public` (tablas de aplicación)
- `users`, `chat_sessions`, `chat_messages`, `clinical_documents`, `analyses`, `user_preferences`, `rag_chunks`

## 🔧 Función RPC: execute_readonly_query

```sql
CREATE OR REPLACE FUNCTION public.execute_readonly_query(query_text text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, mimiciv_hosp, mimiciv_icu  -- ✅ Busca en los esquemas clínicos
```

- Solo permite `SELECT`; bloquea DROP/DELETE/INSERT/UPDATE/ALTER/CREATE/TRUNCATE/GRANT/REVOKE.
- Está en `public` pero puede acceder a `mimiciv_hosp` / `mimiciv_icu` vía `search_path`.

## 🧭 Patrones de acceso

### Python Client con `.schema()` (recomendado)
```python
# Datos hospitalarios
supabase.schema('mimiciv_hosp').table('admissions').select('*').eq('subject_id', 10000032).execute()
# Datos UCI
supabase.schema('mimiciv_icu').table('chartevents').select('*').eq('stay_id', 30057454).execute()
# Datos de aplicación (esquema public por defecto)
supabase.table('chat_sessions').select('*').execute()
```

### RPC (para SQL con JOINs)
```python
# El RPC maneja el search_path; usa nombres con o sin prefijo de esquema
supabase.rpc('execute_readonly_query', {
    'query_text': (
        "SELECT d.long_title, COUNT(*) AS n "
        "FROM mimiciv_hosp.diagnoses_icd x "
        "JOIN mimiciv_hosp.d_icd_diagnoses d "
        "ON d.icd_code = x.icd_code AND d.icd_version = x.icd_version "
        "GROUP BY d.long_title ORDER BY n DESC LIMIT 10"
    )
}).execute()
```

Reglas del RPC: sin punto y coma final, sin comentarios SQL, solo SELECT.

## 🔒 Seguridad

- RLS habilitado en todas las tablas de `mimiciv_hosp` / `mimiciv_icu`.
- Política `SELECT` para el rol `authenticated`; escritura revocada a `anon`/`authenticated`.
- Esquemas expuestos vía PostgREST (`pgrst.db_schemas = public, graphql_public, mimiciv_hosp, mimiciv_icu`).
- El `service_role` (usado por el cargador) tiene permisos completos sobre los esquemas clínicos.

## 🧪 Verificación rápida

```python
# Acceso hospitalario
r = supabase.schema('mimiciv_hosp').table('patients').select('subject_id', count='exact').limit(1).execute()
print('patients:', r.count)   # 100

# RPC
r = supabase.rpc('execute_readonly_query', {'query_text': 'SELECT COUNT(*) AS total FROM mimiciv_hosp.admissions'}).execute()
print('admissions:', r.data)  # 275
```

O bien: `conda activate HCE ; python scripts/load_mimiciv.py --verify-only`

## ✅ Configuración verificada

- Esquemas `mimiciv_hosp` y `mimiciv_icu` cargados con conteos exactos.
- `mimic_ed` eliminado.
- RPC `execute_readonly_query` con search_path a los esquemas nuevos.
- El data service usa `.schema('mimiciv_hosp'|'mimiciv_icu')` según la tabla (mapa `TABLE_SCHEMA`).
