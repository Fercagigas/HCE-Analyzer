# Guías de Base de Datos - ChatHCE

## Dataset MIMIC-IV-ED

MIMIC-IV-ED (Medical Information Mart for Intensive Care IV - Emergency Department) es un dataset de datos médicos del Servicio de Urgencias completamente anonimizado para investigación y educación.

**IMPORTANTE:** Las tablas MIMIC-IV-ED están en el esquema `mimic_ed` en Supabase, separadas de las tablas de aplicación que están en el esquema `public`.

## MCP de Supabase (Solo Desarrollo)

**IMPORTANTE - ACLARACIÓN SOBRE MCP:**

El MCP (Model Context Protocol) de Supabase configurado en `~/.kiro/settings/mcp.json` es **EXCLUSIVAMENTE para uso durante el desarrollo** por el agente de Kiro. Su propósito es:

- Permitir al agente de Kiro consultar la estructura de la base de datos durante el desarrollo
- Facilitar la exploración de esquemas y tablas para tareas de desarrollo
- Ayudar en debugging y verificación de datos durante la implementación

**El sistema ChatHCE NO usa MCP en producción.** En su lugar, utiliza:

- **Database Tool** (`services/unified_chat/tools/database_tool.py`): Herramienta propia que usa el cliente Python de Supabase
- **DatabaseService** (`services/medical_agent/services/database_service.py`): Servicio de acceso a datos con validación de seguridad

No confundir el MCP de desarrollo con la arquitectura de producción del sistema.

## Tablas Principales

### 1. edstays (Estancias en Urgencias)

**Descripción**: Información de cada visita al Servicio de Urgencias

**Columnas Clave**:
```sql
- subject_id (INT): ID único del paciente
- stay_id (INT): ID único de la estancia en urgencias
- hadm_id (INT): ID de hospitalización (si fue ingresado)
- intime (TIMESTAMP): Hora de llegada a urgencias
- outtime (TIMESTAMP): Hora de salida de urgencias
- gender (VARCHAR): Género del paciente
- race (VARCHAR): Raza/etnia
- arrival_transport (VARCHAR): Medio de transporte de llegada
- disposition (VARCHAR): Disposición final (alta, ingreso, traslado, etc.)
```

**Consultas Comunes**:
```sql
-- Información básica de una estancia
SELECT * FROM edstays WHERE subject_id = 10014729;

-- Tiempo de estancia en urgencias
SELECT 
    subject_id,
    stay_id,
    EXTRACT(EPOCH FROM (outtime - intime))/3600 as hours_in_ed
FROM edstays
WHERE subject_id = 10014729;
```

### 2. triage (Triaje)

**Descripción**: Datos de triaje inicial en urgencias

**Columnas Clave**:
```sql
- subject_id (INT): ID del paciente
- stay_id (INT): ID de la estancia
- temperature (FLOAT): Temperatura (°F)
- heartrate (FLOAT): Frecuencia cardíaca (lpm)
- resprate (FLOAT): Frecuencia respiratoria (rpm)
- o2sat (FLOAT): Saturación de oxígeno (%)
- sbp (FLOAT): Presión arterial sistólica (mmHg)
- dbp (FLOAT): Presión arterial diastólica (mmHg)
- pain (VARCHAR): Nivel de dolor (0-10)
- acuity (FLOAT): Nivel de urgencia (1-5, 1=más urgente)
- chiefcomplaint (TEXT): Motivo de consulta principal
```

**Consultas Comunes**:
```sql
-- Signos vitales de triaje
SELECT 
    temperature, heartrate, resprate, o2sat, sbp, dbp, pain, acuity
FROM triage
WHERE subject_id = 10014729;

-- Pacientes con signos vitales críticos
SELECT * FROM triage
WHERE sbp > 180 OR sbp < 90 OR heartrate > 120 OR o2sat < 90;
```

### 3. vitalsign (Signos Vitales)

**Descripción**: Signos vitales registrados durante la estancia

**Columnas Clave**:
```sql
- subject_id (INT): ID del paciente
- stay_id (INT): ID de la estancia
- charttime (TIMESTAMP): Hora del registro
- temperature (FLOAT): Temperatura
- heartrate (FLOAT): Frecuencia cardíaca
- resprate (FLOAT): Frecuencia respiratoria
- o2sat (FLOAT): Saturación de oxígeno
- sbp (FLOAT): Presión sistólica
- dbp (FLOAT): Presión diastólica
- rhythm (VARCHAR): Ritmo cardíaco
- pain (VARCHAR): Nivel de dolor
```

