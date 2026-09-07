# 13 — Regulación, Quality y Clinical Safety

> Este documento es un backlog técnico/organizativo, no asesoramiento jurídico. La clasificación final depende del intended purpose, claims, jurisdicción y uso real.

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

Sin cambios de fondo en Fase 1: intended purpose y matriz de riesgo (Fase 0) siguen vigentes; hazard log de IA, QMS, DPIA, política de cambio de modelo y documentation pack siguen ⏳. Aportaciones de Fase 1 reutilizables en el documentation pack: ADRs 0050–0120, `docs/architecture/INVENTORY.md` (flujos de datos y secretos), `docs/baseline/FASE1_BASELINE.md` (evidencia de pruebas) y `prompt_version`/`model_used` en auditoría (trazabilidad de versiones de modelo y prompt).

## P0 — Determinar frontera regulatoria
Evaluar explícitamente si las funciones previstas constituyen software sanitario/MDSW y cómo interactúan con GDPR, AI Act, MDR/IVDR y normativa/local hospital policy aplicable.

## P0 — Quality Management
Establecer procesos proporcionales para:
- requirements;
- risk management;
- software lifecycle;
- verification/validation;
- change control;
- supplier/model-provider management;
- incident/CAPA;
- release approvals;
- post-deployment monitoring.

## P0 — Clinical risk management
Hazard log específico de IA:
- hallucination;
- omission;
- stale evidence;
- wrong-patient context;
- automation bias;
- unit/time errors;
- guideline mismatch;
- unauthorized access;
- misleading confidence;
- failure/degraded mode.

Cada hazard: severity, probability, controls, verification y residual risk.

## P0 — DPIA / privacy documentation
Data flow, lawful basis/roles, subprocessors, transfers, retention, rights y mitigations con responsables legales/DPO.

## P0 — Human factors
Validar que la UI diferencia hechos/inferencias, que las advertencias se comprenden y que las fuentes pueden verificarse rápidamente.

## P1 — Model change policy
Un cambio de modelo no es una dependencia menor: registrar versión, evaluación, aprobación, rollout y rollback.

## P1 — Knowledge change policy
Aprobación y retirada de protocolos con clinical owner.

## P1 — Post-deployment monitoring
Feedback, incident signals, performance drift, safety metrics y periodic review.

## P1 — Documentation pack
Mantener arquitectura, threat model, SBOM, risk file, test evidence, model cards/deployment records, data processing inventory, SOPs y release notes.

## Definition of Done
Antes del piloto existe una decisión documentada de intended use/regulatory path, un risk file vivo, procesos de cambio/release y evidencia de validación proporcional al riesgo.
