# ✅ Configuración de Supabase - Verificada

## 📋 Resumen de Configuración

### Esquemas de Base de Datos
- **Esquema `public`:** Tablas de aplicación (usuarios, sesiones, chat)
- **Esquema `mimic_ed`:** Tablas MIMIC-IV-ED (datos médicos)
- **Función RPC:** `execute_readonly_query(text)` en esquema `public`
- **IMPORTANTE:** Las tablas MIMIC-IV-ED están en el esquema `mimic_ed`, NO en `public`

### Tablas Disponibles

#### Esquema `mimic_ed` (6 tablas de datos médicos)
1. `mimic_ed.diagnosis` - 545 filas, 6 columnas
2. `mimic_ed.edstays` - 222 filas, 9 columnas  
3. `mimic_ed.triage` - 222 filas, 11 columnas
4. `mimic_ed.vitalsign` - 1,038 filas, 11 columnas
5. `mimic_ed.medrecon` - 2,764 filas, 9 columnas
6. `mimic_ed.pyxis` - 1,082 filas, 7 columnas

#### Esquema `public` (tablas de aplicación)
- `users` - Usuarios del sistema
- `chat_sessions` - Sesiones de chat
- `chat_messages` - Mensajes de chat
- `documents` - Documentos indexados

## 🔧 Función RPC: execute_readonly_query

### Características
```sql
CREATE OR REPLACE FUNCTION execute_readonly_query(query_text text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, mimic_ed  -- ✅ Busca en ambos esquemas
```

**IMPORTANTE:** La función RPC está en el esquema `public` pero puede acceder a tablas en `mimic_ed`

### Validaciones Implementadas
1. ✅ Solo acepta queries que empiecen con `SELECT`
2. ✅ Rechaza keywords peligrosos: DROP, DELETE, INSERT, UPDATE, ALTER, CREATE, TRUNCATE, GRANT, REVOKE
3. ✅ Retorna resultados como JSONB
4. ❌ **NO acepta punto y coma (;) al final de la query**

### Uso Correcto

#### Opción 1: Usando Python Client con .schema()
```python
# ✅ CORRECTO - Acceso directo con schema()
result = supabase.schema('mimic_ed').table('edstays').select('*').limit(10).execute()

# ✅ CORRECTO - Para tablas de aplicación
result = supabase.table('users').select('*').execute()  # usa public por defecto
```

#### Opción 2: Usando RPC Function
```python
# ✅ CORRECTO - Sin prefijo de esquema (RPC maneja el search_path)
result = supabase.rpc('execute_readonly_query', {
    'query_text': 'SELECT * FROM edstays LIMIT 10'
}).execute()

# ❌ INCORRECTO - tiene punto y coma
result = supabase.rpc('execute_readonly_query', {
    'query_text': 'SELECT * FROM edstays LIMIT 10;'
}).execute()

# ❌ INCORRECTO - usa prefijo de esquema en RPC
result = supabase.rpc('execute_readonly_query', {
    'query_text': 'SELECT * FROM mimic_ed.edstays LIMIT 10'
}).execute()
```

## 📊 Reglas para Queries SQL

### ✅ Queries Correctas

#### Usando Python Client (Recomendado)
```python
# Simple select con schema
result = supabase.schema('mimic_ed').table('edstays').select('*').limit(10).execute()

# Con filtros
result = supabase.schema('mimic_ed').table('edstays') \
    .select('subject_id, gender') \
    .eq('gender', 'F') \
    .execute()

# Con ORDER BY
result = supabase.schema('mimic_ed').table('diagnosis') \
    .select('*') \
    .order('seq_num', desc=True) \
    .limit(5) \
    .execute()
```

#### Usando RPC Function (Para queries complejas)
```sql
-- Simple select (sin prefijo de esquema)
SELECT * FROM edstays LIMIT 10

-- Con filtros
SELECT subject_id, gender FROM edstays WHERE gender = 'F'

-- Con JOIN
SELECT e.stay_id, t.acuity 
FROM edstays e 
JOIN triage t ON e.stay_id = t.stay_id

-- Con agregación
SELECT gender, COUNT(*) as total 
FROM edstays 
GROUP BY gender

-- Con ORDER BY
SELECT * FROM diagnosis ORDER BY seq_num DESC LIMIT 5
```

