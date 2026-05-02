# Design Document - Visualization System Improvement

## Overview

Este documento describe el diseño técnico para mejorar el sistema de visualización médica del ChatHCE. El sistema actual presenta problemas de calidad en las gráficas generadas, incluyendo conexión incorrecta de puntos temporales y generación inconsistente. La solución propuesta mejora el sistema existente sin crear código redundante, integrándose perfectamente con el chat unificado y utilizando Claude Sonnet 4.5 para generación de código de visualización.

### Objetivos del Diseño

1. Mejorar la calidad y confiabilidad de las visualizaciones generadas
2. Integrar mejoras en el código existente sin duplicación
3. Asegurar integración automática con el chat unificado
4. Mantener código limpio, legible y sin elementos redundantes
5. Usar Claude Sonnet 4.5 para generación de código de visualización

### Alcance

**Incluido:**
- Mejoras en `visualization_agent.py`
- Nuevo módulo de preprocesamiento de datos
- Validación mejorada de código generado
- Sistema de plantillas para casos comunes
- Integración con chat unificado
- Configuración de Claude Sonnet 4.5

**Excluido:**
- Cambios en la interfaz de usuario de Streamlit
- Modificaciones a la base de datos MIMIC-IV-ED
- Cambios en el sistema RAG
- Nuevos tipos de visualización (se mantienen los existentes)

## Architecture

### Componentes Actuales (a modificar)

```
services/medical_agent/
├── visualization_agent.py          # MODIFICAR: Mejorar generación de código
├── visualization_handler.py        # MANTENER: Sin cambios
├── code_executor.py               # MODIFICAR: Añadir validación mejorada
├── llm_manager.py                 # REUTILIZAR: Para Claude Sonnet 4.5
└── tools/
    └── visualization_collaboration_tool.py  # MODIFICAR: Integración mejorada
```

### Nuevos Componentes

```
services/medical_agent/
├── data_preprocessor.py           # NUEVO: Preprocesamiento de datos
└── visualization_templates.py     # NUEVO: Plantillas de código
```

### Flujo de Datos Mejorado

```
Chat Unificado
    ↓
Detecta necesidad de visualización
    ↓
VisualizationCollaborationTool
    ↓
Obtiene datos de DatabaseService
    ↓
DataPreprocessor (NUEVO)
    ├── Ordenar por tiempo
    ├── Eliminar duplicados
    ├── Detectar outliers
    └── Validar métricas
    ↓
VisualizationAgent
    ├── Verificar plantilla disponible
    ├── Si existe: usar plantilla
    └── Si no: generar con Claude Sonnet 4.5
    ↓
CodeValidator (mejorado)
    ├── Validar sintaxis
    ├── Verificar columnas
    └── Validar métodos Plotly
    ↓
SafeCodeExecutor
    ├── Ejecutar código
    └── Capturar errores
    ↓
Si falla: Reintentar con prompt simplificado
    ↓
Si falla 3 veces: Usar plantilla de respaldo
    ↓
Retornar figura a Chat Unificado
```

## Components and Interfaces

### 1. DataPreprocessor (Nuevo)

**Ubicación**: `services/medical_agent/data_preprocessor.py`

**Responsabilidad**: Limpiar y preparar datos antes de visualización

**Interfaz Pública**:
```python
class DataPreprocessor:
    def preprocess_temporal_data(
        self,
        data: pd.DataFrame,
        time_column: str = 'charttime',
        metrics: Optional[List[str]] = None
    ) -> PreprocessResult:
        """
        Preprocesar datos temporales para visualización.
        
        Args:
            data: DataFrame con datos médicos
            time_column: Nombre de la columna temporal
            metrics: Lista de métricas a procesar
            
        Returns:
            PreprocessResult con datos limpios y metadata
        """
        pass
    
    def detect_outliers(
        self,
        data: pd.DataFrame,
        columns: List[str],
        method: str = 'iqr'
    ) -> pd.DataFrame:
        """
        Detectar outliers en métricas numéricas.
        
        Args:
            data: DataFrame con datos
            columns: Columnas a analizar
            method: Método de detección ('iqr', 'zscore')
            
        Returns:
            DataFrame con columna 'is_outlier' añadida
        """
        pass
    
    def validate_metrics(
        self,
        data: pd.DataFrame,
        requested_metrics: List[str]
    ) -> MetricsValidation:
        """
        Validar disponibilidad y calidad de métricas.
        
        Args:
            data: DataFrame con datos
            requested_metrics: Métricas solicitadas
            
        Returns:
            MetricsValidation con métricas válidas y excluidas
        """
        pass
```

