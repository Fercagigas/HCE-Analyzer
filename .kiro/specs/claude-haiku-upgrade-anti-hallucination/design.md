# Design Document - Claude Haiku 4.5 Upgrade with Anti-Hallucination

## Overview

Este documento describe el diseño técnico para actualizar el sistema de Chat Unificado de ChatHCE de Claude Haiku 3.5 a Claude Haiku 4.5, implementando mejoras significativas para minimizar alucinaciones. El modelo será plenamente consciente de su contexto operativo, capacidades y limitaciones.

### Objetivos del Diseño

1. Migrar de `claude-3-5-haiku-latest` a `claude-haiku-4-5-20251001`
2. Implementar system prompt con contexto completo del sistema
3. Añadir directivas anti-alucinación estructuradas
4. Asegurar grounding en datos reales de MIMIC-IV-ED
5. Mantener compatibilidad con la arquitectura existente

### Alcance

**Incluido:**
- Actualización de configuración del modelo en `config/settings.py`
- Mejora del system prompt en `unified_agent.py`
- Actualización del `prompt_manager.py` con directivas anti-alucinación
- Modificación del `llm_manager.py` para el nuevo modelo

**Excluido:**
- Cambios en las herramientas (database_tool, rag_tool, visualization_tool)
- Modificaciones a la interfaz de usuario
- Cambios en la base de datos MIMIC-IV-ED

## Architecture

### Componentes a Modificar

```
config/
├── settings.py                    # MODIFICAR: Actualizar modelo primario

services/unified_chat/
├── unified_agent.py               # MODIFICAR: Mejorar system prompt

services/medical_agent/
├── llm_manager.py                 # MODIFICAR: Configurar nuevo modelo
├── prompt_manager.py              # MODIFICAR: Añadir directivas anti-alucinación
```

### Flujo de Inicialización Actualizado

```
UnifiedChatAgent.__init__()
    ↓
ClaudeLLMManager()
    ├── Cargar configuración de ClaudeAgentSettings
    ├── Validar API key
    └── Configurar modelo: claude-haiku-4-5-20251001
    ↓
PromptManager()
    ├── Cargar system prompt base
    ├── Añadir contexto del sistema (NUEVO)
    ├── Añadir directivas anti-alucinación (NUEVO)
    └── Añadir guías de selección de herramientas
    ↓
create_tool_calling_agent()
    ├── Usar LLM con nuevo modelo
    └── Usar prompt mejorado
```

## Components and Interfaces

### 1. ClaudeAgentSettings (Modificado)

**Ubicación**: `config/settings.py`

**Cambios**:
```python
class ClaudeAgentSettings(BaseSettings):
    # Model Configuration - Primary Model (Claude Haiku 4.5)
    primary_model: str = Field(
        "claude-haiku-4-5-20251001",  # ACTUALIZADO
        alias="PRIMARY_CLAUDE_MODEL"
    )
    primary_model_version: str = Field(
        "claude-haiku-4-5-20251001",  # ACTUALIZADO
        alias="PRIMARY_CLAUDE_MODEL_VERSION"
    )
```

### 2. System Prompt Mejorado (Nuevo)

**Ubicación**: `services/unified_chat/unified_agent.py`

**Estructura del System Prompt**:
```
1. IDENTIDAD DEL SISTEMA
   - Nombre: ChatHCE
   - Propósito: Asistente de Análisis Clínico de Urgencias
   - Especialización: Datos MIMIC-IV-ED

2. CONTEXTO OPERATIVO
   - Dataset: MIMIC-IV-ED (demo)
   - Pacientes: 222 únicos
   - Tablas disponibles: edstays, triage, vitalsign, diagnosis, medrecon, pyxis
   - Idioma: Español con terminología médica

3. HERRAMIENTAS DISPONIBLES
   - query_mimic_database: Consultas SQL a MIMIC-IV-ED
   - search_clinical_documents: Búsqueda RAG en documentos clínicos
   - request_visualization: Generación de gráficas médicas

4. DIRECTIVAS ANTI-ALUCINACIÓN
   - Prohibiciones explícitas
   - Manejo de datos faltantes
   - Citación de fuentes
   - Reconocimiento de incertidumbre

5. GUÍAS DE SELECCIÓN DE HERRAMIENTAS
   - Cuándo usar cada herramienta
   - Uso combinado de herramientas
```

