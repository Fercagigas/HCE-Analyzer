# Implementación de Memoria Conversacional en ChatHCE

**Fecha**: 2 de Diciembre, 2025  
**Versión**: 2.1.0  
**Estado**: ✅ Implementado y Probado

## Resumen Ejecutivo

Se ha implementado un sistema de memoria conversacional que permite al agente Claude Haiku 4.5 referenciar datos de consultas previas sin necesidad de re-ejecutar herramientas. Esto mejora significativamente la experiencia conversacional y la eficiencia del sistema.

## Problema Identificado

### Antes de la Implementación

El sistema tenía una limitación crítica en la gestión de memoria conversacional:

1. **Usuario**: "Muestra datos del paciente 10014729"
2. **Agente**: Ejecuta `query_mimic_database` → Obtiene datos completos → Responde con resumen
3. **Sistema**: Guarda solo el texto de la respuesta en `st.session_state.unified_messages`
4. **Usuario**: "¿Cuál era su presión arterial?"
5. **Agente**: NO tiene acceso a los datos originales → **Re-ejecuta la consulta**

**Consecuencias**:
- Consultas redundantes a la base de datos
- Mayor latencia en respuestas
- Experiencia conversacional pobre
- Desperdicio de recursos

## Solución Implementada

### Arquitectura de la Solución

```
┌─────────────────────────────────────────────────────────────┐
│  Usuario: "Muestra datos del paciente 10014729"             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  UnifiedChatAgent.process_message()                         │
│  - Ejecuta query_mimic_database                             │
│  - Obtiene datos completos                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  _format_response()                                          │
│  - Extrae tool_results de intermediate_steps                │
│  - Crea resumen estructurado de datos                       │
│  - Guarda datos completos en metadata                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Respuesta Estructurada:                                     │
│  {                                                           │
│    'content': 'Texto visible al usuario',                   │
│    'tool_results': [                                         │
│      {                                                       │
│        'tool': 'query_mimic_database',                      │
│        'summary': '[DATOS: ...]\nPaciente: 10014729...',   │
│        'raw_output': {...datos completos...}                │
│      }                                                       │
│    ]                                                         │
│  }                                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  st.session_state.unified_messages.append()                 │
│  - Guarda objeto completo (no solo texto)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Usuario: "¿Cuál era su presión arterial?"                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  _get_conversation_context()                                 │
│  - Recupera últimos 10 mensajes                             │
│  - Preserva tool_results en mensajes de assistant          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  _prepare_chat_history()                                     │
│  - Enriquece AIMessages con contexto de datos              │
│  - Agrega sección [CONTEXTO DE DATOS]                      │
│  - Incluye resúmenes de tool_results previos               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Claude Haiku 4.5 recibe:                                    │
│  - Pregunta actual                                           │
│  - Historial con datos previos disponibles                  │
│  - Directivas para usar contexto                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Respuesta: "Según los datos consultados anteriormente,     │
│  el paciente 10014729 tiene presión arterial de 120/80"     │
│  ✅ SIN re-ejecutar query_mimic_database                    │
└─────────────────────────────────────────────────────────────┘
```

## Cambios Implementados

### 1. `services/unified_chat/unified_agent.py`

#### Nuevos Métodos

**`_extract_tool_result()`**
- Extrae datos estructurados de tool executions
- Crea resúmenes concisos de los datos
- Preserva datos completos para referencia

**`_create_database_summary()`**
- Genera resúmenes estructurados de consultas a BD
- Extrae signos vitales, diagnósticos, medicamentos
- Formato: `[DATOS: query_mimic_database]\nPaciente: X\nSignos vitales: ...`

**`_create_rag_summary()`**
- Genera resúmenes de búsquedas RAG
- Incluye query y número de documentos encontrados
- Formato: `[DATOS: search_clinical_documents]\nBúsqueda: '...'\nDocumentos: X`

**`_enrich_message_with_context()`**
- Enriquece contenido de AIMessage con datos previos
- Agrega sección `[CONTEXTO DE DATOS - Disponible para referencia]`
- Incluye resúmenes estructurados de tool_results

#### Métodos Modificados

**`_format_response()`**
- Ahora extrae y estructura `tool_results` de intermediate_steps
- Incluye campo `tool_results` en la respuesta
- Preserva datos completos para contexto futuro

**`_prepare_chat_history()`**
- Detecta mensajes con `tool_results`
- Enriquece AIMessages con contexto de datos
- Mantiene últimos 5 tool_results en memoria
- Diferencia entre mensajes recientes (más detalle) y antiguos (solo resumen)

### 2. `ui/unified_chat_interface.py`

#### Métodos Modificados

**`_get_conversation_context()`**
- Preserva estructura completa de mensajes de assistant
- Mantiene `tool_results` en el contexto
- Extrae solo texto para mensajes de usuario

