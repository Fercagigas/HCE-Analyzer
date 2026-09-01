# Inventario de arquitectura de ChatHCE

> **Addendum (sep 2026):** La fuente clínica se migró de MIMIC-IV-ED (schema `mimic_ed`, 6 tablas) a **MIMIC-IV Clinical Demo 2.2** (`mimiciv_hosp` + `mimiciv_icu`, 18 tablas cargadas). Las referencias a `mimic_ed`, `edstays`, `triage`, `vitalsign`, `medrecon`, `pyxis` y `diagnosis` de este inventario reflejan el estado del commit `38b94ba` y ya **no aplican** al runtime actual. El nombre de esquema y el allowlist quedan encapsulados en `DatabaseService.TABLE_SCHEMA`. Ver `docs/MIGRACION_MIMIC_IV.md` y `docs/ESTADO_ACTUAL.md`.

## Alcance y fotografía analizada

Este documento describe el estado real del repositorio en el commit `38b94ba856998eef5cfffa21bc8b03cde510f1c3`. Es un inventario de Fase 0: no describe todavía la arquitectura objetivo ni presupone que una dependencia declarada esté integrada.

La aplicación ejecutable es un monolito Streamlit. `main.py` configura logging e invoca el entry point Streamlit (`main.py:13-38`); `src/core/app.py` resuelve autenticación y navegación y monta las pantallas (`src/core/app.py:14-35`, `src/core/app.py:134-239`). Aunque `fastapi` y `uvicorn` están declarados, no existe una instancia `FastAPI`, router ni endpoint en `main.py`, `src/`, `services/` o `ui/`.

Resumen de la arquitectura observada:

```text
Streamlit runtime
  main.py -> src/core/app.py
    -> SessionManager -> AuthService ---------------------> Supabase Auth/public
    -> UnifiedChatInterface
         -> UnifiedChatAgent -> ClaudeLLMManager --------> Anthropic
              -> DatabaseTool -> DatabaseService --------> Supabase mimic_ed
              -> RAGTool -> ImprovedRAGService ----------> Supabase rag_chunks
              |              -> embeddings/reranker -----> modelos Hugging Face
              |              -> QueryAugmenter ----------> Anthropic
              -> VisualizationCollaborationTool
                             -> DatabaseService ----------> Supabase mimic_ed
                             -> VisualizationAgent -------> Anthropic (fallback)
         -> DocumentManager -> DocumentProcessor
                            -> ImprovedRAGService ---------> Supabase rag_chunks
                            -> ClinicalDocumentService ---> Supabase public
         -> AuthService/AnalysisService ------------------> Supabase public
```

## Inventario de módulos

### `src/`

| Módulo | Responsabilidad real | Quién lo llama / a quién llama | Lógica relevante |
|---|---|---|---|
| `src/core/app.py` | Composición de pantallas, autenticación, navegación y manejo de errores de la aplicación Streamlit. | Lo llama `main.py:31-38`; importa de forma diferida `SessionManager` y toda la UI en `src/core/app.py:14-35`. | Decide el flujo autenticado y el modo de pantalla en `src/core/app.py:163-216`; es lógica de aplicación mezclada con UI. |
| `src/processors/document_processor.py` | Extracción OCR/texto, segmentación y control de memoria para PDF. | Lo crean `ImprovedRAGService` (`services/rag/improved_rag_service.py:156-158`) y `DocumentManager` (`services/unified_chat/document_manager.py:32-34`). | Selección Docling/fallback y chunking en `src/processors/document_processor.py:62-122`, `src/processors/document_processor.py:124-176`; fallback PyPDF2 en `src/processors/document_processor.py:256-259`, `src/processors/document_processor.py:297-322` y `src/processors/document_processor.py:675-677`. |

### `services/`

