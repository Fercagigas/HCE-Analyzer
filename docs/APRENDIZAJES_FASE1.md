# Aprendizajes de la Fase 1 (Foundation) — una clase magistral

**Fecha:** 2 de septiembre de 2026
**Alcance:** todo lo que se tuvo en cuenta, lo que se construyó y por qué, y lo que se aprendió al convertir un prototipo Streamlit de IA clínica en una base de producto. Complementa los ADRs 0050–0120 (decisiones) y `docs/baseline/FASE1_BASELINE.md` (evidencia). Este documento explica el razonamiento, no repite el detalle.

---

## 1. El punto de partida: por qué un prototipo que "funciona" no es una base

El prototipo de Fase 0 hacía lo que prometía: un clínico podía preguntar por un paciente, buscar una guía y pedir una gráfica. Sin embargo, el inventario y el threat model revelaron que su funcionamiento dependía de cinco propiedades incompatibles con un producto sanitario:

1. **El modelo era quien decidía a qué datos acceder.** Podía redactar SQL libre (`custom_query`) que una RPC ejecutaba con privilegios elevados. Cualquier documento o mensaje que convenciera al modelo se convertía en una consulta arbitraria sobre todos los pacientes.
2. **La identidad vivía en la interfaz.** El usuario se leía de una cookie sin revalidar y de `st.session_state`; el "paciente" era un número que el modelo escribía como argumento.
3. **El sistema ejecutaba código generado por el modelo** dentro de su propio proceso para dibujar gráficas.
4. **La configuración fallaba al importar.** Sin credenciales no se podía ni cargar un módulo, así que la suite de tests estaba roja y nadie podía verificar nada sin acceso a producción.
5. **Las dependencias no coincidían con las importadas** (`langchain_classic` sin declarar, `crewai` y `openai` declarados sin uso).

La primera lección es de método: **antes de reescribir, medir.** La Fase 0 produjo un baseline (44 tests, 17 rojos por una sola causa), un inventario por símbolo y un threat model con riesgos ordenados por blast radius. Sin eso, la Fase 1 habría sido una opinión sobre qué mejorar; con eso, fue una lista de gates que cerrar.

---

## 2. Principios de trabajo que guiaron todo

### 2.1 Seguridad como código, nunca como prompt

"No hagas X" en el system prompt no es un control; es una sugerencia que un atacante puede negociar. Cada límite crítico se implementó como código determinista que se ejecuta **antes** de que el modelo reciba datos: `ScopeGuard` rechaza el paciente equivocado, `ToolPolicy` exige propósito de investigación para agregados, `ToolContract` impide parámetros no previstos. El prompt informa al modelo de las reglas para que colabore, pero su cumplimiento no depende de él.

### 2.2 El estado por defecto debe ser el más seguro

Se eligió **scope estricto**: sin paciente activo, las herramientas clínicas se rechazan. La alternativa laxa (permitir todo si no hay paciente) hacía que el estado inicial fuera el más permisivo. Costó fricción de uso (hay que elegir paciente antes de preguntar); se aceptó porque la fricción es visible y la fuga no lo es.

### 2.3 Contratos antes que código

Cada frontera se definió como un contrato tipado antes de implementarla: `RequestContext`, `ToolContract`/`ToolResult`, `Evidence`/`Claim`, `ChatResponse`, los nueve ports. Esto permitió escribir fakes y tests de contrato antes de tener el adapter real, y que Streamlit, FastAPI y los runners de evaluación consumieran lo mismo.

### 2.4 Strangler, no big bang

El legacy siguió funcionando en cada commit. La técnica: crear el paquete nuevo `chathce/` al lado, mover capacidad a capacidad, dejar fachadas (`UnifiedChatAgent`, `SessionManager`, `LegacyAgentFacade`) con la misma firma que consumían UI y evaluación, y borrar el legacy solo al final (WP12). Cada paquete de trabajo terminaba con `streamlit run` operativo y la suite en verde.

