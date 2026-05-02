# Design Document (Continued) - Visualization System Improvement

## Correctness Properties

Ver archivo `correctness-properties.md` para la lista completa de propiedades de corrección, edge cases y examples.

## Error Handling

### Error Categories

1. **Data Errors**
   - DataFrame vacío
   - Métricas solicitadas no disponibles
   - Todas las métricas con >50% nulos
   - Tipos de datos incorrectos

2. **Generation Errors**
   - LLM no responde
   - Código generado inválido
   - Timeout en generación
   - Rate limit alcanzado

3. **Execution Errors**
   - Errores de sintaxis en código
   - Errores de runtime
   - Columnas inexistentes
   - Métodos de Plotly inválidos

4. **Integration Errors**
   - Fallo en comunicación con chat unificado
   - Fallo en conversión de figura a imagen
   - Timeout en herramienta de visualización

### Error Handling Strategy

```python
class VisualizationErrorHandler:
    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        retry_count: int
    ) -> ErrorHandlingDecision:
        """
        Decidir cómo manejar un error basado en tipo y contexto.
        
        Returns:
            ErrorHandlingDecision con acción a tomar
        """
        if isinstance(error, DataError):
            return self._handle_data_error(error, context)
        elif isinstance(error, GenerationError):
            return self._handle_generation_error(error, context, retry_count)
        elif isinstance(error, ExecutionError):
            return self._handle_execution_error(error, context, retry_count)
        else:
            return self._handle_unknown_error(error, context)
```

### Retry Logic

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0
    use_simplified_prompt_on_retry: bool = True
    use_template_fallback: bool = True

def generate_with_retry(
    self,
    data: pd.DataFrame,
    visualization_type: str,
    config: RetryConfig
) -> VisualizationResult:
    """
    Generar visualización con lógica de reintentos.
    
    Estrategia:
    1. Intento 1: Prompt completo con Claude Sonnet 4.5
    2. Intento 2: Prompt simplificado
    3. Intento 3: Prompt mínimo
    4. Fallback: Plantilla predefinida
    """
    pass
```

## Testing Strategy

### Unit Tests

**DataPreprocessor Tests**:
```python
def test_preprocess_temporal_data_orders_by_time():
    """Verificar que datos se ordenan cronológicamente."""
    pass

def test_preprocess_removes_duplicate_timestamps():
    """Verificar que se eliminan timestamps duplicados."""
    pass

def test_preprocess_converts_string_to_datetime():
    """Verificar conversión de string a datetime."""
    pass

def test_detect_outliers_marks_but_not_removes():
    """Verificar que outliers se marcan pero no se eliminan."""
    pass

def test_validate_metrics_excludes_high_null_percentage():
    """Verificar que métricas con >50% nulos se excluyen."""
    pass
```

**VisualizationTemplates Tests**:
```python
def test_get_template_returns_code_for_common_types():
    """Verificar que existen plantillas para tipos comunes."""
    pass

def test_customize_template_replaces_placeholders():
    """Verificar que personalización reemplaza placeholders."""
    pass

def test_validate_template_works_with_multiple_datasets():
    """Verificar que plantilla funciona con diferentes datos."""
    pass
```

**ImprovedCodeValidator Tests**:
```python
def test_validator_checks_fig_variable_exists():
    """Verificar que se detecta ausencia de variable 'fig'."""
    pass

def test_validator_detects_invalid_columns():
    """Verificar que se detectan columnas inexistentes."""
    pass

def test_validator_checks_plotly_methods():
    """Verificar que se validan métodos de Plotly."""
    pass
```

### Integration Tests

**End-to-End Visualization Generation**:
```python
def test_e2e_timeline_visualization():
    """Test completo de generación de timeline."""
    # 1. Crear datos de prueba
    # 2. Llamar a VisualizationAgent
    # 3. Verificar que se genera figura válida
    # 4. Verificar metadata correcta
    pass

def test_e2e_with_preprocessing():
    """Test que incluye preprocesamiento."""
    # 1. Crear datos desordenados con duplicados
    # 2. Generar visualización
    # 3. Verificar que datos fueron preprocesados
    pass

def test_e2e_with_retry_and_fallback():
    """Test de reintentos y fallback."""
    # 1. Simular fallos en generación
    # 2. Verificar que se reintenta
    # 3. Verificar que se usa fallback
    pass
