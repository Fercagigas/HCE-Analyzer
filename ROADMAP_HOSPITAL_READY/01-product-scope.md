# 01 — Product Scope, Intended Use y límites

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Tarea | Estado | Evidencia / nota |
|---|---|---|
| P0.1 Intended purpose | ✅ | `docs/product/INTENDED_PURPOSE.md` (Fase 0) |
| P0.2 Claims de producto | ✅ | `INTENDED_PURPOSE.md` y `.kiro/steering/product.md`; revisar tras `docs/product/COMPETITIVE_POSITIONING.md` |
| P0.3 Actores | ✅ | `INTENDED_PURPOSE.md`; en código solo existen los roles `researcher` y usuario autenticado (ADR 0090) |
| P0.4 Matriz acción/riesgo | ✅ | `docs/product/RISK_CAPABILITY_MATRIX.md` |
| P0.5 Principios de UX | ✅ documentados · 🟡 aplicados | Paciente activo siempre visible en la barra lateral; hechos e inferencias separados en `ChatResponse` pero la UI Streamlit aún los muestra como texto |

Siguiente paso: reclasificar en la matriz las tools de Fase 1 (12 tools read-only, agregados solo en `research`) y los features de `10-ai-features.md` antes de Fase 6.

## Objetivo

Definir ChatHCE como **Clinical AI Intelligence Layer**, no como una HCE alternativa.

## Tareas

### P0.1 — Definir el intended purpose
- Especificar quién utiliza ChatHCE, en qué contexto y para qué tareas.
- Primera versión recomendada: copiloto de información clínica, no diagnóstico autónomo.
- Casos permitidos inicialmente: resumir HCE, localizar evidencia, reconstruir evolución, comparar episodios, buscar protocolos, detectar cambios, preparar borradores y responder preguntas sobre información disponible.
- Casos fuera de alcance inicial: prescripción autónoma, diagnóstico autónomo, triaje autónomo, modificación automática de HCE, órdenes clínicas sin aprobación.

### P0.2 — Definir claims de producto
Evitar claims como "ChatHCE diagnostica". Formular capacidades verificables: "reduce el esfuerzo de revisión", "localiza evidencia", "resume cambios", "permite consultas longitudinales".

### P0.3 — Definir actores
- médico;
- enfermería;
- farmacéutico;
- administrador clínico;
- administrador IT;
- responsable de seguridad/DPO;
- auditor.

### P0.4 — Definir matriz acción/riesgo
Clasificar cada capability como retrieval, summarization, inference, recommendation o write/action y asignar nivel de riesgo y controles.

### P0.5 — Definir principios de UX
- paciente/contexto siempre visible;
- diferenciar hechos de inferencias;
- evidencia accesible en un clic;
- incertidumbre explícita;
- IA nunca presentada como autoridad clínica;
- minimizar alert fatigue.

## Entregables
- `docs/product/INTENDED_PURPOSE.md`
- `docs/product/CLINICAL_USE_CASES.md`
- `docs/product/OUT_OF_SCOPE.md`
- `docs/product/RISK_CAPABILITY_MATRIX.md`

## Definition of Done
Existe una frontera inequívoca entre **información**, **interpretación**, **recomendación** y **acción clínica**, y cualquier nueva feature puede clasificarse antes de desarrollarse.