### ❌ Queries Incorrectas

#### En Python Client
```python
# ❌ Sin especificar schema para tablas MIMIC-IV-ED
result = supabase.table('edstays').select('*').execute()  # Busca en public, no en mimic_ed

# ❌ Schema incorrecto
result = supabase.schema('public').table('edstays').select('*').execute()  # No existe en public
```

#### En RPC Function
```sql
-- ❌ Con punto y coma
SELECT * FROM edstays LIMIT 10;

-- ❌ Con prefijo de esquema (RPC ya maneja el search_path)
SELECT * FROM mimic_ed.edstays LIMIT 10

-- ❌ Con comentarios SQL
SELECT * FROM edstays -- comentario
LIMIT 10

-- ❌ Con columnas inexistentes
SELECT age FROM edstays  -- columna 'age' no existe

-- ❌ Con tablas inexistentes
SELECT * FROM patients  -- tabla 'patients' no existe
```

## 🔍 Columnas Exactas por Tabla

### edstays (9 columnas)
- subject_id (INTEGER, NOT NULL)
- hadm_id (NUMERIC, NULLABLE - 22.52% nulos)
- stay_id (INTEGER, NOT NULL, PK)
- intime (VARCHAR, NOT NULL)
- outtime (VARCHAR, NOT NULL)
- gender (VARCHAR, NOT NULL)
- race (VARCHAR, NOT NULL)
- arrival_transport (VARCHAR, NOT NULL)
- disposition (VARCHAR, NOT NULL)

### diagnosis (6 columnas)
- subject_id (INTEGER, NOT NULL)
- stay_id (INTEGER, NOT NULL)
- seq_num (SMALLINT, NOT NULL)
- icd_code (VARCHAR, NOT NULL)
- icd_version (SMALLINT, NOT NULL)
- icd_title (VARCHAR, NOT NULL)

### triage (11 columnas)
- subject_id (INTEGER, NOT NULL)
- stay_id (INTEGER, NOT NULL, PK)
- temperature (NUMERIC, NULLABLE - 11.71% nulos)
- heartrate (NUMERIC, NULLABLE - 10.81% nulos)
- resprate (NUMERIC, NULLABLE - 10.36% nulos)
- o2sat (NUMERIC, NULLABLE - 10.81% nulos)
- sbp (NUMERIC, NULLABLE - 10.36% nulos)
- dbp (NUMERIC, NULLABLE - 10.36% nulos)
- pain (VARCHAR, NULLABLE - 9.46% nulos)
- acuity (NUMERIC, NULLABLE - 6.76% nulos)
- chiefcomplaint (VARCHAR, NOT NULL)

### vitalsign (11 columnas)
- subject_id (INTEGER, NOT NULL)
- stay_id (INTEGER, NOT NULL)
- charttime (VARCHAR, NOT NULL)
- temperature (NUMERIC, NULLABLE - 44.22% nulos)
- heartrate (NUMERIC, NULLABLE - 2.89% nulos)
- resprate (NUMERIC, NULLABLE - 4.62% nulos)
- o2sat (NUMERIC, NULLABLE - 6.45% nulos)
- sbp (NUMERIC, NULLABLE - 3.85% nulos)
- dbp (NUMERIC, NULLABLE - 3.85% nulos)
- rhythm (VARCHAR, NULLABLE - 96.82% nulos)
- pain (VARCHAR, NULLABLE - 29.09% nulos)

### medrecon (9 columnas)
- subject_id (INTEGER, NOT NULL)
- stay_id (INTEGER, NOT NULL)
- charttime (VARCHAR, NOT NULL)
- name (VARCHAR, NOT NULL)
- gsn (INTEGER, NOT NULL)
- ndc (BIGINT, NOT NULL)
- etc_rn (SMALLINT, NOT NULL)
- etccode (NUMERIC, NULLABLE - 0.14% nulos)
- etcdescription (VARCHAR, NULLABLE - 0.14% nulos)