**Modelos de Datos**:
```python
@dataclass
class PreprocessResult:
    data: pd.DataFrame
    rows_original: int
    rows_processed: int
    rows_removed: int
    duplicates_removed: int
    outliers_detected: int
    metrics_excluded: List[str]
    warnings: List[str]

@dataclass
class MetricsValidation:
    valid_metrics: List[str]
    excluded_metrics: List[str]
    null_percentages: Dict[str, float]
    warnings: List[str]
```

### 2. VisualizationTemplates (Nuevo)

**Ubicación**: `services/medical_agent/visualization_templates.py`

**Responsabilidad**: Proporcionar plantillas de código para casos comunes

**Interfaz Pública**:
```python
class VisualizationTemplates:
    def get_template(
        self,
        visualization_type: str
    ) -> Optional[str]:
        """
        Obtener plantilla de código para tipo de visualización.
        
        Args:
            visualization_type: Tipo de visualización
            
        Returns:
            Código de plantilla o None si no existe
        """
        pass
    
    def customize_template(
        self,
        template: str,
        data_info: Dict[str, Any],
        title: str,
        metrics: List[str]
    ) -> str:
        """
        Personalizar plantilla con parámetros específicos.
        
        Args:
            template: Código de plantilla base
            data_info: Información sobre los datos
            title: Título del gráfico
            metrics: Métricas a visualizar
            
        Returns:
            Código personalizado listo para ejecutar
        """
        pass
    
    def validate_template(
        self,
        template: str,
        test_data: List[pd.DataFrame]
    ) -> bool:
        """
        Validar que plantilla funciona con datos de prueba.
        
        Args:
            template: Código de plantilla
            test_data: Lista de DataFrames de prueba
            
        Returns:
            True si funciona con todos los datos de prueba
        """
        pass
```

**Plantillas Disponibles**:
- `timeline`: Gráfico de línea temporal
- `comparison`: Comparación de múltiples métricas
- `distribution`: Histograma o gráfico de pastel
- `scatter`: Gráfico de dispersión

### 3. VisualizationAgent (Modificado)

**Ubicación**: `services/medical_agent/visualization_agent.py`

**Cambios Principales**:
1. Usar Claude Sonnet 4.5 en lugar del modelo actual
2. Integrar DataPreprocessor
3. Usar VisualizationTemplates cuando sea posible
4. Implementar lógica de reintentos con prompts simplificados
5. Mejorar prompts de generación de código

**Nueva Interfaz**:
```python
class VisualizationAgent:
    def __init__(self):
        # Usar Claude Sonnet 4.5 específicamente
        self.llm = self._initialize_sonnet_45()
        self.preprocessor = DataPreprocessor()
        self.templates = VisualizationTemplates()
        self.validator = ImprovedCodeValidator()
        
    def generate_visualization(
        self,
        data: pd.DataFrame,
        visualization_type: str,
        requirements: Optional[str] = None,
        title: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generar visualización con reintentos y fallbacks.
        
        Flujo:
        1. Preprocesar datos
        2. Verificar si existe plantilla
        3. Si existe: usar plantilla personalizada
        4. Si no: generar con Claude Sonnet 4.5
        5. Validar código generado
        6. Ejecutar código
        7. Si falla: reintentar con prompt simplificado
        8. Si falla 3 veces: usar plantilla de respaldo
        """
        pass
    
    def _initialize_sonnet_45(self) -> ChatAnthropic:
        """Inicializar Claude Sonnet 4.5 específicamente."""
        pass
```

### 4. ImprovedCodeValidator (Modificado)

**Ubicación**: `services/medical_agent/code_executor.py`

