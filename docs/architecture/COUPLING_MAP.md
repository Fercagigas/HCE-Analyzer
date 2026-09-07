# Mapa de acoplamiento — estado tras Fase 1

> Versión anterior (Fase 0, referencias por línea al commit `38b94ba`): ver historial de Git. Esta versión describe qué acoplamientos se cerraron en `fase1/foundation` y cuáles quedan, con referencias por símbolo.

## Criterio

Se considera acoplamiento todo lo que impide ejecutar el core sin Streamlit o sustituir Anthropic/Supabase/MIMIC sin tocar casos de uso. Las fronteras propuestas en Fase 0 (`LLMProvider`, `ModelGateway`, `ClinicalDataProvider`, repositorios auxiliares, `RequestContext`) existen ahora en `chathce/`.

Verificación automática: `tests/unit/test_architecture_boundaries.py` (AST + `sys.modules` en subproceso) sobre `chathce/{domain,ports,application,gateway}`.

## Acoplamientos cerrados

| Fase 0 | Frontera | Estado | Dónde |
|---|---|---|---|
| Streamlit como único entry point; composición en `src/core/app.py` y `ui/` | Composition root | Cerrado | `chathce.composition.build_container`; Streamlit vía `chathce.streamlit_adapter.bootstrap` |
| `st.session_state` como fuente de identidad y contexto | `RequestContext` + `IdentityProvider` | Cerrado | `chathce.domain.context`, `chathce.streamlit_adapter.auth_session`, `chathce.api.dependencies` |
| Cookie con usuario completo sin revalidar | Auth revalidada | Cerrado | `StreamlitAuthSession.ensure_authenticated` (ADR 0100) |
| `ClaudeLLMManager` + LangChain `AgentExecutor` controlan el bucle | `LLMProvider` + `ModelGateway` | Cerrado | `chathce.gateway.model_gateway`, `chathce.adapters.anthropic` (ADR 0080) |
| Segundo cliente Anthropic en `QueryAugmenter` | `LLMProvider` inyectado | Cerrado | `services/rag/query_augmenter.py` recibe el provider |
| `DatabaseService` con SQL libre y `ALLOWED_SCHEMAS` | `ClinicalDataProvider` + `ScopeGuard` | Cerrado | `chathce.adapters.supabase.mimic_clinical_data_provider`, `chathce.application.scope_guard` (ADR 0050) |
| Esquema y reglas SQL en el prompt (`PromptManager`) | Prompt desde contratos | Cerrado | `chathce.application.prompts.system_prompt` |
| Tools con schema abierto (`custom_query`, `table_name`, `filters`) | `ToolContract` cerrado | Cerrado | `chathce.domain.tools`, `chathce.gateway.tools` |
| Visualización con `exec` y fallback LLM | Plantillas parametrizadas | Cerrado | `chathce.adapters.visualization.plotly_templates` (ADR 0040) |
| Persistencia de conversación/análisis desde la UI (`_save_to_database`) | Repositorios | Cerrado | `ConversationService`, `AnalysisRepository` |
| Acceso directo a `store.client.table(...)` desde `improved_rag_service` para listados | `KnowledgeRepository` | Cerrado | `chathce.adapters.supabase.knowledge_repository` |
| Caché de respuestas sin usuario/paciente | Eliminada | Cerrado | `tests/security/test_response_cache_scope.py` |
| `config/config.py` con efectos de importación + `settings` global | `get_settings()` | Cerrado | `config/settings.py`, `config/constants.py` |
| Módulos muertos (`medical_agent/`, `auth_service`, `connection_pool_manager`, `rag_service`) | — | Eliminados | WP12 |

## Acoplamientos que permanecen

| Punto | Dependencia | Riesgo | Plan |
|---|---|---|---|
| `services/rag/improved_rag_service.py`, `supabase_vector_store.py` | Cliente Supabase directo y singleton de proceso con modelos locales (CUDA) | Medio: impide varios workers; código legacy fuera de `chathce/` | Migrar a `chathce/adapters/rag`; servicio de embeddings separado (ADR 0110) |
| `src/processors/document_processor.py` y `services/unified_chat/document_manager.py` | Docling/PyPDF2 y RAG directo | Bajo | Port de documentos + `KnowledgeService.ingest` |
| `ui/components/components/document_manager.py` | `get_rag_service()` directo | Bajo | Usar `KnowledgeService` |
| `ui/unified_chat_interface.py` | Consume el dict legacy de `to_legacy_dict` | Bajo: contrato estable y testeado | Consumir `ChatResponse` y retirar `chathce/legacy` |
| `Evaluation/*` | `LegacyAgentFacade.process_message` | Bajo | Runner sobre `ChatService` directamente |
| Cookie de Streamlit | Componente de cookies en JavaScript (no HttpOnly) | Medio | UI tras la API (Fase 4) |
| Clave de servicio de Supabase | Ignora RLS | Alto (mitigado por `ScopeGuard`) | `SUPABASE_CLINICAL_KEY` de solo lectura ahora; RLS por usuario reenviando JWT (Fase 2) |
| RPC `execute_readonly_query` en la base de datos | Sin consumidor en código | Alto hasta aplicar `db/migrations/0002` | Acción del propietario |

## Fronteras y quién las cruza

```
                          import permitido de SDK/framework
chathce/domain, ports, application, gateway .......... ninguno
chathce/adapters/anthropic ........................... anthropic
chathce/adapters/supabase ............................ supabase, postgrest, services.rag (legacy)
chathce/adapters/memory, logging, visualization ...... plotly, pandas
chathce/api .......................................... fastapi, sse_starlette
chathce/streamlit_adapter, ui/, src/core ............. streamlit
services/rag ......................................... supabase, langchain (splitters), sentence-transformers
scripts/ ............................................. supabase (service_role)
```
