# Sistema de visualización — ChatHCE

**Última actualización**: 2 de septiembre de 2026 (Fase 1; ADR 0040 y 0050)

## Principio

Las visualizaciones se generan con **plantillas parametrizadas** de Plotly. No se genera ni ejecuta código; no hay fallback a LLM. El modelo solo elige parámetros dentro de un schema cerrado.

## Flujo

```
Usuario pide una gráfica
  -> ModelGateway llama a la tool create_visualization (schema cerrado)
  -> handler (chathce/gateway/tools/visualization_tool.py)
       1. obtiene los datos del paciente activo vía ScopeGuard(ClinicalDataProvider)
          source=labs | icu_observations | medications, filtrados por itemids / label_contains / intervalo
       2. construye un DataFrame y llama a create_allowlisted_visualization(...)
          (chathce/adapters/visualization/plotly_templates.py)
       3. guarda VisualizationArtifact(figure_json) en VisualizationRepository (memoria, TTL)
       4. devuelve ToolResult con artifacts.visualization_ids y un resumen para el modelo
  -> ChatResponse.visualizations = [VisualizationRef(viz_id, type, title)]
  -> Streamlit: plotly.io.from_json(figure_json) ; API: GET /api/v1/visualizations/{viz_id}
```

## Contrato de la tool

```
visualization_type: timeline | comparison | bar | histogram
source:             labs | icu_observations | medications
subject_id          (debe coincidir con el paciente activo; lo comprueba ScopeGuard)
hadm_id?            limitar a un ingreso
stay_id?            obligatorio para icu_observations
itemids? (<=5) | label_contains?
start?, end?, title?
```

`extra="forbid"`; sin campos de código, columnas libres ni consultas.

## Plantillas (`plotly_templates.py`)

| Función | Familia | Validaciones |
|---|---|---|
| `plot_timeseries(data, time_column, metrics, title)` | timeline / comparison | columna temporal existente, métricas numéricas, mínimo 1 |
| `plot_bar(data, category_column, metric, title)` | bar | categoría y métrica existentes; agregación por conteo si no hay métrica |
| `plot_histogram(data, metric, title)` | histogram | métrica numérica |
| `create_allowlisted_visualization(kind, data, **params)` | punto de entrada | `kind` en la allowlist; títulos saneados; `VisualizationParameterError` en cualquier otro caso |
| `figure_to_json(figure)` | serialización | `plotly.io.to_json` |

Los agregados de dataset (frecuencias de diagnósticos, fármacos, tipos de ingreso) se obtienen con `get_dataset_statistics` (RPC fijas, modo investigación) y se representan con `bar` a partir de los buckets devueltos.

## Seguridad

- `tests/security/test_visualization_security.py`: escaneo AST de `services/**`, `chathce/**`, `ui/**`, `src/**` sin `exec`, `eval` ni `compile`; ausencia de los antiguos `CodeValidator`/`SafeCodeExecutor`; validación de parámetros de las plantillas.
- Los datos que alimentan la figura pasan por `ScopeGuard`: solo el paciente activo.
- Las figuras no se persisten en base de datos en Fase 1 (repositorio en memoria con TTL); persistencia y descarga son P1.

## Añadir una familia nueva

1. Función `plot_<familia>` en `plotly_templates.py` con validaciones explícitas de columnas y tipos.
2. Añadirla a la allowlist de `create_allowlisted_visualization` y al `Literal` de `visualization_type`.
3. Tests unitarios de parámetros válidos/inválidos y actualización de `test_visualization_security.py` si cambia la lista de tipos anunciados.
