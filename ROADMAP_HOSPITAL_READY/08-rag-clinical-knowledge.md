# 08 — RAG como Clinical Knowledge System

## Estado a 11 de septiembre de 2026 (Fase 2 - oleada 2)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Tarea | Estado | Evidencia / nota |
|---|---|---|
| P0.1 Metadata obligatoria | ✅ | 0007: tenant, clave documental, versión, vigencia, estado, aprobador, fecha y hash en documento/chunk |
| P0.2 Solo contenido aprobado | ✅ | RPC, RLS y repositorio filtran `approved` y vigente; legado migra a `draft` |
| P0.3 Version resolution | ✅ | Selección determinista de la versión vigente más reciente por `document_key` |
| P0.4 Secure ingestion pipeline | ✅ | Borrador, validación, SHA-256/deduplicación, scan básico de inyección y aprobación humana; API legacy bloqueada |
| P0.5 Tenant isolation | ✅ | `tenant_id` en RLS, RPC y filtro defensivo del repositorio |
| P0.6 Retrieval provenance | ✅ | `Source`/`Evidence` incluyen documento, página, score, versión, estado y vigencia |
| P1.1 Hybrid retrieval | ✅ | Legacy vigente (`hybrid_search` + reranker) envuelto por `KnowledgeRepository` |
| P1.2 – P1.4 | ⏳ | |

Pendiente detectado en la evaluación de Fase 1: el agente no siempre invoca `search_clinical_documents` en preguntas de guías, y tres preguntas del golden set RAG carecen de `contexts` (`docs/baseline/FASE1_BASELINE.md` §3). El RAG sigue siendo código legacy fuera de `chathce/` (ADR 0110).

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
