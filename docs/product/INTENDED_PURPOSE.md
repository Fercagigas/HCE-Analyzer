# Intended purpose de ChatHCE

## Estado y alcance del documento

Este documento define el intended purpose aprobado para la primera versión de producto del roadmap hospitalario. Es una especificación de producto y seguridad: no afirma que el prototipo actual esté validado o autorizado para uso asistencial.

ChatHCE se define como un **copiloto de información clínica** que ayuda a profesionales autorizados a encontrar, organizar, resumir y comprender información ya disponible. No realiza diagnóstico autónomo y no sustituye el juicio profesional, la HCE ni los sistemas clínicos que conservan el registro oficial.

Este documento no constituye asesoramiento jurídico y no determina la clasificación regulatoria de ChatHCE. La evaluación regulatoria depende del intended purpose finalmente aprobado, los claims, la jurisdicción y el uso real, y corresponde a la Fase 7 y a `ROADMAP_HOSPITAL_READY/13-regulatory-quality-clinical-safety.md`.

## Intended purpose propuesto

En la versión 1, ChatHCE está destinado a que **médicos autorizados** utilicen datos anonimizados o debidamente preparados para investigación y educación, en cualquier servicio hospitalario, para evaluar tareas de revisión de información: recuperar hechos de la HCE y conocimiento clínico aprobado, resumir la información disponible, reconstruir su evolución temporal, comparar episodios o periodos, identificar cambios, preparar borradores y responder preguntas sobre esas fuentes.

Los resultados de la versión 1 son informativos y se limitan a investigación y educación: no se utilizan para tomar decisiones asistenciales reales ni se incorporan a documentación clínica. Deben mostrar su evidencia, distinguir hechos de inferencias y expresar información ausente o contradictoria. El objetivo futuro es evaluar un uso asistivo real, siempre bajo responsabilidad profesional, pero ese cambio requerirá validación, gestión de riesgos, decisión regulatoria y una nueva aprobación explícita del intended purpose.

> **DECISIÓN ADOPTADA (DP-01):** La versión 1 se limita a investigación y educación y no incluye modo `shadow`. El uso que pueda influir en decisiones asistenciales reales pertenece a una versión futura y exige reabrir formalmente el intended purpose antes de habilitarlo.

## Naturaleza del producto y frontera del sistema

- La HCE hospitalaria continúa siendo el *system of record*.
- ChatHCE es una capa de inteligencia clínica sobre fuentes autorizadas; no es una HCE alternativa.
- El acceso es de solo lectura por defecto y se limita siempre al hospital, usuario y sesión; paciente y episodio son obligatorios únicamente cuando la tarea está vinculada a ellos.
- ChatHCE no asume que la información recuperada sea completa, correcta o vigente. Hace visibles los datos ausentes, los conflictos y la procedencia.
- Los borradores viven en un espacio temporal de trabajo y no forman parte de la HCE hasta que exista una acción humana separada y autorizada.
- Una indisponibilidad del modelo no debe ocultar la evidencia ni impedir la recuperación determinista cuando esta pueda operar de forma segura.

El prototipo del repositorio implementa una interfaz Streamlit con un agente conversacional, consultas sobre el dataset de demostración MIMIC-IV-ED, búsqueda en documentos indexados y visualizaciones. Esto prueba capacidades técnicas parciales, no el cumplimiento de los controles hospitalarios exigidos en [RISK_CAPABILITY_MATRIX.md](RISK_CAPABILITY_MATRIX.md).

## Usuarios y actores

| Actor del roadmap | Relación con ChatHCE v1 | Tareas previstas |
|---|---|---|
| Médico | Usuario previsto en v1 | Evaluar la revisión de historias, consultas de evidencia, comparaciones y resultados o borradores dentro del ámbito de investigación/educación. |
| Enfermería | Actor clínico futuro y participante potencial en validación | No es usuario previsto en v1; requerirá intended purpose, workflows, permisos y evaluación propios antes de habilitarse. |
| Farmacéutico | Actor clínico futuro y participante potencial en validación | No es usuario previsto en v1; requerirá intended purpose, workflows, permisos y evaluación propios antes de habilitarse. |
| Administrador clínico | Usuario de gobierno | Configurar flujos y ámbitos organizativos sin sustituir la aprobación clínica de contenidos. |
| Administrador IT | Usuario técnico | Configurar integración, identidad, disponibilidad y operación; no obtiene acceso clínico por el mero rol técnico. |
| Responsable de seguridad/DPO | Usuario de supervisión | Revisar controles, flujos de datos, incidentes y evidencias de cumplimiento según sus atribuciones. |
| Auditor | Usuario de supervisión | Reconstruir accesos, herramientas, fuentes, versiones y aprobaciones de una interacción. |

Todo acceso está sujeto a identidad, autorización y propósito de uso. La inclusión de un actor en esta tabla no le concede acceso a datos ni a todas las capacidades.

> **DECISIÓN ADOPTADA (DP-02):** Los únicos usuarios clínicos previstos en la versión 1 son médicos. Enfermería y farmacia se mantienen como actores del roadmap, pero no entran en el intended purpose hasta contar con diseño y validación específicos.

> **DECISIÓN ADOPTADA (DP-03):** El intended purpose abarca todos los servicios hospitalarios. MIMIC-IV-ED es un adapter transitorio del prototipo y se prevé migrar o ampliar la fuente a MIMIC general. La activación de una capability en un servicio concreto sigue condicionada a disponer de datos, protocolos, clinical owners, golden sets y validación representativos de ese servicio.

