# Sistema de Visualización - ChatHCE

**Última actualización**: Febrero 2026

## Resumen

El sistema de visualización genera gráficas médicas dinámicas integradas en el Chat Unificado. Usa una arquitectura multi-agente con enfoque **template-first** (templates como flujo principal, LLM solo como fallback).

## Arquitectura

```
Usuario → Chat Unificado (detecta necesidad de visualización)
              ↓
         VisualizationCollaborationTool
              ↓
         ¿Múltiples métricas de signos vitales?
              ↓
         SÍ → generate_multiple_visualizations()
              ↓
         Para CADA métrica:
           1. VisualizationSelector analiza datos
           2. Decide mejor tipo de visualización
           3. VisualizationTemplates genera la gráfica
              ↓
         Opcionalmente: Visualización combinada
              ↓
         Retornar figuras como imagen base64
```

### Componentes

| Componente | Ubicación | Responsabilidad |
|-----------|-----------|-----------------|
| VisualizationCollaborationTool | `services/medical_agent/tools/visualization_collaboration_tool.py` | Orquesta el flujo, obtiene datos, convierte a imagen |
| VisualizationAgent | `services/medical_agent/visualization_agent.py` | Genera código Python con templates o LLM |
| VisualizationSelector | `services/medical_agent/visualization_selector.py` | Selección automática del tipo de gráfica |
| VisualizationTemplates | `services/medical_agent/visualization_templates.py` | 12 templates Plotly con lazy loading |
| CodeExecutor | `services/medical_agent/code_executor.py` | Ejecución segura en sandbox |

## Selector Automático de Visualizaciones

Reglas de decisión basadas en características de los datos:

| Condición | Tipo | Razón |
|-----------|------|-------|
| Datos temporales + ≥3 puntos | `timeline` | Evolución temporal |
| ≤2 puntos de datos | `indicator` | Valor único/pocos datos |
| ≤5 puntos sin temporal | `bar` | Comparación de valores |
| >10 puntos sin temporal | `histogram` | Distribución |
| ≤5 valores únicos | `box` | Estadísticas |
| Columna datetime + 2-5 métricas | `comparison` | Comparar métricas en el tiempo |
| Categórica + numérica (<20 cat.) | `bar` | Comparar categorías |
| 2 métricas numéricas | `scatter` | Correlación |
| Múltiples métricas (>3) | `heatmap` | Matriz de correlación |
| Categórica (<8 categorías) | `pie` | Proporciones |

## Templates Disponibles (12)

| Tipo | Descripción |
|------|-------------|
| `timeline` | Línea temporal (1 métrica) |
| `comparison` | Múltiples líneas temporales |
| `bar` | Barras (categorías) |
| `scatter` | Dispersión (correlación) |
| `histogram` | Distribución de valores |
| `box` | Box plot (estadísticas) |
| `violin` | Distribución detallada |
| `heatmap` | Mapa de calor |
| `pie` | Proporciones |
| `sunburst` | Jerárquico circular |
| `table` | Datos tabulares |
| `indicator` | KPI / valor único |

## Flujo Template-First

```python
def generate_visualization(data, visualization_type, title):
    # 1. Preprocesar datos
    data = preprocess_temporal_data(data)
    
    # 2. Auto-selección si es necesario
    if visualization_type == 'auto':
        visualization_type, params = selector.select_visualization_type(data)
    
    # 3. Intentar con template (FLUJO PRINCIPAL)
    result = _try_template_generation(data, visualization_type, title)
    if result['success']:
        return result  # ✅ Éxito con template
    
    # 4. Fallback a LLM (solo si falla)
    result = _generate_with_llm(data, visualization_type, title)
    return result
```

## Integración con Chat Unificado

### Detección Automática

El agente detecta cuándo generar visualizaciones basándose en:

- **Consultas temporales**: "evolución", "tendencia", "a lo largo del tiempo"
- **Múltiples métricas**: "temperatura y frecuencia cardíaca", "todos los signos vitales"
- **Solicitud explícita**: "muestra un gráfico", "visualiza"
- **Distribuciones**: "distribución de diagnósticos", "frecuencia de medicamentos"

### Presentación en Respuesta

Las visualizaciones se integran con:
- Encabezado: "📊 Visualización Generada" (singular) o "📊 Visualizaciones Generadas (N)"
- Metadata de procesamiento (métricas incluidas/excluidas, registros procesados)
- Imagen base64 inline

### Manejo de Errores

Si la visualización falla, el agente:
1. NO interrumpe el flujo conversacional
2. Continúa con respuesta textual
3. Menciona brevemente que no se pudo generar la gráfica
4. Proporciona análisis textual completo de los datos

## Seguridad

### Validación de Código
- Solo imports permitidos: `plotly`, `pandas`, `numpy`, `datetime`, `math`
- Prohibidos: `os`, `sys`, `subprocess`, `socket`, `eval`, `exec`, `open`
- Verificación de sintaxis Python válida

### Sandbox de Ejecución
- Namespace restringido
- Timeout de ejecución
- Captura de stdout/stderr
- Manejo de excepciones

## Rendimiento

| Métrica | Template-First | Solo LLM (legacy) |
|---------|---------------|-------------------|
| Tiempo de generación | ~200-500ms | ~3-5s |
| Uso de memoria inicial | ~10MB | ~100MB |
| Llamadas LLM | ~5-10% | 100% |
| Predicibilidad | Determinista | Variable |

## Configuración

```python
# config/settings.py
class VisualizationSettings(BaseSettings):
    model_name: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout_seconds: int = 30
    color_palette: List[str] = [
        '#2E86AB', '#06A77D', '#F77F00',
        '#8338EC', '#3A86FF', '#FF006E'
    ]
```

## Archivos del Sistema

```
services/medical_agent/
├── visualization_agent.py          # Agente principal
├── visualization_selector.py       # Selector automático
├── visualization_templates.py      # 12 templates Plotly
├── visualization_handler.py        # Handler de visualización
├── visualization_store.py          # Almacén de visualizaciones
├── code_executor.py                # Ejecutor seguro
└── tools/
    └── visualization_collaboration_tool.py  # Tool de colaboración
```

## Referencias

- [Plotly Python](https://plotly.com/python/)
- [MIMIC-IV-ED](https://physionet.org/content/mimic-iv-ed/)
- Configuración: `config/settings.py`