| Módulo o grupo | Responsabilidad real | Dependencias / consumidores | Lógica de negocio hoy |
|---|---|---|---|
| `services/unified_chat/unified_agent.py` | Orquestador principal: crea LLM, prompt y tools; valida/rate-limita, conserva contexto, ejecuta el agente, formatea, mide y cachea respuestas. | Lo crea `ui/unified_chat_interface.py:102-115`; llama a `ClaudeLLMManager`, `PromptManager`, Database/RAG/Visualization tools (`services/unified_chat/unified_agent.py:42-121`) y LangChain AgentExecutor (`services/unified_chat/unified_agent.py:261-300`). | Es el núcleo de aplicación actual: selección de tools vía prompt (`services/unified_chat/unified_agent.py:123-259`) y procesamiento (`services/unified_chat/unified_agent.py:307-456`). |
| `services/unified_chat/tools/database_tool.py` | Contrato de tool que expone consultas clínicas predefinidas y SQL `custom` al modelo. | Lo monta `UnifiedChatAgent` en `services/unified_chat/unified_agent.py:91-96`; llama a `DatabaseService`. | Schema MIMIC y reglas entregadas al LLM (`services/unified_chat/tools/database_tool.py:19-168`), routing (`:174-229`), validaciones y SQL libre (`:426-645`). |
| `services/unified_chat/tools/rag_tool.py` | Tool RAG con expansión de consulta, búsqueda múltiple, deduplicación y formato de fuentes. | Lo monta `UnifiedChatAgent` (`services/unified_chat/unified_agent.py:101-106`); llama a `QueryAugmenter` e `ImprovedRAGService` (`services/unified_chat/tools/rag_tool.py:54-60`). | Política de cuándo buscar y flujo de retrieval (`services/unified_chat/tools/rag_tool.py:63-203`). |
| `services/unified_chat/document_manager.py` | Ciclo de vida de documentos: validar, extraer, re-chunkear, indexar, listar y eliminar. | Lo crea la UI (`ui/unified_chat_interface.py:125-138`); llama a `DocumentProcessor`, RAG y `ClinicalDocumentService`. | Flujo de ingesta (`services/unified_chat/document_manager.py:46-176`) y sincronización de metadatos (`:460-506`). |
| `services/unified_chat/config.py` | Segundo modelo de configuración específico del chat. | No aparece importado por el flujo principal; coexiste con `config/settings.py`. | Configuración duplicada y potencialmente divergente (`services/unified_chat/config.py:13-178`). |
| `services/medical_agent/llm_manager.py` | Inicialización Claude, cadena de fallback, retry/backoff y traducción de errores. | Lo usa `UnifiedChatAgent` (`services/unified_chat/unified_agent.py:46-49`) y parcialmente visualización. | Política de proveedor/modelo (`services/medical_agent/llm_manager.py:35-213`, `:265-358`) y LLM separado para visualización (`:381-447`). |
| `services/medical_agent/prompt_manager.py` | Construye y cachea identidad, schema MIMIC, documentación de tools, reglas SQL y directivas clínicas. | Lo crea `UnifiedChatAgent` (`services/unified_chat/unified_agent.py:54-60`) y `VisualizationAgent`. | Gran parte de la política del agente está en prompts: contexto/tablas (`services/medical_agent/prompt_manager.py:144-257`, `:536-751`), guardrails (`:301-499`) y conteo Anthropic (`:870-900`). |
| `services/medical_agent/services/database_service.py` | Acceso Supabase a MIMIC, validación de tabla/filtros, agregación clínica y formateo de signos vitales. También ejecuta SQL libre por RPC. | Lo usan ambos database tools y `VisualizationCollaborationTool`. | Allowlist y conexión (`services/medical_agent/services/database_service.py:130-204`), acceso genérico (`:421-495`), resúmenes/transformaciones (`:499-1030`, `:1041-1243`) y SQL RPC (`:1245-1305`). |
| `services/medical_agent/tools/claude_adapter.py` | Base de tools Pydantic/LangChain con nombres y schema orientados a Claude. | Base de los tools de base de datos, RAG y visualización (`services/medical_agent/tools/claude_adapter.py:17-224`). | Adaptación de contratos de tool mezclada con semántica de proveedor. |
| `services/medical_agent/tools/database_tool_claude.py` | Tool legado alternativo para consultas MIMIC, incluido modo SQL `custom`. | Exportado por `services/medical_agent/tools/__init__.py:8`; no forma parte del agente unificado actual. | Routing clínico y paso de SQL libre a `DatabaseService` (`services/medical_agent/tools/database_tool_claude.py:18-63`, `:67-125`). |
| `services/medical_agent/tools/visualization_collaboration_tool.py` | Tool que decide/fetch de datos MIMIC y coordina la generación de figuras. | Lo monta `UnifiedChatAgent` (`services/unified_chat/unified_agent.py:111-116`); llama a `DatabaseService`, `VisualizationAgent` y `VisualizationStore` (`services/medical_agent/tools/visualization_collaboration_tool.py:75-184`). | Selección de fuente/metricas y agregaciones (`services/medical_agent/tools/visualization_collaboration_tool.py:215-637`). |
| `services/medical_agent/visualization_agent.py` | Pipeline template-first y fallback LLM que genera código Plotly. | Lo crea el tool de colaboración. Llama a selector, preprocesador, templates, validador/ejecutor y Anthropic (`services/medical_agent/visualization_agent.py:34-150`). | Decisión template/LLM y generación (`services/medical_agent/visualization_agent.py:150-307`, `:468-916`). |
| `services/medical_agent/code_executor.py` | Valida AST y ejecuta código de visualización en un namespace restringido. | Lo llama `VisualizationAgent` (`services/medical_agent/visualization_agent.py:21`, `:618-824`). | Seguridad de código generado y ejecución (`services/medical_agent/code_executor.py:26-439`). |
| `services/medical_agent/data_preprocessor.py` | Limpieza, coerción, muestreo y métricas de calidad de DataFrames. | Lo usa `VisualizationAgent` (`services/medical_agent/visualization_agent.py:59`). | Transformación de datos para visualización (`services/medical_agent/data_preprocessor.py:69-473`). |
| `services/medical_agent/visualization_selector.py`, `visualization_templates.py` | Heurísticas de selección y plantillas Plotly. | Los usa `VisualizationAgent` (`services/medical_agent/visualization_agent.py:58-60`). | Reglas de presentación y generación determinista (`services/medical_agent/visualization_selector.py:37-325`; `services/medical_agent/visualization_templates.py:25-717`). |
| `services/medical_agent/visualization_store.py`, `visualization_handler.py` | Store en memoria de figuras y render/download específico de Streamlit. | El tool persiste en `VisualizationStore`; la UI recupera por ID (`ui/unified_chat_interface.py:1118-1214`). | Persistencia efímera (`services/medical_agent/visualization_store.py:35-307`) y presentación (`services/medical_agent/visualization_handler.py:139-320`). |
| `services/medical_agent/agent_performance_monitor.py`, `error_handler.py` | Métricas en memoria/decoradores y normalización de errores. | Los usa `UnifiedChatAgent` (`services/unified_chat/unified_agent.py:19-20`, `:66-68`). | Observabilidad y respuesta de error (`services/medical_agent/agent_performance_monitor.py:60-417`; `services/medical_agent/error_handler.py:74-424`). |
| `services/rag/improved_rag_service.py` | Fachada RAG y singleton: processor, parent-child chunking, embeddings, store y reranker. | La usan RAGTool, ambos document managers y `services/rag_service.py`. | Ingesta y retrieval (`services/rag/improved_rag_service.py:39-162`, `:166-440`). |
| `services/rag/parent_child_chunker.py` | Produce chunks padre/hijo y metadatos. | Lo crea `ImprovedRAGService` (`services/rag/improved_rag_service.py:92-96`). | Segmentación jerárquica (`services/rag/parent_child_chunker.py:15-470`). |
| `services/rag/supabase_vector_store.py` | Adapter pgvector/FTS, aunque no implementa una interfaz. | Lo crea `ImprovedRAGService` (`services/rag/improved_rag_service.py:141-143`). | Embeddings/chunks CRUD y RPC de búsqueda (`services/rag/supabase_vector_store.py:38-160`, `:162-377`). |
| `services/rag/query_augmenter.py` | Multi-query y HyDE con Anthropic directo. | Lo crea `RAGTool` (`services/unified_chat/tools/rag_tool.py:59-60`). | Dos generaciones LLM por consulta (`services/rag/query_augmenter.py:49-191`). |
| `services/rag/reranker.py` | Reranking local con cross-encoder descargado de Hugging Face. | Lo crea `ImprovedRAGService` (`services/rag/improved_rag_service.py:145-154`). | Carga/model serving local y scoring (`services/rag/reranker.py:15-179`). |
| `services/rag_service.py` | Wrapper de compatibilidad sobre `ImprovedRAGService`. | Lo usa `scripts/index_guias.py:45-71`. | No añade dominio; delega (`services/rag_service.py:21-72`). |
| `services/auth/auth_service.py` | Auth Supabase, perfil propio, sesiones y mensajes. | Lo instancia `SessionManager` (`services/auth/session_manager.py:35-36`). | Identidad y persistencia están unidas al SDK Supabase (`services/auth/auth_service.py:17-601`). |
| `services/auth/session_manager.py` | Fachada de auth/sesión que guarda servicios, usuario, preferencias y sesión activa dentro de `st.session_state`; usa cookies Streamlit. | La llaman `src/core/app.py` y componentes UI. Delega a `AuthService` y `UserPreferencesService`. | Lógica de sesión y autorización mezclada con runtime (`services/auth/session_manager.py:12-400`). |
| `services/supabase_services.py` | CRUD de `clinical_documents`, `analyses` y `user_preferences`. | Lo llaman DocumentManager, SessionManager y UnifiedChatInterface. | Repositorios concretos sin interfaces (`services/supabase_services.py:14-417`). |
| `services/connection_pool_manager.py` | Pool genérico en memoria para clientes Supabase y HTTP de Anthropic/Hugging Face. | Instancia global importada por `DatabaseService` y `services/__init__.py`. | Creación de proveedores y health checks (`services/connection_pool_manager.py:282-451`). |
| `services/cache_manager.py`, `rate_limiter.py` | Caché/persistencia opcional y rate limits locales en memoria. | Los usa `UnifiedChatAgent`; configuración global. | Políticas transversales dentro del proceso (`services/cache_manager.py:86-612`; `services/rate_limiter.py:54-296`). |

