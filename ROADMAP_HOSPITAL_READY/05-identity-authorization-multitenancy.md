# 05 — Identity, autorización clínica y multitenancy

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