```

**Chat Unificado Integration**:
```python
def test_chat_invokes_visualization_for_temporal_queries():
    """Verificar que chat detecta consultas temporales."""
    pass

def test_chat_includes_visualization_in_response():
    """Verificar que visualización se incluye en respuesta."""
    pass

def test_chat_continues_on_visualization_failure():
    """Verificar manejo graceful de errores."""
    pass
```

## Configuration

### Claude Sonnet 4.5 Configuration

**Archivo**: `config/settings.py`

```python
class VisualizationAgentSettings(BaseSettings):
    """Configuración específica para agente de visualización."""
    
    # Modelo específico para visualización
    model: str = Field(
        "claude-sonnet-4-5",
        env="VISUALIZATION_CLAUDE_MODEL"
    )
    
    model_version: str = Field(
        "claude-sonnet-4-5-20250929",
        env="VISUALIZATION_CLAUDE_MODEL_VERSION"
    )
    
    # Configuración de generación
    max_tokens: int = Field(
        3000,
        env="VISUALIZATION_MAX_TOKENS"
    )
    
    temperature: float = Field(
        0.1,
        env="VISUALIZATION_TEMPERATURE"
    )
    
    # Configuración de reintentos
    max_retries: int = Field(
        3,
        env="VISUALIZATION_MAX_RETRIES"
    )
    
    retry_delay: float = Field(
        1.0,
        env="VISUALIZATION_RETRY_DELAY"
    )
    
    use_template_fallback: bool = Field(
        True,
        env="VISUALIZATION_USE_TEMPLATE_FALLBACK"
    )
    
    # Configuración de preprocesamiento
    outlier_detection_method: str = Field(
        "iqr",
        env="VISUALIZATION_OUTLIER_METHOD"
    )
    
    max_null_percentage: float = Field(
        0.5,
        env="VISUALIZATION_MAX_NULL_PERCENTAGE"
    )
    
    # Configuración visual
    color_palette: List[str] = Field(
        ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#6A994E"],
        env="VISUALIZATION_COLOR_PALETTE"
    )
    
    default_template: str = Field(
        "plotly_white",
        env="VISUALIZATION_DEFAULT_TEMPLATE"
    )
```

### Environment Variables

```bash
# Claude Sonnet 4.5 para visualización
VISUALIZATION_CLAUDE_MODEL=claude-sonnet-4-5
VISUALIZATION_CLAUDE_MODEL_VERSION=claude-sonnet-4-5-20250929

# Configuración de generación
VISUALIZATION_MAX_TOKENS=3000
VISUALIZATION_TEMPERATURE=0.1

# Configuración de reintentos
VISUALIZATION_MAX_RETRIES=3
VISUALIZATION_RETRY_DELAY=1.0
VISUALIZATION_USE_TEMPLATE_FALLBACK=true

# Configuración de preprocesamiento
VISUALIZATION_OUTLIER_METHOD=iqr
VISUALIZATION_MAX_NULL_PERCENTAGE=0.5

