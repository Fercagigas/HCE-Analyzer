# Casos de uso clínicos permitidos

## Regla de inclusión

Un caso de uso está permitido en la versión 1 solo para investigación/educación con médicos, opera sobre fuentes autorizadas y disponibles, conserva el contexto de paciente y episodio cuando la tarea está vinculada a ellos y no influye en decisiones asistenciales reales. Su inclusión en este documento no autoriza su activación: cada capability y servicio debe superar los controles y evaluaciones de [RISK_CAPABILITY_MATRIX.md](RISK_CAPABILITY_MATRIX.md).

Todos los casos comparten estas condiciones:

- acceso de solo lectura y mínimo necesario;
- autorización antes de que los datos lleguen al modelo;
- evidencia y procedencia verificables para las afirmaciones relevantes;
- distinción visible entre hechos, contenido de guías, cálculos e inferencias;
- indicación de información ausente, contradictoria, desactualizada o fuera del ámbito consultado;
- abstención cuando la evidencia no permita responder;
- registro auditable de usuario, contexto, fuentes, herramientas y versiones;
- revisión humana antes de usar el resultado en una decisión o documento clínico.

## UC-01 — Resumir la HCE disponible

**Objetivo:** condensar información autorizada de un paciente o episodio para reducir la lectura manual inicial.

**Entrada:** recursos clínicos seleccionados y delimitados por paciente, episodio y periodo.

**Salida permitida:** resumen estructurado con hechos enlazados a sus fuentes, periodo cubierto, información no disponible, conflictos y cualquier inferencia identificada como tal.

**Límite:** no declarar que el resumen es completo si las fuentes no lo son, no omitir deliberadamente evidencia conflictiva y no convertir el resumen en diagnóstico, triaje o plan terapéutico.

## UC-02 — Localizar evidencia

**Objetivo:** encontrar datos de la HCE o fragmentos de documentos que respondan a una pregunta del profesional.

**Entrada:** una consulta y el contexto clínico autorizado.

**Salida permitida:** resultados recuperados con identificador de fuente, paciente/episodio cuando aplique, fecha, unidad, versión documental, página o sección y calidad de recuperación disponible.

**Límite:** la ausencia de resultados significa «no encontrado en las fuentes consultadas», no que el hecho no exista. El LLM no construye SQL libre contra datos clínicos de producción.

## UC-03 — Reconstruir la evolución

**Objetivo:** ordenar eventos y mediciones para presentar una historia longitudinal navegable.

**Entrada:** eventos clínicos autorizados con timestamps y procedencia.

**Salida permitida:** línea temporal que conserva los eventos originales, normaliza unidades de forma controlada y marca por separado las relaciones temporales inferidas.

**Límite:** no inventar causalidad, no confundir fecha de registro con fecha clínica y no ocultar huecos, duplicados o inconsistencias.

## UC-04 — Comparar episodios o periodos

**Objetivo:** mostrar similitudes y diferencias entre dos ámbitos seleccionados por el profesional.

**Entrada:** episodios, periodos o conjuntos de datos explícitos y comparables.

**Salida permitida:** comparación de valores, tendencias, diagnósticos registrados, medicación registrada o documentos, con evidencia en ambos lados y alcance declarado.

**Límite:** no presentar correlación como causalidad ni emitir una recomendación por el mero hecho de encontrar una diferencia.

## UC-05 — Buscar protocolos

**Objetivo:** recuperar conocimiento clínico relevante para una consulta desde la base documental gobernada.

**Entrada:** pregunta, especialidad/servicio y filtros de vigencia o ámbito.

**Salida permitida:** extractos de documentos aprobados con título, versión, estado, fecha de vigencia, clinical owner y localización exacta; una síntesis debe enlazar cada afirmación a esos extractos.

**Límite:** borradores, documentos vencidos, retirados o sustituidos no participan por defecto. Un protocolo general no se presenta como instrucción individual para el paciente.

