# ADR 0010: Desacoplar el core del runtime y de los proveedores

Estado: propuesto para Fase 1

Fecha: 2026-08-31

## Contexto

ChatHCE se ejecuta hoy como un monolito Streamlit. La UI posee identidad, sesión, historial, contexto y parte de los casos de uso; el agente instancia directamente componentes Anthropic/LangChain; el acceso clínico conoce tablas MIMIC, Supabase y una RPC que ejecuta SQL generado; RAG, identidad y conversaciones también dependen directamente de Supabase.

Esta estructura impide cumplir los objetivos de Fase 1: core testeable sin UI, FastAPI intercambiable, Model Gateway agnóstico, Clinical Data Gateway con herramientas allowlisted y un adapter MIMIC sustituible por FHIR. También impide aplicar de forma uniforme tenant/user/patient/encounter scope antes de acceder a datos o invocar un modelo.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Mantener Streamlit como capa de aplicación y añadir FastAPI alrededor.** Se descarta porque FastAPI acabaría llamando funciones que leen `st.session_state`, y existirían dos runtimes con semánticas de sesión diferentes. No rompe el acoplamiento ni hace el core testeable.
2. **Abstraer únicamente `supabase.Client` con una interfaz genérica de consultas.** Se descarta porque reproducir métodos `table/select/eq/rpc` detrás de una interfaz conserva nombres de tabla, SQL y semántica del proveedor en el dominio. Tampoco crea operaciones clínicas ni DTOs canónicos.
3. **Reescritura completa y simultánea a FastAPI, FHIR y otro frontend.** Se descarta para Fase 1 porque es un cambio big-bang sin baseline suficiente, dificulta comparar comportamiento y mezcla separación arquitectónica con interoperabilidad hospitalaria.
4. **Ports and adapters incrementales, manteniendo Streamlit y Supabase como adapters temporales.** Se elige. Permite caracterizar y envolver el comportamiento actual, cortar dependencias en orden y sustituir adapters sin reescribir los casos de uso.
5. **Un único gateway genérico para LLM, datos clínicos, RAG e identidad.** Se descarta porque diluye políticas y scopes distintos; un fallo o permiso amplio se propagaría a capacidades que deben poder degradarse y autorizarse por separado.

## Decision

Adoptar una separación incremental por ports and adapters con estas reglas:

1. El core de aplicación no importará Streamlit, Supabase, Anthropic ni tipos de sus SDKs. Streamlit permanecerá temporalmente como adapter de presentación; FastAPI será otro adapter.
2. Todo caso de uso recibirá un `RequestContext` obligatorio con tenant, usuario, paciente, episodio, sesión y correlación. Ninguna tool podrá reconstruir ese contexto desde globals o desde el prompt.
3. El acceso clínico se expresará mediante `ClinicalDataProvider`, con operaciones clínicas read-only allowlisted y DTOs canónicos. `MimicClinicalDataProvider` encapsulará tablas/columnas Supabase MIMIC. Un futuro adapter FHIR implementará el mismo port.
4. SQL libre no formará parte del contrato productivo. Si se conserva para investigación MIMIC, vivirá en un adapter y despliegue separados, sin credenciales ni datos de producción.
5. La generación se dividirá en un port `LLMProvider` y un `ModelGateway`. El provider adaptará SDK, mensajes, errores y streaming; el gateway aplicará selección de modelo, fallback, retry, timeout, circuit breaker, policy de tools, trazas y degradación.
6. RAG, identidad, conversación, análisis y preferencias usarán ports propios (`KnowledgeRepository`, `IdentityProvider`, `ConversationRepository`, `AnalysisRepository`, `UserPreferencesRepository`). Supabase será una implementación de infraestructura, no una abstracción transversal del dominio.
7. Los tools usarán contratos internos Pydantic/provider-neutral. Los schemas específicos de Anthropic/LangChain se construirán dentro del Model Gateway.
8. La migración seguirá patrón strangler: primero contratos y tests de caracterización, luego adapters sobre implementaciones actuales, después application services y finalmente FastAPI/SSE. No se añadirán features clínicas durante el corte.

## Motivo

La unidad que necesita estabilidad no es la base de datos ni el SDK, sino el caso de uso clínico con su contexto, autorización y evidencia. Ports clínicos expresivos impiden que el modelo elija tablas o lenguaje de consulta; un Model Gateway concentra política de IA sin obligar al dominio a conocer Anthropic; adapters de presentación permiten retirar Streamlit sin reimplementar la lógica.

El enfoque incremental conserva una ruta verificable desde el comportamiento actual, permite usar MIMIC durante desarrollo y prepara la sustitución por FHIR sin contaminar los agentes con recursos o peculiaridades de proveedor.

## Consecuencias

Positivas:

- El core será ejecutable y testeable sin runtime web ni red.
- MIMIC y FHIR podrán atender el mismo caso de uso mediante DTOs comunes.
- Anthropic podrá sustituirse o combinarse con otros providers sin cambiar application services.
- Autorización, scope, auditoría y trazas se aplicarán antes de recuperar datos o llamar al modelo.
- El modo degradado podrá conservar retrieval y operaciones clínicas deterministas aunque falle el LLM.
- La superficie Supabase quedará localizada y será posible imponer credenciales/policies de mínimo privilegio por adapter.

Negativas y costes:

- Habrá adapters temporales y cierta duplicación mientras convivan Streamlit/FastAPI y contratos viejo/nuevo.
- Los dicts/DataFrames actuales deberán mapearse a DTOs, y los prompts/tools necesitarán cambios coordinados.
- Separar identidad/conversación de `st.session_state` exige definir explícitamente ciclo de vida y persistencia.
- La generación de visualizaciones necesitará un contrato propio si conserva fallback LLM y ejecución de código.
- El SQL dataset-wide útil para investigación dejará de estar disponible en el producto salvo entorno separado.

## Pendientes

1. Definir los métodos iniciales y DTOs de `ClinicalDataProvider` a partir de los casos de uso realmente usados, no de las seis tablas completas.
2. Resolver si las tablas MIMIC canónicas viven en schema `mimic_ed` o `public` y versionar las migraciones/RPC necesarias.
3. Definir `RequestContext`, reglas de propagación y rechazo cuando falte patient/encounter scope.
4. Definir contratos de eventos/respuesta del Model Gateway, incluido streaming sin chain-of-thought.
5. Decidir la tecnología y límites de `ConversationRepository`/`IdentityProvider` durante la transición.
6. Especificar el perfil research-only si se decide conservar SQL libre para MIMIC.
7. Caracterizar con tests chat, RAG, resúmenes, visualización, fallback y persistencia antes de mover código.
8. Inventariar y versionar RLS/policies de Supabase y confirmar el tipo de clave desplegada.
