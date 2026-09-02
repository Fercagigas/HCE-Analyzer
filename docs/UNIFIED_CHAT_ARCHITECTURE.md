# Arquitectura del chat clínico (ChatHCE)

**Última actualización**: 2 de septiembre de 2026 (cierre de Fase 1)
**ADRs**: 0010, 0050, 0080, 0090, 0100, 0110

## Resumen

El chat de ChatHCE es un caso de uso del core `chathce/` (`ChatService`) que recibe un `RequestContext`, ejecuta un bucle agéntico propio (`ModelGateway`) con herramientas allowlisted (`ToolRegistry`) y devuelve una `ChatResponse` con hechos, inferencias y evidencia. Streamlit y FastAPI son adapters de presentación; Supabase y Anthropic son adapters de infraestructura.

## Diagrama

```
                    Streamlit (ui/*, chathce.streamlit_adapter)      FastAPI (chathce.api)
                                   |                                         |
                                   |  StreamlitChatClient / AsyncRunner       |  Bearer JWT -> RequestContext
                                   v                                         v
                          chathce.composition.build_container(settings) -> Container
                                                      |
                                    ChatService.handle_chat / stream_chat
                                                      |
              +---------------------------------------+----------------------------------+
              v                                       v                                  v
     build_system_prompt(contracts, ctx)      ModelGateway.run(...)              ConversationService
     (plantilla + tools + contexto)            |   cadena de modelos, retry,      (historial resumido,
                                               |   deadline, max_iterations       persist_turn)
                                               v
                                   LLMProvider (adapters.anthropic)
                                               |
                             tool_use -> ToolRegistry.dispatch(ctx, call)
                                  validar -> ToolPolicy -> timeout -> validar salida -> cap -> render -> audit
                                               |
          +---------------------------+--------+-----------------------+
          v                           v                                v
  ScopeGuard(ClinicalDataProvider)  KnowledgeRepository           VisualizationRepository
  adapters.supabase.Mimic...        adapters.supabase (RAG)       adapters.visualization.plotly_templates
```

## Componentes

### RequestContext (`chathce/domain/context.py`)

Inmutable por petición: `tenant_id`, `user_id`, `patient_id` (subject_id como texto), `encounter_id` (hadm_id), `session_id`, `trace_id`, `request_id`, `purpose` (`clinical_care` | `research` | `admin`), `roles`, `channel` (`api` | `streamlit` | `evaluation` | `cli`). `build_context()` exige el rol `researcher` para `purpose=research`.

### ChatService (`chathce/application/chat_service.py`)

- `handle_chat(ctx, request) -> ChatResponse` y `stream_chat(ctx, request) -> AsyncIterator[evento]`.
- Aplica rate limit por `user_id`, construye el prompt del sistema, recupera el historial resumido de la sesión (texto y lista de tools usadas, nunca datos de tools antiguos), ejecuta el gateway, compone `facts`/`inferences`/`evidence`/`uncertainty` y persiste el turno.
- No hay caché de respuestas (la anterior no incluía usuario ni paciente).

### ModelGateway (`chathce/gateway/model_gateway.py`)

- Cadena de modelos de `settings.llm.model_chain` con estado por petición; un reintento por modelo ante errores `retryable`; `StatusEvent(fallback)` al cambiar de modelo.
- `max_iterations=6`, `total_timeout_s=120`, `request_timeout_s=60`.
- Con `tool_use`: despacha en paralelo, añade el mensaje real del asistente y un mensaje `user` con los `tool_result`. Al agotar iteraciones hace una llamada final sin tools.
- Eventos: `status{stage}`, `tool_call`, `tool_result_summary`, `text_delta`, `complete{response}`, `error`. Nunca se emite razonamiento interno.

### ToolRegistry y contratos (`chathce/gateway/tool_registry.py`, `chathce/domain/tools.py`)

- `ToolContract`: nombre, versión, descripción, `input_model` (`extra="forbid"`), `output_model`, `requires_patient_scope`, `requires_purpose`, `timeout_s`, `max_rows <= 200`, `audit_category`. Nombre, descripción y schema no pueden contener términos SQL ni nombres de tabla.
- `dispatch` nunca lanza: `unknown_tool`, `invalid_input`, `scope_refused`, `purpose_refused`, `timeout`, `provider_unavailable`, `not_found`, `internal` se devuelven como `ToolResult(success=False)` y llegan al modelo como `is_error`.
- `render_for_model` envuelve el JSON en `<tool_data tool=... operation=... trust="untrusted_data" count=... truncated=...>` con escape del cierre y recorte a 12 000 caracteres.

### Herramientas registradas (`chathce/gateway/tools/`)

