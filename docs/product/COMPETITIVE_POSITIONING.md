# Posicionamiento competitivo de ChatHCE

**Fecha:** 2 de septiembre de 2026
**Estado:** documento de análisis de producto. **No es una decisión adoptada.**

## Estado y alcance del documento

Este documento analiza el efecto que tiene sobre el posicionamiento de ChatHCE la integración de ChatGPT Health con Epic anunciada el 1 de septiembre de 2026, e identifica los ejes de diferenciación que se sostienen y los que dejan de sostenerse.

Es un documento de producto y estrategia. No modifica [INTENDED_PURPOSE.md](INTENDED_PURPOSE.md), [OUT_OF_SCOPE.md](OUT_OF_SCOPE.md) ni el ADR fundacional [0001](../decisions/0001-chathce-capa-ia-clinica-no-hce.md); cuando un análisis implica cambiarlos, se señala en §8 como implicación pendiente, no como cambio realizado. No constituye asesoramiento jurídico ni determina la clasificación regulatoria de ChatHCE, que sigue correspondiendo a `ROADMAP_HOSPITAL_READY/13-regulatory-quality-clinical-safety.md`.

La §7 recoge opciones abiertas con una recomendación razonada. La elección entre ellas queda pendiente de decisión explícita del product owner.

---

## 1. El hecho de mercado

OpenAI integró ChatGPT Health con la HCE de Epic (más de 325 millones de pacientes), con UCSF Health como socio piloto.

| Elemento | Contenido del anuncio |
|---|---|
| Acceso | Importación de notas de consulta, resultados de laboratorio, medicación y documentación de especialistas |
| Capacidades | Resumen y análisis de la historia, identificación de cambios, cronologías clínicas, preparación de la visita siguiente |
| Integración | En determinados sistemas, ChatGPT embebido dentro del propio flujo de trabajo de la HCE |
| Permisos | **Solo lectura.** La IA no escribe nada de vuelta en el registro |
| Conocimiento externo | Plugin *Healthcare Public Data*: ClinicalTrials.gov, CMS Coverage, RxNorm, DailyMed, PubMed |
| Cumplimiento | Business Associate Agreement (HIPAA), workspaces de ChatGPT Work |
| Validación declarada | 4.363 respuestas evaluadas por médicos en 27 casos de uso clínico; 99,1% clasificadas como seguras |
| Posición de uso | OpenAI mantiene que la herramienta no es apta para diagnóstico ni tratamiento |

Dos elementos del contexto son relevantes para el posicionamiento:

- La validación es **autodeclarada por el proveedor**: sin metodología publicada, sin replicación independiente y sin revisión por pares. La prensa especializada del sector la califica como suelo para una conversación de compra y nada más.
- OpenAI acumula litigios en 2026 por consejos de salud dañinos a consumidores, lo que endurece el escrutinio sobre cualquier despliegue clínico de la misma marca.

## 2. El problema que crea: la tercera capa sobre la historia clínica

El efecto de mercado más importante no es la capacidad añadida, sino la acumulación. Un hospital con Epic pasa a tener **tres capas de IA leyendo la misma historia**: la IA nativa de Epic, el proveedor de documentación ambiental ya contratado y ahora ChatGPT. Oracle Health se mueve en paralelo ampliando su Clinical AI Agent a codificación y revisión de historia.

Los problemas concretos que esto traslada a la dirección de sistemas de información son:

1. **Síntesis duplicada y facturada dos veces.** Quien ya compró documentación ambiental paga por resumen previo a la visita; añadir otro proveedor duplica el gasto mientras los clínicos eligen uno de forma tácita.
2. **Discrepancia entre resúmenes.** La confianza clínica se degrada cuando dos herramientas resumen el mismo episodio y no coinciden, y no existe forma de dirimir cuál acierta.
3. **Gobernanza desbordada.** Conexiones solicitadas a nivel de organización por líneas de servicio sin pasar por el circuito de gobierno de IA existente.
4. **Atribución de responsabilidad difusa** cuando el output que informa una revisión no es reconstruible.
5. **Validación local no presupuestada.** La recomendación explícita al sector es validar contra la propia historia clínica en lugar de fiarse de las cifras del proveedor.

Estos cinco puntos son la superficie de oportunidad de ChatHCE. Ninguno se resuelve resumiendo mejor.

## 3. Impacto sobre el posicionamiento actual