> **DECISIÓN ADOPTADA (DP-05):** La versión 1 solo admite protocolos internos aprobados por el hospital. Las guías externas y la búsqueda externa en tiempo real quedan fuera hasta contar con curación, versionado, autoridad, trazabilidad y aprobación explícitos.

## UC-06 — Detectar cambios

**Objetivo:** identificar hechos nuevos, modificados o retirados desde un punto de revisión o entre dos periodos.

**Entrada:** dos snapshots o ventanas temporales explícitas.

**Salida permitida:** diff determinista de eventos y, si la capability de inferencia está validada, una priorización separada de cambios potencialmente relevantes con explicación y evidencia.

**Límite:** «sin cambios detectados» se limita a los recursos comparados. La relevancia clínica es una inferencia, no un hecho, y no sustituye la revisión del profesional.

## UC-07 — Preparar borradores

**Objetivo:** generar un borrador de handoff, resumen o nota a partir de información seleccionada.

**Entrada:** evidencias y contexto reunidos explícitamente por el profesional.

**Salida permitida:** texto editable marcado de forma persistente como `AI-generated draft`, con fuentes y elementos pendientes de comprobar, visible únicamente dentro del workspace de ChatHCE.

**Límite:** ChatHCE no ofrece en la versión 1 una función para copiar, exportar, guardar en la HCE, firmar o enviar el borrador, y este no ejecuta ninguna orden. Cualquier mecanismo de transferencia requerirá una nueva decisión de alcance.

> **DECISIÓN ADOPTADA (DP-06):** Los borradores de la versión 1 permanecen exclusivamente dentro del workspace. No se habilita copia/exportación ni envío a una bandeja de la HCE; este último sería además una `write-action` fuera de alcance.

## UC-08 — Responder preguntas sobre información disponible

**Objetivo:** permitir preguntas factuales o longitudinales sobre la HCE y los documentos autorizados.

**Entrada:** pregunta en lenguaje natural y contexto activo.

**Salida permitida:** respuesta sustentada, con el ámbito consultado, citas a nivel de afirmación y distinción entre respuesta factual e interpretación.

**Límite:** una pregunta que solicite diagnóstico, triaje, prescripción u orden autónomos se rechaza o se reconduce a recuperación de información. Cuando falte evidencia, la respuesta se abstiene y explica qué información falta.

## Actores de soporte y gobierno

Los actores no asistenciales del roadmap tienen casos de uso limitados por función:

- el administrador clínico configura ámbitos y flujos aprobados;
- el administrador IT opera integraciones, identidad y disponibilidad sin obtener acceso clínico implícito;
- el responsable de seguridad/DPO supervisa flujos de datos, políticas e incidentes;
- el auditor reconstruye accesos y decisiones técnicas;
- el futuro knowledge manager aprueba, versiona y retira documentos con un clinical owner.

Estas tareas no habilitan a esos actores para interpretar información clínica ni para eludir la autorización por paciente o propósito de uso.

## Frontera entre información, interpretación, recomendación y acción

| Frontera | Qué puede hacer ChatHCE v1 | Qué debe ver el usuario |
|---|---|---|
| Información | Recuperar y presentar hechos o documentos autorizados. | Fuente original, alcance, fecha, unidades y estado. |
| Interpretación | Resumir o inferir relaciones solo en capabilities validadas. | Etiqueta de IA/inferencia, evidencia, incertidumbre, conflictos y ausencias. |
| Recomendación | No emitir una conducta clínica individual autónoma. Puede recuperar qué dice un protocolo sin aplicarlo como orden al paciente. | Separación inequívoca entre contenido documental y decisión clínica. |
| Acción clínica | No modificar la HCE, prescribir, ordenar, firmar ni enviar sin un flujo futuro, explícito y aprobado. | Ningún affordance que parezca una acción ejecutada cuando solo es texto generado. |
