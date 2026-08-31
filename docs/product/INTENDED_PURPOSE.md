# Intended purpose de ChatHCE

## Estado y alcance del documento

Este documento define el intended purpose de la primera versión de producto propuesta en el roadmap hospitalario. Es una especificación de producto y seguridad: no afirma que el prototipo actual esté validado o autorizado para uso asistencial.

ChatHCE se define como un **copiloto de información clínica** que ayuda a profesionales autorizados a encontrar, organizar, resumir y comprender información ya disponible. No realiza diagnóstico autónomo y no sustituye el juicio profesional, la HCE ni los sistemas clínicos que conservan el registro oficial.

Este documento no constituye asesoramiento jurídico y no determina la clasificación regulatoria de ChatHCE. La evaluación regulatoria depende del intended purpose finalmente aprobado, los claims, la jurisdicción y el uso real, y corresponde a la Fase 7 y a `ROADMAP_HOSPITAL_READY/13-regulatory-quality-clinical-safety.md`.

## Intended purpose propuesto

ChatHCE está destinado a asistir a profesionales sanitarios autorizados, dentro de un contexto clínico institucional y, cuando la tarea esté vinculada a un paciente, sobre el paciente y episodio activos, en tareas de revisión de información: recuperar hechos de la HCE y conocimiento clínico aprobado, resumir la información disponible, reconstruir su evolución temporal, comparar episodios o periodos, identificar cambios, preparar borradores y responder preguntas sobre esas fuentes.

Los resultados son informativos y asistivos. Deben mostrar su evidencia, distinguir hechos de inferencias, expresar información ausente o contradictoria y ser revisados por el profesional antes de influir en una decisión o incorporarse a documentación clínica. La responsabilidad clínica permanece en el profesional y en los procesos del centro.

> **DECISION PENDIENTE:** DP-01 — ¿Cuál será el contexto autorizado de la versión 1: (a) investigación/educación con datos anonimizados, (b) piloto hospitalario `shadow` sin influencia asistencial, o (c) uso asistivo en atención real tras validación? Elegir (b) conserva la ruta incremental del roadmap; elegir (c) exige adelantar validación clínica, gestión de riesgos, privacidad y decisión regulatoria; elegir (a) impide formular claims de uso clínico real.

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
| Médico | Usuario clínico | Revisar la historia, consultar evidencia, comparar episodios y validar resultados o borradores. |
| Enfermería | Usuario clínico | Revisar evolución y cambios pertinentes a su flujo de trabajo, consultar evidencia y validar resultados o borradores. |
| Farmacéutico | Usuario clínico | Revisar información de medicación disponible, cambios y protocolos autorizados, y validar resultados o borradores. |
| Administrador clínico | Usuario de gobierno | Configurar flujos y ámbitos organizativos sin sustituir la aprobación clínica de contenidos. |
| Administrador IT | Usuario técnico | Configurar integración, identidad, disponibilidad y operación; no obtiene acceso clínico por el mero rol técnico. |
| Responsable de seguridad/DPO | Usuario de supervisión | Revisar controles, flujos de datos, incidentes y evidencias de cumplimiento según sus atribuciones. |
| Auditor | Usuario de supervisión | Reconstruir accesos, herramientas, fuentes, versiones y aprobaciones de una interacción. |

Todo acceso está sujeto a identidad, autorización y propósito de uso. La inclusión de un actor en esta tabla no le concede acceso a datos ni a todas las capacidades.

> **DECISION PENDIENTE:** DP-02 — ¿Qué perfiles serán usuarios clínicos de la versión 1: (a) solo médicos, (b) médicos y enfermería, o (c) médicos, enfermería y farmacia con permisos diferenciados? Ampliar perfiles incrementa el valor transversal, pero obliga a diseñar y validar tareas, lenguaje, RBAC/ABAC y riesgos específicos para cada profesión.

> **DECISION PENDIENTE:** DP-03 — ¿Qué servicios delimitan el primer intended purpose: (a) Urgencias, alineado con los datos MIMIC-IV-ED actuales, (b) Urgencias y UCI, alineado también con el corpus documental actual, o (c) varios servicios hospitalarios? Un ámbito más amplio exige fuentes, golden sets, clinical owners y validación representativos de cada servicio antes de habilitarlo.

## Contexto de uso

La arquitectura objetivo admite la misma experiencia como aplicación SMART embebida en una HCE, panel lateral contextual o espacio de trabajo independiente. En cualquiera de los tres modos:

