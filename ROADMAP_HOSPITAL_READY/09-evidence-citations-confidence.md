# 09 — Evidence Engine, citations y calidad de evidencia

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Tarea | Estado | Evidencia / nota |
|---|---|---|
| P0.1 Modelo de afirmaciones | ✅ | `ClaimType` = OBSERVED_FACT, GUIDELINE_STATEMENT, CALCULATION, AI_INFERENCE, UNKNOWN (`chathce/domain/evidence.py`) |
| P0.2 Evidence object | ✅ | `Evidence` con id, tipo, sistema origen, recurso, paciente/episodio, timestamp, valor/unidades, `Provenance(tool_name, tool_use_id, trace_id, retrieved_at, provider)` |
| P0.3 Claim-to-evidence mapping | 🟡 | Una `Claim` por resultado de tool con sus `evidence_ids` y una `AI_INFERENCE` por respuesta; mapeo por afirmación es el Evidence Engine (Fase 3) |
| P0.4 Source viewer | ⏳ | La API expone `evidence`; el visor es Fase 4 |
| P0.5 No unsupported claims | 🟡 | Reglas en el prompt y `uncertainty` en la respuesta; verificación automática pendiente |
| P1.1 – P1.4 | ⏳ | Fase 3 |

## Objetivo
Convertir la trazabilidad en una característica central de ChatHCE.

## Tareas

### P0.1 — Modelo de afirmaciones
Clasificar outputs en:
- `OBSERVED_FACT` — directamente de HCE;
- `GUIDELINE_STATEMENT` — conocimiento aprobado;
- `CALCULATION` — código determinista;
- `AI_INFERENCE` — interpretación del modelo;
- `UNKNOWN/INSUFFICIENT_EVIDENCE`.

### P0.2 — Evidence object
Cada evidencia debe incluir source ID, type, patient/encounter scope, timestamp, provenance, original value/text, units y access metadata.

### P0.3 — Claim-to-evidence mapping
Las afirmaciones clínicas relevantes enlazan uno o más `evidence_id`.

### P0.4 — Source viewer
Desde frontend abrir el dato original o contexto documental que sustenta una afirmación.

### P0.5 — No unsupported claims
Si no existe soporte suficiente, abstenerse o etiquetar explícitamente como hipótesis/inferencia.

### P1.1 — Evidence Quality Engine
No pedir al LLM un porcentaje de confianza. Calcular señales como:
- completeness;
- source authority;
- source freshness;
- agreement/conflict;
- retrieval quality;
- tool success;
- temporal consistency.

Mostrar categorías comprensibles (alta/media/baja evidencia), no falsa precisión.

### P1.2 — Conflict detection
Detectar información contradictoria entre notas, medicación, diagnósticos y fuentes.

### P1.3 — Missing evidence
Mostrar qué información relevante no está disponible.

### P1.4 — Evidence snapshot
Guardar las referencias/versiones utilizadas para poder reconstruir respuestas auditadas aunque cambie posteriormente la HCE o el protocolo.

## Definition of Done
Un revisor puede seleccionar cualquier conclusión de ChatHCE y reconstruir los datos y documentos que la sustentaron, distinguiendo inequívocamente hechos de inferencias.
