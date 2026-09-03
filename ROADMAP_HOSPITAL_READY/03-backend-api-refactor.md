# 03 — Backend y API Refactor

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Tarea | Estado | Evidencia / nota |
|---|---|---|
| P0.1 Extraer lógica de Streamlit | ✅ | `chathce/{domain,ports,application,gateway}` sin `streamlit`; test AST `tests/unit/test_architecture_boundaries.py` (ADR 0110) |
| P0.2 Crear FastAPI | 🟡 | `/health`, `/ready`, `POST /api/v1/chat`, `POST /api/v1/chat/stream`, `GET /api/v1/patients/{id}/summary`, `GET /api/v1/visualizations/{id}`. Pendientes: `timeline`, `changes`, `insights`, `investigations`, `evidence/{id}` (Fases 3 y 6) |
| P0.3 Streaming SSE | ✅ | Eventos `status`, `tool_call`, `tool_result_summary`, `text_delta`, `complete`, `error`; sin chain-of-thought (ADR 0080) |
| P0.4 Application services | ✅ | `ChatService`, `PatientSummaryService`, `KnowledgeService`, `ConversationService` |
| P0.5 Schemas | ✅ | `ChatRequest`/`ChatResponse` con facts, inferences, evidence, uncertainty, metadata (ADR 0090) |
| P0.6 Correlation IDs | ✅ | `trace_id`/`request_id` en `RequestContext`, cabeceras, respuesta y `AuditEvent` |
| P1.1 Versionado API | ✅ | `/api/v1` |
| P1.2 Timeouts/retries/circuit breakers | 🟡 | Timeout por tool, por llamada y total; 1 reintento por modelo. Circuit breaker pendiente (Fase 2) |
| P1.3 Rate limiting y quotas | 🟡 | Por usuario (`chathce/application/rate_limit.py`); por tenant y función pendiente |
| P1.4 Background jobs | ⏳ | Fase 6 (Investigate) |

## Objetivo
Separar por completo UI, lógica de aplicación, IA y acceso clínico.

## Arquitectura

```text
React
  |
FastAPI
  |
Clinical Application Services
  +-- AI Gateway
  +-- Evidence Engine
  +-- Policy Engine
  +-- Clinical Data Gateway
  +-- Knowledge/RAG
  +-- Audit
```

## Tareas

### P0.1 — Extraer lógica de Streamlit
Ninguna función core debe depender de `st.session_state`, widgets o runtime Streamlit.

### P0.2 — Crear FastAPI
Endpoints conceptuales iniciales:
- `/api/v1/chat`;
- `/api/v1/patients/{id}/summary`;
- `/api/v1/patients/{id}/timeline`;
- `/api/v1/patients/{id}/changes`;
- `/api/v1/patients/{id}/insights`;
- `/api/v1/investigations`;
- `/api/v1/evidence/{id}`;
- `/health`, `/ready`.

### P0.3 — Streaming
SSE para tokens/eventos y estados de alto nivel (`retrieving_evidence`, `checking_guidelines`, `complete`). No exponer chain-of-thought.

### P0.4 — Application services
Evitar que los endpoints llamen directamente al LLM/DB. Crear servicios y contratos tipados.

### P0.5 — Schemas
Pydantic para request/response. Respuestas IA estructuradas con facts, inferences, evidence, uncertainty y metadata.

### P0.6 — Correlation IDs
Cada request, tool call y generación recibe `trace_id` y `request_id`.

### P1.1 — Versionado API
`/api/v1` desde el principio.

### P1.2 — Timeouts/retries/circuit breakers
Aplicarlos por dependencia, evitando retries inseguros.

### P1.3 — Rate limiting y quotas
Por tenant, usuario y función.

### P1.4 — Background jobs
Investigaciones largas, ingestión y tareas pesadas fuera del request web.

## Definition of Done
Frontend intercambiable; core testeable sin UI; todas las dependencias externas pasan por interfaces controladas; cada petición es trazable extremo a extremo.
