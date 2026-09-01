# Mapa de acoplamiento para Fase 1

## Criterio del mapa

Este mapa registra los puntos que impiden ejecutar el core sin Streamlit o sustituir Anthropic/Supabase/MIMIC. Las referencias son del commit inventariado en `INVENTORY.md`. Las dificultades estiman la extracción, no un refactor completo:

- **Baja:** adapter/presentación aislable sin cambiar comportamiento.
- **Media:** exige contrato, inyección de dependencia y tests de caracterización.
- **Alta:** mezcla autorización, datos clínicos o control del LLM y requiere rediseñar el caso de uso.

Fronteras propuestas:

- `LLMProvider`: port mínimo, agnóstico al SDK, para generación, streaming y tool calling estructurado.
- `ModelGateway`: servicio de aplicación sobre `LLMProvider` que aplica selección de modelo, timeout, retry, circuit breaker, política de tools, trazas y degradación.
- `ClinicalDataProvider`: port clínico read-only con operaciones allowlisted y DTO canónico; nunca acepta SQL o nombres de tabla.
- Repositorios auxiliares: `IdentityProvider`, `ConversationRepository`, `KnowledgeRepository` y `UserPreferencesRepository`. Son necesarios para sacar Supabase del core aunque no sustituyen las tres fronteras prioritarias.
- `RequestContext(tenant_id, user_id, patient_id, encounter_id, session_id, trace_id)`: argumento obligatorio antes de cualquier operación clínica o generación.

## Acoplamiento a Streamlit

| Punto actual | Dependencia concreta | Qué extraer | Frontera destino | Dificultad |
|---|---|---|---|---|
| `main.py:29-38` | Import/runtime Streamlit como único entry point. | Composición reusable de application services; dejar este fichero como adapter legacy durante la transición. | Composition root + futuro FastAPI | Baja |
| `src/core/app.py:14-35`, `:78-239` | Lazy imports de servicios/UI, auth, router por `st.session_state`, widgets, errores y CSS. | `ApplicationService` para iniciar/continuar sesión y chat; navegación queda en UI. | Streamlit adapter → application services | Alta |
| `services/auth/session_manager.py:19-108` | Cookie manager, identidad y estado autenticado viven en `st.session_state`. | Estado de request/sesión validado en servidor; cookie sólo transporta un identificador/token verificable. | `IdentityProvider` + `RequestContext` | Alta |
| `services/auth/session_manager.py:111-307` | Login, registro, CRUD de chat/perfil llaman a services guardados dentro de `st.session_state`. | Casos de uso de identidad/conversación con dependencias explícitas. | `IdentityProvider`, `ConversationRepository` | Alta |
| `services/auth/session_manager.py:309-400` | Estadísticas, límites y preferencias leen/escriben estado global Streamlit. | Servicios de preferencias/quotas por usuario y contexto. | Application service + repositories | Media |
| `ui/unified_chat_interface.py:58-180` | Estado de mensajes/config/documentos/viz/performance e inicialización lazy ligados a reruns/spinners. | `ChatSessionState` serializable y servicio de composición fuera de UI. | Chat application service | Alta |
| `ui/unified_chat_interface.py:191-833` | Estado del sistema, gestión documental, configuración, métricas y todas las acciones de UI mezcladas. | Commands/queries para ingesta, documentos, preferencias y health; render permanece aquí. | Application services + `KnowledgeRepository` | Media |
| `ui/unified_chat_interface.py:835-1028` | Carga history, input, invocación del agente, métricas, persistencia y render en un mismo ciclo Streamlit. | Caso de uso `handle_chat(request, context)` que devuelva eventos/respuesta estructurada; la UI sólo captura/renderiza. | `ModelGateway` + `ConversationRepository` | Alta |
| `ui/unified_chat_interface.py:1030-1294` | Render de contenido, fuentes, tools, errores y visualizaciones; copia figuras a session state. | View models/eventos independientes de Streamlit; renderer como adapter. | Presentation adapter | Media |
| `ui/unified_chat_interface.py:1296-1448` | Construcción de contexto y persistencia Supabase dependen de `st.session_state`; la UI clasifica el análisis. | `ConversationService` y `AnalysisRepository`; contexto delimitado por `RequestContext`. | Application service/repositories | Alta |
| `ui/unified_chat_interface.py:1450-1535` | Upload/delete combinan temporal, servicio y feedback Streamlit. | Commands de ingesta/borrado con resultado tipado. | Knowledge application service | Media |
| `ui/components/components/auth_pages.py:9-223` | Formularios y reruns llaman directamente a `SessionManager`. | Mantener widgets; sustituir llamadas por cliente del backend/API. | Presentation adapter | Baja |
| `ui/components/components/sidebar.py:10-195` | Navegación, usuario, sesiones y borrado mutan session state. | View model y commands de sesión. | Presentation adapter | Media |
| `ui/components/components/document_manager.py:19-685` | UI secundaria llama directamente a processor/RAG y mantiene widgets/config. | Unificar con el caso de uso documental; retirar duplicación al migrar frontend. | Knowledge application service | Media |
| `ui/components/components/footer.py:9-77` | Presentación/debug Streamlit. | Ninguna lógica core; conservar como adapter o retirar. | Presentation adapter | Baja |
| `services/medical_agent/visualization_handler.py:139-234`, `:245-320` | Un módulo de services usa `st`/containers/download widgets. | Separar serialización de figura de render/download. | Visualization result + presentation adapter | Baja |
| `.streamlit/config.toml:7-10` | Configura runtime y desactiva CORS/XSRF. | No trasladar estas opciones al backend; definir política CORS/CSRF segura por entorno. | Deployment/API security | Media |