## Contexto de uso

La arquitectura objetivo admite la misma experiencia como aplicación SMART embebida en una HCE, panel lateral contextual o espacio de trabajo independiente. En cualquiera de los tres modos:

- el paciente y el episodio activos permanecen visibles en tareas vinculadas a un paciente; las tareas institucionales sin paciente muestran explícitamente «sin paciente seleccionado»;
- un cambio de contexto es inequívoco e invalida el contexto que ya no corresponda;
- solo se exponen datos previamente autorizados y minimizados;
- el profesional puede abrir la fuente de cada afirmación clínica relevante;
- los resultados de IA están identificados como tales y nunca se presentan como autoridad clínica.

La versión 1 se evalúa en investigación/educación, con médicos, sin influir en la atención real. Aunque el intended purpose cubre todos los servicios hospitalarios, cada combinación de servicio, fuente y capability debe demostrar cobertura y funcionamiento antes de evaluarse. Cualquier transición posterior a atención real será de solo lectura en su primera etapa y dependerá de evidencia de seguridad y utilidad por capability.

## Tareas comprendidas

La versión 1 comprende, bajo los controles y gates aplicables:

1. resumir información de la HCE disponible;
2. localizar evidencia clínica y documental autorizada;
3. reconstruir la evolución temporal;
4. comparar episodios, periodos o conjuntos de datos;
5. buscar protocolos aprobados y vigentes;
6. detectar y presentar cambios;
7. preparar borradores claramente identificados como generados por IA;
8. responder preguntas sobre la información disponible.

La descripción operacional y los criterios de aceptación están en [CLINICAL_USE_CASES.md](CLINICAL_USE_CASES.md). Los límites están en [OUT_OF_SCOPE.md](OUT_OF_SCOPE.md).

## Claims de producto verificables

Los siguientes son los claims técnicos autorizados para la versión 1. Describen resultados observables, no exactitud absoluta, ahorro demostrado ni beneficio clínico.

| Claim permitido | Cómo se verifica | Condición para comunicarlo |
|---|---|---|
| ChatHCE localiza evidencia relevante en fuentes autorizadas. | *Retrieval recall*, precisión/relevancia, vigencia de la fuente y tasa de acceso correcto al fragmento original. | Superar el gate definido para el corpus, servicio e idioma evaluados. |
| ChatHCE resume la información clínica disponible y enlaza las afirmaciones relevantes con sus fuentes. | Soporte factual, completitud de citas, tasa de afirmaciones no sustentadas, omisiones críticas y revisión clínica. | Limitar el claim a las fuentes y tipos de resumen validados. |
| ChatHCE presenta cambios entre periodos o revisiones. | Concordancia del diff con un conjunto de referencia, errores temporales, omisiones y falsos cambios. | Diferenciar cambios observados de la priorización inferida. |
| ChatHCE permite realizar consultas longitudinales sobre la información disponible. | Exactitud temporal, soporte de cada respuesta, abstención ante datos insuficientes y ausencia de mezcla de pacientes/episodios. | Limitarlo a recursos y ventanas temporales cubiertos por la validación. |
| ChatHCE permite comparar episodios o periodos conservando la trazabilidad. | Exactitud de valores, unidades, fechas, alcance y enlaces a la evidencia de cada lado de la comparación. | Mostrar datos ausentes y no inferir equivalencia entre episodios incompatibles. |
La reducción del esfuerzo de revisión se conserva como **hipótesis de evaluación**, no como claim autorizado. Para promoverla a claim será necesario un estudio con médicos representativos que mida tiempo y acciones de revisión, verificación de evidencia, errores y carga percibida frente al flujo de referencia.

Claims no permitidos incluyen «ChatHCE diagnostica», «recomienda el mejor tratamiento», «reduce el esfuerzo», «evita errores», «garantiza que no hay alucinaciones» o cualquier afirmación de seguridad, eficacia, ahorro o beneficio clínico no demostrada para el contexto evaluado.

> **DECISIÓN ADOPTADA (DP-04):** La comunicación de la versión 1 se limita a capacidades técnicas verificables. No se autorizan claims de reducción de esfuerzo ni de beneficio clínico hasta disponer de la validación específica correspondiente; tampoco se publican claims cuantitativos sin umbrales predefinidos y resultados reproducibles.

## Principios de UX

1. **Paciente y contexto siempre visibles.** Hospital, paciente y episodio no pueden quedar implícitos en una interacción clínica.
2. **Hechos e inferencias diferenciados.** También se distinguen afirmaciones de guías, cálculos deterministas e información desconocida o insuficiente.
3. **Evidencia accesible en un clic.** Una afirmación relevante permite abrir el valor, nota, documento, página o sección que la sustenta.
4. **Incertidumbre explícita.** Se muestran calidad de evidencia, datos ausentes, conflictos, fallos de herramientas y abstenciones sin porcentajes de confianza inventados por el modelo.
5. **La IA no es autoridad clínica.** El lenguaje y la jerarquía visual preservan la revisión humana y evitan presentar una inferencia como orden o decisión.
6. **Minimizar alert fatigue.** Se priorizan pocos elementos relevantes, se evita repetir avisos sin nueva información y se valida el impacto de alertas con usuarios.

Estos principios son requisitos verificables de diseño y pruebas de factores humanos, no meras recomendaciones visuales.