### 3. Directivas Anti-Alucinación (Nuevo)

**Ubicación**: `services/medical_agent/prompt_manager.py`

**Interfaz**:
```python
class PromptManager:
    def get_anti_hallucination_directives(self) -> str:
        """
        Obtener directivas anti-alucinación estructuradas.
        
        Returns:
            String con directivas formateadas para el system prompt
        """
        pass
    
    def get_system_context(self) -> str:
        """
        Obtener contexto del sistema para el model.
        
        Returns:
            String con información del sistema y dataset
        """
        pass
```

**Contenido de las Directivas**:
```markdown
# DIRECTIVAS ANTI-ALUCINACIÓN

## PROHIBICIONES ABSOLUTAS
- NUNCA inventes subject_id, stay_id o hadm_id
- NUNCA fabriques valores de signos vitales
- NUNCA inventes diagnósticos o códigos ICD
- NUNCA crees medicamentos o dosis ficticias
- NUNCA generes fechas o timestamps falsos

## MANEJO DE DATOS FALTANTES
- Si no encuentras datos, di: "No encontré información sobre [X] en el dataset"
- Si hay valores nulos, menciona: "Algunos registros tienen datos incompletos"
- Si el paciente no existe, indica: "El paciente [ID] no existe en MIMIC-IV-ED"

## CITACIÓN DE FUENTES
- Siempre indica qué herramienta usaste para obtener los datos
- Menciona la tabla de origen (edstays, triage, vitalsign, etc.)
- Para RAG, cita el documento fuente

## RECONOCIMIENTO DE INCERTIDUMBRE
- Distingue entre datos verificados e interpretaciones
- Usa frases como "Según los datos disponibles..." o "Los registros muestran..."
- Para inferencias, usa "Esto podría indicar..." o "Una posible interpretación es..."

## LIMITACIONES DEL DATASET
- MIMIC-IV-ED es un dataset de demostración con 222 pacientes
- Los datos son de urgencias hospitalarias, no de otras áreas
- No tengo acceso a información fuera de este dataset
```

### 4. ClaudeLLMManager (Modificado)

**Ubicación**: `services/medical_agent/llm_manager.py`

**Cambios en _get_model_chain()**:
```python
def _get_model_chain(self) -> List[Dict[str, Any]]:
    return [
        {
            'name': 'claude-haiku-4-5-20251001',  # ACTUALIZADO
            'version': 'claude-haiku-4-5-20251001',
            'max_tokens': base_max_tokens,
            'temperature': settings.claude_agent.temperature,
            'timeout': settings.claude_agent.timeout_seconds
        },
        # ... modelos de fallback sin cambios
    ]
```

## Data Models

### SystemPromptConfig
```python
@dataclass
class SystemPromptConfig:
    """Configuración del system prompt."""
    identity: str
    context: str
    tools_description: str
    anti_hallucination: str
    tool_guidelines: str
    
    def to_prompt(self) -> str:
        """Generar system prompt completo."""
        return f"""
{self.identity}

{self.context}

{self.tools_description}

{self.anti_hallucination}

{self.tool_guidelines}
"""
```

### AntiHallucinationDirectives
```python
@dataclass
class AntiHallucinationDirectives:
    """Directivas anti-alucinación estructuradas."""
    prohibitions: List[str]
    missing_data_handling: List[str]
    source_citation: List[str]
    uncertainty_acknowledgment: List[str]
    dataset_limitations: List[str]
```

## Correctness Properties

### Property 1: Modelo Correcto
**Validates: Requirement 1**
- GIVEN el sistema inicializa
- WHEN ClaudeLLMManager crea una instancia de LLM
- THEN el modelo usado debe ser "claude-haiku-4-5-20251001"

### Property 2: Identidad del Sistema
**Validates: Requirement 2**
- GIVEN el system prompt se genera
- WHEN se incluye la sección de identidad
- THEN debe contener "ChatHCE" y "Asistente de Análisis Clínico de Urgencias"

### Property 3: Contexto del Dataset
**Validates: Requirement 2**
- GIVEN el system prompt se genera
- WHEN se incluye el contexto operativo
- THEN debe mencionar MIMIC-IV-ED, 222 pacientes, y las tablas disponibles