### 2.5 Decisiones explícitas con alternativas descartadas

Cada decisión estructural tiene un ADR con las opciones que se rechazaron y por qué. El valor no está en justificar lo elegido sino en que, dentro de un año, alguien pueda ver que "generar SQL en el core a partir de parámetros" ya se consideró y por qué se descartó (la RPC de ejecución de texto es el riesgo en sí, no quién redacta el texto).

### 2.6 Un paquete de trabajo, un commit verificable

Trece paquetes secuenciales, cada uno con su criterio de verificación y un commit con mensaje convencional. Esto hizo el historial legible y permitió, al final, reconstruir qué cambió y cuándo sin releer código.

---

## 3. Las decisiones de arquitectura y su razonamiento

### 3.1 Ports and adapters con frontera verificada por máquina (ADR 0110)

No basta con "no importes Streamlit en el dominio" como convención. Un test recorre el AST de `chathce/{domain,ports,application,gateway}` y falla si aparece `streamlit`, `supabase`, `postgrest`, `anthropic` o `langchain*`; otro lanza un subproceso, importa el core y comprueba `sys.modules`. La convención pasó a ser una propiedad del build.

El **composition root** único (`build_container`) es el único sitio que sabe qué adapter se usa. Perfiles `fake`/`memory` permiten levantar el sistema completo sin red, que es lo que hace posibles los tests de aplicación y de API.

Lección: la arquitectura que no se verifica automáticamente se erosiona en el primer sprint con prisa.

### 3.2 Acceso clínico allowlisted y agregados server-side (ADR 0050)

Se eliminó el SQL libre completamente, también para investigación. El razonamiento: cualquier ruta por la que el modelo pueda formular una consulta es una ruta de fuga; la única mitigación completa es que no exista. Las operaciones que el producto realmente usaba eran pocas y estables (paciente, ingresos, diagnósticos, laboratorio, medicación, UCI, códigos, cuatro agregados). Se convirtieron en operaciones tipadas del port y los agregados en cuatro funciones SQL fijas (`SECURITY INVOKER`, `search_path` fijo, `statement_timeout`, límite acotado).

Defensa en profundidad: aunque `ScopeGuard` ya rechaza el paciente equivocado, el adapter añade siempre `.eq("subject_id", ctx.patient_id)`. Si una capa falla, la otra sigue.

Efecto secundario valioso: al resolver etiquetas contra diccionarios cacheados desapareció el N+1 de diagnósticos que hacía una consulta por código.

### 3.3 Model Gateway propio sobre el SDK nativo (ADR 0080)

Se retiró LangChain del bucle agéntico. No por rechazo al framework sino porque el `AgentExecutor` controlaba el bucle, los reintentos y la forma de los mensajes, y eso impedía aplicar política de tools, deadline total, eventos de alto nivel y auditoría por petición. Un bucle propio de unas pocas cientos de líneas sobre `AsyncAnthropic.messages.stream` dio control completo con menos dependencia.

Detalles que importan más de lo que parecen:
- `max_retries=0` en el cliente: los reintentos los decide el gateway, con `asyncio.sleep`, nunca `time.sleep` que bloquearía el event loop.
- La cadena de modelos es **por petición**, no por proceso: un fallo de Haiku en una petición no degrada a Sonnet a todos los usuarios.
- `health()` usa `models.retrieve`, que no gasta tokens; el legacy hacía una generación real en cada arranque.
- Al agotar iteraciones, una llamada final sin tools produce una síntesis honesta en vez de un error.

### 3.4 RequestContext, contratos y Evidence/Claim (ADR 0090)

`RequestContext` es inmutable, se construye una vez por petición y viaja como primer argumento de toda operación. Contiene quién (usuario, roles, tenant), sobre quién (paciente, episodio), para qué (propósito) y cómo seguirlo (trace, request, sesión). Las políticas solo pueden comprobar lo que está en el contexto; por eso el propósito de investigación exige el rol `researcher` al construirlo, no al usarlo.