### `ui/`

| Módulo | Responsabilidad y llamadas | Observación |
|---|---|---|
| `ui/unified_chat_interface.py` | Pantalla principal; crea agente/document manager (`:37-159`), recoge chat y ejecuta el core (`:914-1028`), construye contexto (`:1296-1330`) y persiste mensajes/análisis (`:1332-1448`). | Concentra UI, estado, casos de uso, métricas y persistencia. Es el mayor punto de extracción de Fase 1. |
| `ui/components/components/auth_pages.py` | Formularios login/registro/logout; llama a `SessionManager` (`ui/components/components/auth_pages.py:9-223`). | UI pura salvo validación/form flow. |
| `ui/components/components/sidebar.py` | Usuario, navegación, sesiones recientes y borrado (`ui/components/components/sidebar.py:10-212`). | Cambia `st.session_state` y llama a sesión/auth. |
| `ui/components/components/document_manager.py` | Segunda UI completa de ingesta, búsqueda, listado, estadísticas y reset RAG (`ui/components/components/document_manager.py:19-685`). | Duplica parte de `UnifiedChatInterface` y llama al servicio RAG directamente. |
| `ui/components/components/footer.py` | Footer y debug UI (`ui/components/components/footer.py:9-77`). | Presentación Streamlit. |

### `utils/`

