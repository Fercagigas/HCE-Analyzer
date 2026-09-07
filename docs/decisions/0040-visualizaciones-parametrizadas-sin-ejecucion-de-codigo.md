# ADR 0040 — Visualizaciones parametrizadas sin ejecución de código

Estado: Aceptada

Fecha: 2026-09-01

## Contexto

El threat model inicial identifica AI-13, ejecución de código arbitrario generado
por el modelo, como riesgo Crítico. La ruta real intentaba primero plantillas que
eran cadenas Python y, si estas fallaban, pedía a Anthropic una nueva cadena de
código. Ambas terminaban en `exec` dentro del proceso Streamlit, con acceso a los
datos, secretos y privilegios del proceso. El validador AST no era un sandbox y
el argumento de timeout del executor no se aplicaba.

La inspección de `main` confirmó la ejecución en
`services/medical_agent/code_executor.py` y el fallback en
`services/medical_agent/visualization_agent.py`. La referencia del threat model
a `ui/unified_chat_interface.py:1459-1500` no corresponde en la versión actual a
un fallback de visualización, sino a la carga temporal de documentos. La UI sí
anunciaba tipos que dependían de generación dinámica y debía alinearse con la
capacidad segura real.

Los cinco casos funcionales de visualización existentes cubren tres familias:
series y comparaciones temporales, barras de frecuencias e histogramas. El
intended purpose y las decisiones DP-01 a DP-08 permanecen sin cambios.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Cubrir las familias utilizadas hoy mediante funciones parametrizadas.**
   Incluye timeline/comparison, barras e histogramas/distribuciones. Se amplía la
   cobertura dentro de esas familias con una o varias métricas temporales, barras
   sobre valores preagregados o conteos categóricos y aliases habituales. Se
   descartan los tipos raros no cubiertos por los casos funcionales actuales.
2. **Convertir los doce templates existentes en doce funciones.** Habría
   conservado scatter, box, violin, heatmap, pie, sunburst, table e indicator,
   además de las familias anteriores. Se descartó por ampliar de forma material
   un cambio temporal que será reescrito en Fase 1 y exigir una superficie mayor
   de validación y pruebas.
3. **Desactivar todas las visualizaciones hasta Fase 1.** Elimina la superficie
   con el menor código posible, pero se descartó porque también elimina los cinco
   casos de uso ya evaluados que pueden implementarse sin ejecución dinámica.
4. **Conservar generación de código dentro de un sandbox.** Se descartó porque
   P0.7 exige eliminar código arbitrario y P0.8 solo aplica si el código es
   imprescindible. Para estas visualizaciones no lo es. Además, construir un
   sandbox real excede el carácter quirúrgico de la mitigación.
5. **Seguir ejecutando únicamente los templates locales.** Se descartó porque
   mantiene `exec` y porque la personalización interpolaba parámetros en cadenas
   Python. No satisface el patrón de funciones parametrizadas ni elimina la
   interpretación dinámica.

## Decision

Se adopta la opción 1, confirmada por el usuario con la indicación de cubrir
tantos casos como sea posible dentro de ese alcance.

La allowlist canónica contiene `timeline`, `comparison`, `bar` e `histogram`.
Se aceptan los aliases `line`, `timeseries`, `time_series`, `temporal`, `trend`
y `distribution`, que se normalizan antes del dispatch. `distribution` produce
un histograma para datos numéricos y barras de frecuencia cuando hay categorías.
El agente puede elegir el tipo y aportar título o métricas mediante el contrato
existente, pero el runtime valida de forma determinista:

- que el tipo pertenezca a la allowlist;
- que los datos sean un DataFrame no vacío;
- que las columnas solicitadas existan;
- que las métricas sean numéricas, distintas y como máximo cinco;
- que exista una columna temporal para series;
- que las barras reciban una categoría, una métrica numérica o ambas;
- que el título sea texto y no supere 200 caracteres.

Las figuras se construyen mediante llamadas directas a Plotly. El agente de
visualización no inicializa un LLM, no crea prompts de código y no tiene fallback
de código. La API histórica `execute_visualization_code` se conserva solo como
compatibilidad fail-closed: rechaza toda entrada sin interpretarla. Un tipo no
permitido produce un error controlado y la conversación puede continuar con
respuesta textual.

## Motivo

Esta decisión elimina el confín de confianza modelo-código-host y satisface P0.7
sin introducir el coste o la falsa seguridad de un sandbox. Conserva exactamente
las familias exigidas por la evaluación funcional actual y amplía sus variantes
con parámetros validados, manteniendo el cambio acotado a la mitigación que será
reescrita en Fase 1.

## Consecuencias

- Ya no se puede ejecutar Python generado por el modelo, por templates ni por un
  consumidor del executor legado.
- Se conservan evoluciones temporales de una o varias métricas, barras de valores
  preagregados, frecuencias categóricas o valores contra índice, e
  histogramas/distribuciones.
- La selección automática que antes elegía un tipo avanzado se reconduce a una
  familia segura cuando los datos permiten timeline, comparison, bar o histogram.
- Solicitudes explícitas de scatter, heatmap, box, violin, pie, sunburst, table,
  indicator, 3D, surface, contour, treemap, waterfall, sankey, candlestick o tipos
  libres se rechazan. No existe fallback dinámico.
- La UI deja de anunciar capacidades que ya no están disponibles.
- Las plantillas de cadenas existentes pueden permanecer temporalmente como
  compatibilidad no conectada; el agente no las carga y el executor rechaza su
  API de ejecución. No se amplía este cambio para retirar módulos que serán
  reemplazados en Fase 1.
- Las pruebas verifican las familias conservadas, aliases, validación de
  parámetros, rechazo de tipos no permitidos, ausencia de llamadas dinámicas y
  ausencia de efectos al presentar una carga Python maliciosa.

## Pendientes

- En Fase 1, sustituir el contrato libre de visualización por un schema tipado que
  exponga directamente la allowlist y elimine campos de requisitos no usados.
- Retirar definitivamente los módulos y APIs de templates/código obsoletos cuando
  se reescriba la arquitectura de visualización.
- Añadir una nueva función parametrizada solo cuando exista un caso aprobado,
  validación explícita de todos sus parámetros y pruebas funcionales/adversariales.
- Incorporar límites de filas y coste por herramienta dentro de los contratos y
  controles de recursos previstos por P0.1, P0.6 y el roadmap de Fase 1/Fase 2.
