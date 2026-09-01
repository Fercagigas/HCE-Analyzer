# Threat model inicial de ChatHCE

Estado: baseline de Fase 0; describe el sistema actual, no una autorización de despliegue

Fecha: 2026-09-01

Fotografía del código: `235f5ea`

## Resumen ejecutivo

ChatHCE es hoy un monolito Streamlit de investigación que combina autenticación y persistencia en Supabase, un agente LangChain/Anthropic, acceso a MIMIC-IV-ED, RAG sobre documentos y generación de visualizaciones. Este documento modela esa implementación; los gateways, controles hospitalarios y separaciones del roadmap se tratan como mitigaciones futuras, no como controles existentes.

La exposición actual no es adecuada para un entorno hospitalario compartido. Los riesgos residuales más urgentes son:

1. una cookie aceptada como identidad sin revalidar la sesión con Supabase;
2. lectura y escritura de mensajes por `session_id` sin comprobar en código su propietario;
3. ausencia de contexto obligatorio de tenant, usuario, paciente y episodio;
4. SQL `custom` elegido por el modelo, incluidas consultas de todo el dataset;
5. caché de respuestas sin usuario, tenant, paciente ni sesión en la clave;
6. Python generado por el modelo ejecutado dentro del proceso, sin aislamiento y con un timeout declarado que no se aplica;
7. carga e indexación de documentos sin análisis de malware, aprobación, vigencia, aislamiento por tenant ni defensa frente a instrucciones embebidas;
8. prompts, consultas y contenido clínico persistidos o registrados sin una capa de minimización/redacción;
9. CORS y XSRF desactivados en Streamlit;
10. ausencia de un audit trail suficiente para atribuir y reconstruir accesos y decisiones de tools.

El intended purpose aprobado permanece intacto: v1 es para investigación/educación con médicos y datos anonimizados o debidamente preparados, sin influencia en decisiones asistenciales reales (`docs/product/INTENDED_PURPOSE.md`, DP-01 a DP-04 y DP-08). Este threat model no acepta riesgo residual ni amplía ese alcance. Conforme a DP-07, los riesgos Críticos permanecen prohibidos; y no existe todavía la gobernanza que permitiría aceptar riesgo clínico residual Medio o Alto para uso asistencial.

## Alcance, método y límites

### Incluido

- Runtime Streamlit, estado de sesión, cookies, UI y componentes de autenticación.
- Agente unificado, system prompt, historial, tool calling y respuestas.
- Datos MIMIC-IV-ED accedidos en Supabase y la RPC de SQL libre.
- Auth, perfiles, conversaciones, análisis, preferencias y documentos en Supabase.
- Ingesta, procesamiento, embeddings, retrieval y administración del corpus RAG.
- Anthropic, modelos/artefactos de Hugging Face y sus flujos de red.
- Generación y ejecución de código para visualizaciones.
- Caché, memoria, logs, ficheros temporales, configuración, secretos y scripts administrativos.

### Excluido

- La arquitectura objetivo FastAPI/React/FHIR/SMART y controles aún no implementados.
- Infraestructura externa no versionada: RLS/policies de Supabase, definición de RPC, proxy/TLS, WAF, red, secret manager y configuración de proveedores.
- Ataques activos, explotación, fuzzing, red team o llamadas live. No se ejecutó ningún exploit.
- Clasificación jurídica, DPIA, MDR/AI Act o un clinical safety risk file completo.

### Metodología

Se aplica STRIDE a cada confín de confianza real y se complementa con un catálogo específico de IA. Cada amenaza registra activo, vector, precondiciones, impacto clínico y de privacidad, probabilidad, controles observados, riesgo residual y trazabilidad de mitigación. La elección se formaliza en `docs/decisions/0030-metodologia-y-alcance-threat-model-inicial.md`.

La probabilidad es cualitativa:

- **Alta:** superficie alcanzable en un flujo normal y control ausente o claramente insuficiente.
- **Media:** requiere cuenta, contenido preparado, fallo previo o acceso operativo, pero es plausible.
- **Baja:** requiere compromiso de proveedor, host o supply chain con acceso privilegiado.

El riesgo residual combina probabilidad e impacto después de los controles que existen en esta fotografía:

- **Crítico:** puede permitir acceso no autorizado amplio, fuga entre contextos, compromiso del proceso o indisponibilidad grave; bloquea cualquier exposición hospitalaria.
- **Alto:** puede revelar o corromper información sensible, degradar materialmente la respuesta o impedir atribución/continuidad.
- **Medio:** daño acotado o condicionado, pero necesita mitigación y pruebas antes de ampliar el uso.
- **Bajo:** impacto y explotabilidad acotados con controles efectivos verificables.

Esta escala describe riesgos de seguridad del sistema y no sustituye la clasificación de capabilities de `docs/product/RISK_CAPABILITY_MATRIX.md`.

Las referencias abreviadas del registro apuntan a estos documentos del roadmap:

