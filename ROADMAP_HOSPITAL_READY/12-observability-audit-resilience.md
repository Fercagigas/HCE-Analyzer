# 12 — Audit, observabilidad y resiliencia

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Área | Estado | Evidencia / nota |
|---|---|---|
| Audit trail P0 | 🟡 | `AuditEvent` (`chathce/domain/audit.py`) registra timestamp, tenant/user/patient/encounter/session, trace/request, acción, tool, operación, categorías de datos, filas, modelo, `prompt_version`, tokens, latencia y código de error, sin PHI; sink JSONL con rotación diaria. Pendientes: documentos/versiones usados, policy decisions explícitas, referencia a evidence snapshot |
| AI observability | ⏳ | Sin dashboards; datos disponibles en `logs/audit/audit.jsonl` |
| Timeouts y circuit breakers | 🟡 | Timeouts por tool, llamada y total; circuit breaker pendiente |
| Kill switch | ⏳ | Fase 2 |
| Graceful degradation | 🟡 | Errores de LLM/datos devuelven `success=False` con sugerencias, tools fallidas quedan en `uncertainty`; retrieval sin LLM pendiente |
| Provider fallback | ✅ | Cadena Haiku → Sonnet → Opus dentro del mismo proveedor (ADR 0080) |
| Backup/restore, incident response | ⏳ | Fase 7; checklist de Supabase cubre contención y rotación |

## Audit trail P0
Registrar de forma segura:
- timestamp;
- tenant/user/patient/encounter/session;
- purpose/action;
- tools invocadas;
- categorías de datos accedidos;
- modelo/model version;
- prompt/config version;
- documentos/versiones usados;
- policy decisions;
- response/evidence snapshot reference;
- latency/errors;
- clinician approval cuando exista.

No convertir el audit log en otra fuga de PHI.

## AI observability
Dashboards para:
- request volume;
- latency P50/P95/P99;
- tool errors;
- FHIR/RAG/LLM failures;
- grounded/citation coverage;
- unsupported claim rate;
- abstention rate;
- prompt injection attempts;
- blocked access attempts;
- model/prompt/version distribution;
- user feedback.

Usar trazas distribuidas (p.ej. OpenTelemetry) y correlation IDs.

## Resiliencia

### P0 — Timeouts y circuit breakers
Evitar cascadas cuando LLM/FHIR/vector DB fallan.

### P0 — Kill switch
Desactivar capacidades generativas/inferenciales de forma centralizada.

### P1 — Graceful degradation
- LLM down -> retrieval/evidence-only si es seguro;
- RAG down -> no afirmar guideline support;
- FHIR partial -> indicar datos incompletos;
- model timeout -> no inventar respuesta.

### P1 — Provider fallback
Solo entre modelos/deployments previamente aprobados para la misma clasificación de datos.

### P1 — Backup/restore
Definir RPO/RTO para configuración, knowledge base, audit y datos propios.

### P1 — Incident response
Playbooks para data leak, prompt attack, compromised document, model regression y external provider outage.

## Definition of Done
Un incidente puede investigarse de extremo a extremo y el hospital puede desactivar la IA o degradar el servicio sin perder control ni producir respuestas engañosas.