Dependencia indirecta importante: aunque `services/unified_chat/unified_agent.py` no importa Streamlit, la única entrada real le pasa `session_id` y contexto construidos desde `st.session_state` (`ui/unified_chat_interface.py:943-954`, `:1296-1330`). Hasta introducir `RequestContext`, el core no está aislado por usuario/paciente/episodio.

## SQL generado o libre

| Punto actual | Qué ocurre | Extracción/eliminación | Frontera destino | Dificultad |
|---|---|---|---|---|
| `services/unified_chat/tools/database_tool.py:19-59`, `:89-168` | El schema de tool ofrece `query_type=custom`, `custom_query`, tablas/columnas y ejemplos SQL al LLM. | Eliminar `custom` del contrato de producción; ofrecer tools clínicas (`get_patient_summary`, `get_vitals`, etc.) con DTOs. | `ClinicalDataProvider` | Alta |
| `services/unified_chat/tools/database_tool.py:174-229`, `:426-468` | Routing acepta la salida SQL del modelo, la registra parcialmente y la envía al DB service. | Routing sólo sobre operaciones tipadas y scope explícito del `RequestContext`. | Model Gateway → `ClinicalDataProvider` | Alta |
| `services/unified_chat/tools/database_tool.py:470-645` | Defensa regex/keyword/allowlist intenta convertir SQL libre en seguro. No hace parsing/plan ni impone paciente. | Retirar de producción; si se conserva para investigación MIMIC, adapter separado, feature flag y entorno sin datos productivos. | Research-only adapter, fuera del Clinical Data Gateway | Alta |
| `services/medical_agent/prompt_manager.py:192-257`, `:536-751`, `:1006-1033` | Prompts enseñan schema, reglas y ejemplos SQL y describen parámetros SQL al agente. | Reescribir documentación desde schemas de tools clínicas; el modelo no debe conocer tablas. | Model Gateway/tool registry | Alta |
| `services/medical_agent/tools/database_tool_claude.py:18-63`, `:67-125` | Tool legado también ofrece `custom_query` y lo pasa casi directamente al DB service. | Retirar/aislar junto con el modo research; evitar que quede una ruta alternativa importable. | `ClinicalDataProvider` | Media |
| `services/medical_agent/services/database_service.py:291-353`, `:383-417` | Validador SQL genérico y método directo no implementado. | No portar al gateway clínico; caracterizar y eliminar como API de producción. | Adapter MIMIC research-only | Media |
| `services/medical_agent/services/database_service.py:1245-1305` | Ejecuta texto SQL mediante RPC `execute_readonly_query`; sólo exige prefijo SELECT y bloquea keywords. | Deshabilitar en producción y reemplazar llamadas por operaciones clínicas parametrizadas. | `MimicClinicalDataProvider` | Alta |
| `services/rag/supabase_vector_store.py:275-377` | RPC SQL fija (`hybrid_search`, `vector_search`) para retrieval; no es SQL generado por el LLM, pero acopla el store a funciones PostgreSQL no versionadas aquí. | Mantener como implementación privada detrás de `KnowledgeRepository`; versionar migrations/contratos. | Knowledge/vector-store adapter | Media |
| `services/unified_chat/config.py:112-128`, `config/settings.py:152-153` | Flags/límites sugieren que validar SQL permite habilitarlo. | Cambiar semántica a feature research-only; en producción no debe existir el parámetro SQL. | Policy/config del Clinical Data Gateway | Baja |

