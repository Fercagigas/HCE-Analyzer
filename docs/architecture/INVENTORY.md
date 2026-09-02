# Inventario del sistema — cierre de Fase 1

> Rama `fase1/foundation`, 2 de septiembre de 2026. Sustituye al inventario de Fase 0 (commit `38b94ba`, disponible en el historial de Git). Referencias por símbolo, no por línea.

## 1. Runtime y canales

| Canal | Entry point | Autenticación | Notas |
|---|---|---|---|
| Streamlit | `main.py` → `src/core/app.py` → `ui/*` | Supabase Auth; cookie `hce_session` solo con refresh token, revalidada en cada carga | Adapter de presentación (`chathce/streamlit_adapter`) |
| FastAPI | `chathce/api/app.py` (`create_app`) | Bearer JWT de Supabase Auth | `uvicorn --workers 1`; bind `127.0.0.1:8000`; CORS `localhost:8501` |
| Evaluación / CLI | `Evaluation/*`, `scripts/*` | `.env` | `LegacyAgentFacade` con `channel=evaluation` |

## 2. Módulos

### Core (`chathce/`, sin frameworks ni SDKs)

| Paquete | Contenido |
|---|---|
| `domain/` | `RequestContext`, DTOs clínicos (`Patient`, `Admission`, `Condition`, `LabObservation`, `Medication`, `IcuStay`, `IcuObservation`, `Page`, `PatientSummary`, `AdmissionDetails`, `FrequencyResult`, `DatasetSummary`), `Evidence`/`Claim`, `ToolContract`/`ToolResult`, `ChatRequest`/`ChatResponse`/eventos, `AuditEvent`, `Principal`/`AuthSession`, errores, correlación |
| `ports/` | `LLMProvider`, `ClinicalDataProvider`, `KnowledgeRepository`, `IdentityProvider`, `ConversationRepository`, `AnalysisRepository`, `UserPreferencesRepository`, `VisualizationRepository`, `AuditSink` |
| `application/` | `ChatService`, `ConversationService`, `PatientSummaryService`, `KnowledgeService`, `ScopeGuard`, `RateLimiter`, eventos de auditoría, `build_system_prompt` + plantilla |
| `gateway/` | `ModelGateway`, `ToolRegistry`, `ToolPolicy`, `render_for_model`, 12 tools |

### Adapters (`chathce/adapters/`)

| Adapter | Dependencias externas | Sustituye a (Fase 0) |
|---|---|---|
| `anthropic/` | `anthropic` | `ClaudeLLMManager`, `ChatAnthropic` |
| `supabase/` | `supabase`, `postgrest`; `services/rag` para conocimiento | `DatabaseService`, `AuthService`, `supabase_services` |
| `memory/` | — | Fakes para tests y perfiles `fake`/`memory` |
| `logging/audit_sink.py` | — | Nuevo (`jsonl`/`stdout`/`null`) |
| `visualization/plotly_templates.py` | `plotly`, `pandas` | `code_executor`, `visualization_agent` |

### Composición y compatibilidad

- `chathce/composition/container.py`: `build_container(settings, ...)`, perfiles `llm` (anthropic|fake), `clinical` (supabase_mimic|memory), persistencia (supabase|memory). `async_runner.py` para llamadas síncronas.
- `chathce/legacy/`: `LegacyAgentFacade`, `to_legacy_dict` (contrato dict de la UI y `Evaluation/`).
- `services/unified_chat/unified_agent.py`: fachada `UnifiedChatAgent` y `get_shared_container()`.
- `services/auth/session_manager.py`: fachada estática sobre `StreamlitAuthSession`.

### Legacy vigente

| Módulo | Estado |
|---|---|
| `services/rag/` (`improved_rag_service`, `parent_child_chunker`, `supabase_vector_store`, `query_augmenter`, `reranker`) | Vivo, envuelto por `KnowledgeRepository`; `query_augmenter` usa `LLMProvider` |
| `services/unified_chat/document_manager.py`, `src/processors/document_processor.py` | Vivos (ingesta de documentos) |
| `services/supabase_services.py` | Solo `ClinicalDocumentService` |
| `services/cache_manager.py` | Vivo (caché de embeddings), sin uso para respuestas de chat |
| `ui/*`, `src/core/app.py` | Presentación Streamlit |
| `utils/validators/mimic_validator.py` | Herramienta de operación |

### Eliminados en Fase 1

`services/medical_agent/` completo (`llm_manager`, `prompt_manager`, `visualization_agent`, `code_executor`, `database_service`, `error_handler`, tools), `services/auth/auth_service.py`, `services/connection_pool_manager.py`, `services/rag_service.py`, `services/unified_chat/config.py`, `services/unified_chat/tools/`, `config/config.py`, `tests/test_system.py`, `tests/test_database.py`.

