# Guía de Prompt Engineering - ChatHCE

**Última actualización**: Febrero 2026
**Versión**: 3.0

## Resumen

Esta guía documenta las estrategias de prompt engineering implementadas en el sistema ChatHCE. El agente unificado usa Claude Haiku 4.5 (Anthropic) con LangChain y un system prompt estructurado que integra identidad, herramientas, directivas anti-alucinación y guías de selección.

## Arquitectura del Sistema de Prompts

### Componentes

| Componente | Ubicación | Responsabilidad |
|-----------|-----------|-----------------|
| PromptManager | `services/medical_agent/prompt_manager.py` | Genera el system prompt completo con todas las secciones |
| UnifiedChatAgent | `services/unified_chat/unified_agent.py` | Usa el prompt para crear el AgentExecutor de LangChain |
| ClaudeToolAdapter | `services/medical_agent/tools/claude_adapter.py` | Define descripciones de herramientas para el agente |

### Estructura del System Prompt

El system prompt se construye en `PromptManager.get_system_prompt()` con las siguientes secciones en orden:

```
1. IDENTIDAD DEL SISTEMA
   - Nombre: ChatHCE - Asistente de Análisis Clínico de Urgencias
   - Propósito y capacidades

2. CONTEXTO OPERATIVO
   - Dataset MIMIC-IV-ED (222 pacientes, 6 tablas)
   - Esquema mimic_ed en Supabase

3. HERRAMIENTAS DISPONIBLES
   - query_mimic_database: consultas a MIMIC-IV-ED
   - search_clinical_documents: búsqueda RAG en documentos
   - request_visualization: generación de gráficas

4. DIRECTIVAS ANTI-ALUCINACIÓN
   - Prohibiciones absolutas
   - Manejo de datos faltantes
   - Citación de fuentes
   - Reconocimiento de incertidumbre

5. IDIOMA Y TERMINOLOGÍA
   - Respuestas en español
   - Terminología médica apropiada

6. BASE DE DATOS MIMIC-IV-ED
   - Esquema completo de tablas
   - Columnas y tipos de datos
   - Reglas SQL (solo SELECT, sin punto y coma)

7. FORMATO DE RESPUESTA
   - Estructura obligatoria
   - Uso de emojis médicos
   - Citación de fuentes

8. GUÍAS CLÍNICAS
   - Valores de referencia de signos vitales
   - Niveles de acuidad

9. GUÍAS DE SELECCIÓN DE HERRAMIENTAS
   - Cuándo usar cada herramienta
   - Combinaciones de herramientas

10. MEMORIA CONVERSACIONAL
    - Uso de datos previos en contexto
    - Cuándo re-ejecutar herramientas
```

## Directivas Anti-Alucinación

### Prohibiciones Absolutas

```
- NUNCA inventes subject_id, stay_id o hadm_id
- NUNCA fabriques valores de signos vitales
- NUNCA inventes diagnósticos o códigos ICD
- NUNCA crees medicamentos o dosis ficticias
- NUNCA generes fechas o timestamps falsos
```

### Manejo de Datos Faltantes

```
- Si no encuentra datos: "No encontré información sobre [X] en el dataset"
- Si hay valores nulos: "Algunos registros tienen datos incompletos"
- Si el paciente no existe: "El paciente [ID] no existe en MIMIC-IV-ED"
```

### Citación de Fuentes

```
- Siempre indicar qué herramienta se usó
- Mencionar la tabla de origen (edstays, triage, vitalsign, etc.)
- Para RAG, citar el documento fuente
```

### Reconocimiento de Incertidumbre

```
- Datos verificados: "Según los datos disponibles..."
- Observaciones directas: "Los registros muestran..."
- Interpretaciones: "Esto podría indicar..."
- Inferencias: "Una posible interpretación es..."
```

## Descripciones de Herramientas

Las descripciones de herramientas son críticas para la selección automática. Cada herramienta define su descripción en el constructor de `ClaudeToolAdapter`:

### query_mimic_database (DatabaseTool)

```
Ubicación: services/unified_chat/tools/database_tool.py

Tipos de consulta:
1. patient_summary - Resumen completo del paciente
   Requerido: subject_id
2. vital_signs - Signos vitales de una estancia
   Requerido: stay_id
3. diagnoses - Búsqueda de diagnósticos
   Requerido: icd_code O icd_title
4. medications - Historial de medicamentos
   Requerido: subject_id
5. custom - Consulta SQL personalizada (validada)
   Requerido: custom_query
```

### search_clinical_documents (RAGTool)

```
Ubicación: services/unified_chat/tools/rag_tool.py

Parámetros:
- query (requerido): Pregunta o búsqueda
- specialty (opcional): Filtrar por especialidad
- top_k (opcional): Número de documentos (default: 5)

Pipeline:
1. Query augmentation con Claude Haiku (multi-query + HyDE)
2. Búsqueda híbrida (pgvector + tsvector) por cada query aumentada
3. Merge y deduplicación de resultados
4. Retornar top_k mejores resultados
```

### request_visualization (VisualizationCollaborationTool)

