# Matriz de riesgo por capability

## Finalidad y límites

Esta matriz permite clasificar una capability antes de diseñarla, habilitarla o modificarla. Los niveles son una taxonomía interna y conservadora de riesgo de producto; no son una clasificación de producto sanitario, una evaluación jurídica ni el risk file clínico exigido en Fase 7.

El riesgo indicado es **inherente**, antes de controles. La activación requiere verificar todos los controles, evaluar el riesgo residual y obtener la aprobación correspondiente. Una etiqueta de riesgo no convierte una capability fuera de alcance en permitida.

## Taxonomía de capability

Cada capability recibe una categoría primaria según su efecto más relevante:

| Categoría | Definición | Ejemplo |
|---|---|---|
| `retrieval` | Recupera información sin transformarla clínicamente. | Abrir una medición o un fragmento de protocolo. |
| `summarization` | Selecciona, organiza, compara o condensa información existente. | Resumen de episodio o diff literal. |
| `inference` | Deriva una relación, hipótesis o relevancia no registrada explícitamente. | Priorizar cambios potencialmente relevantes. |
| `recommendation` | Propone una conducta clínica para un caso individual. | Sugerir una pauta o prioridad asistencial. |
| `write-action` | Cambia un sistema o desencadena una acción con efecto operativo o clínico. | Firmar una nota o emitir una orden. |

Si una feature combina categorías, se separa en capabilities evaluables. Si no puede separarse, hereda la categoría y el nivel más altos.

## Escala interna de riesgo

| Nivel | Criterio operativo |
|---|---|
| Bajo | Un error es visible y reversible, con impacto clínico improbable; no elimina controles de privacidad o autorización. |
| Medio | Un error puede desinformar o retrasar la revisión, pero la fuente es accesible y no se propone una decisión clínica. |
| Alto | Una omisión, error temporal o inferencia puede influir de forma material en el juicio o la documentación clínica. Requiere validación clínica específica. |
| Crítico | Puede producir una decisión o cambio clínico directo. No está admitido en la versión 1. |

> **DECISION PENDIENTE:** DP-07 — ¿Se ratifican esta escala y las asignaciones provisionales, y quién acepta el riesgo residual por capability? Opciones: (a) product owner con clinical safety owner para Medio/Alto, (b) comité multidisciplinar para Alto y cualquier excepción, o (c) otro esquema institucional. Sin propietario y umbrales aprobados, la matriz sirve para diseño pero no como gate de release.

## Controles exigidos

| ID | Control mínimo verificable |
|---|---|
| C01 | Identidad institucional y autorización RBAC/ABAC antes del LLM; contexto obligatorio de tenant, usuario, paciente, episodio y sesión. |
| C02 | Acceso de solo lectura, mínimo necesario y mediante operaciones allowlisted; sin SQL libre en producción. |
| C03 | Procedencia completa: fuente, timestamp, unidades, versión y ámbito de paciente/episodio; acceso al original en un clic. |
| C04 | Validación de schema, tipos, tamaño, unidades, timestamps, ámbito y freshness de los resultados de herramientas. |
| C05 | Separación visible de `OBSERVED_FACT`, `GUIDELINE_STATEMENT`, `CALCULATION`, `AI_INFERENCE` y `UNKNOWN/INSUFFICIENT_EVIDENCE`. |
| C06 | Mapeo claim-to-evidence, abstención ante soporte insuficiente y presentación de datos ausentes o contradictorios. |
| C07 | Contenido documental aprobado, vigente, versionado, aislado por tenant y tratado como datos no confiables frente a prompt injection. |
| C08 | Registro auditable de usuario, propósito, contexto, fuentes, versiones, modelo, herramientas, policy decisions y aprobación humana, sin PHI innecesaria en logs. |
| C09 | Evaluación por capability: soporte factual, citas, omisiones, temporalidad, unidades, abstención, leakage y errores clínicos; gates de regresión. |
| C10 | Interfaz que mantiene contexto visible, identifica salida de IA y facilita revisión sin automation bias ni alert fatigue. |
| C11 | Revisión humana obligatoria antes de usar una inferencia o borrador en una decisión o documento clínico. |
| C12 | Modo degradado y kill switch: desactivar generación/inferencia conservando retrieval determinista seguro cuando sea posible. |
| C13 | Para cambios: snapshots comparables, punto de revisión explícito, diff determinista y separación de la priorización inferida. |
| C14 | Para borradores: etiqueta persistente, texto editable, fuentes, campos pendientes y ausencia de guardado, firma o envío automático. |
| C15 | Para una futura acción: API separada y tipada, permiso específico, previsualización, confirmación explícita, idempotencia, fail-closed y auditoría inmutable. |