- el paciente y el episodio activos permanecen visibles en tareas vinculadas a un paciente; las tareas institucionales sin paciente muestran explícitamente «sin paciente seleccionado»;
- un cambio de contexto es inequívoco e invalida el contexto que ya no corresponda;
- solo se exponen datos previamente autorizados y minimizados;
- el profesional puede abrir la fuente de cada afirmación clínica relevante;
- los resultados de IA están identificados como tales y nunca se presentan como autoridad clínica.

El despliegue inicial hospitalario previsto por el roadmap es controlado, de solo lectura y con pocos servicios y usuarios. La ampliación depende de evidencia de seguridad y utilidad obtenida por capability.

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

Los siguientes son claims de capacidad propuestos. Describen resultados observables, no exactitud absoluta ni beneficio clínico demostrado.

| Claim permitido | Cómo se verifica | Condición para comunicarlo |
|---|---|---|
| ChatHCE localiza evidencia relevante en fuentes autorizadas. | *Retrieval recall*, precisión/relevancia, vigencia de la fuente y tasa de acceso correcto al fragmento original. | Superar el gate definido para el corpus, servicio e idioma evaluados. |
| ChatHCE resume la información clínica disponible y enlaza las afirmaciones relevantes con sus fuentes. | Soporte factual, completitud de citas, tasa de afirmaciones no sustentadas, omisiones críticas y revisión clínica. | Limitar el claim a las fuentes y tipos de resumen validados. |
| ChatHCE presenta cambios entre periodos o revisiones. | Concordancia del diff con un conjunto de referencia, errores temporales, omisiones y falsos cambios. | Diferenciar cambios observados de la priorización inferida. |
| ChatHCE permite realizar consultas longitudinales sobre la información disponible. | Exactitud temporal, soporte de cada respuesta, abstención ante datos insuficientes y ausencia de mezcla de pacientes/episodios. | Limitarlo a recursos y ventanas temporales cubiertos por la validación. |
| ChatHCE permite comparar episodios o periodos conservando la trazabilidad. | Exactitud de valores, unidades, fechas, alcance y enlaces a la evidencia de cada lado de la comparación. | Mostrar datos ausentes y no inferir equivalencia entre episodios incompatibles. |
| ChatHCE puede reducir el esfuerzo de revisión de información clínica. | Estudio con usuarios representativos: tiempo y acciones de revisión, tasa de verificación de evidencia, errores y carga percibida frente al flujo de referencia. | Tratarlo como hipótesis hasta demostrar una mejora sin degradar métricas de seguridad. |

Claims no permitidos incluyen «ChatHCE diagnostica», «recomienda el mejor tratamiento», «evita errores», «garantiza que no hay alucinaciones» o cualquier afirmación de seguridad, eficacia o ahorro no sustentada para el contexto evaluado.

> **DECISION PENDIENTE:** DP-04 — ¿Qué claims se autorizarán para comunicación externa y con qué umbrales de evidencia? Opciones: (a) comunicar solo capacidades técnicas verificadas, (b) añadir reducción de esfuerzo tras un estudio de usabilidad, o (c) añadir beneficios clínicos tras validación clínica específica. Cada escalón aumenta la carga de evidencia y puede modificar la evaluación regulatoria; los umbrales deben acordarse antes de publicar claims cuantitativos.

## Principios de UX

1. **Paciente y contexto siempre visibles.** Hospital, paciente y episodio no pueden quedar implícitos en una interacción clínica.
2. **Hechos e inferencias diferenciados.** También se distinguen afirmaciones de guías, cálculos deterministas e información desconocida o insuficiente.
3. **Evidencia accesible en un clic.** Una afirmación relevante permite abrir el valor, nota, documento, página o sección que la sustenta.
4. **Incertidumbre explícita.** Se muestran calidad de evidencia, datos ausentes, conflictos, fallos de herramientas y abstenciones sin porcentajes de confianza inventados por el modelo.
5. **La IA no es autoridad clínica.** El lenguaje y la jerarquía visual preservan la revisión humana y evitan presentar una inferencia como orden o decisión.
6. **Minimizar alert fatigue.** Se priorizan pocos elementos relevantes, se evita repetir avisos sin nueva información y se valida el impacto de alertas con usuarios.

Estos principios son requisitos verificables de diseño y pruebas de factores humanos, no meras recomendaciones visuales.
