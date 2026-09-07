# 05 — Identity, autorización clínica y multitenancy

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Tarea | Estado | Evidencia / nota |
|---|---|---|
| P0.1 SSO hospitalario | 🟡 | Identidad delegada a Supabase Auth (JWT verificado remotamente, ADR 0100); OIDC/SAML hospitalario pendiente (Fase 2) |
| P0.2 MFA | ⏳ | Delegar al IdP |
| P0.3 RBAC | 🟡 | Rol `researcher` habilita `purpose=research`; roles clinician/reviewer/admin/auditor/knowledge-manager pendientes |
| P0.4 ABAC contextual | 🟡 | `RequestContext` lleva paciente, episodio y propósito; relación asistencial y servicio pendientes |
| P0.5 Autorización antes del LLM | ✅ | `ScopeGuard`/`ToolPolicy` rechazan antes de consultar; el modelo solo recibe datos del paciente activo |
| P0.6 Context isolation | 🟡 | `RequestContext` obligatorio y RLS por ownership/JWT en producto (ADR 0130); falta integrar la relacion asistencial/paciente en todos los flujos clinicos |
| P0.7 Tests de cross-patient leakage | 🟡 | Offline: `tests/security/test_cross_patient_isolation.py` y repositorios RLS con cliente ligado a JWT; pendiente aplicar/validar RLS live, tabs paralelas, jobs y cross-tenant |
| P1.1 Multi-tenant isolation | ⏳ | `tenant_id="default"` en todo el sistema; sin aislamiento real |
| P1.2 Break-glass | ⏳ | |
| P1.3 Session lifecycle | 🟡 | Revalidación en cada carga, refresh rotatorio, logout; invalidación al cambiar contexto SMART pendiente |

Riesgo abierto: la migracion RLS y la clave clinica readonly requieren aplicacion manual del propietario; la relacion asistencial/paciente aun no esta integrada en todos los flujos.

## Tareas

### P0.1 — SSO hospitalario
Soportar OIDC/OAuth2 y, según despliegue, SAML/Entra ID/AD/LDAP mediante un Identity Provider. No mantener contraseñas clínicas propias como estrategia final.

### P0.2 — MFA
Delegar al IdP hospitalario cuando sea posible.

### P0.3 — RBAC
Roles mínimos: clinician, reviewer, admin, security/auditor, knowledge-manager.

### P0.4 — ABAC contextual
La autorización no termina en `is_authenticated`. Evaluar atributos como hospital, servicio, paciente, encounter, relación asistencial, purpose of use y contexto activo.

### P0.5 — Autorización antes del LLM
El modelo solo recibe información ya autorizada.

### P0.6 — Context isolation obligatorio
Cada operación debe llevar:
- `tenant_id`;
- `user_id`;
- `patient_id`;
- `encounter_id` cuando aplique;
- `session_id`.

### P0.7 — Tests de cross-patient leakage
Cambios rápidos de paciente, tabs paralelas, conversaciones antiguas, caché y background jobs.

### P1.1 — Multi-tenant isolation
Preferencia: DB/schema/vector namespace y encryption key por hospital según riesgo/escala. Nunca confiar exclusivamente en filtros generados por IA.

### P1.2 — Break-glass
Diseñar acceso excepcional con motivo obligatorio, mayor auditabilidad y alertas.

### P1.3 — Session lifecycle
Timeout, revocación, logout y invalidación cuando cambia contexto SMART.

## Definition of Done
No existe una ruta de código que pueda devolver datos clínicos sin comprobar tenant + identidad + autorización + contexto de paciente. Las pruebas automatizadas demuestran ausencia de cross-patient/cross-tenant leakage.