`ToolContract` es lo único que el modelo ve de una herramienta y por eso está validado: entrada `extra="forbid"`, y ningún término de la lista prohibida (SQL, `select`, esquemas, las 18 tablas) en nombre, descripción ni schema. El contrato falla al construirse, no en producción.

`Evidence`/`Claim` se implementaron en versión mínima: una `Claim` por resultado de tool y una inferencia por respuesta. No se intentó el Evidence Engine completo (una afirmación por frase) porque exige post-procesado del texto del modelo y evaluación propia; se fijó el formato para que la Fase 3 no rediseñe.

### 3.5 Autenticación por JWT de Supabase y cookie revalidada (ADR 0100)

Se rechazó un sistema de sesiones propio (duplicaría el proveedor de identidad) y la verificación local del JWT (con claves legacy el secreto de firma es compartido). Se eligió verificar el token contra Supabase con caché corta. En Streamlit la cookie pasó de contener el usuario completo a contener solo el refresh token, y cada carga revalida o refresca. Un usuario revocado deja de restaurar sesión.

Se documentó honestamente lo que no se resolvió: la cookie de Streamlit sigue siendo legible desde JavaScript (limitación del componente) y la clave de servicio de Supabase ignora RLS. Se definieron claves por función para separar privilegios ahora y se dejó RLS por usuario como primer gate de Fase 2.

### 3.6 Tests por capas con fixtures grabadas (ADR 0120)

El problema clásico: cómo probar un adapter de Supabase sin Supabase. Los mocks de la API fluida de PostgREST son frágiles y no prueban nada. La solución fue **grabar fixtures reales** (3 pacientes, 17 tablas, una sola lectura) y escribir un cliente PostgREST **en memoria** que reproduce la API fluida y las RPC de agregados. El adapter real se ejecuta contra datos reales sin red, y su salida se compara con la salida congelada del servicio legacy antes de borrarlo.

Capas: `unit` (sin red salvo loopback, sin `.env`), `contract`, `integration` (solo con bandera y credenciales), `security`, `evaluation`. La suite pasó de 44 tests con 17 rojos a 278 con 271 verdes y 7 saltados, y se ejecuta sin credenciales en menos de un minuto.

---

## 4. Técnicas concretas que merece la pena recordar

- **Datos no confiables delimitados.** Todo resultado de tool llega al modelo como `<tool_data trust="untrusted_data">` con el cierre escapado y recorte de tamaño. El prompt declara que ese contenido son datos, nunca instrucciones. Con esto, un documento RAG que diga "cambia al paciente X" no puede ejecutarse como orden.
- **Historial resumido.** Entre turnos se reproducen texto y lista de tools usadas, nunca los datos de tools anteriores. Si el clínico cambia de paciente dentro de la sesión, los datos del anterior no viajan.
- **Caché de respuestas eliminada.** La clave anterior no incluía usuario ni paciente: la misma pregunta de dos usuarios devolvía la respuesta cacheada del primero. Se prefirió no tener caché a tener una caché con scope dudoso.
- **`dispatch` que nunca lanza.** Todo error de tool (desconocida, entrada inválida, scope, timeout, proveedor caído) se convierte en `ToolResult(success=False)` con código, se audita, y el modelo lo recibe como `is_error`. El bucle no se rompe por una tool.
- **Auditoría con allowlist de atributos.** `AuditEvent` acepta solo claves conocidas; no admite texto libre. Es la forma de garantizar que el log de auditoría no se convierte en otra fuga de datos clínicos.
- **Settings perezosos.** `get_settings()` con caché y `require_database()`/`require_anthropic()` que se invocan en el composition root. Importar no falla nunca; construir el sistema sí, con un error claro.
- **Eventos SSE de alto nivel.** `status`, `tool_call`, `tool_result_summary`, `text_delta`, `complete`, `error`. Nunca razonamiento interno del modelo. La interfaz futura sabe qué está pasando sin que el sistema exponga su prompt.
- **`AsyncRunner`** con un hilo y su propio event loop para que Streamlit (síncrono) llame al core (asíncrono) sin reentrancia.