| Tool | Scope | Propósito | Fuente |
|---|---|---|---|
| `get_patient_summary` | paciente | — | provider |
| `get_admission_details` | paciente (hadm_id verificado) | — | provider |
| `get_diagnoses` | paciente | — | provider + d_icd_diagnoses |
| `get_labs`, `search_lab_items` | paciente / ninguno | — | provider + d_labitems |
| `get_medications` | paciente | — | prescriptions (+ administraciones opcionales) |
| `get_icu_stays`, `get_icu_observations` | paciente (stay_id verificado) | — | provider + d_items |
| `search_icd_codes` | ninguno | — | diccionarios |
| `get_dataset_statistics` | ninguno | `research` | RPC `clinical_*_v1` |
| `search_clinical_documents` | ninguno | — | KnowledgeRepository (RAG) |
| `create_visualization` | paciente | — | provider + plantillas Plotly |

### ScopeGuard (`chathce/application/scope_guard.py`)

Envuelve el `ClinicalDataProvider` en el composition root. Sin `patient_id` → `ScopeViolation`; `subject_id` distinto → `patient_mismatch`; `hadm_id`/`stay_id` se resuelven a su paciente antes de consultar; agregados exigen `purpose=research`. Cada rechazo emite `AuditEvent(tool_refused)`.

### Persistencia y auditoría

- `ConversationRepository`, `AnalysisRepository`, `UserPreferencesRepository` sobre `public.*` (adapters Supabase; en memoria para tests).
- `AuditSink` con `AuditEvent` (acción, resultado, componente, identificadores, tool, modelo, tokens, latencia, código de error; atributos con allowlist). Sin mensajes, resultados, emails ni tokens de sesión.

## Respuesta (`chathce/domain/chat.py`)

```json
{
  "success": true,
  "content": "…texto final…",
  "facts": [{"claim_id": "…", "type": "OBSERVED_FACT", "text": "…", "evidence_ids": ["mimic:labevent:123"]}],
  "inferences": [{"claim_id": "…", "type": "AI_INFERENCE", "text": "…", "evidence_ids": []}],
  "evidence": [{"evidence_id": "mimic:labevent:123", "type": "clinical_record", "resource_type": "labevent", "provenance": {"tool_name": "get_labs", "tool_use_id": "…", "trace_id": "…"}}],
  "uncertainty": {"level": "low", "notes": [], "unresolved_tool_errors": 0, "scope_refusals": 0},
  "tool_calls": [{"tool_name": "get_labs", "success": true, "count": 42, "truncated": false, "elapsed_ms": 310}],
  "sources": [], "visualizations": [{"viz_id": "…", "type": "timeline", "title": "…"}],
  "metadata": {"session_id": "…", "trace_id": "…", "request_id": "…", "model_requested": "claude-haiku-4-5-20251001", "model_used": "…", "fallback_used": false, "iterations": 2, "latency_ms": 4200, "prompt_version": "chat-system/1+a1b2c3d4"}
}
```

El contrato dict legacy que consume `ui/unified_chat_interface.py` y `Evaluation/` se obtiene con `chathce.legacy.response_mapper.to_legacy_dict`. En ese dict cada entrada de `tool_results` lleva `raw_output` con el texto visible al modelo (`<tool_data>`) de la tool, obtenido por `ChatService.handle_chat_detailed`; los runners de evaluación lo usan como contexto (RAGAS). La API pública nunca lo expone.

## Canales

- **Streamlit**: `bootstrap.get_container()` (cache_resource), `StreamlitAuthSession` (cookie con refresh token, revalidación), `StreamlitChatClient.send(...)`. Selector de paciente activo y episodio en la barra lateral; modo investigación para `researcher`.
- **FastAPI**: `create_app()`; `lifespan` construye el contenedor y carga el RAG en un hilo; `/ready` 503 hasta entonces. Middleware de correlación (`X-Trace-Id` heredado o nuevo, `request_id`) y auditoría `http_request` sin body. CORS por defecto `localhost:8501`. Arranque con un solo worker.

## Fronteras verificadas

- `tests/unit/test_architecture_boundaries.py`: `chathce/{domain,ports,application,gateway}` no importan `streamlit`, `supabase`, `postgrest`, `anthropic`, `langchain*`.
- `tests/security/test_tool_schema_surface.py` y `tests/unit/gateway/test_prompt_has_no_schema.py`: superficie del modelo sin SQL ni tablas; ningún módulo `langchain_classic`/`langchain_anthropic` cargado.
- `tests/security/test_cross_patient_isolation.py`: rechazo sin paciente, con paciente ajeno y con `hadm_id` ajeno.