**Nota**: Los métodos `_render_assistant_message()` y guardado en `st.session_state` ya manejaban correctamente objetos dict, por lo que no requirieron cambios.

### 3. `services/medical_agent/prompt_manager.py`

#### Nueva Sección en System Prompt

**`🧠 MEMORIA CONVERSACIONAL Y CONTEXTO DE DATOS`**

Directivas agregadas:
- Cómo identificar datos previos en el contexto
- Cuándo usar datos del contexto vs re-ejecutar herramientas
- Formato de referencia a datos previos
- Ejemplos de uso correcto
- Ventajas de usar el contexto

**Contenido clave**:
```
## 🧠 MEMORIA CONVERSACIONAL Y CONTEXTO DE DATOS

### Uso de Datos Previos en la Conversación
- En el historial encontrarás secciones marcadas como **[CONTEXTO DE DATOS - Disponible para referencia]**
- Estos bloques contienen **resúmenes de datos obtenidos en consultas anteriores**
- **PUEDES y DEBES** referenciar estos datos para responder preguntas de seguimiento
- **NO necesitas re-ejecutar herramientas** si los datos ya están disponibles

### Cuándo Usar Datos del Contexto
- Si el usuario pregunta sobre datos que ya consultaste
- Si necesitas comparar con información previa
- Si el usuario hace preguntas de seguimiento sobre el mismo paciente
- Si los datos en el contexto son suficientes para responder

### Cuándo Re-ejecutar Herramientas
- Si el usuario solicita datos de un **nuevo paciente**
- Si necesitas información **más detallada** que no está en el resumen
- Si el usuario solicita explícitamente **datos actualizados**
- Si los datos del contexto son **incompletos**
```

## Estructura de Datos

### Formato de tool_results

```python
{
    'tool': 'query_mimic_database',
    'timestamp': '2025-12-02T12:00:00',
    'input': {
        'subject_id': 10014729,
        'query_type': 'vital_signs'
    },
    'raw_output': {
        'temperature': 98.6,
        'heartrate': 75,
        'sbp': 120,
        'dbp': 80,
        'o2sat': 98
    },
    'summary': '''[DATOS: query_mimic_database]
Tipo: vital_signs
Paciente: 10014729
Signos vitales: T=98.6°F, HR=75, BP=120/80, O2=98%'''
}
```

### Formato de Mensaje Enriquecido

```python
AIMessage(content='''
El paciente 10014729 tiene signos vitales normales.

---
[CONTEXTO DE DATOS - Disponible para referencia]

[DATOS: query_mimic_database]
Tipo: vital_signs
Paciente: 10014729
Signos vitales: T=98.6°F, HR=75, BP=120/80, O2=98%
Datos completos disponibles: ['temperature', 'heartrate', 'sbp', 'dbp', 'o2sat']
---
''')
```

## Gestión de Tokens

### Estrategia de Limitación

1. **Límite de mensajes**: Máximo 10 mensajes en contexto (configurable)
2. **Límite de tool_results**: Últimos 5 tool_results preservados
3. **Diferenciación por antigüedad**:
   - Últimos 3 mensajes: Datos completos + resumen
   - Mensajes 4-10: Solo resumen estructurado

### Estimación de Tokens

- Resumen de database query: ~50-100 tokens
- Resumen de RAG search: ~30-50 tokens
- Contexto completo (10 mensajes): ~2000-3000 tokens
- Límite de Claude Haiku 4.5: 200K tokens (amplio margen)

## Tests Implementados

### `tests/test_conversation_memory.py`

**Test 1: `test_database_summary_creation`**
- Verifica creación de resúmenes de consultas BD
- Valida inclusión de signos vitales
- Confirma formato estructurado

**Test 2: `test_enrich_message_with_context`**
- Verifica enriquecimiento de mensajes
- Valida inclusión de sección de contexto
- Confirma preservación de contenido original

**Test 3: `test_rag_summary_creation`**
- Verifica creación de resúmenes RAG
- Valida inclusión de query
- Confirma formato estructurado

**Resultado**: ✅ 3/3 tests pasando

## Beneficios

### Para el Usuario

1. **Conversaciones más naturales**: Puede hacer preguntas de seguimiento sin repetir contexto
2. **Respuestas más rápidas**: No hay espera de re-consultas innecesarias
3. **Consistencia**: Los datos referenciados son exactamente los mismos consultados antes

### Para el Sistema

1. **Eficiencia**: Reduce consultas redundantes a Supabase
2. **Escalabilidad**: Menor carga en la base de datos
3. **Costo**: Menos llamadas a APIs externas
4. **Performance**: Respuestas más rápidas (sin latencia de BD)

### Para el LLM

