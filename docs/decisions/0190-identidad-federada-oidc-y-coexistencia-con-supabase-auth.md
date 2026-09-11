# ADR 0190 - Identidad federada OIDC y coexistencia con Supabase Auth

Estado: Aceptada

Fecha: 2026-09-11

## Contexto

La Fase 1 autentica API y Streamlit con Supabase Auth (ADR 0100). Un hospital necesita delegar la identidad, MFA, ciclo de vida de cuentas y políticas de acceso en su IdP, y puede usar Keycloak, Microsoft Entra ID u otra plataforma OIDC. ChatHCE no debe almacenar contraseñas clínicas como arquitectura final.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Integrar SAML directamente en ChatHCE.** Descartada: duplica protocolos y superficies criptográficas en la aplicación; SAML debe federarse a OIDC desde el IdP o un broker corporativo.
2. **Mantener solo Supabase Auth.** Descartada: no resuelve por sí misma la gobernanza, MFA y ciclo de vida ya operados por el hospital.
3. **Proxy de identidad/BFF como único mecanismo.** Descartada como requisito exclusivo: es recomendable para cookies HttpOnly y despliegues web, pero impediría integraciones API legítimas y no elimina la necesidad de validar los JWT recibidos.
4. **OIDC genérico en el puerto de identidad, coexistiendo con Supabase** (elegida). Permite migración progresiva y varios issuers confiables sin cambiar la capa de aplicación.

## Decision

- Se añade `OidcIdentityProvider`, seleccionable con `IDENTITY_PROVIDER=oidc`; `supabase` permanece como valor por defecto y `memory` se usa en tests/desarrollo.
- OIDC usa discovery, JWKS cacheado, firmas asimétricas, issuer/audience/exp obligatorios y `nonce` para `id_token`; Authorization Code usa PKCE S256, `state` y nonce de un solo uso.
- Los claims configurables `sub`, tenant, roles, servicio y nombre se convierten en `Principal` y los atributos relevantes se propagan a `RequestContext`.
- La API expone login/callback mínimos. Streamlit acepta una `AuthSession` OIDC validada; no hay login, registro ni recuperación de contraseña propios en el modo OIDC.
- Los secretos solo provienen de variables de entorno/secret manager. El adapter no contiene claves privadas ni secretos de IdP.

## Consecuencias

Positivas: SSO hospitalario, MFA delegado, migración sin romper Supabase y posibilidad de confiar explícitamente en varios issuers. Los tests unitarios verifican JWT sintéticos contra JWKS local y el compose incluye Keycloak aislado.

Negativas: el estado PKCE inicial es local a la instancia durante la redirección; para alta disponibilidad se requiere un store compartido o afinidad de sesión. El callback debe estar protegido por BFF/proxy en una UI web para emitir cookies HttpOnly. OIDC autentica, pero no sustituye las reglas RBAC/ABAC, RLS ni relación asistencial.
