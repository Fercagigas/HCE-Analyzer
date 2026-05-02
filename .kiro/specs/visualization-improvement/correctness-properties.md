# Correctness Properties - Visualization System Improvement

## Property Reflection

Después de analizar todas las propiedades identificadas en el prework, se han consolidado las siguientes propiedades para eliminar redundancia:

**Consolidaciones realizadas:**
- Propiedades 1.1, 1.2, 1.3, 1.5 se consolidan en Property 1 (preprocesamiento temporal completo)
- Propiedades 2.1, 2.2 se consolidan en Property 2 (reintentos con corrección)
- Propiedades 3.2, 3.3, 3.4, 3.5 se consolidan en Property 4 (calidad de código generado)
- Propiedades 4.1, 4.2, 4.5 se consolidan en Property 5 (validación de métricas)
- Propiedades 5.1, 5.2, 5.3, 5.4, 5.5 se consolidan en Property 7 (configuración visual consistente)
- Propiedades 6.1, 6.2, 6.3, 6.4 se consolidan en Property 8 (validación completa de código)
- Propiedades 7.2, 7.3, 7.4, 7.5 se consolidan en Property 10 (feedback detallado)

## Core Properties

### Property 1: Preprocesamiento temporal completo
*Para cualquier* DataFrame con columna temporal, el preprocesamiento debe ordenar cronológicamente, eliminar duplicados temporales, convertir a datetime si es necesario, y preservar la integridad de todas las columnas de métricas.
**Validates: Requirements 1.1, 1.2, 1.3, 1.5**

### Property 2: Reintentos con corrección automática
*Para cualquier* fallo en generación o ejecución de código, el sistema debe reintentar con prompt simplificado, capturar errores, y solicitar corrección al LLM hasta 3 intentos.
**Validates: Requirements 2.1, 2.2**

### Property 3: Generación garantizada con datos válidos
*Para cualquier* conjunto de datos válidos, el sistema debe generar al menos una visualización básica, ya sea mediante código generado o plantilla de respaldo.
**Validates: Requirements 2.3**

### Property 4: Calidad de código generado
*Para cualquier* código generado por el LLM, debe incluir solo imports necesarios, usar nombres de variables descriptivos en español, evitar comentarios redundantes, y usar template='plotly_white' en el layout.
**Validates: Requirements 3.2, 3.3, 3.4, 3.5**

### Property 5: Validación y filtrado de métricas
*Para cualquier* DataFrame procesado, el sistema debe identificar porcentaje de nulos por columna, excluir métricas con >50% nulos, y reemplazar valores infinitos/NaN con None.
**Validates: Requirements 4.1, 4.2, 4.5**

### Property 6: Detección no destructiva de outliers
*Para cualquier* conjunto de datos con outliers detectados por IQR, los outliers deben ser marcados pero no eliminados, y visualizados con colores diferentes.
**Validates: Requirements 4.3, 4.4**

### Property 7: Configuración visual consistente
*Para cualquier* visualización generada, debe usar paleta de colores médicos predefinida, títulos de ejes en español, formato de fecha legible para ejes temporales, hover tooltips con todas las métricas y unidades, y hovermode='x unified' para gráficas temporales.
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

### Property 8: Validación completa de código
*Para cualquier* código generado, el validador debe verificar existencia de variable 'fig', uso correcto de columnas disponibles, métodos de Plotly válidos, y rechazar código con columnas inexistentes.
**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 9: Uso inteligente de plantillas
*Para cualquier* tipo de visualización común (timeline, comparison, distribution, scatter), el sistema debe verificar existencia de plantilla y usarla como base antes de generar código desde cero.
**Validates: Requirements 8.1, 8.2, 8.4**

### Property 10: Feedback detallado y transparente
*Para cualquier* operación de visualización, el sistema debe proporcionar feedback sobre métricas disponibles cuando las solicitadas están ausentes, incluir errores específicos en mensajes de fallo, incluir metadata en respuestas exitosas, e informar sobre registros excluidos y razones.
**Validates: Requirements 7.2, 7.3, 7.4, 7.5**

### Property 11: Compatibilidad de interfaces públicas
*Para cualquier* interfaz pública existente en el sistema de visualización, las mejoras deben mantener la misma firma de métodos y comportamiento esperado.
**Validates: Requirements 9.4**

### Property 12: Integración automática con chat unificado
*Para cualquier* consulta sobre tendencias temporales o datos numéricos múltiples, el chat unificado debe invocar automáticamente la herramienta de visualización e incluir resultados en la respuesta.
**Validates: Requirements 10.1, 10.2, 10.3**

### Property 13: Manejo graceful de errores en chat
*Para cualquier* fallo en generación de visualización desde el chat unificado, el sistema debe continuar con respuesta textual sin interrumpir el flujo conversacional.
**Validates: Requirements 10.5**

## Edge Cases

### Edge Case 1: Gaps temporales grandes
WHEN datos temporales tienen gaps mayores a 24 horas THEN usar mode='lines+markers' en lugar de solo 'lines'
**Validates: Requirements 1.4**

### Edge Case 2: Fallback después de 3 fallos
WHEN el agente completa 3 intentos fallidos THEN generar visualización de respaldo usando plantillas predefinidas y registrar error en logs
**Validates: Requirements 2.4, 2.5**

### Edge Case 3: DataFrame vacío
WHEN el sistema recibe DataFrame vacío THEN retornar mensaje descriptivo indicando ausencia de datos
**Validates: Requirements 7.1**

## Examples

### Example 1: Configuración de Claude Sonnet 4.5
El agente de visualización debe estar configurado para usar específicamente Claude Sonnet 4.5:
```python
model = "claude-sonnet-4-5"
model_version = "claude-sonnet-4-5-20250929"
```
**Validates: Requirements 3.1**

### Example 2: Plantillas disponibles
El sistema debe mantener plantillas para los siguientes tipos:
- timeline
- comparison
- distribution
- scatter
**Validates: Requirements 8.3**

### Example 3: Validación exitosa
WHEN el validador aprueba código THEN retornar (True, código_validado)
**Validates: Requirements 6.5**
