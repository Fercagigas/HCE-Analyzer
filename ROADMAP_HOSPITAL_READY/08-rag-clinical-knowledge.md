# 08 — RAG como Clinical Knowledge System

## Objetivo
Pasar de "PDFs + embeddings" a una base de conocimiento clínico gobernada.

## Tareas

### P0.1 — Metadata obligatoria
Cada documento/chunk hereda:
- tenant/hospital;
- specialty/department;
- title;
- version;
- effective date;
- expiry/review date;
- status;
- approved_by/clinical_owner;
- source;
- language;
- document/chunk IDs.

### P0.2 — Solo contenido aprobado
`DRAFT`, `SUPERSEDED`, `EXPIRED` y `REVOKED` no participan por defecto en respuestas clínicas.

### P0.3 — Version resolution
Si existen múltiples versiones, seleccionar explícitamente la vigente y conservar trazabilidad.

### P0.4 — Secure ingestion pipeline
Upload -> file validation -> malware scan -> text extraction -> prompt-injection/content scan -> metadata -> human clinical approval -> index.

### P0.5 — Tenant isolation
Índices/namespaces separados o enforcement determinista del tenant antes del retrieval.

### P0.6 — Retrieval provenance
Cada chunk recuperado conserva documento, versión, página/sección y score.

### P1.1 — Hybrid retrieval
Evaluar lexical + vector + metadata filters + reranking.

### P1.2 — Temporal relevance
Preferir protocolos vigentes; nunca confundir la fecha del documento con la fecha clínica del paciente.

### P1.3 — Knowledge manager UI
Permitir aprobar, retirar, versionar y revisar documentos sin tocar la base directamente.

### P1.4 — RAG evaluation por dominio
Golden sets por especialidad, tipo de pregunta, idioma y hospital.

## Definition of Done
Para cualquier fragmento utilizado puede saberse exactamente qué documento, versión y sección lo originó y por qué estaba autorizado/vigente en el momento de la respuesta.