## 3. Datos

| Almacén | Contenido | Acceso |
|---|---|---|
| Supabase `mimiciv_hosp` (15 tablas), `mimiciv_icu` (3) | MIMIC-IV Clinical Demo 2.2, 100 pacientes, ~1,48 M filas | Solo `MimicClinicalDataProvider` (PostgREST, `select` explícito, filtro por `subject_id`) y RPC `clinical_*_v1` |
| Supabase `public` | `users`, `chat_sessions`, `chat_messages`, `analyses`, `user_preferences`, `clinical_documents`, `rag_chunks` | Repositorios Supabase; RAG legacy |
| Supabase Auth | Usuarios, JWT, refresh tokens | `SupabaseIdentityProvider` |
| Memoria de proceso | Diccionarios MIMIC (1 h), visualizaciones (TTL), caché de tokens verificados (60 s), rate limit | — |
| `logs/audit/audit.jsonl` | Eventos de auditoría sin PHI, rotación diaria | `JsonlFileAuditSink` |
| `tests/fixtures/mimic/` | 3 pacientes, 17 tablas, salidas esperadas congeladas | Tests |
| Local | `Guías/` (PDF para indexar), `_mimic_iv_extract/` (ignorado), `data/` | Scripts |

Categorías de datos que salen del proceso: hacia Anthropic viajan el prompt, el mensaje del usuario, el historial resumido y los resultados de tools del turno (datos clínicos desidentificados del paciente activo). Hacia Supabase, consultas filtradas y persistencia de la conversación.

## 4. Secretos y claves

| Variable | Uso | Alcance recomendado |
|---|---|---|
| `ANTHROPIC_API_KEY` | `AnthropicLLMProvider` | Runtime |
| `SUPABASE_URL`, `SUPABASE_KEY` | Auth, `public.*`, RAG | Runtime; objetivo bajo privilegio (hoy `service_role`) |
| `SUPABASE_CLINICAL_KEY` | `MimicClinicalDataProvider` | Runtime; rol de solo lectura sobre `mimiciv_*` (pendiente de crear) |
| `SUPABASE_SERVICE_ROLE_KEY` | Scripts de carga | Nunca en runtime |
| `HUGGINFACEHUB_API_TOKEN` | Descarga de modelos HF (opcional) | Runtime |
| `HCE_TEST_USER_EMAIL` / `HCE_TEST_USER_PASSWORD` | Tests live de identidad/API | Fuera del repo |

Eliminados: `SECRET_KEY`, `OPENAI_API_KEY` (sin consumidores). Ningún secreto se escribe en auditoría ni en logs; `.env` y `.streamlit/secrets.toml` en `.gitignore`.

## 5. Dependencias externas (runtime)

| Servicio | Dónde se usa | Fallo → comportamiento |
|---|---|---|
| Anthropic API | `chathce/adapters/anthropic` | Fallback por cadena; `LLM_UNAVAILABLE` 503 / `success=False` con sugerencias |
| Supabase PostgREST | `chathce/adapters/supabase`, `services/rag` | `CLINICAL_DATA_UNAVAILABLE` 503; tools devuelven `provider_unavailable` |
| Supabase Auth | Identidad | 401 en API; sesión limpiada en Streamlit |
| Hugging Face Hub | Descarga inicial de embeddings/reranker | RAG no disponible; `/ready` 503 |

Paquetes clave (`requirements.txt`): `anthropic>=0.77,<1`, `fastapi`, `uvicorn`, `sse-starlette`, `pydantic`/`pydantic-settings`, `supabase`, `streamlit`, `plotly`, `pandas`, `langchain`/`langchain-community` (solo RAG), `sentence-transformers`, `docling`, `pytest`, `pytest-cov`, `pytest-asyncio`, `hypothesis`. Retirados: `langchain-classic`, `langchain-anthropic`, `crewai*`, `openai`, `pathlib`.

## 6. Superficie expuesta al modelo

- 12 tools con schemas cerrados; ningún parámetro acepta SQL, tabla o filtro libre.
- Prompt del sistema generado desde contratos; sin esquema de base de datos.
- Resultados como `<tool_data trust="untrusted_data">`; fragmentos RAG como `<document>`.
- Historial resumido; sin datos de tools de turnos anteriores.

## 7. Tests y evaluación

- `tests/`: 278 tests (271 pasan, 7 se saltan sin `HCE_RUN_INTEGRATION`), cobertura 56 % (`docs/baseline/FASE1_BASELINE.md`).
- `Evaluation/`: golden set v2 (40 preguntas MIMIC-IV, 20 pendientes de validación clínica), payloads de seguridad (SQL, inyección, alucinación, cross-patient, scope ausente), runners RAGAS/seguridad/latencia/casos.