| Módulo | Responsabilidad y llamadas |
|---|---|
| `utils/helpers/utils.py` | Helpers de archivos, texto y validación (`utils/helpers/utils.py:18-241`); consumidos por la UI de documentos. |
| `utils/validators/mimic_validator.py` | Valida conteos, columnas e integridad de las seis tablas MIMIC mediante un cliente Supabase directo (`utils/validators/mimic_validator.py:15-209`). Lo llama `scripts/validate_mimic.py:13-28`. |
| `utils/formatters/` | Sólo contiene `__init__.py`; no hay implementación. |

### `scripts/`

| Script | Entrada/salida |
|---|---|
| `scripts/index_guias.py` | Lee tres PDF conocidos de `guias/` y los entrega a `RAGService`, que escribe chunks/embeddings en Supabase (`scripts/index_guias.py:21-88`). |
| `scripts/clear_rag.py` | Crea cliente Supabase y elimina todo `rag_chunks` con confirmación interactiva (`scripts/clear_rag.py:20-98`). |
| `scripts/test_rag_quick.py` | Crea el agente real, llama Anthropic/RAG y evalúa cuatro preguntas (`scripts/test_rag_quick.py:54-153`). No es test aislado. |
| `scripts/validate_mimic.py` | Ejecuta `MimicValidator` contra Supabase (`scripts/validate_mimic.py:13-46`). |

### `config/`

| Módulo | Responsabilidad | Riesgo observado |
|---|---|---|
| `config/settings.py` | Árbol Pydantic de DB, AI, app, seguridad, RAG, agentes, performance, visualización y chat; instancia global en `config/settings.py:469-499`. | Cada submodelo vuelve a declarar `.env`; hay alias duplicados y campos obligatorios que no coinciden con `.env.example`. |
| `config/config.py` | Carga `dotenv`, reexporta secretos/constantes legacy, RAG config y crea directorios al importar (`config/config.py:11-16`, `:27-67`, `:80-90`). | Efectos laterales de importación y segunda ruta de carga/configuración. |
| `config/constants.py` | Nombre, versión, textos y constantes estáticas (`config/constants.py:1-67`). | Sin proveedor externo. |
| `config/logging_config.py` | Logging de consola/fichero/structlog y sesiones debug (`config/logging_config.py:47-305`). | El runtime crea logs antes de autenticar (`main.py:13-27`); revisar PHI en mensajes de log. |

## Dónde reside hoy la lógica de negocio

No existe una capa de dominio o application services independiente. La lógica se reparte así:

- Orquestación conversacional y política de tools: `services/unified_chat/unified_agent.py:80-456` y prompts en `services/medical_agent/prompt_manager.py:144-827`.
- Operaciones clínicas y normalización ad hoc: `services/medical_agent/services/database_service.py:499-1243`.
- Contrato que ve el modelo, incluido SQL libre: `services/unified_chat/tools/database_tool.py:19-168`.
- Retrieval/ingesta: `services/rag/improved_rag_service.py:166-440`, `services/unified_chat/tools/rag_tool.py:105-203` y `services/unified_chat/document_manager.py:46-176`.
- Sesión, identidad y conversaciones: `services/auth/session_manager.py:23-400`, `services/auth/auth_service.py:68-601` y `ui/unified_chat_interface.py:835-1028`, `:1296-1448`.
- Caso de uso de visualización: `services/medical_agent/tools/visualization_collaboration_tool.py:215-637` y `services/medical_agent/visualization_agent.py:150-916`.

La consecuencia es que ninguna de esas capacidades puede exponerse hoy por FastAPI sin importar runtime Streamlit, SDKs concretos o modelos/tablas de proveedor.

## Inventario de datos

### MIMIC-IV-ED demo 2.2

El repositorio contiene seis CSV bajo `mimic-iv-ed-demo-2.2/ed/`: `diagnosis`, `edstays`, `medrecon`, `pyxis`, `triage` y `vitalsign`. No hay ninguna llamada `read_csv` ni referencia a esa ruta en el runtime o scripts Python actuales: los CSV son fuente versionada/de referencia, pero la aplicación consulta una copia cargada en Supabase.

El contrato real de columnas está codificado en `utils/validators/mimic_validator.py:18-35` y repetido en el prompt/tool (`services/unified_chat/tools/database_tool.py:100-124`):

| Tabla | Contenido | Claves/campos observados | Entrada y salida en runtime |
|---|---|---|---|
| `mimic_ed.edstays` | Episodios de urgencias y demografía limitada | `subject_id`, `hadm_id`, `stay_id`, tiempos, `gender`, `race`, transporte, destino | Supabase REST en `DatabaseService.get_table_data`; alimenta resúmenes, detalle y agente. |
| `mimic_ed.triage` | Constantes iniciales, dolor, acuidad y motivo | `subject_id`, `stay_id`, temperatura, FC, FR, SpO2, PA, `chiefcomplaint` | Recuperación clínica/visualización. |
| `mimic_ed.vitalsign` | Serie temporal de constantes | `subject_id`, `stay_id`, `charttime`, constantes, ritmo, dolor | Recuperación clínica y gráficos. |
| `mimic_ed.diagnosis` | Diagnósticos ED | IDs, secuencia, código/versión/título ICD | Búsqueda y agregaciones. |
| `mimic_ed.medrecon` | Medicación habitual reconciliada | IDs, tiempo, nombre, GSN/NDC/ETC | Historial farmacológico. |
| `mimic_ed.pyxis` | Medicación dispensada en urgencias | IDs, tiempo, nombre, GSN | Historial y agregaciones. |

Todas pasan por acceso genérico a tabla en `services/medical_agent/services/database_service.py:421-495`. Los resúmenes combinan tablas en `services/medical_agent/services/database_service.py:499-671` y `:675-878`. El modo `custom` sale por la RPC `execute_readonly_query` (`services/medical_agent/services/database_service.py:1245-1305`).

Hay deriva de schema: el runtime principal selecciona explícitamente `mimic_ed` (`services/medical_agent/services/database_service.py:138-145`, `:450-473`), pero `MimicValidator` consulta tablas sin `.schema()` y sus comentarios dicen `public` (`utils/validators/mimic_validator.py:50-73`). El README también conserva índices `public.*` (`README.md:249-280`). La fuente y el schema canónicos se resolverán en la línea de trabajo separada de migración integral de Supabase; este inventario no selecciona una alternativa.

### Supabase Auth y tablas de producto