**Consultas Comunes**:
```sql
-- Evolución de signos vitales
SELECT charttime, temperature, heartrate, sbp, dbp, o2sat
FROM vitalsign
WHERE subject_id = 10014729
ORDER BY charttime;

-- Tendencia de presión arterial
SELECT 
    charttime,
    sbp,
    dbp,
    LAG(sbp) OVER (ORDER BY charttime) as prev_sbp
FROM vitalsign
WHERE subject_id = 10014729;
```

### 4. diagnosis (Diagnósticos)

**Descripción**: Diagnósticos asignados durante la estancia

**Columnas Clave**:
```sql
- subject_id (INT): ID del paciente
- stay_id (INT): ID de la estancia
- seq_num (INT): Número de secuencia del diagnóstico
- icd_code (VARCHAR): Código ICD-10
- icd_title (TEXT): Descripción del diagnóstico
- icd_version (INT): Versión de ICD (9 o 10)
```

**Consultas Comunes**:
```sql
-- Diagnósticos de un paciente
SELECT icd_code, icd_title, icd_version
FROM diagnosis
WHERE subject_id = 10014729
ORDER BY seq_num;

-- Diagnósticos más frecuentes
SELECT icd_code, icd_title, COUNT(*) as frequency
FROM diagnosis
GROUP BY icd_code, icd_title
ORDER BY frequency DESC
LIMIT 10;
```

### 5. medrecon (Reconciliación de Medicamentos)

**Descripción**: Medicamentos que el paciente toma habitualmente

**Columnas Clave**:
```sql
- subject_id (INT): ID del paciente
- stay_id (INT): ID de la estancia
- charttime (TIMESTAMP): Hora del registro
- name (VARCHAR): Nombre del medicamento
- gsn (VARCHAR): Generic Sequence Number
- ndc (VARCHAR): National Drug Code
- etc_rn (INT): Número de secuencia
- etccode (VARCHAR): Código de categoría terapéutica
- etcdescription (TEXT): Descripción de la categoría
```

**Consultas Comunes**:
```sql
-- Medicamentos habituales del paciente
SELECT DISTINCT name, etcdescription
FROM medrecon
WHERE subject_id = 10014729;

-- Medicamentos por categoría
SELECT etcdescription, COUNT(DISTINCT name) as med_count
FROM medrecon
WHERE subject_id = 10014729
GROUP BY etcdescription;
```

### 6. pyxis (Dispensación de Medicamentos)

**Descripción**: Medicamentos administrados en urgencias

**Columnas Clave**:
```sql
- subject_id (INT): ID del paciente
- stay_id (INT): ID de la estancia
- charttime (TIMESTAMP): Hora de administración
- name (VARCHAR): Nombre del medicamento
- gsn_rn (INT): Número de secuencia GSN
- gsn (VARCHAR): Generic Sequence Number
```

**Consultas Comunes**:
```sql
-- Medicamentos administrados en urgencias
SELECT charttime, name
FROM pyxis
WHERE subject_id = 10014729
ORDER BY charttime;

-- Frecuencia de administración de medicamentos
SELECT name, COUNT(*) as times_given
FROM pyxis
WHERE subject_id = 10014729
GROUP BY name
ORDER BY times_given DESC;
```

## Índices Optimizados

### Índices de Aplicación
```sql
-- Chat y usuarios
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_users_id ON users(id);
```

### Índices MIMIC-IV-ED
```sql
-- edstays
CREATE INDEX idx_edstays_subject_id ON edstays(subject_id);
CREATE INDEX idx_edstays_hadm_id ON edstays(hadm_id);
CREATE INDEX idx_edstays_intime ON edstays(intime);

-- triage
CREATE INDEX idx_triage_subject_id ON triage(subject_id);
CREATE INDEX idx_triage_acuity ON triage(acuity);

-- vitalsign
CREATE INDEX idx_vitalsign_subject_id ON vitalsign(subject_id);
CREATE INDEX idx_vitalsign_stay_id ON vitalsign(stay_id);
CREATE INDEX idx_vitalsign_charttime ON vitalsign(charttime);
CREATE INDEX idx_vitalsign_subject_charttime ON vitalsign(subject_id, charttime);

-- diagnosis
CREATE INDEX idx_diagnosis_subject_id ON diagnosis(subject_id);
CREATE INDEX idx_diagnosis_stay_id ON diagnosis(stay_id);
CREATE INDEX idx_diagnosis_icd_code ON diagnosis(icd_code);
CREATE INDEX idx_diagnosis_subject_stay ON diagnosis(subject_id, stay_id);

-- medrecon
CREATE INDEX idx_medrecon_subject_id ON medrecon(subject_id);
CREATE INDEX idx_medrecon_stay_id ON medrecon(stay_id);
CREATE INDEX idx_medrecon_charttime ON medrecon(charttime);
CREATE INDEX idx_medrecon_subject_charttime ON medrecon(subject_id, charttime);

-- pyxis
CREATE INDEX idx_pyxis_subject_id ON pyxis(subject_id);
CREATE INDEX idx_pyxis_stay_id ON pyxis(stay_id);
CREATE INDEX idx_pyxis_charttime ON pyxis(charttime);
CREATE INDEX idx_pyxis_subject_charttime ON pyxis(subject_id, charttime);
```

