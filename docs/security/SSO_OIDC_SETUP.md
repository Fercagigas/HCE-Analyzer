# SSO OIDC para ChatHCE

ChatHCE admite OIDC genérico mediante Authorization Code con PKCE (`S256`). No mantiene contraseñas clínicas cuando `IDENTITY_PROVIDER=oidc`: el IdP hospitalario gestiona login, MFA, baja, revocación y políticas de contraseña.

## Claims requeridos

El `id_token` y el `access_token` deben estar firmados por el issuer configurado, incluir `iss`, `aud`, `exp` y un identificador estable de usuario. El callback comprueba además el `nonce` del `id_token`. ChatHCE no usa el correo como identificador ni lo conserva en `Principal`.

| Dato ChatHCE | Claim por defecto | Uso |
| --- | --- | --- |
| Usuario | `sub` | Identificador estable (`RequestContext.user_id`) |
| Tenant | `tenant_id` | Aislamiento entre hospitales (`RequestContext.tenant_id`) |
| Roles | `roles` | RBAC, por ejemplo `clinician`, `researcher`, `reviewer`, `admin`, `auditor`, `knowledge-manager` |
| Servicio | `service` | Contexto firmado (`RequestContext.service_id`), que se contrasta con la relación asistencial |
| Nombre visible | `name` | Solo presentación |

Cada nombre se puede mapear en `OIDC_ISSUERS.claims`; admite rutas anidadas con puntos, por ejemplo `realm_access.roles` de Keycloak. El tenant es obligatorio y los roles deben pertenecer a la matriz RBAC de ADR 0170; un token sin esos claims se rechaza antes de crear el `RequestContext`.

## Configuración

Defina las variables en el secret manager o entorno del despliegue, nunca en el repositorio:

```dotenv
IDENTITY_PROVIDER=oidc
OIDC_REDIRECT_URI=https://api.chathce.hospital.example/api/v1/auth/callback
OIDC_ISSUERS=[{"issuer":"https://sso.hospital.example/realms/clinica","client_id":"chathce-api","audiences":["chathce-api"],"claims":{"sub":"sub","tenant":"hospital_id","roles":"realm_access.roles","service":"department","display_name":"name"}}]
OIDC_SCOPES=["openid","profile","email"]
```

`OIDC_ISSUERS` admite más de un objeto. Solo esos valores exactos de `issuer` son confiables: el adapter obtiene discovery desde `/.well-known/openid-configuration`, cachea discovery y JWKS, y rechaza tokens con un issuer, `kid`, algoritmo, audiencia o expiración no válidos. Los algoritmos de firma permitidos son RSA/EC asimétricos; no se acepta `none` ni HMAC.

Para un cliente confidencial puede definirse `OIDC_CLIENT_SECRET` fuera del repo. Para aplicaciones de navegador y el cliente de prueba, configure un cliente público con PKCE y deje esa variable vacía.

## Endpoints y Streamlit

- `GET /api/v1/auth/login?issuer=<issuer-opcional>` inicia el redirect al IdP, generando `state`, `nonce` y `code_verifier` de un solo uso.
- `GET /api/v1/auth/callback?code=...&state=...` intercambia el código, valida ambos tokens y entrega un `AuthSession` al cliente confiable.

El estado de login se conserva en memoria durante `OIDC_STATE_TTL_S` (600 segundos por defecto), por lo que todas las peticiones de login/callback deben alcanzar la misma instancia hasta que se introduzca un almacén compartido. En producción, coloque la API detrás de un BFF/proxy que transforme la respuesta de callback en cookie `HttpOnly`; no exponga tokens en logs, URLs ni almacenamiento persistente. `StreamlitAuthSession` ofrece `start_oidc_login`, `complete_oidc_login` y `accept_oidc_session` para recibir esa sesión ya validada, sin formularios ni contraseñas propias.

## Keycloak local reproducible

El repositorio incluye un realm de prueba, cliente público y usuario dummy. No se usa para datos clínicos ni entornos hospitalarios.

```powershell
docker compose -f docker-compose.oidc.yml up -d
$env:IDENTITY_PROVIDER = "oidc"
$env:OIDC_REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback"
$env:OIDC_ISSUERS = '[{"issuer":"http://localhost:8081/realms/chathce-test","client_id":"chathce-api","claims":{"sub":"sub","tenant":"tenant_id","roles":"realm_access.roles","service":"service","display_name":"name"}}]'
python -m uvicorn chathce.api.app:app --host 127.0.0.1 --port 8000
```

Abra `http://localhost:8000/api/v1/auth/login`. El realm incluye el usuario dummy `doctor-demo` y sus roles/atributos, pero no contiene contraseñas ni credenciales de administración. Asígnelas localmente mediante la consola de Keycloak o aprovisiónelas desde variables del entorno de desarrollo; elimine el usuario en cualquier entorno no local. Compruebe la integración opcional con `HCE_RUN_INTEGRATION=1; python -m pytest tests/integration/oidc -m integration`. Si Keycloak no está disponible, el test se salta.

## Entra ID y otros IdP hospitalarios

En Microsoft Entra ID, registre una aplicación web, añada la URI exacta de callback, active Authorization Code + PKCE y use como issuer el valor `issuer` publicado por el documento OpenID de su tenant. Añada app roles o group claims y mapéelos en `claims.roles`; si usa grupos, filtre o transforme en el IdP para emitir los roles clínicos mínimos. Emita atributos de tenant y servicio mediante optional claims, directory extensions o un proxy de identidad hospitalario según la gobernanza local.

Para otro proveedor (Ping, Okta, ADFS con OIDC o gateway hospitalario), use su discovery URL/issuer HTTPS, registre la misma callback y configure audiencias y claim mapping. SAML directo no se integra en la aplicación: fedérelo hacia OIDC en el IdP o proxy corporativo para conservar una única superficie de validación.

Antes del piloto, valide con seguridad del hospital la rotación de claves, MFA, logout/revocación, clock skew, grupos/roles y el contrato de claims. El adapter autentica y alimenta tenant, roles y servicio de RBAC/ABAC; aun así, `ScopeGuard` exige una relación asistencial vigente para el paciente y servicio. Los roles OIDC se administran en el IdP, no con el endpoint local de asignación de roles.