| Recurso | Datos | Escritura/lectura |
|---|---|---|
| Supabase Auth | email/password, usuario y sesión del proveedor | Login/signup/logout/refresh/reset en `services/auth/auth_service.py:68-309`. |
| `public.users` | perfil (`id`, email, nombre, especialidad, licencia, login) | `services/auth/auth_service.py:91-167`, `:208-219`, `:450-477`. |
| `public.chat_sessions` | usuario, título, timestamps | CRUD/listado/estadísticas en `services/auth/auth_service.py:311-376`, `:483-601`. |
| `public.chat_messages` | sesión, rol, contenido y metadata (tools, fuentes, modelo, latencia) | `services/auth/auth_service.py:378-448`; el contenido se construye en `ui/unified_chat_interface.py:1332-1389`. |
| `public.clinical_documents` | filename, título, tipo, especialidad, ruta temporal, metadata, procesado | `services/supabase_services.py:14-191`; sincronizado desde `services/unified_chat/document_manager.py:460-506`. |
| `public.analyses` | usuario, tipo, pregunta/contenido, resultados JSON y documento opcional | `services/supabase_services.py:194-318`; la UI decide tipo y payload en `ui/unified_chat_interface.py:1395-1445`. |
| `public.user_preferences` | JSON de preferencias por usuario | `services/supabase_services.py:321-417`; cargado en `st.session_state` por `services/auth/session_manager.py:352-397`. |

### Vector store / conocimiento

El vector store no es un sistema separado: es Supabase PostgreSQL con pgvector/tsvector.

- Tabla `public.rag_chunks` (`services/rag/supabase_vector_store.py:38-50`) con `document_id`, `chunk_id`, `parent_id`, contenido, embedding, metadata, flag padre, filename, especialidad y tipo (`services/rag/supabase_vector_store.py:96-145`).
- RPC `hybrid_search` con embedding, texto, `match_count` y RRF (`services/rag/supabase_vector_store.py:275-324`).
- RPC `vector_search` como fallback (`services/rag/supabase_vector_store.py:334-377`).
- Los embeddings `sentence-transformers/all-MiniLM-L6-v2` se generan localmente (`services/rag/improved_rag_service.py:99-139`); el reranker local usa `cross-encoder/ms-marco-MiniLM-L-6-v2` (`services/rag/reranker.py:15-58`). Ambos pueden descargar artefactos desde Hugging Face en la primera carga.
- Los documentos entran desde upload temporal o `guias/`, se extraen, se trocean, se vectorizan y salen como fragmentos/fuentes hacia el agente (`services/unified_chat/document_manager.py:111-166`; `services/rag/improved_rag_service.py:308-440`).

### Egresos y persistencia no obvia

- Anthropic recibe el mensaje, historial y resultados de tools dentro del AgentExecutor (`services/unified_chat/unified_agent.py:261-300`, `:383-394`, `:458-478`). La expansión RAG envía además la consulta a Anthropic dos veces (multi-query y HyDE) (`services/rag/query_augmenter.py:114-191`).
- La caché en proceso usa como clave el mensaje y el contexto serializado (`services/unified_chat/unified_agent.py:366-373`) y guarda la respuesta (`:412-415`); puede contener información clínica.
- Logs registran previews de mensajes y consultas (`services/unified_chat/unified_agent.py:332`; `services/unified_chat/tools/database_tool.py:454`; `services/medical_agent/services/database_service.py:1277`).
- Visualizaciones y su data permanecen en singletons/memoria y se copian a `st.session_state` (`services/medical_agent/visualization_store.py:35-307`; `ui/unified_chat_interface.py:1118-1214`).

## Inventario de secretos

No se documenta ningún valor. La revisión de ficheros versionados no encontró una credencial real de alta confianza; los patrones de README y `.env.example` son ejemplos/placeholders. `.env` y `.streamlit/secrets.toml` están ignorados (`.gitignore:1-3`, `.gitignore:88-89`) y no están versionados en esta fotografía.