Riesgo principal: limitar a `SELECT` y seis tablas no resuelve acceso excesivo. Los ejemplos dataset-wide no requieren paciente (`services/unified_chat/tools/database_tool.py:151-161`) y la RPC recibe el texto completo (`services/medical_agent/services/database_service.py:1277-1284`).

## Acoplamiento directo a Supabase

| Punto actual | Dependencia concreta | Qué extraer | Frontera destino | Dificultad |
|---|---|---|---|---|
| `services/connection_pool_manager.py:316-352` | Crea/pool/health-check de `supabase.Client` y conoce `mimic_ed.edstays`. | Factory de adapter; health check clínico detrás del provider. | `MimicClinicalDataProvider` | Media |
| `services/medical_agent/services/database_service.py:130-252`, `:421-495` | SDK, schema/table API, pool y DataFrames dentro del servicio clínico. | Convertir la clase en adapter MIMIC que implemente operaciones y DTOs canónicos; no exponer `get_table_data`. | `ClinicalDataProvider` | Alta |
| `services/medical_agent/services/database_service.py:499-1243` | Resúmenes y formateo clínico están escritos sobre columnas MIMIC/DataFrames. | Separar mapping MIMIC→DTO del servicio de aplicación; conservar mapping dentro del adapter. | `MimicClinicalDataProvider` | Alta |
| `services/medical_agent/services/database_service.py:1245-1305` | RPC SQL Supabase. | Ruta research-only; nunca parte del port productivo. | Fuera de producción | Alta |
| `services/rag/supabase_vector_store.py:38-459` | Cliente, tabla `rag_chunks`, CRUD y RPCs están en la implementación usada directamente. | Definir `KnowledgeRepository`/`VectorStore` y encapsular cliente, tablas y RPC. | Supabase knowledge adapter | Media |
| `services/rag/improved_rag_service.py:500-558` | La fachada rompe encapsulación accediendo a `self.store.client.table(...)`. | Añadir operaciones `list/reset/export` al port del store. | `KnowledgeRepository` | Baja |
| `services/auth/auth_service.py:31-62`, `:68-309` | Cliente Supabase Auth y `public.users` dentro de identidad. | Adapter Supabase de identidad; devolver principal/token validado, no dict de proveedor. | `IdentityProvider` | Alta |
| `services/auth/auth_service.py:311-448`, `:483-601` | `chat_sessions`/`chat_messages` y estadísticas mediante SDK. | Repositorio de conversaciones con ownership y tenant scope explícitos. | `ConversationRepository` | Alta |
| `services/supabase_services.py:14-191` | CRUD concreto de `clinical_documents`. | Repositorio de catálogo documental; no confundir con datos de paciente. | `KnowledgeRepository` | Media |
| `services/supabase_services.py:194-318` | CRUD concreto de `analyses`. | `AnalysisRepository` con trace/request IDs y minimización. | Application repository | Media |
| `services/supabase_services.py:321-417` | CRUD concreto de preferencias. | `UserPreferencesRepository`. | Application repository | Baja |
| `services/unified_chat/document_manager.py:460-506` | Import dinámico de service Supabase; sincronización best-effort puede divergir de `rag_chunks`. | Transacción/outbox lógica del caso de uso de ingesta; repositorios inyectados. | Knowledge application service | Media |
| `ui/unified_chat_interface.py:1332-1448` | La UI usa auth service y crea `AnalysisService` concreto. | Persistencia dentro del caso de uso, no del renderer. | Conversation/Analysis repositories | Alta |
| `services/auth/session_manager.py:352-397` | Import dinámico y almacenamiento de `UserPreferencesService` en Streamlit. | Inyectar repositorio en servicio de preferencias. | UserPreferencesRepository | Media |
| `utils/validators/mimic_validator.py:15-209` | Cliente SDK directo y schema implícito/public. | Validación sobre `ClinicalDataProvider.capabilities/health`, o herramienta del adapter MIMIC. | `MimicClinicalDataProvider` | Media |
| `scripts/clear_rag.py:20-49` | Borrado masivo directo de `rag_chunks`. | CLI administrativa sobre `KnowledgeRepository`, con autorización/entorno. | Knowledge admin adapter | Baja |