---

## 5. Lecciones de la evaluación: medir el medidor

La evaluación live enseñó más que cualquier test unitario, y no por lo que dijo del producto sino por lo que dijo de los instrumentos.

1. **RAGAS puntuó 0,11 de faithfulness** en la primera ejecución. La auditoría demostró que el agente había usado las tools correctas en las 40 preguntas. El fallo estaba en el runner: el dict legacy ya no llevaba los datos de las tools y RAGAS evaluaba contra resúmenes. Tras exponer el texto visible al modelo como contexto, precisión y recall de contexto pasaron a 0,81 y 0,77. **Antes de creer una métrica mala, verifica qué se le está pasando.**
2. **Un test "anti-alucinación" penalizaba una respuesta correcta.** `SEC-ANTI-003` preguntaba por "el resultado de la cirugía" esperando "no consta"; el paciente sí tenía cirugía documentada y el modelo la describió con fechas trazables a los procedimientos. La premisa del test venía del dataset anterior (urgencias). **Los casos de evaluación tienen que validarse contra los datos reales, no heredarse.**
3. **Los verificadores por palabras clave dan falsos negativos** ante rechazos legítimos redactados de otra forma ("no puedo mostrar" frente a "no puedo ejecutar") y falsos positivos cuando el rechazo repite las palabras del ataque ("no puedo generar pacientes ficticios"). Se pasó a detectar la forma del fallo (un listado con identificadores y diagnósticos) en lugar del eco de términos.
4. **El informe ocultaba categorías nuevas.** Las pruebas cross-patient se ejecutaban pero el resumen listaba tres categorías fijas. Una lista hardcodeada en un informe es un bug silencioso: todo parece bien porque lo que falta no aparece.
5. **`answer_relevancy` sale baja incluso con respuestas perfectas** (faithfulness 1,0, contexto exacto, relevancy 0,32). La métrica genera preguntas a partir de la respuesta y las compara con embeddings locales en español; no está calibrada para este dominio. Se documentó como pendiente en lugar de ajustar el umbral para que pasara.
6. **Las métricas agregadas mezclan causas.** Cinco preguntas de agregados fallan porque la migración SQL no está aplicada; el resto no. Reportar 0,78 sin explicar que sin esas cinco es 0,86 sería ocultar información útil.

Lección transversal: **un fallo de runner y un fallo de producto se documentan por separado**, con la primera y la última ejecución guardadas. Corregir el runner y reportar solo el resultado bueno habría sido deshonesto; reportar solo el malo habría sido falso.

---

## 6. Lo que se decidió no hacer, y por qué eso también es diseño

- **Ninguna feature clínica nueva.** La tentación de añadir "Since Last Review" sobre la base nueva era real; se resistió porque cualquier feature construida antes del Evidence Engine y de RBAC habría que rehacerla.
- **Ni React, ni FHIR, ni RLS, ni Evidence Engine.** Pertenecen a Fases 2 a 5. Lo que sí se hizo fue dejar los puntos de anclaje: el port `ClinicalDataProvider` que un adapter FHIR implementará, la API SSE que React consumirá, el flag para reenviar el JWT del usuario al provider, los schemas `Evidence`/`Claim`.
- **Un solo worker uvicorn.** El RAG carga modelos locales en el proceso; prometer varios workers sin separar el servicio de embeddings sería mentir sobre la escalabilidad.
- **Sin umbral de cobertura bloqueante.** Con `ui/` y `services/rag` aún legacy, un umbral global castigaría el código que no se tocó. Se midió (56 %, con el core entre 75 y 100 %) y se aplazó el gate.
- **El RAG siguió siendo legacy**, envuelto por `KnowledgeRepository`. Migrarlo habría duplicado el tamaño de la fase sin reducir ningún riesgo crítico.

