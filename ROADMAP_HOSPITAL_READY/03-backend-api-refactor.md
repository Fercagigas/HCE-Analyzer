# 03 — Backend y API Refactor

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