C01, C03, C04, C08, C09, C10 y C12 son transversales a toda capability clínica. Los controles adicionales de cada fila no los sustituyen.

## Matriz

| Capability evaluable | Categoría primaria | Riesgo inherente | Estado v1 | Controles adicionales exigidos |
|---|---|---:|---|---|
| Localizar un hecho de la HCE autorizada | `retrieval` | Medio | Permitida con gate | C02, C03, C04; respuesta literal y ámbito consultado explícito. |
| Localizar un protocolo o guía | `retrieval` | Medio | Permitida con gate | C03, C07; mostrar versión, vigencia, clinical owner y no aplicarlo automáticamente al paciente. |
| Visualizar mediciones registradas | `summarization` | Medio | Permitida con gate | C02-C04; funciones parametrizadas, unidades y periodo visibles, sin código arbitrario generado por IA. |
| Resumir la HCE disponible | `summarization` | Alto | Permitida tras validación específica | C05, C06, C09-C11; periodo y fuentes cubiertas, conflictos y omisiones visibles. |
| Reconstruir evolución o timeline | `summarization` | Alto | Permitida tras validación específica | C03-C06, C09-C11; orden temporal validado, huecos visibles y relaciones inferidas separadas. |
| Comparar episodios, periodos o conjuntos | `summarization` | Alto | Permitida tras validación específica | C03-C06, C09-C11; comparabilidad y alcance explícitos, sin inferir causalidad. |
| Detectar cambios literales desde una revisión | `summarization` | Medio | Permitida con gate | C03, C04, C06, C09, C13; declarar recursos y ventanas incluidos. |
| Priorizar cambios potencialmente relevantes | `inference` | Alto | Permitida solo tras evaluación clínica | C05, C06, C09-C13; pocos resultados, explicación, evidencia y posibilidad de descartar. |
| Responder una pregunta factual sobre fuentes disponibles | `summarization` | Medio | Permitida con gate | C02-C06, C09, C10; abstención y ámbito consultado explícitos. |
| Responder una pregunta interpretativa o longitudinal | `inference` | Alto | Permitida solo tras evaluación clínica | C03-C06, C09-C12; soporte por afirmación y prohibición de convertirla en recomendación. |
| Preparar un borrador de handoff, resumen o nota | `summarization` | Alto | Permitida sin escritura automática | C03, C05, C06, C09-C11, C14; verificación completa antes de reutilizarlo. |
| Proponer diagnóstico individual como conclusión | `inference` | Crítico | Prohibida | No implementar en v1; requeriría nuevo intended purpose, evaluación regulatoria y validación clínica. |
| Recomendar tratamiento, dosis o triaje individual | `recommendation` | Crítico | Prohibida | No implementar en v1; recuperar información de protocolos no equivale a recomendar una conducta. |
| Crear, modificar, firmar o enviar contenido a la HCE | `write-action` | Crítico | Prohibida | C15 no basta por sí solo: requiere decisión de alcance, aprobación humana y todos los gates de [OUT_OF_SCOPE.md](OUT_OF_SCOPE.md). |
| Ejecutar una orden clínica | `write-action` | Crítico | Prohibida | No implementar en v1; nunca delegar la confirmación al modelo ni inferirla de la conversación. |

## Reglas de aplicación

1. Product y clinical safety asignan categoría, riesgo inherente y hazards antes del desarrollo.
2. Ingeniería convierte los controles aplicables en requisitos y pruebas observables.
3. Evaluación clínica define datasets, usuarios, métricas y umbrales proporcionales a la capability.
4. Seguridad y privacidad verifican aislamiento, mínimo necesario, ataques y auditoría.
5. El responsable designado acepta o rechaza el riesgo residual antes de habilitarla.
6. Un cambio de modelo, prompt, fuente, herramienta, ámbito clínico o UX relevante reabre la evaluación.
7. Una capability sin clasificación, controles verificables o propietario permanece deshabilitada.