### 3.1 Lo que queda validado

La tesis fundacional del ADR 0001 —ChatHCE es una capa de inteligencia clínica sobre la HCE, no una HCE alternativa, y la HCE conserva el *system of record*— queda confirmada por el movimiento del mayor actor del mercado, que se posiciona exactamente en esa frontera y en solo lectura.

### 3.2 Lo que se erosiona

| Elemento del posicionamiento actual | Situación tras el anuncio |
|---|---|
| «Solo lectura por defecto» como principio diferencial (ADR 0001) | Deja de diferenciar: pasa a ser requisito de mercado |
| Resumir la HCE, detectar cambios, reconstruir evolución y preparar la visita como claims principales (`01-product-scope.md` P0.1/P0.2) | Se convierten en *commodity* ofrecida por tres proveedores con distribución que ChatHCE no tiene |
| Ventaja por integración | Inalcanzable: Epic más piloto en UCSF frente a un prototipo Streamlit en Fase 0/1 |

La conclusión operativa es que el catálogo de tareas del intended purpose sigue siendo correcto como **alcance funcional**, pero ya no sirve como **argumento de compra**. El argumento tiene que desplazarse a cómo se produce el resultado y bajo qué garantías, no a qué tarea se resuelve.

## 4. Ejes de diferenciación sostenibles

### 4.1 Jurisdicción y soberanía del dato

OpenAI resuelve el cumplimiento con un BAA bajo HIPAA. Ese instrumento no cubre el marco aplicable a un hospital del Sistema Nacional de Salud: RGPD, EU AI Act, MDR/IVDR si las funciones constituyen software sanitario, Esquema Nacional de Seguridad, requisitos de contratación pública, residencia de datos, DPIA y el marco EHDS en despliegue.

La diferencia no es de grado, es arquitectónica: el modelo de OpenAI consiste en **importar los datos a su workspace**, mientras que la arquitectura objetivo de ChatHCE mantiene el acceso dentro del perímetro autorizado mediante el Clinical Data Gateway (`04-clinical-data-gateway-fhir.md`) y un Model Gateway que permite elegir dónde se ejecuta la inferencia.

Respaldo en el roadmap: `06-privacy-phi-security.md`, `13-regulatory-quality-clinical-safety.md`, `05-identity-authorization-multitenancy.md`.

### 4.2 Evidencia reconstruible frente a resumen fluido

El producto de OpenAI se comunica como facilidad de resumen. El diseño de ChatHCE se comunica como reconstruibilidad, y ya está especificado en `09-evidence-citations-confidence.md`:

- taxonomía de afirmaciones: `OBSERVED_FACT`, `GUIDELINE_STATEMENT`, `CALCULATION`, `AI_INFERENCE`, `UNKNOWN/INSUFFICIENT_EVIDENCE`;
- vínculo afirmación → `evidence_id` con procedencia, unidades, ámbito y sello temporal;
- calidad de evidencia calculada con señales deterministas —completitud, autoridad, vigencia, concordancia, calidad de recuperación— en lugar de un porcentaje de confianza pedido al modelo;
- detección de conflictos y exposición explícita de evidencia ausente;
- *evidence snapshot* versionado que permite reconstruir una respuesta auditada aunque la HCE o el protocolo cambien después.

Esto ataca directamente el problema 2 de la §2. Ante dos resúmenes discrepantes, ChatHCE puede sostener de qué dato concreto salió cada afirmación; una herramienta de resumen generalista no. Es el diferenciador técnico verificable de mayor valor y el más avanzado en diseño.

### 4.3 Validación local como entregable, no como tarea interna

La recomendación del sector es presupuestar validación contra la historia clínica propia. Eso convierte el trabajo de `11-evaluation-red-team.md` —golden sets, baseline por capability y por servicio, red teaming, métricas de seguridad— en una **característica de producto**: el hospital ejecuta la validación sobre sus propios datos y conserva la evidencia para su comité y su expediente regulatorio.

Un proveedor cuya cifra de seguridad es autodeclarada y no replicable no puede ofrecer esto sin desmentir su propio material comercial.

### 4.4 Grounding en protocolo local aprobado

El plugin de conocimiento externo de OpenAI se apoya en fuentes públicas estadounidenses (CMS Coverage, DailyMed, RxNorm). En España eso produce desalineación de guía respecto a la cobertura del SNS y a las fichas técnicas de la AEMPS —el *hazard* «guideline mismatch» del hazard log de `13-regulatory-quality-clinical-safety.md`.

