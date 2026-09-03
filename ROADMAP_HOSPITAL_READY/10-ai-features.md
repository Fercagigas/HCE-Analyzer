# 10 — Features AI-first diferenciadoras

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

Todas las features de este documento siguen ⏳ (Fase 6). Fase 1 deja la base que necesitan: `RequestContext` con paciente y episodio, DTOs clínicos con `evidence_id`, `PatientSummaryService`, `ClinicalDataProvider` con series temporales de laboratorio y UCI, y `ChatResponse` con hechos e inferencias separados. Antes de activar cualquiera hay que clasificarla en `docs/product/RISK_CAPABILITY_MATRIX.md` y disponer del Evidence Engine (Fase 3).

## Objetivo
No competir con Oracle/Epic almacenando información; transformar información fragmentada en comprensión clínica navegable.

## P1 — What Matters Now
Al abrir un paciente, identificar pocos cambios/hallazgos potencialmente relevantes y explicar por qué, siempre con evidencia. Diseñar para evitar alert fatigue.

## P1 — Since Your Last Review
Guardar el último punto de revisión del profesional y generar un diff clínico: nuevas analíticas, notas, cambios de medicación, microbiología, etc., priorizando relevancia.

## P1 — AI Clinical Timeline
Transformar eventos en una historia longitudinal conectada. Mantener eventos originales y separar las relaciones inferidas por IA.

## P1 — Longitudinal Questions
Responder preguntas como:
- ¿cuándo empezó la anemia?;
- ¿cómo ha evolucionado la función renal?;
- ¿qué tratamientos se probaron?;
- ¿por qué se retiró una medicación?;
- ¿ha tenido episodios similares?

## P1 — Compare
Comparar episodios, periodos o conjuntos de datos y resaltar diferencias con evidencia.

## P1 — Clinical Deep Research / Investigate
Workflow agentic de mayor duración que combine HCE + protocolos aprobados + fuentes externas aprobadas (si se habilitan), construya un informe de evidencia y señale información ausente. Debe ser claramente distinto de una recomendación autónoma.

## P1/P2 — Evidence Graph
Representar visualmente relaciones entre datos, eventos y conclusiones. Cada nodo debe ser clicable y marcar si la relación es observada o inferida.

## P1 — Ask This Data
Seleccionar cualquier tarjeta/valor/fuente y preguntar, comparar, buscar historia relacionada o añadir a investigación.

## P1 — Clinical Workspace
Espacio temporal donde el profesional reúne evidencias, preguntas, comparaciones y borradores sin modificar la HCE original.

## P1 — Draft generation
Borradores de handoff, resumen o nota. Siempre `AI-generated draft`, nunca guardado automáticamente en HCE.

## Requisitos comunes
Todas estas features deben:
- respetar autorización/patient scope;
- citar evidencia;
- mostrar missing/conflicting data;
- diferenciar hechos e inferencias;
- ser auditables;
- tener evaluación específica antes de activarse.

## Definition of Done
ChatHCE ofrece valor que no se obtiene navegando manualmente por una HCE: reduce lectura, reconstruye contexto y permite investigar información longitudinal sin ocultar las fuentes.