| Referencia | Documento y fase principal |
|---|---|
| `03` | `ROADMAP_HOSPITAL_READY/03-backend-api-refactor.md` — F1 |
| `04` | `ROADMAP_HOSPITAL_READY/04-clinical-data-gateway-fhir.md` — F1 para gateway/adapter; interoperabilidad posterior |
| `05` | `ROADMAP_HOSPITAL_READY/05-identity-authorization-multitenancy.md` — F2 para foundation de seguridad |
| `06` | `ROADMAP_HOSPITAL_READY/06-privacy-phi-security.md` — F2 |
| `07` | `ROADMAP_HOSPITAL_READY/07-agent-safety-tooling.md` — contratos iniciados en F1 y enforcement en F2 |
| `08` | `ROADMAP_HOSPITAL_READY/08-rag-clinical-knowledge.md` — F3 en el plan; sus controles de ingesta/aislamiento son gate previo si RAG se comparte antes |
| `09` | `ROADMAP_HOSPITAL_READY/09-evidence-citations-confidence.md` — F3 |
| `11` | `ROADMAP_HOSPITAL_READY/11-evaluation-red-team.md` — programa/gates de F2 y evolución continua |
| `12` | `ROADMAP_HOSPITAL_READY/12-observability-audit-resilience.md` — audit foundation en F1, controles de seguridad/resiliencia en F2 y operación posterior |
| `14` | `ROADMAP_HOSPITAL_READY/14-deployment-devsecops.md` — hardening de pilot readiness/F7 |

### Evidencia y supuestos conservadores

- La base factual principal es `docs/architecture/INVENTORY.md` y `docs/architecture/COUPLING_MAP.md`, contrastada con las rutas de código citadas.
- No se encontró una credencial real de alta confianza en ficheros versionados; no se inspeccionaron ni documentaron valores externos. La ubicación y el uso de secretos se citan solo por fichero y línea (`docs/architecture/INVENTORY.md:171-192`).
- No se acredita RLS, separación de claves, cifrado, TLS, retención contractual ni aislamiento de red porque no son verificables en el repositorio.
- El tipo y privilegios reales de `SUPABASE_KEY`, las policies/RLS y las definiciones de RPC son desconocidos (`docs/architecture/INVENTORY.md:230-236`). Ante esa incertidumbre, no se contabilizan como controles.
- Los datos versionados son MIMIC-IV-ED demo, pero el mismo código acepta una instancia Supabase configurable. El impacto se evalúa para los activos realmente manejados y para el daño que produciría conectar la aplicación sin cambios a datos sensibles; esto no afirma que hoy contenga PHI real.
- El baseline ejecutó 27/44 tests, no midió cobertura y no ejecutó ninguna de las 13 pruebas de seguridad live (`docs/baseline/FASE0_BASELINE.md`). Por tanto, la mera existencia de tests o validadores no demuestra resistencia.

## Modelo del sistema actual

```text
Navegador no confiable
  | formularios, cookie, prompts, uploads, clicks
  v
Monolito Streamlit / mismo proceso Python
  |-- SessionManager + AuthService --------------------> Supabase Auth/public
  |-- UnifiedChatAgent --------------------------------> Anthropic
  |     |-- DatabaseTool -- DatabaseService -----------> Supabase mimic_ed + RPC SQL
  |     |-- RAGTool -- QueryAugmenter -----------------> Anthropic
  |     |           -- ImprovedRAGService -------------> Supabase rag_chunks
  |     |           -- embeddings/reranker ------------> Hugging Face/artefactos locales
  |     `-- VisualizationTool -- VisualizationAgent ---> Anthropic
  |                                  `-- exec Python en el proceso
  |-- DocumentManager -- extracción/chunking ----------> Supabase rag_chunks/public
  `-- logs, caché, visualizaciones y session_state ----> disco/memoria local

