# 15 — Fases de implementación

Este orden evita construir features vistosas encima de una arquitectura que después haya que rehacer.

> **Estado a 11 de septiembre de 2026:** Fases 0 y 1 completadas (`main`); la oleada 1 de Fase 2 está integrada (ADRs 0130, 0140, 0150 y 0160) y su cierre operativo requiere verificaciones live del propietario. RBAC/ABAC, gobierno RAG y SSO OIDC están en curso en la oleada 2. Detalle en `docs/ESTADO_ACTUAL.md` y `docs/baseline/FASE2_BASELINE.md`.

## Fase 0 — Freeze y baseline ✅ (completada, sep 2026)
- ejecutar suite actual y guardar baseline;
- inventariar arquitectura, datos, secretos y dependencias;
- threat model inicial;
- definir intended purpose y out-of-scope;
- identificar lógica acoplada a Streamlit/SQL/Supabase/Anthropic.

**Salida:** `docs/baseline/FASE0_BASELINE.md`, `docs/architecture/`, `docs/security/THREAT_MODEL.md`, `docs/product/`, ADRs 0001/0010/0020/0030.

## Fase 1 — Foundation / P0 ✅ (completada, 2 de septiembre de 2026)
- separar core de Streamlit → `chathce/` con test de fronteras (ADR 0110);
- FastAPI → `/health`, `/ready`, `/api/v1/chat` (JSON y SSE), `/api/v1/patients/{id}/summary`, `/api/v1/visualizations/{id}` con JWT de Supabase (ADR 0100);
- schemas estructurados → `ChatRequest`/`ChatResponse` con facts, inferences, evidence, uncertainty (ADR 0090);
- Model Gateway → `LLMProvider` + `ModelGateway` sobre SDK `anthropic`, sin LangChain en el bucle (ADR 0080);
- Clinical Data Gateway → `ClinicalDataProvider` + `ScopeGuard`, operaciones allowlisted, agregados por RPC fijas (ADR 0050);
- adapter MIMIC → `MimicClinicalDataProvider` con fixtures y cliente en memoria para tests;
- tool contracts → `ToolContract`/`ToolResult`, 12 tools read-only;
- context isolation → `RequestContext` obligatorio, scope estricto de paciente, historial sin datos de tools, sin caché de respuestas;
- audit/correlation IDs → `trace_id`/`request_id` y `AuditEvent` sin PHI.

**Salida:** ADRs 0050/0080/0090/0100/0110/0120, `docs/baseline/FASE1_BASELINE.md` (271 tests en verde sin credenciales, 56 % cobertura, evaluación live 18/18 seguridad, 57/58 casos funcionales).

**Pendientes del propietario para cerrar del todo:** aplicar `db/migrations/0001` y `0002` en Supabase, crear `SUPABASE_CLINICAL_KEY`, validar 20 preguntas del golden set, definir usuario de pruebas para tests live de identidad/API.

## Fase 2 — Security foundation 🔄 (oleada 1 integrada; oleada 2 en curso)
- SSO-ready architecture — 🔄 identidad delegada a Supabase Auth; SSO OIDC hospitalario en curso, no integrado;
- RBAC + ABAC — 🔄 rol `researcher` y propósito existentes; RBAC/ABAC completo y relación asistencial en curso, no integrados;
- PHI minimisation — ✅ catálogo por DTO, pseudonimización por sesión y detector configurable antes del modelo (ADR 0160); DLP externo y política de egreso pendientes;
- secure logging — ✅ auditoría sin PHI (adelantado en Fase 1);
- prompt/indirect injection controls — ✅ suite adversarial offline ampliada y gate CI; live indirecto pendiente de entorno autorizado (ADR 0150);
- eliminación de SQL/código arbitrario — ✅ en código y migraciones versionadas; verificar aplicación de `0005` y estado real por entorno;
- tenant/patient leakage tests — ✅ contratos offline para cross-tenant y pestañas paralelas; ⏳ RLS/multi-tenant live y background jobs;
- kill switch — ✅ kill switch de runtime y circuit breaker por `provider+model` (ADR 0140);
- RLS por usuario/paciente y clave clínica readonly — ✅ versionadas (ADR 0130); ⏳ aplicación de `0005`, emisión de clave y validación live del propietario.

**Gate:** ninguna violación crítica en suite adversarial. **Oleada 1:** ✅ 0 violaciones críticas (78/78 controles offline); no sustituye las verificaciones live pendientes.

## Fase 3 — Evidence-first AI
- Evidence objects — ✅ schema disponible (`Evidence`, `Claim`, `ClaimType`);
- claim-to-evidence mapping — 🟡 una Claim por tool; mapeo por afirmación pendiente;
- facts vs inferences — 🟡 separados en `ChatResponse`; verificación automática pendiente;
- source viewer contract — ⏳;
- RAG metadata/versioning/approval — ⏳;
- evidence quality + missing/conflict handling — ⏳.

**Gate:** respuestas clínicas relevantes verificables.

## Fase 4 — Nuevo frontend
- React/TypeScript/Vite;
- Clinical Design System;
- patient context;
- Ask;
- evidence UI;
- responsive embedded/standalone shell;
- accessibility;
- SSE streaming — ✅ ya emitido por la API.

**Gate:** usability test con usuarios clínicos representativos.

## Fase 5 — Interoperabilidad
- FHIR R4 adapter — el port `ClinicalDataProvider` y los DTOs ya existen;
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

| # | Tarea | Estado |
|---|---|---|
| 1 | Crear ADR: ChatHCE = AI layer, no EHR | ✅ ADR 0001 |
| 2 | Extraer agent/RAG core de Streamlit | ✅ `chathce/` (RAG sigue legacy envuelto por `KnowledgeRepository`) |
| 3 | Crear FastAPI y `/health` + `/api/v1/chat` | ✅ más `/ready`, SSE, resumen de paciente |
| 4 | Crear interfaces `LLMProvider` y `ClinicalDataProvider` | ✅ `chathce/ports/` |
| 5 | Encapsular MIMIC como `MimicClinicalDataProvider` | ✅ |
| 6 | Sustituir SQL genérico por clinical tools allowlisted | ✅ (RPC de SQL libre eliminada en Supabase el 2026-09-02: `execute_readonly_query` y `exec_sql`) |
| 7 | Introducir `RequestContext(tenant,user,patient,encounter,session)` obligatorio | ✅ |
| 8 | Crear `Evidence` y `Claim` schemas | ✅ |
| 9 | Ampliar security suite con indirect injection + cross-patient tests | ✅ cross-patient live y offline; indirect injection offline (live pendiente) |
| 10 | Crear frontend React shell con Patient Context + Ask + Evidence | ⏳ Fase 4 |
| 11 | Implementar SSE entre FastAPI y React | 🟡 lado servidor hecho; cliente React pendiente |
| 12 | Conectar un sandbox FHIR/SMART y demostrar lectura de Observation/Condition/MedicationRequest | ⏳ Fase 5 |

Con las tareas 1 a 9 terminadas, ChatHCE ha cambiado de arquitectura de prototipo a una base coherente para producto clínico. Las tareas 10 a 12 abren las Fases 4 y 5.