| Variable | Necesidad actual | Dónde se declara/carga | Dónde se consume |
|---|---|---|---|
| `SUPABASE_URL` | Obligatoria para importar `config.settings` y para todos los flujos Supabase. | `config/settings.py:13`, con `.env` en `config/settings.py:16-20`; ruta legacy `load_dotenv`/`os.getenv` en `config/config.py:13-16`, `:31`. Documentada en `.env.example:15`. | Pool (`services/connection_pool_manager.py:331-341`), MIMIC (`services/medical_agent/services/database_service.py:180-204`), vector store (`services/rag/supabase_vector_store.py:62-68`), auth y repositorios legacy. |
| `SUPABASE_KEY` | Obligatoria; el código no distingue anon key de service-role key. | `config/settings.py:14`, `:16-20`; ruta legacy `config/config.py:13-16`, `:32`. Documentada en `.env.example:16`. | Mismos puntos que `SUPABASE_URL`. |
| `ANTHROPIC_API_KEY` | Obligatoria por duplicado para RAG y agente Claude. | `config/settings.py:88`, `:117-121`; `config/settings.py:169`, `:198-202`; también opcional en `config/settings.py:25`. Ruta legacy en `config/config.py:30`. Documentada en `.env.example:11`. | LLM manager (`services/medical_agent/llm_manager.py:55-72`), query augmenter (`services/rag/query_augmenter.py:57-60`), visualización (`services/medical_agent/visualization_agent.py:81-147`), prompt token count (`services/medical_agent/prompt_manager.py:54-61`) y pool HTTP (`services/connection_pool_manager.py:354-410`). |
| `SECRET_KEY` | Declarada obligatoria al construir settings, pero no aparece consumida fuera de configuración. | `config/settings.py:43`, con `.env` en `config/settings.py:45-49`. **No está documentada en `.env.example`.** | Ningún uso runtime encontrado. Bloquea importaciones aunque no protege todavía sesiones/tokens. |
| `HUGGINFACEHUB_API_TOKEN` | Opcional para descarga de modelos; el nombre contiene la grafía legacy `HUGGINFACE`. | `config/settings.py:26`, `:31-35`; alias legacy en `config/config.py:33`; `.env.example:20`. | Embeddings (`services/rag/improved_rag_service.py:108-119`) y pool opcional (`services/connection_pool_manager.py:360-362`, `:412-447`). |
| `OPENAI_API_KEY` | Opcional/declarada, sin cliente OpenAI en el runtime. | `config/settings.py:24`; sólo comentada en `.env.example:296`. | Ningún uso encontrado. |
| `SMTP_PASSWORD` | Opcional/declarada, sin envío SMTP implementado. | `config/settings.py:74`; sólo comentada en `.env.example:302`. | Ningún uso encontrado. |
| `ENCRYPTION_KEY` | Sólo expectativa documental; no se carga. | Comentada en `.env.example:285`. | Ningún uso encontrado. |

Hallazgos de seguridad/configuración:

1. **Crítico — SQL libre controlable por el modelo.** El tool anuncia y acepta `custom_query` (`services/unified_chat/tools/database_tool.py:48-50`, `:146-166`), lo valida con regex/listas (`:470-645`) y lo ejecuta mediante `execute_readonly_query` (`services/medical_agent/services/database_service.py:1245-1287`). No hay `RequestContext`, scope obligatorio de paciente/episodio ni contrato clínico.
2. **Crítico — restauración de autenticación confiando en cookie.** Un valor de cookie basta para marcar `authenticated=True` y poblar el usuario (`services/auth/session_manager.py:51-69`); la cookie guarda el diccionario de usuario (`services/auth/session_manager.py:77-86`) sin revalidación visible de una sesión Supabase.
3. **Crítico — protecciones web desactivadas.** Streamlit configura `enableCORS=false` y `enableXsrfProtection=false` (`.streamlit/config.toml:7-10`).
4. **Alto — configuración no reproducible.** `SECRET_KEY` es obligatoria pero falta en `.env.example`; `ANTHROPIC_API_KEY` está declarada en tres submodelos y existen dos mecanismos de carga (`config/settings.py` y `config/config.py`).
5. **Alto — naturaleza de `SUPABASE_KEY` no impuesta.** El mismo secreto sirve Auth, datos clínicos, tablas públicas, vector store y RPC SQL. El código no permite verificar por tipo si se ha configurado una clave de mínimo privilegio.

## Inventario de dependencias

`requirements.txt` y el bloque `pip` de `environment.yml` son casi copias. Sólo Python está fijado (`python=3.11`, `environment.yml:6`). No hay lockfile, hashes ni versión exacta de paquetes Python, por lo que el entorno no es reproducible.

| Grupo | Dependencias declaradas | Restricción |
|---|---|---|
| Framework | `streamlit`, `fastapi`, `uvicorn[standard]` | Sin versión (`requirements.txt:2-4`). FastAPI/Uvicorn no tienen implementación actual. |
| IA/agentes | `openai`; `anthropic`, `langchain`, `langchain-community`, `langchain-anthropic`, `langchain-huggingface`, `sentence-transformers`, `tiktoken`, `crewai`, `crewai-tools` | Sólo mínimos `>=` para todas salvo `openai`; ningún máximo/exacto (`requirements.txt:7-20`). OpenAI/CrewAI no se importan en el runtime. |
| Documentos | `docling`, `pypdf2`, `python-docx`, `python-multipart` | Sin versión (`requirements.txt:23-26`). |
| Datos/storage | `supabase`, `redis`, `pandas`, `numpy`, `plotly`, `seaborn`, `matplotlib` | Sin versión (`requirements.txt:29-37`). Redis no aparece integrado. |
| HTTP/API | `requests`, `httpx`, `aiofiles` | Sin versión (`requirements.txt:40-42`). |
| Auth/seguridad | `pyjwt`, `passlib[bcrypt]`, `python-jose[cryptography]`, `extra-streamlit-components` | Sin versión (`requirements.txt:45-48`). Sólo `extra-streamlit-components` aparece en el flujo actual. |
| Config/utilidades | `pydantic`, `pydantic-settings`, `python-dotenv`, `email-validator`, `python-dateutil`, `pytz`, `pathlib`, `json5` | Sin versión (`requirements.txt:51-62`). `pathlib` no está en `environment.yml`. |
| Desarrollo/observabilidad | `pytest`, `pytest-asyncio`, `black`, `flake8`, `structlog`, `psutil` | Sin versión (`requirements.txt:65-72`). |
| Ficheros/reporting | `openpyxl`, `xlsxwriter`, `reportlab`, `weasyprint`, `jinja2` | Sin versión (`requirements.txt:75-84`); no se observan en el flujo principal. |
| Jobs/rate limit | `celery`, `slowapi` | Sin versión (`requirements.txt:79`, `:87`); no están integradas. |