La posición del ADR 0001 es la opuesta y sigue siendo válida: en la versión 1 solo se utilizan protocolos internos aprobados por el hospital, con gobierno, aprobación, vigencia, versionado y aislamiento por hospital (`08-rag-clinical-knowledge.md`). Responde a la pregunta que un servicio clínico formula realmente, que es qué dice *su* protocolo.

### 4.5 Brecha abierta: localización clínica española

No está cubierta hoy en el roadmap y constituye una barrera de entrada estructural frente a un producto estadounidense: texto clínico en español, CIE-10-ES, SNOMED CT edición española y perfiles HL7 FHIR ES. La fuente actual de investigación, MIMIC-IV, es angloparlante y con codificación estadounidense, por lo que ninguna evidencia obtenida sobre ella demuestra rendimiento en este eje.

### 4.6 Resumen comparativo

| Dimensión | ChatGPT Health + Epic | Posición de ChatHCE | Respaldo documental |
|---|---|---|---|
| Marco de cumplimiento | BAA / HIPAA (EE. UU.) | RGPD, AI Act, MDR, ENS, EHDS | `06`, `13` |
| Ubicación del dato en inferencia | Importado al workspace del proveedor | Acceso mediado dentro del perímetro autorizado | `04`, `05` |
| Trazabilidad del output | Resumen; sin modelo de evidencia publicado | Afirmación → evidencia, con procedencia y snapshot | `09` |
| Confianza | No expuesta de forma auditable | Señales deterministas, categorías sin falsa precisión | `09` |
| Conflictos y datos ausentes | No anunciado | Detección y exposición explícitas | `09` |
| Validación | 99,1% autodeclarado, no replicable | Baseline y golden sets ejecutables por el hospital | `11` |
| Conocimiento clínico | Fuentes públicas de EE. UU. | Protocolos internos aprobados y versionados | `08` |
| Elección de modelo | Proveedor único | Model Gateway, modelo intercambiable | `03` |
| Degradación | No anunciada | Recuperación determinista y acceso a evidencia sin generación | ADR 0001 |
| Distribución e integración | Epic, 325M pacientes, piloto en UCSF | Sin socio de HCE; SMART on FHIR previsto | `04` |
| Localización española | No | Brecha abierta (§4.5) | — |

## 5. Lo que ChatHCE no debe intentar

- **Competir en distribución.** No hay estrategia viable frente a la base instalada de Epic.
- **Usar el resumen previo a la visita como claim principal.** Es *commodity* y se compara desfavorablemente contra tres proveedores ya integrados.
- **Competir en capacidad bruta del modelo o en coste por consulta.**
- **Adelantar la escritura en la HCE** para diferenciarse. Sigue fuera de alcance conforme al ADR 0001 y exigiría un ADR propio; además el competidor ha fijado solo lectura como norma, por lo que escribir sería asumir el riesgo sin obtener contraste favorable.

## 6. Riesgo propio: ChatHCE también es una capa más

El argumento de la §2 aplica a ChatHCE. Un hospital con Epic, documentación ambiental y ChatGPT no tiene un hueco natural para un cuarto lector de la historia, y el diferenciador de la §4.2 solo se percibe si el interlocutor ya ha sufrido el problema de la discrepancia entre resúmenes.

Hay dos salidas y son estrategias distintas, no complementarias en Fase 1:

- **Ser otra capa, pero la auditable y soberana:** compite por el mismo trabajo con argumento regulatorio y de evidencia. Es coherente con el ADR 0001 y con el intended purpose vigente.
- **Ser la capa de gobernanza sobre las demás:** no resume mejor, sino que registra, compara y audita lo que producen las otras capas y detecta cuándo se contradicen. Resuelve el dolor exacto de la dirección de sistemas, pero cambia el producto y **reabriría el ADR 0001 y el intended purpose**, porque el objeto de análisis dejaría de ser únicamente la información clínica.

## 7. Opciones abiertas

Ninguna está adoptada. Requieren decisión explícita del product owner antes de condicionar Fase 1.