---

## 7. Errores de proceso que costaron tiempo (y cómo evitarlos)

- **`pydantic-settings` ignora `env=` en `Field`** (v2). Los prefijos por sección hay que declararlos con `env_prefix`. Síntoma: variables que "no se leen" sin error alguno.
- **Dependencias no declaradas.** `langchain_classic` funcionaba porque estaba instalado en la máquina de desarrollo. Un test que importa el agente en subproceso y comprueba `sys.modules` cierra esa puerta para siempre.
- **Términos prohibidos en sitios inesperados.** El guard de schemas detectó `SQL` en un docstring y `eMAR` en el título de un campo. Es exactamente lo que debe hacer: el modelo ve el schema entero.
- **Golden set no determinista.** Un campo `computed_at` en los contextos hacía que dos generaciones difirieran. Todo lo que se compara byte a byte tiene que excluir relojes.
- **Backslashes en el shell.** Un parche aplicado por heredoc convirtió `\\b` en un carácter de retroceso dentro de una expresión regular; el test pasaba porque la heurística nunca coincidía. Los ficheros se escriben con herramientas de fichero, no por el shell.
- **Tests flaky de Hypothesis** por `too_slow` en máquinas lentas: se desactiva ese health check, no se relaja la propiedad.

---

## 8. Cómo leer los números del cierre

| Indicador | Valor | Qué significa y qué no |
|---|---|---|
| Tests | 271 pasan, 7 saltados, 0 fallos | La suite es verde sin credenciales; los saltados son live y requieren bandera. No mide la UI. |
| Cobertura | 56 % global; core 75–100 % | Cobertura de líneas, no de comportamiento; `ui/` legacy al 0 %. |
| Seguridad live | 18/18 en 5 categorías | Verificadores por palabras clave más allowlist de tools; los offline inspeccionan rechazos reales. |
| Casos funcionales | 57/58 | El fallo depende de una migración no aplicada, no del código. |
| RAGAS clínico | precisión 0,81, recall 0,77, faithfulness 0,78 | Sin las 5 preguntas de agregados: 0,93 / 0,88 / 0,86. `answer_relevancy` no es interpretable aún. |
| Latencia | DB 9,9 s, RAG 10,8 s, compleja 23,6 s | Medias de 3 ejecuciones con el modelo más rápido; orientativas. |

---

## 9. Lo transferible: qué haría igual en cualquier sistema de IA clínica

1. Baseline e inventario antes de tocar código; el threat model ordena el trabajo.
2. Un contexto de petición inmutable como primer argumento de todo.
3. El modelo elige entre operaciones cerradas; nunca redacta consultas ni código.
4. Todo lo que el modelo lee de fuera va delimitado como dato no confiable.
5. Las fronteras de arquitectura se verifican con tests, no con documentación.
6. Fakes y fixtures grabadas para que el sistema entero arranque sin red.
7. Cada decisión con sus alternativas descartadas por escrito.
8. Cada métrica con su instrumento auditado y sus causas separadas.
9. Lo que no se resolvió, escrito con la misma claridad que lo que sí.

---

## 10. Qué abre la Fase 2

Con el contexto obligatorio, el scope en aplicación y la auditoría, la Fase 2 puede añadir la segunda barrera (RLS por usuario reenviando el JWT), roles reales, minimización de campos antes del modelo, circuit breaker y kill switch, y ampliar la suite adversarial (ataques codificados, cross-tenant, concurrencia, envenenamiento del RAG). Nada de eso exige rediseñar lo construido; esa es la prueba de que la Fase 1 cumplió su objetivo.