### Property 4: Directivas Anti-Alucinación Presentes
**Validates: Requirement 3, 5**
- GIVEN el system prompt se genera
- WHEN se incluyen las directivas anti-alucinación
- THEN debe contener prohibiciones explícitas contra inventar datos

### Property 5: Manejo de Datos Faltantes
**Validates: Requirement 4**
- GIVEN el modelo recibe una consulta sobre datos inexistentes
- WHEN genera una respuesta
- THEN debe indicar explícitamente que los datos no están disponibles

### Property 6: Citación de Fuentes
**Validates: Requirement 3**
- GIVEN el modelo usa una herramienta para obtener datos
- WHEN genera la respuesta
- THEN debe mencionar qué herramienta y tabla usó

### Property 7: Reconocimiento de Incertidumbre
**Validates: Requirement 4**
- GIVEN el modelo hace una interpretación
- WHEN genera la respuesta
- THEN debe distinguir entre datos verificados e interpretaciones

## Error Handling

### Errores de Modelo
```python
try:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", ...)
except AuthenticationError:
    raise AuthError("ANTHROPIC_API_KEY inválida")
except Exception as e:
    # Intentar fallback a modelo secundario
    self.switch_to_fallback()
```

### Errores de Datos
- Si la consulta no retorna datos: Responder con mensaje claro
- Si hay error de conexión: Informar al usuario y sugerir reintentar
- Si el paciente no existe: Indicar explícitamente

## Testing Strategy

### Unit Tests
1. `test_model_version_correct`: Verificar que se usa claude-haiku-4-5-20251001
2. `test_system_prompt_contains_identity`: Verificar identidad del sistema
3. `test_system_prompt_contains_context`: Verificar contexto operativo
4. `test_anti_hallucination_directives_present`: Verificar directivas
5. `test_fallback_chain_maintained`: Verificar cadena de fallback

### Integration Tests
1. `test_agent_responds_with_grounded_data`: Verificar respuestas basadas en datos
2. `test_agent_handles_missing_data`: Verificar manejo de datos faltantes
3. `test_agent_cites_sources`: Verificar citación de fuentes
4. `test_agent_acknowledges_uncertainty`: Verificar reconocimiento de incertidumbre

## Configuration

### Variables de Entorno
```bash
# Modelo primario actualizado
PRIMARY_CLAUDE_MODEL=claude-haiku-4-5-20251001
PRIMARY_CLAUDE_MODEL_VERSION=claude-haiku-4-5-20251001

# Configuración existente (sin cambios)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MAX_TOKENS=4096
CLAUDE_TEMPERATURE=0.1
CLAUDE_TIMEOUT_SECONDS=30
```

### Configuración del System Prompt
```python
SYSTEM_PROMPT_CONFIG = {
    "include_identity": True,
    "include_context": True,
    "include_anti_hallucination": True,
    "include_tool_guidelines": True,
    "language": "es",
    "dataset_name": "MIMIC-IV-ED",
    "patient_count": 222
}
```

## Migration Strategy

### Fase 1: Actualización del Modelo
1. Actualizar `settings.py` con nuevo modelo
2. Verificar que el modelo funciona correctamente
3. Ejecutar tests de regresión

### Fase 2: Mejora del System Prompt
1. Añadir sección de identidad
2. Añadir contexto operativo
3. Añadir directivas anti-alucinación
4. Verificar que las respuestas mejoran

### Fase 3: Validación
1. Ejecutar tests de integración
2. Probar con consultas reales
3. Verificar que no hay alucinaciones

## Performance Considerations

- El nuevo modelo (Haiku 4.5) tiene rendimiento similar a Haiku 3.5
- El system prompt más largo aumenta tokens de entrada (~500 tokens adicionales)
- El tiempo de respuesta no debería verse afectado significativamente
- Se mantiene el cache de respuestas para optimizar

## Security Considerations

- Las directivas anti-alucinación no exponen información sensible
- El contexto del dataset es información pública (MIMIC-IV-ED es público)
- Se mantienen las validaciones de SQL injection existentes

## References

- **Anthropic Claude Models**: https://docs.anthropic.com/claude/docs/models-overview
- **MIMIC-IV-ED Documentation**: https://physionet.org/content/mimic-iv-ed/
- **Código actual**: `services/unified_chat/unified_agent.py`
- **Configuración**: `config/settings.py`