# Configuración visual
VISUALIZATION_COLOR_PALETTE=["#2E86AB","#A23B72","#F18F01","#C73E1D","#6A994E"]
VISUALIZATION_DEFAULT_TEMPLATE=plotly_white
```

## Implementation Notes

### Reutilización de Código Existente

1. **llm_manager.py**: Reutilizar para inicializar Claude Sonnet 4.5
   ```python
   # En visualization_agent.py
   from .llm_manager import ClaudeLLMManager
   
   def _initialize_sonnet_45(self):
       # Crear configuración específica para Sonnet 4.5
       llm_manager = ClaudeLLMManager()
       # Configurar para usar Sonnet 4.5 específicamente
       return llm_manager.get_llm()
   ```

2. **code_executor.py**: Extender CodeValidator existente
   ```python
   # Añadir ImprovedCodeValidator como subclase
   class ImprovedCodeValidator(CodeValidator):
       # Heredar validación de seguridad
       # Añadir validaciones adicionales
       pass
   ```

3. **visualization_handler.py**: Mantener sin cambios
   - Ya maneja correctamente la conversión de figuras
   - Ya integra con Streamlit
   - No requiere modificaciones

### Modificaciones Mínimas

**visualization_agent.py**:
- Añadir `self.preprocessor = DataPreprocessor()`
- Añadir `self.templates = VisualizationTemplates()`
- Modificar `generate_visualization()` para incluir preprocesamiento
- Añadir lógica de reintentos
- Mejorar prompts

**visualization_collaboration_tool.py**:
- Añadir llamada a preprocesamiento antes de generar visualización
- Mejorar manejo de errores
- Añadir metadata en respuestas

**code_executor.py**:
- Añadir clase `ImprovedCodeValidator`
- Mantener `SafeCodeExecutor` sin cambios

### Nuevos Archivos

1. **data_preprocessor.py**: Completamente nuevo
2. **visualization_templates.py**: Completamente nuevo

### Eliminación de Código Legacy

No hay código legacy a eliminar en esta fase. El sistema actual se mejora sin eliminar funcionalidad existente.

## Performance Considerations

### Optimizaciones

1. **Cache de Plantillas**:
   ```python
   class VisualizationTemplates:
       def __init__(self):
           self._template_cache = {}
           self._load_templates()
   ```

2. **Preprocesamiento Eficiente**:
   ```python
   # Usar operaciones vectorizadas de pandas
   data = data.sort_values('charttime')  # Más rápido que iteración
   data = data.drop_duplicates(subset=['charttime', 'subject_id'])
   ```

3. **Validación Rápida**:
   ```python
   # Validar solo lo necesario
   if visualization_type in COMMON_TYPES:
       # Usar plantilla (más rápido)
       return self.templates.get_template(visualization_type)
   ```

### Métricas de Performance

- Tiempo de preprocesamiento: < 100ms para 1000 filas
- Tiempo de generación con plantilla: < 500ms
- Tiempo de generación con LLM: < 3000ms
- Tiempo total end-to-end: < 5000ms

## Security Considerations

### Validación de Código

El sistema mantiene todas las validaciones de seguridad existentes en `CodeValidator`:
- Prevención de imports peligrosos
- Prevención de operaciones prohibidas
- Sandbox de ejecución

### Validación de Datos

Nuevas validaciones en `DataPreprocessor`:
- Validar tipos de datos esperados
- Limitar tamaño de DataFrames procesados
- Sanitizar nombres de columnas

## Migration Strategy

### Fase 1: Añadir Nuevos Componentes
1. Crear `data_preprocessor.py`
2. Crear `visualization_templates.py`
3. Añadir tests para nuevos componentes

### Fase 2: Modificar Componentes Existentes
1. Actualizar `visualization_agent.py`
2. Actualizar `code_executor.py`
3. Actualizar `visualization_collaboration_tool.py`
4. Actualizar tests existentes

### Fase 3: Integración con Chat Unificado
1. Actualizar detección de intención en chat
2. Añadir lógica de invocación automática
3. Mejorar presentación de visualizaciones

### Fase 4: Validación y Optimización
1. Ejecutar suite completa de tests
2. Realizar pruebas de performance
3. Ajustar configuración según resultados
4. Documentar cambios

## Dependencies

### Nuevas Dependencias

Ninguna. El sistema usa las bibliotecas ya instaladas:
- pandas
- numpy
- plotly
- langchain-anthropic
- anthropic

### Versiones Requeridas

- pandas >= 1.5.0
- numpy >= 1.23.0
- plotly >= 5.14.0
- langchain-anthropic >= 0.1.0
- anthropic >= 0.18.0

## Documentation Updates

### Archivos a Actualizar

1. **docs/VISUALIZATION_AGENT_ARCHITECTURE.md**
   - Añadir sección sobre preprocesamiento
   - Documentar sistema de plantillas
   - Actualizar diagramas de flujo

2. **docs/UNIFIED_CHAT_ARCHITECTURE.md**
   - Documentar integración automática de visualizaciones
   - Añadir ejemplos de consultas que generan visualizaciones

3. **README.md**
   - Actualizar sección de visualizaciones
   - Añadir ejemplos de uso mejorado

### Nueva Documentación

1. **docs/VISUALIZATION_TEMPLATES_GUIDE.md**
   - Guía para crear nuevas plantillas
   - Ejemplos de personalización
   - Best practices

2. **docs/DATA_PREPROCESSING_GUIDE.md**
   - Explicación del preprocesamiento
   - Configuración de detección de outliers
   - Manejo de valores faltantes

## References

- **Requirements**: `.kiro/specs/visualization-improvement/requirements.md`
- **Correctness Properties**: `.kiro/specs/visualization-improvement/correctness-properties.md`
- **Current Implementation**: `services/medical_agent/visualization_agent.py`
- **Chat Integration**: `services/unified_chat/unified_agent.py`
- **Settings**: `config/settings.py`