No se debe crear una interfaz genérica que replique `.table().select().eq()`: trasladaría el acoplamiento en lugar de romperlo. Para datos clínicos, el port debe expresar operaciones clínicas; para datos de producto, repositorios de agregado.

## Acoplamiento directo a Anthropic

| Punto actual | Dependencia concreta | Qué extraer | Frontera destino | Dificultad |
|---|---|---|---|---|
| `services/medical_agent/llm_manager.py:8-14`, `:35-213` | Imports `ChatAnthropic` y excepciones Anthropic, API key, creación, test y tipos de retorno concretos. | `AnthropicLLMProvider`; mapear errores/respuestas a errores/eventos propios. | `LLMProvider` | Alta |
| `services/medical_agent/llm_manager.py:215-379` | Cadena de modelos Claude y retry/fallback mezclados en el manager concreto. | Mover política de routing/retry al Model Gateway; provider sólo ejecuta una petición. | Model Gateway | Media |
| `services/medical_agent/llm_manager.py:381-447` | Constructor Claude separado para visualización. | Perfil/capability `code_generation` resuelto por el gateway. | Model Gateway + `LLMProvider` | Media |
| `services/unified_chat/unified_agent.py:30-121`, `:261-300`, `:307-478` | El core instancia `ClaudeLLMManager` y LangChain tool-calling; errores/modelo actual son específicos. | Inyectar Model Gateway y tool registry neutral; request/response propios. | Model Gateway | Alta |
| `services/medical_agent/tools/claude_adapter.py:17-68`, `:206-224` | Naming/schema/documentación orientados a Claude aunque acaba usando `StructuredTool`. | Renombrar a provider-neutral tool contract y adaptar por provider en el borde. | Model Gateway/tool registry | Media |
| `services/medical_agent/prompt_manager.py:21-64`, `:870-900` | Cliente `Anthropic` sólo para contar tokens; defaults/model IDs Claude. | Token accounting capability del provider o estimador local del gateway. | `LLMProvider` | Baja |
| `services/rag/query_augmenter.py:49-191` | Crea `Anthropic` y llama `messages.create` directamente para multi-query/HyDE. | Servicio de query augmentation que recibe `LLMProvider`/perfil económico; degradación determinista. | Model Gateway | Media |
| `services/medical_agent/visualization_agent.py:81-147`, `:150-307` | Crea `ChatAnthropic`, pasa API key y llama `.invoke` como fallback de código. | Pedir generación estructurada al Model Gateway; mantener templates fuera. | Model Gateway | Media |
| `services/connection_pool_manager.py:354-410` | Cliente HTTP, URL, headers y versión API Anthropic hardcoded. | El provider gestiona transporte/health; retirar pool paralelo si el SDK ya lo hace. | `AnthropicLLMProvider` | Baja |
| `config/settings.py:82-121`, `:166-202`, `:260-322`; `config/config.py:38-67` | Model IDs y API key repetidos por RAG/agente/visualización. | Catálogo de modelos/capabilities del Model Gateway y un único secret binding por provider. | Model Gateway config | Media |
| `services/unified_chat/tools/database_tool.py:62`, `services/unified_chat/tools/rag_tool.py:41`, `services/medical_agent/tools/visualization_collaboration_tool.py:75` | Tools de dominio heredan `ClaudeToolAdapter`. | Contrato interno de tools; adapter Anthropic/LangChain en Model Gateway. | Model Gateway/tool registry | Media |