```
Ubicación: services/medical_agent/tools/visualization_collaboration_tool.py

Parámetros:
- subject_id (requerido): ID del paciente
- metrics (opcional): Lista de métricas a visualizar
- visualization_type (opcional): Tipo de gráfica

Flujo:
1. Obtiene datos del paciente via DatabaseService
2. VisualizationSelector decide el tipo de gráfica
3. VisualizationTemplates genera el código
4. CodeExecutor ejecuta en sandbox
5. Retorna imagen base64
```

## Estrategias de Prompt Engineering

### 1. Chain of Thought

El system prompt guía al agente a través de un proceso de razonamiento:

```
1. Analizar la consulta del usuario
2. Identificar datos necesarios
3. Seleccionar herramientas apropiadas
4. Ejecutar herramientas
5. Interpretar resultados clínicamente
6. Sintetizar respuesta en español
```

### 2. Few-Shot Learning

Las descripciones de herramientas incluyen ejemplos concretos:

```
Ejemplo: {"query_type": "patient_summary", "subject_id": 10014729}
Ejemplo: {"query": "protocolo para hipertensión arterial"}
```

### 3. Role Prompting

Identidad clara del agente:

```
Eres ChatHCE, un asistente de análisis clínico de urgencias
especializado en datos del dataset MIMIC-IV-ED.
```

### 4. Structured Output

Formato obligatorio de respuesta:

```
1. Resumen Ejecutivo (2-3 líneas)
2. Datos Clínicos Detallados
3. Interpretación Clínica
4. Hallazgos Destacados
5. Visualizaciones (si aplica)
6. Fuentes utilizadas
```

### 5. Constraint Specification

Restricciones explícitas:

```
✓ Responde SIEMPRE en español
✓ Usa terminología médica apropiada
✓ Cita valores con unidades
✓ Destaca valores críticos con ⚠️
✓ NUNCA inventes datos
```

### 6. Memory Context Injection

El historial de conversación se enriquece con datos de herramientas previas:

```
[CONTEXTO DE DATOS - Disponible para referencia]
[DATOS: query_mimic_database]
Tipo: vital_signs
Paciente: 10014729
Signos vitales: T=98.6°F, HR=75, BP=120/80, O2=98%
```

## Configuración

### Variables de Entorno

```bash
# Modelo primario
PRIMARY_CLAUDE_MODEL=claude-haiku-4-5-20251001

# Parámetros del LLM
CLAUDE_MAX_TOKENS=4096
CLAUDE_TEMPERATURE=0.1
CLAUDE_TIMEOUT_SECONDS=30

# Configuración del agente
CLAUDE_MAX_ITERATIONS=15
CLAUDE_VERBOSE=True
```

### Archivos de Configuración

```
config/settings.py          → ClaudeAgentSettings (modelos, tokens, temperatura)
services/unified_chat/config.py → UnifiedChatSettings (contexto, caché, herramientas)
```

## Optimización de Tokens

### Estrategia

- System prompt: ~3000 tokens (optimizado vs ~6500 con otros modelos)
- Contexto conversacional: máximo 10 mensajes
- Tool results en memoria: últimos 5 resultados
- Mensajes recientes: datos completos + resumen
- Mensajes antiguos: solo resumen estructurado

### Límites de Claude Haiku 4.5

- Ventana de contexto: 200K tokens
- Max output: 4096 tokens (configurable)
- Margen amplio para conversaciones largas

## Mejores Prácticas

### Para Desarrolladores

1. Mantener consistencia en el formato del system prompt
2. Incluir ejemplos concretos en descripciones de herramientas
3. Usar secciones marcadas con `##` para estructura clara
4. Validar cambios con casos de prueba reales
5. Monitorear métricas de selección de herramientas

### Para Usuarios

1. Ser específico: "Paciente 10014729" mejor que "un paciente"
2. Usar IDs cuando estén disponibles
3. Usar terminología médica estándar
4. Una pregunta a la vez para mejores resultados
5. Aprovechar preguntas de seguimiento (el sistema mantiene contexto)

## Troubleshooting

### El agente no usa la herramienta correcta

- Verificar que la descripción del tool sea clara y específica
- Añadir más ejemplos en la descripción
- Revisar las guías de selección en el system prompt

### Respuestas en inglés en lugar de español

- Verificar sección "IDIOMA Y TERMINOLOGÍA" en el system prompt
- Confirmar `UNIFIED_CHAT_RESPONSE_LANGUAGE=es`

### Respuestas sin estructura

- Verificar sección "FORMATO DE RESPUESTA" en el system prompt
- Confirmar que el PromptManager genera todas las secciones

### El agente re-ejecuta herramientas innecesariamente

- Verificar sección "MEMORIA CONVERSACIONAL" en el system prompt
- Confirmar que `_prepare_chat_history()` enriquece mensajes con contexto

## Referencias

- **System prompt**: `services/medical_agent/prompt_manager.py`
- **Agente unificado**: `services/unified_chat/unified_agent.py`
- **Herramientas**: `services/unified_chat/tools/`
- **Configuración**: `config/settings.py`
- **Memoria conversacional**: `docs/CONVERSATION_MEMORY_IMPLEMENTATION.md`
