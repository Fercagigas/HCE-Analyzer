# ADR 0001 — ChatHCE es una capa de IA clínica, no una HCE

Estado: Aceptado como decisión fundacional del roadmap.

Fecha: 2026-08-31

## Contexto

El prototipo actual ofrece una interfaz conversacional Streamlit que combina consultas sobre MIMIC-IV-ED, búsqueda RAG en documentos indexados y visualizaciones. Esta arquitectura demuestra recuperación y síntesis, pero no debe evolucionar mediante la reproducción de módulos de una HCE ni convertirse en un segundo repositorio oficial de información clínica.

Los hospitales ya disponen de una HCE que gestiona identidad clínica, episodios, datos, órdenes, documentación y obligaciones de conservación. Duplicar esas responsabilidades aumentaría la fragmentación, los problemas de sincronización, el acceso a datos y el alcance de validación. El valor diferencial de ChatHCE está en comprender, interrogar, comparar e investigar información fragmentada con evidencia trazable.

Se necesita una frontera estable para orientar producto, UX, integración, seguridad y evaluación antes de añadir nuevas features clínicas.

## Opciones consideradas

1. **Construir ChatHCE como una HCE completa que sustituya al sistema existente.** Descartada porque duplica funciones maduras, convierte ChatHCE en *system of record*, amplía de forma desproporcionada el alcance de interoperabilidad, seguridad, operación y migración, y desvía el producto de su valor AI-first.
2. **Construir una aplicación clínica independiente con su propia copia longitudinal como fuente principal.** Descartada porque crea dos versiones de la verdad, introduce latencia y conflictos de sincronización y obliga al profesional a trabajar en otro silo.
3. **Construir ChatHCE como capa de inteligencia clínica integrada sobre la HCE existente.** Elegida. La HCE conserva el registro oficial; ChatHCE accede a información autorizada mediante gateways, aporta recuperación, síntesis e investigación y devuelve evidencia verificable.
4. **Mantener indefinidamente el prototipo de investigación sin una frontera de producto.** Descartada porque no permite razonar de forma consistente sobre intended purpose, claims, permisos, riesgo, integración ni gates para un piloto hospitalario.

## Decision

ChatHCE será una **Clinical AI Intelligence Layer / Clinical AI Workspace**, no una HCE.

La HCE hospitalaria seguirá siendo el *system of record*. ChatHCE:

- tendrá una versión 1 de investigación/educación para médicos, sin modo `shadow` ni influencia en decisiones asistenciales reales;
- abarcará como intended purpose todos los servicios hospitalarios, aunque cada servicio y capability deberá disponer de fuentes y validación representativas antes de evaluarse o habilitarse;
- se integrará preferentemente mediante SMART on FHIR y FHIR R4, con adaptadores que no contaminen el dominio central;
- accederá a datos a través de un Clinical Data Gateway que aplique identidad, autorización, contexto, minimización, allowlists, auditoría y procedencia antes del LLM;
- será de solo lectura por defecto;
- mostrará únicamente superficies donde la IA aporte valor, sin recrear módulos generales de Labs, Orders, Pharmacy u otros salvo como evidencia necesaria;
- mantendrá workspaces, comparaciones y borradores como artefactos auxiliares, no como registro clínico oficial;
- no ejecutará prescripciones, triaje, diagnóstico autónomo, modificaciones de HCE u órdenes clínicas sin una futura decisión explícita y aprobación profesional;
- conservará recuperación determinista y acceso a evidencia cuando la generación de IA deba degradarse o desactivarse.

## Motivo

Esta opción concentra el producto en evaluar si puede reducir la carga de revisión y hacer navegable la información clínica sin competir con las capacidades transaccionales de una HCE. También preserva una fuente oficial, facilita una integración agnóstica de proveedor, limita privilegios y hace posible evaluar cada capability de IA de manera separada.

La decisión aplica los principios del roadmap: evidence before eloquence, read-only by default, least privilege, human in the loop, interoperabilidad, degradación segura, auditabilidad y UX clínica en lugar de UX de chatbot genérico.

## Consecuencias

- La arquitectura debe separar presentación, orquestación de IA y acceso clínico; el LLM no conoce credenciales ni consulta libremente producción.
- MIMIC-IV-ED se conserva como adapter y entorno de investigación, no como modelo de dominio ni evidencia de preparación hospitalaria.
- El adapter deberá evolucionar desde MIMIC-IV-ED hacia fuentes MIMIC más amplias y, posteriormente, fuentes hospitalarias que cubran todos los servicios incluidos en el intended purpose.
- La nueva UX se diseña alrededor de contexto de paciente, preguntas, cambios, timeline, evidencia e investigación, no alrededor de mantener un expediente paralelo.
- La escritura futura queda fuera de alcance hasta contar con un flujo separado, permiso específico, previsualización, aprobación humana, auditoría y validación.
- Los borradores permanecen dentro del workspace en v1, sin funciones de copia/exportación ni envío a la HCE.
- La base documental necesita gobierno, aprobación, vigencia, versionado y aislamiento por hospital.
- La versión 1 solo utiliza protocolos internos aprobados por el hospital; la incorporación de guías o búsquedas externas exige una decisión posterior.
- Cada afirmación clínica relevante debe poder reconstruirse desde datos o documentos fuente y diferenciar hechos de inferencias.
- ChatHCE depende de la disponibilidad y calidad de los sistemas fuente; debe mostrar información ausente, conflictos y fallos sin aparentar completitud.
- La comunicación externa de v1 se limita a claims técnicos verificables; la reducción de esfuerzo y cualquier beneficio clínico siguen siendo hipótesis hasta validarse.
- El riesgo residual Medio requiere aceptación conjunta del product owner y el clinical safety owner; el riesgo Alto y las excepciones corresponden a un comité multidisciplinar; el riesgo Crítico permanece prohibido en v1.
- La integración con múltiples HCE y la operación de gateways añaden trabajo inicial, pero evitan acoplar el producto a un proveedor o duplicar el registro oficial.
- Cualquier propuesta futura de utilizar ChatHCE en decisiones asistenciales reales, convertirlo en repositorio principal o habilitar acciones clínicas reabre este ADR y el intended purpose.

## Pendientes

No quedan decisiones de producto abiertas para cerrar este ADR. Permanecen como trabajo de implementación y futuros gates:

- ampliar el adapter MIMIC-IV-ED hacia MIMIC general y demostrar cobertura por servicio;
- definir antes de la comunicación externa los umbrales de evaluación de cada claim técnico;
- designar nominalmente product owner, clinical safety owner y comité multidisciplinar;
- reabrir el intended purpose, este ADR y la evaluación regulatoria antes de cualquier transición desde investigación/educación hacia decisiones asistenciales reales;
- documentar mediante un nuevo ADR cualquier futura escritura o transferencia de borradores a la HCE.