El objetivo no es ocultar el string `Claude`, sino impedir que application services importen SDKs, excepciones, mensajes o schemas de Anthropic. El provider concreto seguirá existiendo en infraestructura.

## Acoplamientos combinados de mayor riesgo

| Flujo | Cadena actual | Por qué bloquea Fase 1 | Corte mínimo |
|---|---|---|---|
| Pregunta clínica | `st.session_state` → `UnifiedChatAgent` → Claude selecciona `custom_query` → RPC Supabase | El contexto de paciente no es obligatorio y el modelo controla el lenguaje de acceso. | `ChatApplicationService(RequestContext)` → Model Gateway → tool allowlisted → `ClinicalDataProvider`. |
| Restaurar sesión | Cookie Streamlit → dict usuario confiado → `authenticated=True` → services Supabase | No existe verificación de principal por request. | Cookie/token opaco → `IdentityProvider.verify()` → `RequestContext`. |
| RAG | UI → RAGTool → Anthropic multi-query/HyDE → Supabase RPC → texto a Anthropic principal | Dos providers concretos y varias llamadas LLM están ocultos dentro de un tool. | `KnowledgeService` + `KnowledgeRepository`; augmentation a través de Model Gateway y modo degradado sin LLM. |
| Visualización | Claude tool → Supabase tablas MIMIC → DataFrame → Claude genera código → executor → session state | Une selección de datos, provider, ejecución y renderer. | Tool tipada → `ClinicalDataProvider`; transformaciones/templates deterministas en Fase 1; renderer UI separado. El código generado queda fuera de la ruta clínica. |
| Persistencia de chat | UI clasifica respuesta → AuthService/AnalysisService Supabase | El caso de uso no es invocable desde FastAPI y carece de trazas/contexto uniformes. | Application service transaccional con Conversation/Analysis repositories. |

## Orden recomendado de extracción en Fase 1

1. Definir `RequestContext`, DTOs clínicos y contratos de tool; caracterizar el comportamiento actual con tests sin mover implementación.
2. Crear `ClinicalDataProvider` y exponer sólo operaciones clínicas. El adapter concreto y la migración integral de Supabase pertenecen a una línea de trabajo separada; este mapa no elige la fuente sucesora. Deshabilitar `custom` fuera de un perfil research explícito.
3. Crear `LLMProvider` y `AnthropicLLMProvider`; colocar fallback, retry, tracing, tool registry y degradación en Model Gateway.
4. Extraer `ChatApplicationService` de `ui/unified_chat_interface.py:835-1028`, `:1296-1448`; Streamlit se convierte en un cliente/adapter.
5. Extraer `IdentityProvider`, `ConversationRepository`, `AnalysisRepository`, `UserPreferencesRepository` y el port de conocimiento para que la migración de Supabase se realice detrás de contratos estables.
6. Separar resultados de visualización del renderer Streamlit, admitir únicamente templates deterministas en la ruta clínica y, sólo entonces, exponer FastAPI/SSE.

## Criterios verificables de desacoplamiento

- Un test del caso de uso chat corre sin importar `streamlit`, `supabase`, `anthropic` ni `langchain_anthropic`.
- Ningún schema visible al LLM contiene `sql`, `custom_query`, nombre de schema o nombre de tabla clínica.
- Toda tool clínica recibe `RequestContext` y una operación tipada; el adapter MIMIC y un futuro FHIR devuelven los mismos DTOs.
- El Model Gateway puede usar un fake provider y seleccionar Anthropic sólo en composition root.
- El fallo de Anthropic permite retrieval determinista sin query augmentation y no impide consultar datos clínicos allowlisted.
- Supabase sólo aparece en adapters de infraestructura y scripts administrativos, nunca en UI/application/domain.
- Ninguna ruta clínica productiva ejecuta código de visualización generado por un LLM.