Operador local / scripts --------------------------------> Supabase/RAG
```

No hay una API FastAPI operativa ni separación frontend/backend. La composición real está documentada en `docs/architecture/INVENTORY.md:3-28`.

## Activos

| ID | Activo | Sensibilidad y ubicación actual | Propiedad de seguridad prioritaria |
|---|---|---|---|
| A-01 | Datos clínicos MIMIC-IV-ED | Seis tablas clínicas en `mimic_ed`; copia de referencia CSV versionada (`docs/architecture/INVENTORY.md:121-140`) | Confidencialidad, integridad, scope de paciente/episodio, disponibilidad |
| A-02 | Identidad y sesión | Supabase Auth, `public.users`, cookie y `st.session_state` (`services/auth/session_manager.py:23-108`) | Autenticidad, revocación, no suplantación |
| A-03 | Conversaciones y análisis | `chat_sessions`, `chat_messages`, `analyses`; contienen preguntas, respuestas, tools y fuentes (`docs/architecture/INVENTORY.md:142-152`) | Confidencialidad, ownership, integridad, retención |
| A-04 | Corpus RAG | PDFs/texto, chunks, embeddings y metadata en `public.rag_chunks` (`docs/architecture/INVENTORY.md:154-162`) | Integridad, procedencia, vigencia, aislamiento por tenant |
| A-05 | Prompts y políticas de agente | System prompt, schema MIMIC, documentación de tools y reglas SQL (`services/medical_agent/prompt_manager.py:66-111`, `:180-257`, `:650-754`) | Integridad, confidencialidad defensiva, control de privilegios |
| A-06 | Secretos y configuración | Claves de Supabase/Anthropic/Hugging Face y settings duplicados; no se reproducen valores (`docs/architecture/INVENTORY.md:171-192`) | Confidencialidad, mínimo privilegio, rotación |
| A-07 | Logs, caché y memoria de sesión | Logs rotatorios, caché global en proceso, visualizaciones y `st.session_state` (`docs/architecture/INVENTORY.md:164-169`) | Confidencialidad, integridad, borrado, aislamiento |
| A-08 | Modelos y artefactos IA | Modelos Claude externos; embeddings/reranker locales descargables desde Hugging Face (`docs/architecture/INVENTORY.md:219-228`) | Integridad de proveedor/artefacto, versión, disponibilidad |
| A-09 | Proceso y host | Proceso Python que posee UI, secretos, clientes, datos y executor de código | Integridad, aislamiento, disponibilidad |
| A-10 | Evidencia y trazabilidad | Fuentes RAG parciales, metadata de tool y resultados; no existe Evidence/Audit object uniforme | Integridad, no repudio, reconstrucción |

## Actores

### Legítimos actuales

| Actor | Capacidad observada hoy |
|---|---|
| Usuario registrado/autenticado | Puede iniciar sesión, conversar, invocar indirectamente tools, consultar historial y usar gestión documental. El código no hace cumplir que sea médico ni implementa RBAC/ABAC. |
| Operador/desarrollador local | Configura secretos, inicia el runtime, ejecuta scripts, accede a logs y puede indexar o borrar el RAG. |
| Supabase | Proveedor de identidad, datos clínicos, datos de producto, vector store y RPC. |
| Anthropic | Recibe prompts, historial, resultados de tools, consultas de augmentation y muestras de datos de visualización. |
| Hugging Face | Proporciona artefactos de embedding/reranking y, opcionalmente, un API/token. |

Los roles futuros de administrador clínico/IT, DPO, auditor y knowledge manager están aprobados como actores de producto, pero todavía no existen como fronteras de autorización en el runtime (`docs/product/INTENDED_PURPOSE.md`).

### Hostiles o no confiables

- Atacante externo sin autenticar con acceso al navegador o al endpoint Streamlit.
- Usuario autenticado malicioso, cuenta comprometida o usuario que intenta ampliar su scope.
- Autor de una nota, documento o fragmento RAG con instrucciones adversariales embebidas.
- Modelo o respuesta de tool no confiable que produce argumentos manipulados, contenido falso o código hostil.
- Insider u operador con acceso al host, credenciales o scripts administrativos.
- Proveedor externo, dependencia, paquete o artefacto de modelo comprometido.
- Atacante capaz de observar o modificar tráfico en un despliegue donde la capa TLS/red no esté correctamente configurada; esa capa no está definida en el repo.

## Superficies de entrada

| Superficie | Datos controlables | Destino/efecto |
|---|---|---|
| Login, registro, reset y cookie | Email, password, objeto de cookie | Supabase Auth y `st.session_state`; restauración en `services/auth/session_manager.py:51-69` |
| Prompt e historial de chat | Texto de usuario, mensajes persistidos, metadata/tool results | System prompt, Anthropic y selección de tools (`services/unified_chat/unified_agent.py:261-300`, `:307-415`, `:522-628`) |
| Argumentos de tools producidos por el LLM | `query_type`, IDs, filtros, SQL, consulta RAG, requisitos de visualización | Supabase, RAG, Anthropic y executor |
| Upload documental | Nombre, extensión, bytes y metadata | Fichero temporal, extractores Docling/PyPDF2, embeddings y `rag_chunks` (`ui/unified_chat_interface.py:1450-1500`) |
| Corpus y resultados recuperados | Texto/metadata controlado por autores o por la base | Contexto del agente principal y respuesta al usuario |
| Datos/model output de visualización | Muestra de DataFrame, prompt y código Python devuelto | `exec` en el mismo proceso (`services/medical_agent/visualization_agent.py:232-283`) |
| Respuestas de proveedores | Auth/data/RPC, texto de modelos, modelos descargados | Core, UI, memoria y persistencia |
| Configuración y dependencias | Variables de entorno, paquetes sin pin, modelos hardcoded | Secretos, permisos, comportamiento y supply chain |
| Scripts locales | Confirmaciones y paths predefinidos | Indexación y borrado masivo de RAG (`scripts/index_guias.py:45-89`, `scripts/clear_rag.py:20-79`) |

## Confines de confianza reales

| ID | Confín | Cambio de confianza | Datos/operaciones que lo cruzan |
|---|---|---|---|
| TB-01 | Navegador ↔ Streamlit | Cliente controlable a proceso que posee secretos y datos | Credenciales, cookie, prompts, uploads, respuestas, descargas |
| TB-02 | UI/`st.session_state` ↔ core/agente | Estado mutable de presentación se usa como identidad, sesión y contexto de caso de uso | Usuario, `session_id`, historial, documentos, visualizaciones |
| TB-03 | Core ↔ Supabase Auth/public | Proceso local a identidad y repositorios de producto externos | Tokens/sesión del proveedor, perfiles, chats, análisis, preferencias, documentos |
| TB-04 | DatabaseTool/DatabaseService ↔ Supabase `mimic_ed`/RPC | Modelo y código de aplicación a datos clínicos y motor SQL | IDs, filtros, SQL completo, resultados clínicos |
| TB-05 | Agente/QueryAugmenter/VisualizationAgent ↔ Anthropic | Datos y políticas locales a proveedor LLM externo no determinista | System prompt, chat, tool results, consultas, muestra de datos y código |
| TB-06 | Upload/RAGTool ↔ processor/vector store/corpus | Fichero y texto no confiables se convierten en conocimiento privilegiado del agente | Bytes, texto extraído, metadata, embeddings, chunks recuperados |
| TB-07 | VisualizationAgent ↔ executor/host | Salida de modelo no confiable pasa a ejecución dentro del proceso confiable | Código Python, DataFrame, stdout/stderr, figura |
| TB-08 | Runtime ↔ disco/memoria/scripts | Datos sensibles y privilegios salen del flujo request a estado compartido o administración local | Logs, caché, temporales, figuras, settings, borrado/indexación |
| TB-09 | Runtime ↔ Hugging Face/artefactos locales | Código confía en modelos descargables y dependencias no fijadas | Token opcional, pesos/modelos, ejecución local |

## STRIDE por confín de confianza

La matriz aplica las seis categorías a todos los confines. Los IDs remiten al registro detallado posterior; «—» no significa imposible, sino que el escenario relevante queda cubierto por otra categoría del mismo confín.

| Confín | Spoofing | Tampering | Repudiation | Information disclosure | Denial of service | Elevation of privilege |
|---|---|---|---|---|---|---|
| TB-01 | C-01 suplantación por cookie | C-02 petición cross-site/upload manipulado | C-07 atribución insuficiente | C-02, AI-05 respuestas/datos al navegador | AI-12 prompts/uploads costosos | C-01/C-02 acceso como otro usuario |
| TB-02 | C-01 identidad confiada desde estado | AI-01/AI-03 alteran instrucciones; C-03 cambia `session_id` | C-07 no hay principal/contexto auditado uniforme | C-03, AI-06, AI-07, C-06 | AI-12 estado/contexto desmesurado | C-03/AI-11 tools fuera de scope |
| TB-03 | C-04 cliente usa una clave de naturaleza no impuesta | C-05/C-08 escritura o borrado sin gobierno verificable | C-07 operaciones sin trail completo | C-03/C-06/AI-05 datos de producto | C-08 borrado masivo; C-09 dependencia externa | C-04 privilegios efectivos de clave/RLS desconocidos |
| TB-04 | AI-11 modelo actúa como decisor de acceso | AI-04 SQL/tool injection; C-05 datos alterados | C-07 SQL parcial en logs sin identidad/contexto | AI-06/AI-07/AI-08 | AI-08/AI-12 consultas masivas | AI-04/AI-11 modelo amplía acceso lógico |
| TB-05 | C-10 proveedor/modelo/artefacto no atestado | AI-01/AI-02/AI-03 y salida manipulada | C-07 no se guarda policy decision/prompt version | AI-02/AI-05 prompts, resultados y muestras | C-09/AI-12 retries, timeout y outage | AI-11 tool calling inducido por salida del modelo |
| TB-06 | AI-09 origen/owner documental no probado | AI-09/AI-10 poisoning e instrucciones embebidas | C-07/C-08 aprobación y cambios no reconstruibles | AI-05/AI-07 corpus compartido | AI-10/AI-12 documentos costosos | C-08 usuario autenticado opera como knowledge manager |
| TB-07 | AI-13 código se presenta como salida de visualización | AI-13 altera proceso/datos/figura | C-07 código/ejecución sin evento audit uniforme | AI-05/AI-13 muestra de datos o exfiltración | AI-12/AI-13 CPU/RAM/bloqueo | AI-13 ejecución con privilegios del proceso |
| TB-08 | C-08 operador/script sin identidad de aplicación | C-05/C-08 alteración de corpus/logs/estado | C-07 logs mutables y acciones locales no auditadas | C-06/C-11 logs, caché, secretos y memoria | C-08/AI-12 borrado o agotamiento local | C-08/C-11 privilegios de host/secretos |
| TB-09 | C-10 identidad/origen del artefacto no fijado | C-10 modelo/dependencia comprometidos | C-07 versión/procedencia incompleta | C-11 token/configuración por errores o host | C-09/C-10 descarga o modelo indisponible | C-10 código nativo/dependencia con privilegios del proceso |

## Registro de amenazas clásicas

| ID / STRIDE | Activo afectado | Vector y precondiciones | Impacto clínico y de privacidad | Prob. | Controles existentes hoy | Riesgo residual | Mitigación trazada |
|---|---|---|---|---|---|---|---|
| **C-01 — Suplantación de sesión** (`S`,`E`) | A-02, A-03, A-01 | Un valor presente en `hce_remember_me` se copia a `st.session_state.user` y marca `authenticated=True` sin revalidación visible con Supabase (`services/auth/session_manager.py:51-69`). Requiere poder fijar, robar o reutilizar la cookie. | Acceso con identidad ajena; exposición de conversaciones y posible acceso a tools/datos clínicos. En un uso clínico podría mezclar evidencia de usuarios/pacientes. | Alta | Login inicial mediante Supabase; expiración de cookie de una hora; logout intenta borrar cookie (`services/auth/session_manager.py:77-103`, `:111-147`). | **Crítico** | F1: `IdentityProvider` y `RequestContext`, ADR 0010 y `03`; F2: SSO/MFA/session lifecycle en `05`. |
| **C-02 — Peticiones cross-site y superficie web debilitada** (`S`,`T`,`I`,`E`) | A-02, A-03, A-04 | Streamlit tiene `enableCORS=false` y `enableXsrfProtection=false` (`.streamlit/config.toml:7-10`). Requiere navegador con sesión y origen/página hostil o despliegue expuesto. | Acciones con sesión del usuario, uploads o consultas no intencionadas; posible exposición y contaminación de datos. | Alta | Autenticación de aplicación; ninguna defensa compensatoria verificable en repo. | **Crítico** | F2: browser security en `06` P0.8 y sesión en `05`; F7: WAF/red en `14`. |
| **C-03 — IDOR y ownership incompleto de conversaciones** (`S`,`I`,`E`) | A-02, A-03 | `save_message`/`get_session_messages` aceptan `session_id` tras comprobar solo `is_authenticated`; `AuthService` inserta/consulta por ese ID sin `user_id` (`services/auth/session_manager.py:238-278`; `services/auth/auth_service.py:378-448`). Requiere conocer/adivinar/obtener otro ID o policy externa permisiva. | Lectura o escritura en conversación ajena; fuga de prompts, resultados clínicos, fuentes y metadata; contaminación de contexto. | Alta | Listado, borrado y cambio de título sí filtran por `user_id` (`services/auth/auth_service.py:347-376`, `:483-516`, `:574-598`); posible RLS externo no verificable. | **Crítico** | F1: repositorios con ownership y `RequestContext` en ADR 0010/`03`; F2: C01/C06 y tests de leakage en `05`. |
| **C-04 — Credencial Supabase con privilegio excesivo o confuso** (`S`,`I`,`T`,`E`) | A-01 a A-06 | Una sola `SUPABASE_KEY` alimenta Auth, tablas públicas, MIMIC, vector store y RPC; el tipo de clave no se impone (`docs/architecture/INVENTORY.md:175-192`). Requiere configuración privilegiada, fuga o policy débil. | Compromiso transversal de identidad, conversaciones, corpus y datos; aumenta el blast radius de cualquier fallo de app o secreto. | Media | Secreto fuera de Git por `.gitignore`; allowlists parciales en código. No se verifican privilegios/RLS. | **Crítico** | F1: separar credenciales/mínimo privilegio y adapters (ADR 0010); F2: cifrado/secretos y autorización (`05`, `06`); F7: secret manager/rotación (`14`). |
| **C-05 — Alteración de datos o corpus sin integridad/procedencia suficiente** (`T`) | A-01, A-04, A-10 | Escrituras directas Supabase, metadatos best-effort, RPCs no versionadas y administración por filename/ID. Requiere cuenta/clave con escritura o compromiso del backend. | Evidencia clínica falsa, incompleta o desactualizada; respuestas incorrectas y pérdida de confianza. Puede introducir datos de otra procedencia/paciente. | Media | Metadata básica, IDs de chunks y fuentes; confirmación UI/script para algunos borrados. | **Alto** | F1: repositorios/contratos y audit; F2: validación de tool results; F3: `08` y `09`; F7: backups/rollback. |
| **C-06 — Divulgación por logs, caché y memoria compartida** (`I`) | A-01, A-03, A-06, A-07 | Se registran previews de mensajes y SQL (`services/unified_chat/unified_agent.py:332`, `services/unified_chat/tools/database_tool.py:454`, `services/medical_agent/services/database_service.py:1277`); la caché global usa mensaje+contexto y conserva respuesta (`services/unified_chat/unified_agent.py:366-415`). Requiere acceso a logs/host o colisión lógica de clave. | PHI/PII, consultas y resultados disponibles a otro usuario u operador; retención fuera de la política y fuga de contexto. | Alta | Logs rotatorios por tamaño; TTL de caché de 300 s; caché en memoria; no se observó redacción ni scope. | **Crítico** | F1: `RequestContext`/correlation IDs y stores tipados; F2: minimización, detector PHI, logging seguro y aislamiento (`06`, `05`); F7: retención/operación. |
| **C-07 — Repudio y audit trail insuficiente** (`R`) | A-02, A-10 | Logs técnicos carecen de tenant/user/patient/encounter/purpose/policy decision uniforme y pueden contener texto pero no una cadena auditable. Requiere incidente o disputa. | No se puede atribuir ni reconstruir acceso, fuga, tool call o aprobación; dificulta respuesta clínica, privacidad y notificación. | Alta | Logs, metadata de mensajes, tools usadas, modelo y latencia parciales (`services/auth/auth_service.py:395-412`). | **Alto** | F1: audit/correlation IDs (`03`, `12` P0); F2: logging seguro; F7: observabilidad, incident response y evidencia operacional. |
| **C-08 — Administración de RAG sin roles ni separación de funciones** (`T`,`D`,`E`) | A-04, A-10 | Cualquier flujo autenticado que alcance la UI documental puede indexar/eliminar; scripts locales usan la misma configuración y `scripts/clear_rag.py` borra todo (`scripts/clear_rag.py:20-79`). Requiere cuenta autenticada o acceso local. | Poisoning, retirada de protocolos, pérdida de disponibilidad y procedencia; exposición cruzada si el corpus se comparte. | Alta | Confirmación para borrado en UI/script; extensión/tamaño en upload; no hay RBAC `knowledge-manager`. | **Crítico** | F1: application service/repository y audit; F2: RBAC/ABAC en `05`; F2 como prerrequisito de exposición: ingesta segura/tenant scope de `08` P0 (planificada nominalmente en F3). |
| **C-09 — Dependencia externa sin circuit breaker/kill switch** (`D`) | A-08, A-09 | Fallos Anthropic/Supabase/Hugging Face activan retries/backoff sin circuit breaker global ni modo degradado; inicialización depende de credenciales y red. | Indisponibilidad, latencia, bloqueo de revisión y respuestas parciales potencialmente engañosas; no hay pérdida de PHI directa salvo errores/logs. | Media | Timeouts del cliente/agente, retries y fallback de modelo (`services/unified_chat/unified_agent.py:289-296`; `services/medical_agent/llm_manager.py:265-353`); RAG augmentation degrada a query original. | **Alto** | F1: Model Gateway/timeouts/circuit breakers (`03`, ADR 0010); F2: kill switch/degradación en `07`/`12`; F7: resiliencia/IR. |
| **C-10 — Supply chain/modelo o proveedor manipulado** (`S`,`T`,`E`) | A-05, A-08, A-09 | Dependencias Python no fijadas y artefactos HF descargables; modelos/IDs y SDK externos controlan outputs. Requiere compromiso de paquete, índice, proveedor o canal. | Código comprometido, salida clínica alterada, exfiltración de secretos/datos o indisponibilidad. | Baja | Model IDs configurados explícitamente y entorno observado documentado; ningún lock/hash/SBOM/attestation. | **Alto** | F1: Model Gateway/provider adapters; F2: policies por modelo/egress; F7: pinning, SCA, SBOM, artefactos firmados y egress allowlist (`14`). |
| **C-11 — Exposición o uso indebido de secretos/configuración** (`I`,`E`) | A-06, A-09 | Errores, debug, host comprometido o credencial reutilizada; settings duplicados amplían puntos de carga/uso. Requiere acceso al proceso/host/logs o fallo que incluya configuración. | Acceso a proveedores, gasto, extracción/corrupción de datos y movimiento lateral. | Media | `.env` y `.streamlit/secrets.toml` están ignorados; no hay secreto real versionado de alta confianza; errores de UI suelen generalizar autenticación. | **Alto** | F1: composition root y credenciales por función (ADR 0010); F2: cifrado/rotación y logging seguro (`06`); F7: secret manager/scanning (`14`). |

## Registro de amenazas específicas de IA

| ID | Activo afectado | Vector y precondiciones | Impacto clínico y de privacidad | Prob. | Controles existentes hoy | Riesgo residual | Mitigación trazada |
|---|---|---|---|---|---|---|---|
| **AI-01 — Prompt injection directa** | A-01, A-04, A-05, A-09 | El usuario instruye al modelo para ignorar políticas, alterar rol o invocar tools. Solo requiere poder enviar un prompt. | Respuesta clínica falsa, tool call fuera de propósito, acceso excesivo o divulgación de datos. | Alta | System message separado, límite de 5.000 caracteres, máximo 5 iteraciones/120 s y validadores en cada tool (`services/unified_chat/unified_agent.py:261-296`, `:332-364`). No hay policy enforcement independiente del prompt. | **Crítico** | F1: tool contracts/Model Gateway/Clinical Data Gateway (`03`, `04`, ADR 0010); F2: `07` P0.3-P0.6 y suite adversarial `11`. |
| **AI-02 — Extracción del system prompt, schema o configuración** | A-05, A-06 | Peticiones directas, encoded/obfuscated o multivuelta para reproducir instrucciones, nombres de tools, schema o configuración. | Facilita bypass y fingerprinting; puede revelar arquitectura y reglas SQL. No debería revelar valores de secretos salvo fallo adicional. | Alta | Separación de mensaje `system`; tres casos básicos definidos pero no ejecutados y verificación por keywords débil (`Evaluation/run_security_tests.py:223-263`; baseline). No hay detector o filtro de salida. | **Alto** | F2: `07` P0.4, DLP/egress `06` P1.2 y ampliación/gates `11`. |
| **AI-03 — Prompt injection indirecta** | A-01, A-03, A-04, A-05 | Instrucciones embebidas en PDF/texto, historial persistido o resultados de tools se incorporan al contexto. Requiere que el contenido sea cargado/recuperado o aparezca en historial. | El corpus puede redirigir tools, ocultar evidencia, exfiltrar datos o generar afirmaciones peligrosas; persiste y afecta a múltiples usuarios. | Alta | Roles LangChain para historial; top-k/deduplicación/truncado de tool context. El contenido RAG no se delimita como dato no confiable ni se escanea. | **Crítico** | F1: contratos/result validation; F2: `07` P0.5-P0.6 y tests `11`; ingesta segura de `08` P0.4 debe adelantarse como gate antes de compartir RAG. |
| **AI-04 — Inyección vía SQL o tools** | A-01, A-04, A-09 | El prompt induce `custom_query`, filtros o argumentos inesperados. El LLM conoce schema y ejemplos y la RPC recibe SQL completo (`services/unified_chat/tools/database_tool.py:89-168`, `:426-645`). | Lectura excesiva, inferencia de cohortes, errores/coste/DoS y potencial bypass dependiente de la RPC/DB. Aunque sea `SELECT`, viola mínimo necesario. | Alta | Solo `SELECT`, keywords/patrones/tablas permitidas, longitud 2.000, complejidad y límites parciales. Son regex, no parser/plan, y no imponen paciente/tenant. | **Crítico** | F1: eliminar `custom` productivo y usar operaciones allowlisted con `RequestContext` (`04` P0.1-P0.3, ADR 0010); F2: `07` y `11`. |
| **AI-05 — Exfiltración de datos por salida o proveedor** | A-01, A-03, A-04, A-06, A-07 | Prompt pide volcar datos; tools devuelven datos amplios; Anthropic recibe mensaje, historial y tool results; augmentation recibe consulta y visualización envía muestra de DataFrame (`docs/architecture/INVENTORY.md:164-169`; `services/medical_agent/visualization_agent.py:869-888`). | Divulgación de datos clínicos/PII a usuario, logs o proveedor; incumplimiento de propósito, minimización, residencia/retención. | Alta | Autenticación básica, top-k/row limits parciales, proveedor vía SDK. No hay clasificación PHI, minimización, pseudonimización, DLP ni policy de modelo verificable. | **Crítico** | F1: autorización antes de tools/modelo; F2: `06` P0.2-P0.7/P1.2, `05` P0.5, `07` P0.9 y tests `11`. |
| **AI-06 — Fuga entre pacientes** | A-01, A-03, A-07 | IDs de paciente/estancia son argumentos elegidos por usuario/modelo; no existe `RequestContext` obligatorio ni relación asistencial. Caché/historial no están ligados al paciente. | Mezcla de historias y evidencia; daño de privacidad y, si se reutiliza clínicamente, decisiones sobre el paciente incorrecto. | Alta | IDs deben ser enteros positivos en algunas operaciones; filtros por `subject_id`/`stay_id`; ninguna autorización de relación/contexto. | **Crítico** | F1: `RequestContext` y Clinical Data Gateway (`04`, ADR 0010); F2: ABAC/context isolation y leakage tests (`05`, `11`). Gate aprobado: 0 fugas. |
| **AI-07 — Fuga entre tenants** | A-01, A-03, A-04, A-07 | No hay `tenant_id` en requests, repositorios, caché ni búsquedas; `rag_chunks` y RPCs son globales. Requiere más de un hospital/tenant sobre el mismo despliegue. | Exposición de historias, conversaciones o protocolos de otro hospital; contaminación de conocimiento y responsabilidad contractual/regulatoria. | Alta en despliegue multitenant; no aplicable en instancia estrictamente única | Ningún control de tenant en código. Una instancia única reduce exposición actual, pero no constituye aislamiento multitenant. | **Crítico** | F1: `RequestContext`; F2: tenant isolation/RBAC/ABAC (`05` P0.6/P1.1), PHI policy `06`, tests `11`; RAG tenant namespace `08` P0.5 antes de multitenancy. |
| **AI-08 — Consultas masivas no autorizadas** | A-01, A-08, A-09 | El propio tool enseña consultas dataset-wide sin `subject_id`; el límite se aplica al resultado Python después de ejecutar la RPC custom (`services/unified_chat/tools/database_tool.py:151-161`, `:426-467`). | Enumeración de pacientes/cohortes, extracción masiva, coste y carga de DB/LLM. | Alta | Límites nominales 1.000/5.000 filas; rate limiter local por `session_id`; máximo de iteraciones. No hay quota por tenant/usuario/función ni límite garantizado en DB para SQL custom. | **Crítico** | F1: retirar SQL, operaciones tipadas y límites en provider (`03` P1.3, `04`); F2: DLP/egress `06`, tool contracts `07`, pruebas `11`. |
| **AI-09 — Envenenamiento del RAG** | A-04, A-05, A-10 | Usuario o insider indexa contenido falso, obsoleto o adversarial; metadata personalizada se mezcla sin aprobación (`services/unified_chat/document_manager.py:91-138`). | Respuestas sistemáticamente falsas o sesgadas, pérdida de procedencia y propagación a otros usuarios; posible fuga vía instrucciones. | Alta | Extensión/tamaño, chunk IDs, filename/specialty/type y ranking. No hay status, clinical owner, version resolution, aprobación ni tenant. | **Crítico** | F2 como gate de seguridad: RBAC/scan/aislamiento; F3: gobierno completo en `08` P0.1-P0.6 y evidencia en `09`; evaluación en `11`. |
| **AI-10 — Documentos maliciosos** | A-04, A-05, A-09 | PDF/DOCX/TXT preparado explota parser, consume recursos o contiene instrucciones ocultas. Requiere upload o acceso a `guias/`. | Compromiso/DoS del proceso, poisoning persistente, exfiltración y respuestas clínicas manipuladas. | Media | Allowlist por extensión, máximo 50 MB, temporal aleatorio y borrado best-effort (`services/unified_chat/document_manager.py:62-89`; `ui/unified_chat_interface.py:1459-1500`). Sin MIME/magic, malware scan, sandbox o content scan. | **Crítico** | F2: upload auth/RBAC, límites y content injection controls; `08` P0.4 debe ser prerrequisito; F7: aislamiento/scan de artefactos. |
| **AI-11 — Uso indebido de herramientas** | A-01, A-04, A-05, A-09 | El modelo decide entre DB, RAG y visualización mediante prompt; las tools no reciben permisos, propósito, tenant/patient scope ni approval. | Acceso a datos o acción documental fuera de propósito, respuestas con evidencia equivocada y gasto. | Alta | Schemas Pydantic, validación específica y máximo de iteraciones. No hay policy engine fuera del prompt ni audit metadata uniforme. | **Crítico** | F1: contratos explícitos, registry, `RequestContext`, Model/Clinical Gateway (`03`, `04`, ADR 0010); F2: `07` P0.1-P0.6 y `11`. |
| **AI-12 — Agotamiento de recursos** | A-08, A-09 | Prompts repetidos, historial grande, multi-query+HyDE, búsquedas múltiples, PDFs/OCR, embeddings, reranking, SQL amplio o código/figuras costosos. Requiere acceso autenticado o upload. | Indisponibilidad y coste; retraso de evaluaciones y respuestas incompletas. Puede afectar a todos los usuarios del proceso compartido. | Alta | Mensaje 5.000 chars, rate limiter singleton en memoria, top-k, historial máximo alto, 5 iteraciones/120 s, file size 50 MB y cache LRU. No hay quotas distribuidas ni límites efectivos CPU/RAM por tarea. | **Alto** | F1: timeouts/circuit breakers/background jobs/quotas (`03`); F2: tool timeouts/max data y kill switch (`07`, `12`); F7: resource limits/infra. |
| **AI-13 — Ejecución de código arbitrario generado por el modelo** | A-01, A-06, A-09 | Si falla un template, Anthropic genera Python que pasa un validador AST y se ejecuta con `exec` en el proceso (`services/medical_agent/visualization_agent.py:232-283`; `services/medical_agent/code_executor.py:301-437`). `__import__` está disponible; no hay proceso, filesystem o red aislados y el parámetro timeout no se aplica. | Compromiso del proceso/host, lectura de secretos/datos, exfiltración, manipulación de resultados y DoS. | Media | Allowlist nominal de imports/nombres, builtins reducidos y validación de figura. El enfoque de denylist/AST no es un sandbox. | **Crítico** | F1: sacar generación de código de la ruta y usar templates deterministas (ADR 0010); F2: `07` P0.7-P0.8 y tests `11`. No habilitar en entorno compartido. |

## Riesgos críticos que no pueden esperar

El orden prioriza blast radius, facilidad de acceso y dependencia de otras mitigaciones. «No puede esperar» significa que debe ser un gate antes de exponer el prototipo a usuarios o datos hospitalarios, aunque la implementación pertenezca a Fase 1 o 2.

| Prioridad | Riesgos | Gate requerido | Fase/documentos |
|---:|---|---|---|
| 1 | C-01, C-03, AI-06, AI-07 | Ninguna petición o repositorio opera sin principal revalidado, ownership y contexto obligatorio; cero fugas entre usuario/paciente/tenant. | **F1** `RequestContext`, `IdentityProvider`, repositorios; **F2** SSO/RBAC/ABAC y tests (`03`, `05`, ADR 0010, `11`). |
| 2 | AI-04, AI-08, AI-11 | Eliminar SQL libre del contrato productivo; operaciones clínicas allowlisted, scoped, limitadas y auditadas antes del LLM. | **F1** Clinical Data Gateway/tool contracts (`04`, `07`, ADR 0010); **F2** suite adversarial (`11`). |
| 3 | AI-13 | Desactivar el fallback de código generado en toda ruta compartida; solo templates deterministas. | **F1** ADR 0010; **F2** `07` P0.7-P0.8 y `11`. |
| 4 | C-06, AI-05 | Impedir que PHI/PII llegue sin necesidad a modelo, logs, caché o respuestas; scope de caché y política de egreso verificable. | **F1** fronteras/contexto; **F2** `06`, `05`, `07`, `11`. |
| 5 | AI-03, AI-09, AI-10, C-08 | Suspender uploads compartidos hasta tener rol de knowledge manager, análisis de fichero/contenido, aprobación y tenant scope. | **F2** controles de identidad/inyección; adelantar como gate los P0 de `08` que el plan agrupa en **F3**. |
| 6 | C-02 | Reactivar protecciones web y definir cookies/CSRF/CORS/headers por entorno. | **F2** `06` P0.8; endurecimiento de red en F7 `14`. |
| 7 | C-04, C-11 | Separar credenciales por función, verificar RLS/policies, eliminar claves amplias y preparar rotación. | **F1** adapters/mínimo privilegio; **F2** `05`/`06`; F7 `14`. |
| 8 | C-07, C-09, AI-12 | Audit/correlation IDs desde el primer corte; límites, circuit breakers y kill switch antes de pruebas multiusuario. | **F1** `03`/`12`; **F2** `07`/`12`; F7 operación completa. |

Hasta cerrar al menos las prioridades 1 a 7, el sistema debe permanecer limitado a un entorno de investigación controlado, de un solo tenant, con datos anonimizados/preparados y usuarios explícitamente autorizados. Esa restricción aplica el intended purpose vigente; no es una nueva aceptación de riesgo.

## Cobertura de pruebas y criterios de cierre

La suite actual no proporciona evidencia suficiente para reducir ningún riesgo crítico:

- las 13 definiciones de seguridad no se ejecutaron por bloqueo de configuración;
- solo hay casos básicos de SQL injection, prompt injection y anti-hallucination;
- no hay pruebas ejecutadas de indirect injection, prompt extraction robusta, cross-patient, cross-tenant, exfiltración, bulk queries, RAG poisoning, documentos maliciosos, tool misuse, resource exhaustion o escape del executor;
- los verificadores actuales se basan en keywords de respuesta y no inspeccionan policy decisions, accesos reales ni ausencia de efectos laterales (`Evaluation/run_security_tests.py:45-140`).

Fase 2 debe convertir los objetivos de `ROADMAP_HOSPITAL_READY/11-evaluation-red-team.md` en gates bloqueantes. Se mantienen los tres objetivos ya aprobados: 0 accesos no autorizados, 0 fugas entre pacientes/tenants y 0 violaciones de políticas de herramientas (`docs/product/RISK_CAPABILITY_MATRIX.md`).

## Incertidumbres que deben verificarse, no asumirse

Estas preguntas no requieren cambiar las decisiones DP-01 a DP-08, pero sí evidencia antes de recalcular el riesgo residual:

1. tipo y privilegios efectivos de cada `SUPABASE_KEY` desplegada;
2. RLS/policies de todas las tablas y autorización de las RPC `execute_readonly_query`, `hybrid_search` y `vector_search`;
3. topología de despliegue, terminación TLS, acceso de red y controles del reverse proxy;
4. retención, región, training policy y acuerdos del deployment Anthropic utilizado;
5. corpus realmente indexado, responsables, licencias, versión, vigencia y aprobación;
6. quién puede alcanzar hoy gestión documental y scripts administrativos;
7. si la caché está habilitada en cada entorno y si existen varios procesos/instancias;
8. qué datos reales contiene la instancia Supabase usada en cada entorno.

Un control externo solo podrá descontarse del riesgo cuando esté documentado, probado y vinculado al despliegue. Ninguna de estas incertidumbres se interpreta como control existente.

## Mantenimiento del modelo

Revisar este threat model al introducir `RequestContext`, FastAPI, un Model/Clinical Data Gateway, una nueva fuente clínica, multitenancy, un proveedor/modelo distinto, cambios de tools/prompts, ingesta RAG, ejecución de código, SMART/FHIR o una transición de intended purpose. Cada cambio debe actualizar amenazas, controles, evidencia de pruebas, propietario y riesgo residual sin borrar la fotografía de Fase 0.