## Consultas Optimizadas

### Resumen Completo de Paciente
```sql
WITH patient_info AS (
    SELECT 
        e.subject_id,
        e.stay_id,
        e.gender,
        e.race,
        e.intime,
        e.outtime,
        e.disposition,
        EXTRACT(EPOCH FROM (e.outtime - e.intime))/3600 as hours_in_ed
    FROM edstays e
    WHERE e.subject_id = :subject_id
),
triage_data AS (
    SELECT 
        t.temperature,
        t.heartrate,
        t.resprate,
        t.o2sat,
        t.sbp,
        t.dbp,
        t.pain,
        t.acuity,
        t.chiefcomplaint
    FROM triage t
    WHERE t.subject_id = :subject_id
),
diagnoses AS (
    SELECT 
        d.icd_code,
        d.icd_title
    FROM diagnosis d
    WHERE d.subject_id = :subject_id
    ORDER BY d.seq_num
)
SELECT * FROM patient_info, triage_data, diagnoses;
```

### Tendencia de Signos Vitales
```sql
SELECT 
    charttime,
    temperature,
    heartrate,
    resprate,
    o2sat,
    sbp,
    dbp,
    -- Calcular cambios
    temperature - LAG(temperature) OVER (ORDER BY charttime) as temp_change,
    heartrate - LAG(heartrate) OVER (ORDER BY charttime) as hr_change,
    sbp - LAG(sbp) OVER (ORDER BY charttime) as sbp_change
FROM vitalsign
WHERE subject_id = :subject_id
ORDER BY charttime;
```

### Medicamentos Completos
```sql
-- Medicamentos habituales + administrados en urgencias
SELECT 
    'Habitual' as source,
    m.name,
    m.etcdescription as category,
    m.charttime
FROM medrecon m
WHERE m.subject_id = :subject_id

UNION ALL

SELECT 
    'Urgencias' as source,
    p.name,
    NULL as category,
    p.charttime
FROM pyxis p
WHERE p.subject_id = :subject_id

ORDER BY charttime;
```

## Conexión con Supabase

### Arquitectura de Esquemas

Supabase tiene dos esquemas separados:
- **`public`**: Tablas de aplicación (users, chat_sessions, chat_messages, documents)
- **`mimic_ed`**: Tablas MIMIC-IV-ED (edstays, diagnosis, triage, vitalsign, medrecon, pyxis)

### Configuración
```python
from config.settings import settings
from supabase import create_client, Client

# Crear cliente
supabase: Client = create_client(
    settings.database.supabase_url,
    settings.database.supabase_key
)

# Acceder a tablas MIMIC-IV-ED (esquema mimic_ed)
result = supabase.schema('mimic_ed').table('edstays').select('*').execute()

# Acceder a tablas de aplicación (esquema public, por defecto)
result = supabase.table('users').select('*').execute()
```

### Consultas Seguras
```python
def query_patient_data(subject_id: int) -> Dict[str, Any]:
    """
    Consultar datos de paciente de forma segura
    
    Args:
        subject_id: ID del paciente
        
    Returns:
        Dict con datos del paciente
    """
    # Validar input
    if not isinstance(subject_id, int) or subject_id <= 0:
        raise ValueError("subject_id debe ser un entero positivo")
    
    # Ejecutar consulta con parámetros en esquema mimic_ed
    response = supabase.schema('mimic_ed').table('edstays') \
        .select('*') \
        .eq('subject_id', subject_id) \
        .execute()
    
    return response.data
```

### Prevención de SQL Injection
```python
def validate_sql_query(query: str) -> bool:
    """
    Validar que la consulta SQL sea segura
    
    Args:
        query: Consulta SQL a validar
        
    Returns:
        True si es segura, False si no
        
    Raises:
        InvalidQueryError: Si contiene operaciones prohibidas
    """
    # Operaciones prohibidas
    forbidden = [
        "DROP", "DELETE", "UPDATE", "INSERT", 
        "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"
    ]
    
    query_upper = query.upper()
    
    for keyword in forbidden:
        if keyword in query_upper:
            raise InvalidQueryError(
                f"Operación prohibida detectada: {keyword}"
            )
    
    # Solo permitir SELECT
    if not query_upper.strip().startswith("SELECT"):
        raise InvalidQueryError("Solo se permiten consultas SELECT")
    
    return True
```

