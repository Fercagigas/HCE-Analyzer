# Sistema de Chat Unificado - ChatHCE

## Visión General

El Chat Unificado es la interfaz principal del sistema. Integra automáticamente acceso a base de datos MIMIC-IV-ED, búsqueda de documentos clínicos (RAG), y generación de visualizaciones en una sola conversación.

## Modelo de IA

**Modelo Primario**: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- Actualizado en Noviembre 2025
- Incluye directivas anti-alucinación
- Respuestas siempre fundamentadas en datos reales

## Componentes Principales

### 1. Unified Chat Agent
**Ubicación**: `services/unified_chat/unified_agent.py`
**LLM**: Claude Haiku 4.5 (Anthropic) - claude-haiku-4-5-20251001
**Framework**: LangChain

**Responsabilidades**:
- Analizar intención del usuario
- Seleccionar herramientas apropiadas
- Coordinar ejecución de herramientas
- Sintetizar respuestas integradas
- Mantener contexto conversacional
- **Aplicar directivas anti-alucinación**

### 2. Database Tool
**Ubicación**: `services/unified_chat/tools/database_tool.py`
**Propósito**: Consultas a MIMIC-IV-ED

**Cuándo se usa**:
- Consultas sobre pacientes específicos (subject_id)
- Signos vitales y tendencias
- Diagnósticos con códigos ICD
- Medicamentos administrados
- Datos de triaje y estancias

### 3. RAG Tool
**Ubicación**: `services/unified_chat/tools/rag_tool.py`
**Propósito**: Búsqueda en documentos clínicos

## Sistema Anti-Alucinación

El sistema incluye directivas para prevenir la generación de información falsa:

### Prohibiciones Absolutas
- NUNCA inventar subject_id, stay_id o hadm_id
- NUNCA fabricar valores de signos vitales
- NUNCA inventar diagnósticos o códigos ICD
- NUNCA crear medicamentos o dosis ficticias
- NUNCA generar fechas o timestamps falsos

### Manejo de Datos Faltantes
- Si no encuentra datos: "No encontré información sobre [X] en el dataset"
- Si hay valores nulos: "Algunos registros tienen datos incompletos"
- Si el paciente no existe: "El paciente [ID] no existe en MIMIC-IV-ED"

### Citación de Fuentes
- Siempre indicar qué herramienta se usó para obtener los datos
- Mencionar la tabla de origen (edstays, triage, vitalsign, etc.)
- Para RAG, citar el documento fuente

### Reconocimiento de Incertidumbre
- Distinguir entre datos verificados e interpretaciones
- Usar frases como "Según los datos disponibles..." o "Los registros muestran..."
- Para inferencias, usar "Esto podría indicar..." o "Una posible interpretación es..."

### Limitaciones del Dataset
- MIMIC-IV-ED es un dataset de demostración con 222 pacientes
- Los datos son de urgencias hospitalarias, no de otras áreas
- No hay acceso a información fuera de este dataset

## Configuración del Modelo

**Archivo**: `config/settings.py`
```python
primary_model: str = "claude-haiku-4-5-20251001"
primary_model_version: str = "claude-haiku-4-5-20251001"
```

**Cadena de Fallback**:
1. Claude Haiku 4.5 (primario)
2. Claude Sonnet 4.5 (secundario)
3. Claude Opus 4 (terciario)
