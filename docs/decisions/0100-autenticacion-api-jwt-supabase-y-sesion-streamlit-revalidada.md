# ADR 0100 — Autenticación de la API por JWT de Supabase y revalidación de sesión en Streamlit

Estado: Aceptada

Fecha: 2026-09-02

## Contexto

Streamlit restauraba la sesión a partir de una cookie que contenía el usuario completo, sin
revalidar contra Supabase (riesgo Crítico del threat model). Con FastAPI como nuevo canal era
necesario decidir el mecanismo de autenticación y el uso de claves de Supabase, que hoy es una
única `SUPABASE_KEY` con rol `service_role` (ignora RLS) compartida por auth, datos clínicos y
RAG (ADR 0070).

## Opciones consideradas (incluidas las descartadas y por que)

1. **Sesiones propias firmadas con `SECRET_KEY`.** Descartada: duplica el proveedor de
   identidad, exige almacén de sesiones y rotación propia; `SECRET_KEY` no tenía consumidor.
2. **Validar el JWT localmente con el secreto/JWKS de Supabase.** Descartada para Fase 1:
   con las claves legacy el secreto de firma es compartido y su exposición al runtime amplía
   el impacto de una fuga; con claves asimétricas es viable y queda como mejora.
3. **Bearer JWT de Supabase Auth verificado remotamente con `auth.get_user(jwt)`** (elegida),
   con caché corta por hash del token para no llamar a Supabase en cada petición.
4. **Cookie HttpOnly emitida por FastAPI y Streamlit como cliente.** Descartada por ahora:
   Streamlit no puede leer cookies HttpOnly desde el servidor sin un proxy; se retoma cuando
   la UI viva tras la API (Fase 4).

## Decision

- FastAPI: `HTTPBearer` obligatorio; `IdentityProvider.verify_access_token` devuelve un
  `Principal` (`user_id`, `tenant_id`, `roles`, `expires_at`); 401 `AUTH_REQUIRED`/`AUTH_INVALID_TOKEN`.
  El rol `researcher` habilita `purpose=research`; en otro caso 403 `PURPOSE_NOT_ALLOWED`.
- Streamlit (`chathce/streamlit_adapter/auth_session.py`): la cookie `hce_session` solo guarda
  el refresh token; el access token y el `Principal` viven en `st.session_state`;
  `ensure_authenticated()` verifica o refresca contra Supabase en cada carga y limpia la sesión
  si el token es inválido o el usuario fue revocado (evento de auditoría `session_restored`).
- Claves por función: `SUPABASE_KEY` para auth y `public.*`; `SUPABASE_CLINICAL_KEY` (rol de
  solo lectura sobre `mimiciv_hosp`/`mimiciv_icu`) para `MimicClinicalDataProvider`;
  `SUPABASE_SERVICE_ROLE_KEY` únicamente en scripts de carga. Documentado en `db/README.md`
  y en la checklist de Supabase.
- `SECRET_KEY` se elimina de la configuración.

## Motivo

Supabase Auth ya es el proveedor de identidad del producto; reutilizar sus JWT evita un
segundo sistema de sesiones y permite la misma verificación en API y Streamlit. Guardar solo el
refresh token reduce lo que una cookie robada revela, y la revalidación en cada carga cierra el
riesgo de sesiones restauradas sin comprobar.

## Consecuencias

- Positivas: la API es utilizable desde cualquier cliente con un token de Supabase; el estado
  de sesión en Streamlit ya no es fuente de verdad; tests
  (`tests/unit/api/test_health_and_auth.py`, `tests/unit/ui/test_streamlit_auth_session.py`).
- Negativas: una llamada a Supabase por token no cacheado; la cookie de Streamlit sigue siendo
  legible desde JavaScript (limitación del componente de cookies), mitigada con refresh token
  rotatorio y caducidad de 1 h.

## Pendientes

- RLS por usuario reenviando el JWT del usuario al provider en lugar de la clave de servicio
  (flag preparado en el composition root, sin activar).
- Verificación local con claves asimétricas de Supabase cuando el proyecto migre a claves
  modernas (`publishable`/`secret`).
- Crear la clave `SUPABASE_CLINICAL_KEY` en el proyecto (acción del propietario).
