# ChatHCE — Roadmap Hospital Ready

> Objetivo: transformar ChatHCE de prototipo avanzado de IA clínica en una **capa de inteligencia clínica segura, verificable, interoperable y fácil de integrar sobre la HCE existente**, sin intentar sustituir a Oracle Health, Epic u otros EHR.

> **Estado a 2 de septiembre de 2026:** Fases 0 y 1 completadas y fusionadas en `main`. Cada documento lleva un bloque «Estado a 2 de septiembre de 2026» con el detalle tarea a tarea; el orden de ejecución y lo que queda está en [15-implementation-phases.md](15-implementation-phases.md). Estado global del producto: `docs/ESTADO_ACTUAL.md`.

## Visión de producto

ChatHCE no será una nueva HCE. El EHR seguirá siendo el *system of record*. ChatHCE será el **Clinical AI Workspace / Clinical Intelligence Layer** que permite comprender, interrogar, comparar e investigar una historia clínica fragmentada mediante IA, siempre con evidencia trazable.

Principios:

1. **AI-first, not EHR-first.**
2. **Evidence before eloquence.** Cada afirmación relevante debe poder rastrearse hasta su fuente.
3. **Read-only by default.** Ninguna acción clínica irreversible debe ejecutarse autónomamente.
4. **Least privilege / minimum necessary data.**
5. **Human in the loop.** La IA propone; el profesional valida.
6. **EHR agnostic.** SMART on FHIR + FHIR R4 como interfaz preferente.
7. **Model agnostic.** El producto no debe depender estructuralmente de un único proveedor LLM.
8. **Safe degradation.** Si falla la IA, deben seguir disponibles recuperación determinista y evidencia.
9. **Auditability by design.**
10. **Clinical UX, not chatbot UX.**

## Arquitectura objetivo

```text
Hospital EHR / LIS / RIS / PACS / Pharmacy
                 |
          SMART on FHIR / FHIR R4
                 |
        Clinical Data Gateway
                 |
       Clinical AI Gateway
   +-------------+--------------+
   |             |              |
Policy       Agent/RAG      Evidence Engine
Engine       Orchestrator   + Citations
   |             |              |
   +-------------+--------------+
                 |
          FastAPI Backend
                 |
        React + TypeScript
     Embedded / Side panel /
          Standalone mode
```

Lo que ya existe tras Fase 1 (paquete `chathce/`): Clinical Data Gateway (`ClinicalDataProvider` + `ScopeGuard`, adapter MIMIC), Clinical AI Gateway (`ModelGateway` + `ToolRegistry` + `ToolPolicy`), schemas `Evidence`/`Claim`, FastAPI con JSON y SSE. Faltan: Evidence Engine completo, Policy Engine con RBAC/ABAC, FHIR/SMART y el frontend React.

## Índice de trabajo

| Documento | Área | Prioridad | Estado (sep 2026) |
|---|---|---|---|
| [01-product-scope.md](01-product-scope.md) | Posicionamiento, intended use y límites | P0 | ✅ Fase 0 |
| [02-frontend-clinical-ai-workspace.md](02-frontend-clinical-ai-workspace.md) | Sustitución de Streamlit y UX AI-first | P0 | ⏳ Fase 4 (Streamlit ya es solo adapter) |
| [03-backend-api-refactor.md](03-backend-api-refactor.md) | Separación frontend/backend y API | P0 | ✅ P0 hecho salvo endpoints de features; P1 parcial |
| [04-clinical-data-gateway-fhir.md](04-clinical-data-gateway-fhir.md) | FHIR, SMART y eliminación de SQL libre | P0 | ✅ P0 (SQL libre eliminado, adapter MIMIC); ⏳ FHIR/SMART |
| [05-identity-authorization-multitenancy.md](05-identity-authorization-multitenancy.md) | SSO, RBAC/ABAC, aislamiento | P0 | 🟡 contexto y scope hechos; SSO/RBAC/RLS pendientes |
| [06-privacy-phi-security.md](06-privacy-phi-security.md) | PHI, minimización, cifrado y DLP | P0 | 🟡 logging seguro hecho; minimización y detección PHI pendientes |
| [07-agent-safety-tooling.md](07-agent-safety-tooling.md) | Seguridad agentic, tools y sandbox | P0 | ✅ P0 completo; ⏳ kill switch |
| [08-rag-clinical-knowledge.md](08-rag-clinical-knowledge.md) | RAG clínico gobernado y anti-poisoning | P0/P1 | 🟡 provenance hecho; gobierno documental pendiente |
| [09-evidence-citations-confidence.md](09-evidence-citations-confidence.md) | Evidencia, provenance y confianza | P0/P1 | 🟡 schemas hechos; Evidence Engine Fase 3 |
| [10-ai-features.md](10-ai-features.md) | Diferenciadores AI-first | P1 | ⏳ Fase 6 |
| [11-evaluation-red-team.md](11-evaluation-red-team.md) | Evaluación clínica, seguridad y red team | P0 | 🟡 suite de seguridad y golden set v2; CI y red team pendientes |
| [12-observability-audit-resilience.md](12-observability-audit-resilience.md) | Auditoría, observabilidad y continuidad | P0/P1 | 🟡 audit trail y timeouts hechos; dashboards, kill switch pendientes |
| [13-regulatory-quality-clinical-safety.md](13-regulatory-quality-clinical-safety.md) | GDPR, AI Act, MDR y QMS | P0 | ⏳ (intended purpose y matriz de riesgo hechos) |
| [14-deployment-devsecops.md](14-deployment-devsecops.md) | Infraestructura y DevSecOps hospitalario | P1 | ⏳ |
| [15-implementation-phases.md](15-implementation-phases.md) | Orden recomendado de ejecución | — | Fases 0–1 ✅ · Fase 2 siguiente |

## Definition of Done global

ChatHCE podrá considerarse candidato a piloto hospitalario cuando, como mínimo:

| Criterio | Estado |
|---|---|
| no exista acceso SQL libre generado por LLM a datos clínicos de producción | ✅ en código; ⏳ eliminar RPC en Supabase (`db/migrations/0002`) |
| exista aislamiento estricto hospital/usuario/paciente/episodio/sesión | 🟡 paciente/episodio/sesión en aplicación; tenant y RLS pendientes |
| SSO y autorización clínica se apliquen antes de exponer datos al modelo | 🟡 JWT de Supabase y scope antes de tools; SSO hospitalario y RBAC pendientes |
| toda acción y acceso clínico relevante sea auditable | ✅ `AuditEvent` con correlación, sin PHI |
| PHI se minimice antes de llegar al modelo | ⏳ |
| las respuestas clínicas relevantes dispongan de provenance/citas verificables | 🟡 `evidence_ids` por dato y `Claim` por tool; citación por afirmación pendiente |
| el RAG solo utilice documentación aprobada, versionada y vigente | ⏳ |
| las herramientas agentic tengan contratos y permisos explícitos | ✅ `ToolContract` |
| no se ejecute código arbitrario generado por el modelo en el backend | ✅ ADR 0040 |
| exista una batería amplia de evaluaciones clínicas y adversariales | 🟡 18 payloads live, 52 tests offline, golden set v2; ampliar y llevar a CI |
| exista un modo degradado y kill switch de IA | 🟡 fallback y errores controlados; kill switch pendiente |
| el frontend pueda funcionar como SMART app embebida y como aplicación standalone | ⏳ |
| el intended purpose y la estrategia regulatoria estén documentados antes de añadir decisiones clínicas de alto riesgo | 🟡 intended purpose sí; estrategia regulatoria pendiente |
