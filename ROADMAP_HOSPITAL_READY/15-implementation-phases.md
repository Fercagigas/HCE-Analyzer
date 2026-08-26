# 15 — Fases de implementación

Este orden evita construir features vistosas encima de una arquitectura que después haya que rehacer.

## Fase 0 — Freeze y baseline
- ejecutar suite actual y guardar baseline;
- inventariar arquitectura, datos, secretos y dependencias;
- threat model inicial;
- definir intended purpose y out-of-scope;
- identificar lógica acoplada a Streamlit/SQL/Supabase/Anthropic.

**Salida:** baseline reproducible + ADRs iniciales.

## Fase 1 — Foundation / P0
- separar core de Streamlit;
- FastAPI;
- schemas estructurados;
- Model Gateway;
- Clinical Data Gateway;
- adapter MIMIC;
- tool contracts;
- context isolation;
- audit/correlation IDs.

**No añadir todavía features clínicas nuevas.**

## Fase 2 — Security foundation
- SSO-ready architecture;
- RBAC + ABAC;
- PHI minimisation;
- secure logging;
- prompt/indirect injection controls;
- eliminación de SQL/código arbitrario;
- tenant/patient leakage tests;
- kill switch.

**Gate:** ninguna violación crítica en suite adversarial.

## Fase 3 — Evidence-first AI
- Evidence objects;
- claim-to-evidence mapping;
- facts vs inferences;
- source viewer contract;
- RAG metadata/versioning/approval;
- evidence quality + missing/conflict handling.

**Gate:** respuestas clínicas relevantes verificables.

## Fase 4 — Nuevo frontend
- React/TypeScript/Vite;
- Clinical Design System;
- patient context;
- Ask;
- evidence UI;
- responsive embedded/standalone shell;
- accessibility;
- SSE streaming.

**Gate:** usability test con usuarios clínicos representativos.

## Fase 5 — Interoperabilidad
- FHIR R4 adapter;
- SMART App Launch;
- sandbox EHR;
- capability discovery;
- read-only scopes;
- vendor adapter layer.

**Gate:** mismo workflow MIMIC/FHIR sin cambiar agentes.

## Fase 6 — Diferenciadores AI-first
Implementar incrementalmente y evaluar por separado:
1. Since Your Last Review;
2. AI Timeline;
3. longitudinal Q&A;
4. Compare;
5. What Matters Now;
6. Ask This Data;
7. Clinical Workspace;
8. Investigate/Deep Research;
9. Evidence Graph.

Priorizar `Since Last Review` y longitudinal Q&A: valor alto con menor riesgo que recomendaciones clínicas autónomas.

## Fase 7 — Hospital pilot readiness
- observability dashboards;
- incident response;
- backups/DR;
- deployment hardening;
- SBOM/security gates;
- DPIA/risk documentation;
- clinical validation plan;
- admin/knowledge manager tools;
- pilot runbook y support process.

## Fase 8 — Piloto controlado
- pocos servicios/usuarios;
- read-only;
- shadow/assistive use;
- feedback estructurado;
- medir tiempo ahorrado, evidence verification, error/abstention rates y safety signals;
- weekly safety review.

## Fase 9 — Expansión
Solo tras evidencia del piloto:
- más servicios;
- más hospitales;
- nuevas fuentes;
- nuevos modelos;
- borradores integrados;
- estudiar CDS de mayor riesgo bajo estrategia regulatoria adecuada.

---

# Backlog de primeras 12 tareas concretas

1. Crear ADR: ChatHCE = AI layer, no EHR.
2. Extraer agent/RAG core de Streamlit.
3. Crear FastAPI y `/health` + `/api/v1/chat`.
4. Crear interfaces `LLMProvider` y `ClinicalDataProvider`.
5. Encapsular MIMIC como `MimicClinicalDataProvider`.
6. Sustituir SQL genérico por clinical tools allowlisted.
7. Introducir `RequestContext(tenant,user,patient,encounter,session)` obligatorio.
8. Crear `Evidence` y `Claim` schemas.
9. Ampliar security suite con indirect injection + cross-patient tests.
10. Crear frontend React shell con Patient Context + Ask + Evidence.
11. Implementar SSE entre FastAPI y React.
12. Conectar un sandbox FHIR/SMART y demostrar lectura de Observation/Condition/MedicationRequest.

Cuando estas 12 tareas estén terminadas, ChatHCE habrá cambiado de arquitectura de prototipo a una base coherente para producto clínico.