| Opción | Vector de entrada | Coste y contrapartida |
|---|---|---|
| **A. Soberanía y expediente regulatorio UE** | Despliegue dentro del perímetro del hospital, RGPD/AI Act/MDR, EHDS | Trabajo documental intensivo y demostración poco vistosa; es razón de compra, no producto |
| **B. Motor de evidencia auditable** | Afirmación → evidencia, conflictos, evidencia ausente, snapshot | Ya está diseñado en `09`; diferenciador técnico verificable y demostrable |
| **C. Arnés de validación local como producto** | El hospital valida sobre su propia historia clínica y conserva la evidencia | Exige golden sets clínicos nuevos: los actuales (`Evaluation/golden_set_*.json`) son de urgencias y quedaron obsoletos con la migración a MIMIC-IV |
| **D. Capa de gobernanza multiproveedor** | Auditar y contrastar la IA de terceros | Máxima alineación con el dolor del CIO, pero reabre el ADR 0001 y el intended purpose |

**Recomendación para la decisión:** **B** como núcleo técnico y **A** como razón de compra, con **C** como el artefacto tangible que se muestra a un jefe de servicio. **D** es atractiva por el momento de mercado, pero cambia la naturaleza del producto y no debería resolverse como efecto colateral de este análisis.

**Qué haría falta para decidir con fundamento:** contrastar los ejes de §4 con al menos un interlocutor hospitalario real (dirección de sistemas y un jefe de servicio), y estimar el coste de los golden sets clínicos de la opción C, que es la dependencia crítica compartida por A, B y C.

## 8. Implicaciones documentales pendientes

Estas correcciones se derivan del análisis y **no se han aplicado**. Requieren decisión previa sobre §7:

1. `ROADMAP_HOSPITAL_READY/01-product-scope.md` P0.2 — los claims propuestos («resume cambios», «localiza evidencia», «permite consultas longitudinales») siguen siendo verificables pero ya no son distintivos. Necesitan reformularse en términos de reconstruibilidad, jurisdicción y validación local.
2. ADR 0001 y [INTENDED_PURPOSE.md](INTENDED_PURPOSE.md) — «solo lectura por defecto» debe mantenerse como **control de seguridad**, pero dejar de utilizarse como diferenciador en comunicación externa.
3. `ROADMAP_HOSPITAL_READY/11-evaluation-red-team.md` — si se adopta la opción C, la evaluación pasa de trabajo interno a entregable de producto y cambia su prioridad relativa dentro de Fase 1.
4. `04-clinical-data-gateway-fhir.md` — conviene registrar el efecto del relanzamiento de Open@Epic previsto para 2026 sobre la estrategia de integración SMART on FHIR.
5. Localización española (§4.5) — no existe hoy tarea asignada en el roadmap; si se considera diferenciador, necesita entrada propia.
6. Si se decidiera explorar la opción D, requiere ADR nuevo y reapertura del intended purpose antes de cualquier trabajo de implementación.

## 9. Fuentes

- TechCrunch, «ChatGPT Health adds Epic integration for clinicians to import patient data», 1 de septiembre de 2026 — https://techcrunch.com/2026/09/01/chatgpt-health-adds-epic-integration-for-clinicians-to-import-patient-data/
- HealthSystemCIO, «ChatGPT's Epic Integration Stacks a Third AI Layer on the Chart, Leaving CIOs to Sort the Overlap», 1 de septiembre de 2026 — https://healthsystemcio.com/2026/09/01/chatgpt-epic-integration-ai-overlap/
- Becker's Hospital Review, «ChatGPT for Healthcare adds Epic integration» — https://www.beckershospitalreview.com/healthcare-information-technology/innovation/chatgpt-for-healthcare-adds-epic-integration/
- PYMNTS, «OpenAI Brings Epic Health Records to ChatGPT for Clinicians» — https://www.pymnts.com/news/artificial-intelligence/2026/openai-brings-epic-health-records-to-chatgpt-for-clinicians/

## Documentos relacionados

- [INTENDED_PURPOSE.md](INTENDED_PURPOSE.md) — intended purpose aprobado de la versión 1
- [OUT_OF_SCOPE.md](OUT_OF_SCOPE.md) — límites explícitos
- [RISK_CAPABILITY_MATRIX.md](RISK_CAPABILITY_MATRIX.md) — clasificación de capabilities y controles
- [ADR 0001](../decisions/0001-chathce-capa-ia-clinica-no-hce.md) — ChatHCE es una capa de IA clínica, no una HCE
- [ESTADO_ACTUAL.md](../ESTADO_ACTUAL.md) — fase y estado de implementación