**Mejoras**:
```python
class ImprovedCodeValidator(CodeValidator):
    def validate_code(
        self,
        code: str,
        data_columns: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validación mejorada que verifica:
        1. Seguridad (hereda de CodeValidator)
        2. Existencia de variable 'fig'
        3. Uso de columnas correctas
        4. Métodos de Plotly válidos
        """
        pass
    
    def check_column_usage(
        self,
        code: str,
        available_columns: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Verificar que el código solo usa columnas disponibles.
        
        Returns:
            (is_valid, missing_columns)
        """
        pass
    
    def check_plotly_methods(
        self,
        code: str
    ) -> Tuple[bool, List[str]]:
        """
        Verificar que los métodos de Plotly existen.
        
        Returns:
            (is_valid, invalid_methods)
        """
        pass
```

### 5. VisualizationCollaborationTool (Modificado)

**Ubicación**: `services/medical_agent/tools/visualization_collaboration_tool.py`

**Mejoras**:
1. Integrar preprocesamiento automático
2. Mejorar manejo de errores
3. Proporcionar feedback más detallado

**Cambios en execute()**:
```python
def execute(
    self,
    visualization_type: str,
    stay_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    metrics: Optional[List[str]] = None,
    data_source: str = "vitalsign",
    title: Optional[str] = None,
    requirements: Optional[str] = None
) -> str:
    """
    Flujo mejorado:
    1. Validar inputs
    2. Obtener datos de base de datos
    3. Preprocesar datos (NUEVO)
    4. Validar métricas (NUEVO)
    5. Generar visualización con reintentos
    6. Retornar resultado con metadata
    """
    pass
```

## Data Models

### PreprocessResult
```python
@dataclass
class PreprocessResult:
    """Resultado del preprocesamiento de datos."""
    data: pd.DataFrame
    rows_original: int
    rows_processed: int
    rows_removed: int
    duplicates_removed: int
    outliers_detected: int
    metrics_excluded: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para logging."""
        return {
            'rows_original': self.rows_original,
            'rows_processed': self.rows_processed,
            'rows_removed': self.rows_removed,
            'duplicates_removed': self.duplicates_removed,
            'outliers_detected': self.outliers_detected,
            'metrics_excluded': self.metrics_excluded,
            'warnings': self.warnings
        }
```

### MetricsValidation
```python
@dataclass
class MetricsValidation:
    """Resultado de validación de métricas."""
    valid_metrics: List[str]
    excluded_metrics: List[str]
    null_percentages: Dict[str, float]
    warnings: List[str]
    
    @property
    def has_valid_metrics(self) -> bool:
        """Verificar si hay métricas válidas."""
        return len(self.valid_metrics) > 0
```

### VisualizationResult
```python
@dataclass
class VisualizationResult:
    """Resultado completo de generación de visualización."""
    success: bool
    figure: Optional[Any]
    code: Optional[str]
    visualization_type: str
    error: Optional[str] = None
    preprocess_metadata: Optional[Dict[str, Any]] = None
    used_template: bool = False
    retry_count: int = 0
    execution_time_ms: float = 0.0
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Ver archivo `correctness-properties.md` para la lista completa de 13 propiedades de corrección consolidadas, 3 edge cases y 3 examples.

**Resumen de Propiedades Principales:**
1. Preprocesamiento temporal completo
2. Reintentos con corrección automática
3. Generación garantizada con datos válidos
4. Calidad de código generado
5. Validación y filtrado de métricas
6. Detección no destructiva de outliers
7. Configuración visual consistente
8. Validación completa de código
9. Uso inteligente de plantillas
10. Feedback detallado y transparente
11. Compatibilidad de interfaces públicas
12. Integración automática con chat unificado
13. Manejo graceful de errores en chat

## Secciones Adicionales

Ver archivo `design-continued.md` para:
- Error Handling (estrategias y categorías)
- Testing Strategy (unit tests e integration tests)
- Configuration (Claude Sonnet 4.5 y variables de entorno)
- Implementation Notes (reutilización y modificaciones)
- Performance Considerations
- Security Considerations
- Migration Strategy
- Dependencies
- Documentation Updates
- References
