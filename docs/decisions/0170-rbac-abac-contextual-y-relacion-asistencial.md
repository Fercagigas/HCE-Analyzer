# ADR 0170 — RBAC, ABAC contextual y relación asistencial

Estado: Aceptada

Fecha: 2026-09-11

## Contexto

Fase 1 disponía de `RequestContext` con paciente, episodio, tenant y propósito, pero la única regla de rol era `researcher` para `purpose=research`. El paciente activo podía ser seleccionado sin comprobar una relación asistencial vigente. La tabla `public.user_patient_access` de 0005 no contenía tenant, servicio ni vigencia.

Se requiere autorización determinista antes de cualquier tool, acceso clínico o llamada al modelo. El futuro SSO/OIDC debe poder sustituir el adapter de identidad sin cambiar la lógica de autorización.

## Opciones consideradas (incluidas las descartadas y por qué)

1. **Mantener `researcher` y checks ad hoc.** Descartada: deja permisos implícitos y divergencia entre API y tools.
2. **Aceptar roles, tenant o servicio en el cuerpo.** Descartada: permitiría elevar privilegios. Roles y tenant provienen solo de claims verificados `app_metadata`; el servicio se verifica contra la relación asistencial.
3. **Resolver roles en cada adapter Supabase.** Descartada: acopla las políticas al proveedor e impide un cambio limpio a OIDC/SAML.
4. **Confiar solo en RLS.** Descartada: la autorización debe ocurrir antes de recuperar PHI o enviarlo al LLM; RLS es defensa adicional.
5. **Break-glass automático sin relación.** Descartada por ahora: exige motivo, doble control, alerta y operación auditada. Este paquete aplica fail-closed y no incorpora bypass.

## Decisión

- Se definen `clinician`, `reviewer`, `admin`, `auditor`, `knowledge_manager` y `researcher` en `chathce.domain.authorization`, con matriz explícita rol × tool, rol × endpoint y propósito. Lo no listado se deniega.
- `ToolPolicy` comprueba la matriz antes de invocar una tool y los routers lo hacen antes de cada endpoint protegido.
- `SupabaseIdentityProvider` toma `tenant_id` y `roles` exclusivamente de `app_metadata` tras `auth.get_user(token)`. Rechaza claims ausentes/inválidos e ignora `user_metadata` y `public.users` para autorización. `IdentityProvider` sigue siendo el punto único de identidad.
- `ScopeGuard` exige coincidencia de paciente/episodio, tenant, servicio y concesión asistencial vigente. Sin fuente o relación activa, rechaza y audita sin PHI.
- La migración 0006 añade `tenant_id`, `service_id`, `valid_from` y `valid_until` a `user_patient_access`, y cambia su clave a `(user_id, tenant_id, subject_id, service_id)`.
- `PUT /api/v1/admin/users/{user_id}/roles` y `PUT /api/v1/admin/patient-access` requieren `admin`, usan `IdentityProvider` y emiten `AuditEvent(authorization_changed)` sin registrar usuario objetivo, paciente, token ni contenido clínico.
- No se modifica el gobierno documental RAG. La matriz permite búsqueda documental a `knowledge_manager`; futuros endpoints de gestión deben reutilizar este hook RBAC.

## Consecuencias

- Positivas: no se aceptan roles en JSON, tenant/servicio/relación expirada fallan cerrados y la política no depende de Supabase.
- Negativas: todo principal clínico necesita una concesión vigente; 0006 debe aplicarse antes de desplegar contra Supabase.
- Operación: los administradores asignan `tenant_id` y roles en `app_metadata`; `public.users.role` no es fuente autorizativa.
- Seguimiento: break-glass requiere ADR y controles operacionales propios.