## Mejores Prácticas

### 1. Siempre Especificar Esquema para MIMIC-IV-ED
```python
# ✅ BIEN - Especifica esquema mimic_ed
result = supabase.schema('mimic_ed').table('vitalsign') \
    .select('*') \
    .eq('subject_id', 10014729) \
    .execute()

# ❌ MAL - No especifica esquema (busca en public)
result = supabase.table('vitalsign') \
    .select('*') \
    .eq('subject_id', 10014729) \
    .execute()
```

### 2. Usar Índices
```python
# ✅ BIEN - Usa índice en subject_id
result = supabase.schema('mimic_ed').table('vitalsign') \
    .select('*') \
    .eq('subject_id', 10014729) \
    .execute()

# ❌ MAL - Filtro que no usa índice
result = supabase.schema('mimic_ed').table('vitalsign') \
    .select('*') \
    .filter('subject_id', 'like', '%729') \
    .execute()
```

### 2. Limitar Resultados
```python
# ✅ BIEN - Limitar filas
result = supabase.schema('mimic_ed').table('vitalsign') \
    .select('*') \
    .eq('subject_id', 10014729) \
    .order('charttime', desc=True) \
    .limit(100) \
    .execute()

# ❌ MAL - Sin límite
result = supabase.schema('mimic_ed').table('vitalsign') \
    .select('*') \
    .eq('subject_id', 10014729) \
    .execute()
```

### 3. Usar Parámetros
```python
# ✅ BIEN - Parámetros seguros con Python Client
result = supabase.schema('mimic_ed').table('edstays') \
    .select('*') \
    .eq('subject_id', subject_id) \
    .execute()

# ❌ MAL - Concatenación de strings (vulnerable a injection)
query = f"SELECT * FROM edstays WHERE subject_id = {subject_id}"
```

### 4. Manejar Errores
```python
try:
    result = supabase.schema('mimic_ed').table('edstays').select('*').execute()
except Exception as e:
    logger.error(f"Error en consulta: {e}")
    return {"error": "No se pudo obtener los datos"}
```

### 5. Usar Connection Pooling
```python
from services.connection_pool_manager import ConnectionPoolManager

# Usar pool de conexiones
pool = ConnectionPoolManager()
with pool.get_connection() as conn:
    result = conn.execute(query)
```

## Valores de Referencia Clínicos

### Signos Vitales Normales
```python
NORMAL_RANGES = {
    'temperature': (96.8, 100.4),  # °F
    'heartrate': (60, 100),         # lpm
    'resprate': (12, 20),           # rpm
    'o2sat': (95, 100),             # %
    'sbp': (90, 140),               # mmHg
    'dbp': (60, 90)                 # mmHg
}
```

### Niveles de Acuidad (Triage)
```python
ACUITY_LEVELS = {
    1: "Resucitación (inmediato)",
    2: "Emergencia (10-15 min)",
    3: "Urgente (30-60 min)",
    4: "Menos urgente (1-2 horas)",
    5: "No urgente (2-4 horas)"
}
```

## Ejemplos de Consultas por Caso de Uso

### Análisis de Paciente Individual
```sql
-- Resumen completo
SELECT 
    e.*,
    t.temperature, t.heartrate, t.sbp, t.dbp, t.acuity,
    d.icd_code, d.icd_title
FROM edstays e
LEFT JOIN triage t ON e.stay_id = t.stay_id
LEFT JOIN diagnosis d ON e.stay_id = d.stay_id
WHERE e.subject_id = :subject_id;
```

### Análisis de Tendencias
```sql
-- Pacientes con hipertensión en triaje
SELECT COUNT(*) as hypertensive_patients
FROM triage
WHERE sbp > 140 OR dbp > 90;
```

### Análisis de Medicamentos
```sql
-- Medicamentos más administrados
SELECT name, COUNT(*) as frequency
FROM pyxis
GROUP BY name
ORDER BY frequency DESC
LIMIT 20;
```

## Referencias

- **Documentación MIMIC-IV-ED**: https://physionet.org/content/mimic-iv-ed/
- **Configuración Supabase**: `docs/CONFIGURACION_SUPABASE_VERIFICADA.md`
- **Código de Database Tool**: `services/unified_chat/tools/database_tool.py`
- **Settings**: `config/settings.py`