1. **Contexto rico**: Acceso a datos estructurados previos
2. **Mejor razonamiento**: Puede comparar y analizar datos históricos
3. **Coherencia**: Mantiene consistencia en análisis multi-turno

## Ejemplos de Uso

### Ejemplo 1: Consulta de Seguimiento Simple

```
👤 Usuario: "Muestra datos del paciente 10014729"

🤖 Asistente: [Ejecuta query_mimic_database]
"El paciente 10014729 es un varón que llegó a urgencias con los siguientes signos vitales:
- Temperatura: 98.6°F
- Frecuencia cardíaca: 75 lpm
- Presión arterial: 120/80 mmHg
- Saturación O2: 98%"

[Guarda tool_results con datos completos]

👤 Usuario: "¿Cuál era su presión arterial?"

🤖 Asistente: [NO re-ejecuta query, usa contexto]
"Según los datos consultados anteriormente, el paciente 10014729 tiene presión arterial de 120/80 mmHg (sistólica/diastólica)."
```

### Ejemplo 2: Análisis Comparativo

```
👤 Usuario: "Muestra signos vitales del paciente 10014729"

🤖 Asistente: [Ejecuta query_mimic_database]
"Signos vitales del paciente 10014729:
- Temperatura: 98.6°F
- Frecuencia cardíaca: 75 lpm
- Presión arterial: 120/80 mmHg"

👤 Usuario: "¿Están dentro de rangos normales?"

🤖 Asistente: [Usa contexto + conocimiento clínico]
"Sí, según los datos consultados anteriormente:
- Temperatura 98.6°F: Normal (rango 96.8-100.4°F)
- Frecuencia cardíaca 75 lpm: Normal (rango 60-100 lpm)
- Presión arterial 120/80: Normal (rango 90-140/60-90 mmHg)"
```

### Ejemplo 3: Múltiples Herramientas

```
👤 Usuario: "Analiza al paciente 10014729 según protocolos"

🤖 Asistente: [Ejecuta query_mimic_database + search_clinical_documents]
"Datos del paciente: T=98.6°F, HR=75, BP=120/80
Según el Protocolo de Triaje: Nivel de urgencia 3 (urgente, 30-60 min)"

[Guarda tool_results de ambas herramientas]

👤 Usuario: "¿Qué dice el protocolo sobre su presión?"

🤖 Asistente: [Usa contexto de ambas herramientas]
"Según el Protocolo de Triaje consultado anteriormente, la presión arterial de 120/80 mmHg del paciente 10014729 está dentro de rangos normales y no requiere intervención inmediata."
```

## Configuración

### Variables de Configuración

**En `ui/unified_chat_interface.py`**:
```python
st.session_state.unified_config = {
    'max_context_messages': 10,  # Máximo de mensajes en contexto
    # ... otras configuraciones
}
```

**En `unified_agent.py`**:
```python
# Límite de tool_results en memoria
recent_tool_results = recent_tool_results[-5:]  # Últimos 5
```

### Ajustes Recomendados

- **Conversaciones cortas**: `max_context_messages = 5`
- **Conversaciones normales**: `max_context_messages = 10` (default)
- **Análisis complejos**: `max_context_messages = 15`

## Limitaciones Conocidas

1. **Datos muy grandes**: Tablas con >1000 filas se truncan en el resumen
2. **Contexto antiguo**: Mensajes >10 turnos atrás se pierden
3. **Datos complejos**: Estructuras muy anidadas se simplifican en resúmenes
4. **Visualizaciones**: No se preservan datos de imagen, solo metadata

## Trabajo Futuro

### Mejoras Potenciales

1. **Compresión inteligente**: Usar LLM para comprimir datos antiguos
2. **Índice semántico**: Buscar datos relevantes en todo el historial
3. **Persistencia**: Guardar tool_results en base de datos
4. **Priorización**: Mantener datos más relevantes, no solo más recientes
5. **Agregación**: Combinar múltiples consultas del mismo paciente

### Integración con LangGraph

Si se migra a LangGraph en el futuro:
- Usar `InMemoryStore` para long-term memory
- Implementar `ToolRuntime` con estado personalizado
- Usar `Command` objects para actualizar estado
- Implementar middleware para gestión automática de memoria

## Conclusión

La implementación de memoria conversacional mejora significativamente la experiencia del usuario y la eficiencia del sistema. El agente ahora puede mantener conversaciones más naturales y coherentes, referenciando datos previos sin necesidad de re-ejecutar consultas costosas.

**Estado**: ✅ Producción  
**Tests**: ✅ 3/3 pasando  
**Documentación**: ✅ Completa  
**Compatibilidad**: ✅ Claude Haiku 4.5

---

**Fecha**: 2 de Diciembre, 2025  
**Versión del documento**: 1.0
