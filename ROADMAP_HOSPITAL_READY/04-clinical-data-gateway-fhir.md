# 04 — Clinical Data Gateway, SMART on FHIR y FHIR R4

## Objetivo
El LLM nunca debe disponer de acceso libre a la base clínica de producción.

## Tareas

### P0.1 — Eliminar Text-to-SQL libre de producción
Mantener SQL libre únicamente en entorno de investigación MIMIC si se desea. Producción debe exponer operaciones clínicas limitadas.

Ejemplos:
- `get_patient_vitals()`;
- `get_latest_labs()`;
- `get_medications()`;
- `get_conditions()`;
- `get_encounter_summary()`;
- `get_clinical_documents()`.

### P0.2 — Crear Clinical Data Gateway
Responsabilidades:
- autenticación;
- autorización;
- patient/encounter scope;
- allowlist de recursos/campos;
- minimización;
- normalización;
- audit;
- rate limiting;
- provenance.

### P0.3 — Modelo canónico clínico
No acoplar agentes a tablas MIMIC. Crear DTOs internos (`ClinicalObservation`, `Medication`, `Condition`, `Encounter`, etc.).

### P0.4 — Adaptador MIMIC
Convertir el backend actual en un adapter de desarrollo que implemente el mismo contrato que FHIR.

### P1.1 — Adaptador FHIR R4
Recursos prioritarios:
- Patient;
- Encounter;
- Observation;
- Condition;
- MedicationRequest/MedicationStatement;
- AllergyIntolerance;
- DiagnosticReport;
- Procedure;
- DocumentReference.

### P1.2 — SMART App Launch
Implementar OAuth/OIDC SMART y recepción segura de `patient`, `encounter`, `fhirUser`, issuer y scopes.

### P1.3 — Capability discovery
Leer `CapabilityStatement` y adaptar features a recursos realmente disponibles.

### P1.4 — Vendor adapters
Preparar peculiaridades Oracle/Epic/otros sin contaminar el dominio central.

### P1.5 — Read-only first
Scopes FHIR de lectura. Cualquier escritura futura debe tener flujo separado, autorización explícita y clinician approval.

## Definition of Done
El mismo caso de uso funciona contra MIMIC y contra un sandbox FHIR cambiando únicamente el adapter; el LLM no conoce credenciales ni construye consultas arbitrarias contra producción.