### pyxis (7 columnas)
- subject_id (INTEGER, NOT NULL)
- stay_id (INTEGER, NOT NULL)
- charttime (VARCHAR, NOT NULL)
- med_rn (SMALLINT, NOT NULL)
- name (VARCHAR, NOT NULL)
- gsn_rn (SMALLINT, NOT NULL)
- gsn (NUMERIC, NULLABLE - 2.96% nulos)

## ⚠️ Limitaciones del Dataset

### Tablas que NO existen
- ❌ `patients` - No hay tabla de pacientes separada
- ❌ `admissions` - No hay tabla de admisiones
- ❌ `demographics` - Datos demográficos están en `edstays`

### Columnas que NO existen
- ❌ `age` - No hay columna de edad
- ❌ `dob` - No hay fecha de nacimiento
- ❌ Solo hay `intime` y `outtime` en `edstays`

### Datos Disponibles
- ✅ 64 pacientes únicos (subject_id)
- ✅ 222 estancias en emergencias (stay_id)
- ✅ Datos de 2125-2178 (fechas anonimizadas)
- ✅ Solo género y raza en `edstays`

## 🧪 Pruebas de Verificación

### Verificar acceso con Python Client
```python
# Verificar esquema mimic_ed
result = supabase.schema('mimic_ed').table('edstays').select('stay_id').limit(1).execute()
print(f"✅ Acceso a mimic_ed: {len(result.data)} filas")

# Verificar esquema public
result = supabase.table('users').select('id').limit(1).execute()
print(f"✅ Acceso a public: {len(result.data)} filas")
```

### Verificar función RPC
```python
# Verificar RPC con tablas MIMIC-IV-ED
result = supabase.rpc('execute_readonly_query', {
    'query_text': 'SELECT COUNT(*) as total FROM edstays'
}).execute()
print(f"✅ RPC funciona: {result.data}")
```

### Verificar esquemas en Supabase
```sql
-- Ver todos los esquemas
SELECT schema_name FROM information_schema.schemata;

-- Ver tablas en mimic_ed
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'mimic_ed';

-- Ver tablas en public
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';
```

## 📝 Arquitectura de Esquemas

### Separación de Esquemas
```
Supabase Database
├── public (esquema de aplicación)
│   ├── users
│   ├── chat_sessions
│   ├── chat_messages
│   ├── documents
│   └── execute_readonly_query() [RPC Function]
│
└── mimic_ed (esquema de datos médicos)
    ├── edstays
    ├── diagnosis
    ├── triage
    ├── vitalsign
    ├── medrecon
    └── pyxis
```

### Métodos de Acceso

#### 1. Python Client con .schema() (Recomendado)
```python
# Para datos MIMIC-IV-ED
supabase.schema('mimic_ed').table('edstays').select('*').execute()

# Para datos de aplicación
supabase.table('users').select('*').execute()  # usa 'public' por defecto
```

#### 2. RPC Function (Para queries SQL complejas)
```python
# La función RPC tiene search_path = public, mimic_ed
# Por lo tanto, puede acceder a tablas en ambos esquemas sin prefijo
supabase.rpc('execute_readonly_query', {
    'query_text': 'SELECT * FROM edstays'  # Encuentra en mimic_ed
}).execute()
```

## ✅ Estado Final

**Configuración verificada:**
- ✅ Esquema `mimic_ed` contiene todas las tablas MIMIC-IV-ED
- ✅ Esquema `public` contiene tablas de aplicación
- ✅ Python Client usa `.schema('mimic_ed')` para acceso directo
- ✅ Función RPC puede acceder a ambos esquemas
- ✅ Sanitización de queries implementada
- ✅ Documentación actualizada con arquitectura de esquemas

**El agente médico usa `.schema('mimic_ed')` para todas las consultas a datos médicos.**
