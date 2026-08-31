# Casos de uso clínicos permitidos

## Regla de inclusión

Un caso de uso está permitido en la versión 1 solo si es asistivo, opera sobre fuentes autorizadas y disponibles, conserva el contexto de paciente y episodio, y deja la interpretación y decisión final al profesional. Su inclusión en este documento no autoriza su activación: cada capability debe superar los controles y evaluaciones de [RISK_CAPABILITY_MATRIX.md](RISK_CAPABILITY_MATRIX.md).

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

> **DECISION PENDIENTE:** DP-05 — ¿Qué fuentes admite la base de conocimiento de la versión 1: (a) solo protocolos internos aprobados por el hospital, (b) protocolos internos y guías externas curadas por un clinical owner, o (c) además búsqueda externa en tiempo real? (a) ofrece el gobierno más claro; (b) amplía cobertura con trabajo de versionado; (c) introduce riesgos de vigencia, autoridad y trazabilidad y no debería habilitarse sin controles adicionales.

## UC-06 — Detectar cambios

**Objetivo:** identificar hechos nuevos, modificados o retirados desde un punto de revisión o entre dos periodos.

**Entrada:** dos snapshots o ventanas temporales explícitas.

**Salida permitida:** diff determinista de eventos y, si la capability de inferencia está validada, una priorización separada de cambios potencialmente relevantes con explicación y evidencia.

**Límite:** «sin cambios detectados» se limita a los recursos comparados. La relevancia clínica es una inferencia, no un hecho, y no sustituye la revisión del profesional.

## UC-07 — Preparar borradores

**Objetivo:** generar un borrador de handoff, resumen o nota a partir de información seleccionada.

**Entrada:** evidencias y contexto reunidos explícitamente por el profesional.

**Salida permitida:** texto editable marcado de forma persistente como `AI-generated draft`, con fuentes y elementos pendientes de comprobar.

**Límite:** el borrador no se guarda automáticamente en la HCE, no se firma, no se envía y no ejecuta ninguna orden. El profesional debe verificarlo y asumir la autoría mediante un flujo separado antes de cualquier incorporación.

> **DECISION PENDIENTE:** DP-06 — ¿Qué tratamiento de borradores se permite en la versión 1: (a) solo visualización dentro del workspace, (b) copia/exportación manual con aviso y auditoría, o (c) posponer por completo la generación de borradores hasta después del piloto? (a) minimiza el riesgo de propagación pero reduce utilidad; (b) aporta utilidad, aunque puede perder trazabilidad fuera de ChatHCE; (c) reduce el alcance que debe validarse en v1. El envío a una bandeja de la HCE es una `write-action` y queda fuera de v1 en las tres opciones.

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