Derivas concretas:

- `python-multipart` está duplicada en `requirements.txt:26` y `requirements.txt:90`.
- `pathlib` aparece sólo en `requirements.txt:61`; es un backport archivado e innecesario en Python 3.11. La propia ficha del paquete indica que no recibe mantenimiento: <https://pypi.org/project/pathlib/>.
- PyPI indica que `PyPDF2` 3.0.x es la última línea y que el desarrollo continúa como `pypdf`; el código aún importa PyPDF2 en tres fallbacks. Fuente: <https://pypi.org/project/PyPDF2/>.
- Constraints `>=` sin techo en Anthropic/LangChain/CrewAI y ausencia total de constraints para Streamlit, Supabase, Pydantic, Docling, Pandas y NumPy dejan expuesta la aplicación a cambios incompatibles.
- `requirements.txt` incluye varias capacidades no usadas (FastAPI, OpenAI, CrewAI, Redis, Celery, SlowAPI, reporting), ampliando superficie de supply chain sin una necesidad runtime demostrada.

## Superficie de proveedores externos

| Proveedor | Uso real | Acoplamiento |
|---|---|---|
| Anthropic | Chat/agente, fallback de modelos, query augmentation, HyDE, conteo de tokens y generación de visualizaciones. | SDK Anthropic, `langchain-anthropic`, clases/excepciones/model IDs y HTTP directo (`services/medical_agent/llm_manager.py:8-14`; `services/rag/query_augmenter.py:21-23`; `services/connection_pool_manager.py:364-410`). |
| Supabase | Auth, perfiles, conversación, análisis, preferencias, datos MIMIC, pgvector y RPC SQL/búsqueda. | SDK concreto repartido por al menos ocho módulos; una sola pareja URL/key. |
| Hugging Face | Descarga/uso de embedding y reranker; pool de inference API opcional. | Model IDs hardcoded en `config/config.py:52-67` y `services/rag/reranker.py:25`; token opcional. |
| LangChain | Tool schemas, prompt/messages y AgentExecutor. | El orquestador devuelve/consume objetos LangChain (`services/unified_chat/unified_agent.py:13-15`, `:261-300`). |
| OpenAI | Dependencia y setting solamente. | No hay cliente ni llamada en el runtime. |
| Streamlit | Runtime, estado, cookies, navegación, widgets y render. | No es sólo frontend: posee sesión, services y parte del caso de uso. Véase `COUPLING_MAP.md`. |

## Preguntas abiertas para Fase 1

1. ¿Qué fuente y schema sustituirán a las tablas clínicas actuales (`mimic_ed`/copias `public`)? Decisión reservada a la línea de trabajo de migración integral de Supabase; el futuro adapter deberá ofrecer una única respuesta al core.
2. ¿Qué tipo de `SUPABASE_KEY` se despliega hoy y qué RLS/policies protegen cada tabla/RPC? No puede deducirse del repositorio.
3. ¿`execute_readonly_query`, `hybrid_search` y `vector_search` están versionadas fuera del repositorio? No se encontró migración SQL que defina sus contratos.
4. ¿Cómo se coordinará el corte de conversaciones/identidad con la migración integral de Supabase? Fase 1 sí extraerá sus ports; el backend sucesor y su calendario pertenecen a esa migración separada.
5. ¿Qué documentos de `guias/` están aprobados, versionados y autorizados para indexación? El código contiene una allowlist nominal, no gobernanza.
6. ¿Se conservará generación de código para visualizaciones? No bloquea el mapa de acoplamiento, pero sí condiciona el Model Gateway y la política de tools.
