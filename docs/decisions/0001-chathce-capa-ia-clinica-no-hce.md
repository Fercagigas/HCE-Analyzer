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

- se integrará preferentemente mediante SMART on FHIR y FHIR R4, con adaptadores que no contaminen el dominio central;
- accederá a datos a través de un Clinical Data Gateway que aplique identidad, autorización, contexto, minimización, allowlists, auditoría y procedencia antes del LLM;
- será de solo lectura por defecto;
- mostrará únicamente superficies donde la IA aporte valor, sin recrear módulos generales de Labs, Orders, Pharmacy u otros salvo como evidencia necesaria;
- mantendrá workspaces, comparaciones y borradores como artefactos auxiliares, no como registro clínico oficial;
- no ejecutará prescripciones, triaje, diagnóstico autónomo, modificaciones de HCE u órdenes clínicas sin una futura decisión explícita y aprobación profesional;
- conservará recuperación determinista y acceso a evidencia cuando la generación de IA deba degradarse o desactivarse.

## Motivo

Esta opción concentra el producto en reducir la carga de revisión y hacer navegable la información clínica sin competir con las capacidades transaccionales de una HCE. También preserva una fuente oficial, facilita una integración agnóstica de proveedor, limita privilegios y hace posible evaluar cada capability de IA de manera separada.

La decisión aplica los principios del roadmap: evidence before eloquence, read-only by default, least privilege, human in the loop, interoperabilidad, degradación segura, auditabilidad y UX clínica en lugar de UX de chatbot genérico.

## Consecuencias

- La arquitectura debe separar presentación, orquestación de IA y acceso clínico; el LLM no conoce credenciales ni consulta libremente producción.
- MIMIC-IV-ED se conserva como adapter y entorno de investigación, no como modelo de dominio ni evidencia de preparación hospitalaria.
- La nueva UX se diseña alrededor de contexto de paciente, preguntas, cambios, timeline, evidencia e investigación, no alrededor de mantener un expediente paralelo.
- La escritura futura queda fuera de alcance hasta contar con un flujo separado, permiso específico, previsualización, aprobación humana, auditoría y validación.
- La base documental necesita gobierno, aprobación, vigencia, versionado y aislamiento por hospital.
- Cada afirmación clínica relevante debe poder reconstruirse desde datos o documentos fuente y diferenciar hechos de inferencias.
- ChatHCE depende de la disponibilidad y calidad de los sistemas fuente; debe mostrar información ausente, conflictos y fallos sin aparentar completitud.
- La integración con múltiples HCE y la operación de gateways añaden trabajo inicial, pero evitan acoplar el producto a un proveedor o duplicar el registro oficial.
- Cualquier propuesta futura de convertir ChatHCE en repositorio principal o habilitar acciones clínicas reabre este ADR y el intended purpose.

## Pendientes

Las decisiones abiertas que concretan esta arquitectura se mantienen en los documentos de producto:

- DP-01: contexto autorizado de la versión 1;
- DP-02: perfiles clínicos habilitados;
- DP-03: servicios incluidos en el primer intended purpose;
- DP-04: claims externos y umbrales de evidencia;
- DP-05: fuentes admitidas en la base de conocimiento;
- DP-06: tratamiento permitido de los borradores dentro del alcance de v1;
- DP-07: gobierno y aceptación del riesgo residual.

Ninguno de estos pendientes cambia la decisión fundacional de que la HCE conserva el registro oficial y ChatHCE actúa como capa asistiva.
