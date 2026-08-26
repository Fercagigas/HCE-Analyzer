# 12 — Audit, observabilidad y resiliencia

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
