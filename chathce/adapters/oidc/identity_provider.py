"""Proveedor OIDC generico con discovery, JWKS cacheado y PKCE.

No conoce ningun IdP concreto: los issuers, audiencias y claims viven en
``IdentitySettings``. El adapter no persiste contrasenas ni claves privadas.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, FrozenSet, Mapping, Optional
from urllib.parse import urlencode

import httpx
import jwt

from chathce.domain.errors import AuthenticationFailed
from chathce.domain.authorization import Role
from chathce.domain.identity import AuthSession, Principal

JsonFetcher = Callable[[str], Awaitable[Mapping[str, Any]]]
FormPoster = Callable[[str, Mapping[str, str]], Awaitable[Mapping[str, Any]]]

_ALGORITHMS = ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512")


@dataclass(frozen=True)
class OidcAuthorizationRequest:
    authorization_url: str
    state: str
    expires_at: datetime


@dataclass(frozen=True)
class _PendingAuthorization:
    issuer: Any
    redirect_uri: str
    code_verifier: str
    nonce: str
    expires_at: float


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _claim(payload: Mapping[str, Any], name: str) -> Any:
    """Lee un claim plano o anidado, por ejemplo ``realm_access.roles``."""
    value: Any = payload
    for part in name.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _roles(value: Any) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset(part for part in value.replace(",", " ").split() if part)
    if isinstance(value, (list, tuple, set)):
        return frozenset(str(part) for part in value if isinstance(part, (str, int)) and str(part))
    return frozenset()


class OidcIdentityProvider:
    """Implementacion local del port ``IdentityProvider`` para OIDC/OAuth2.

    ``fetch_json`` y ``post_form`` son puntos de inyeccion para tests offline.
    En produccion usan HTTPX con timeout y nunca escriben tokens en logs.
    """

    def __init__(
        self,
        settings: Any,
        *,
        fetch_json: Optional[JsonFetcher] = None,
        post_form: Optional[FormPoster] = None,
        patient_access: Optional[Any] = None,
    ) -> None:
        issuers = list(getattr(settings, "oidc_issuers", []) or [])
        if not issuers:
            raise ValueError("OIDC_ISSUERS no contiene issuers confiables")
        self._settings = settings
        self._issuers = {str(item.issuer).rstrip("/"): item for item in issuers}
        self._fetch_json = fetch_json or self._http_get_json
        self._post_form = post_form or self._http_post_form
        self._discovery_cache: Dict[str, tuple[float, Mapping[str, Any]]] = {}
        self._jwks_cache: Dict[str, tuple[float, Mapping[str, Any]]] = {}
        self._pending: Dict[str, _PendingAuthorization] = {}
        self._patient_access = patient_access

    async def _http_get_json(self, url: str) -> Mapping[str, Any]:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, Mapping):
            raise AuthenticationFailed("Respuesta OIDC invalida")
        return data

    async def _http_post_form(self, url: str, data: Mapping[str, str]) -> Mapping[str, Any]:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.post(url, data=dict(data), headers={"Accept": "application/json"})
            response.raise_for_status()
            result = response.json()
        if not isinstance(result, Mapping):
            raise AuthenticationFailed("Respuesta OIDC invalida")
        return result

    def _issuer(self, issuer: Optional[str] = None) -> Any:
        if issuer is None:
            return next(iter(self._issuers.values()))
        selected = self._issuers.get(issuer.rstrip("/"))
        if selected is None:
            raise AuthenticationFailed("Issuer OIDC no confiable")
        return selected

    async def _discovery(self, issuer: Any, *, force: bool = False) -> Mapping[str, Any]:
        key = str(issuer.issuer).rstrip("/")
        cached = self._discovery_cache.get(key)
        now = time.monotonic()
        if not force and cached and now < cached[0]:
            return cached[1]
        url = getattr(issuer, "discovery_url", None) or f"{key}/.well-known/openid-configuration"
        try:
            document = await self._fetch_json(url)
        except AuthenticationFailed:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed("No se pudo descubrir el proveedor OIDC") from exc
        if str(document.get("issuer", "")).rstrip("/") != key or not document.get("jwks_uri"):
            raise AuthenticationFailed("Discovery OIDC no coincide con el issuer configurado")
        self._discovery_cache[key] = (now + float(self._settings.oidc_discovery_cache_s), document)
        return document

    async def _jwks(self, issuer: Any, *, force: bool = False) -> Mapping[str, Any]:
        key = str(issuer.issuer).rstrip("/")
        cached = self._jwks_cache.get(key)
        now = time.monotonic()
        if not force and cached and now < cached[0]:
            return cached[1]
        discovery = await self._discovery(issuer)
        try:
            document = await self._fetch_json(str(discovery["jwks_uri"]))
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed("No se pudieron obtener las claves OIDC") from exc
        if not isinstance(document.get("keys"), list):
            raise AuthenticationFailed("JWKS OIDC invalido")
        self._jwks_cache[key] = (now + float(self._settings.oidc_jwks_cache_s), document)
        return document

    async def _decode(self, token: str, *, nonce: Optional[str] = None) -> tuple[Mapping[str, Any], Any]:
        if not token:
            raise AuthenticationFailed("Token ausente")
        try:
            unverified = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed("Token OIDC malformado") from exc
        issuer_value = str(unverified.get("iss", "")).rstrip("/")
        issuer = self._issuers.get(issuer_value)
        if issuer is None:
            raise AuthenticationFailed("Issuer OIDC no confiable")
        kid, algorithm = header.get("kid"), header.get("alg")
        if not kid or algorithm not in _ALGORITHMS:
            raise AuthenticationFailed("Algoritmo o clave OIDC no permitidos")

        jwks = await self._jwks(issuer)
        key_data = next((item for item in jwks["keys"] if item.get("kid") == kid), None)
        if key_data is None:  # rotacion de claves: se reintenta una vez sin cache.
            jwks = await self._jwks(issuer, force=True)
            key_data = next((item for item in jwks["keys"] if item.get("kid") == kid), None)
        if key_data is None:
            raise AuthenticationFailed("Clave de firma OIDC desconocida")
        try:
            key = jwt.PyJWK.from_dict(key_data).key
            audiences = list(getattr(issuer, "audiences", []) or []) or [str(issuer.client_id)]
            payload = jwt.decode(
                token,
                key=key,
                algorithms=list(_ALGORITHMS),
                audience=audiences,
                issuer=str(issuer.issuer).rstrip("/"),
                options={"require": ["exp", "iss", getattr(issuer.claims, "sub", "sub")]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed("Token OIDC invalido o expirado") from exc
        if nonce is not None and payload.get("nonce") != nonce:
            raise AuthenticationFailed("Nonce OIDC invalido")
        return payload, issuer

    def _principal(self, payload: Mapping[str, Any], issuer: Any) -> Principal:
        mapping = issuer.claims
        user_id = _claim(payload, mapping.sub)
        if user_id is None or not str(user_id):
            raise AuthenticationFailed("El token OIDC no contiene el subject requerido")
        exp = payload.get("exp")
        try:
            expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)
        except (TypeError, ValueError, OSError) as exc:
            raise AuthenticationFailed("El token OIDC no contiene expiracion valida") from exc
        tenant = _claim(payload, mapping.tenant)
        if not isinstance(tenant, str) or not tenant.strip() or len(tenant) > 100:
            raise AuthenticationFailed("El token OIDC no contiene un tenant valido")
        roles = _roles(_claim(payload, mapping.roles))
        try:
            roles = frozenset(Role(role).value for role in roles)
        except ValueError as exc:
            raise AuthenticationFailed("El token OIDC contiene un rol no reconocido") from exc
        service = _claim(payload, mapping.service)
        display_name = _claim(payload, mapping.display_name)
        return Principal(
            user_id=str(user_id), tenant_id=tenant, roles=roles,
            service=str(service) if service not in (None, "") else None,
            display_name=str(display_name) if display_name not in (None, "") else None, expires_at=expires_at,
        )

    async def verify_access_token(self, token: str) -> Principal:
        payload, issuer = await self._decode(token)
        return self._principal(payload, issuer)

    async def begin_authorization(self, *, redirect_uri: str, issuer: Optional[str] = None) -> OidcAuthorizationRequest:
        configured_redirect = getattr(self._settings, "oidc_redirect_uri", None)
        if configured_redirect and redirect_uri != configured_redirect:
            raise AuthenticationFailed("Redirect URI OIDC no autorizada")
        selected = self._issuer(issuer)
        discovery = await self._discovery(selected)
        endpoint = discovery.get("authorization_endpoint")
        if not endpoint:
            raise AuthenticationFailed("El issuer OIDC no publica authorization_endpoint")
        verifier = _b64url(secrets.token_bytes(48))
        state, nonce = _b64url(secrets.token_bytes(32)), _b64url(secrets.token_bytes(32))
        expires = time.monotonic() + float(self._settings.oidc_state_ttl_s)
        self._purge_pending()
        self._pending[state] = _PendingAuthorization(selected, redirect_uri, verifier, nonce, expires)
        params = {
            "response_type": "code", "client_id": str(selected.client_id), "redirect_uri": redirect_uri,
            "scope": " ".join(getattr(self._settings, "oidc_scopes", ["openid"])), "state": state, "nonce": nonce,
            "code_challenge": _b64url(hashlib.sha256(verifier.encode("ascii")).digest()), "code_challenge_method": "S256",
        }
        return OidcAuthorizationRequest(
            str(endpoint) + "?" + urlencode(params), state,
            datetime.fromtimestamp(time.time() + float(self._settings.oidc_state_ttl_s), tz=timezone.utc),
        )

    def _purge_pending(self) -> None:
        now = time.monotonic()
        self._pending = {key: value for key, value in self._pending.items() if value.expires_at > now}

    async def exchange_authorization_code(self, *, code: str, state: str) -> AuthSession:
        self._purge_pending()
        pending = self._pending.pop(state, None)
        if pending is None or not code:
            raise AuthenticationFailed("Estado OIDC ausente, expirado o ya utilizado")
        discovery = await self._discovery(pending.issuer)
        endpoint = discovery.get("token_endpoint")
        if not endpoint:
            raise AuthenticationFailed("El issuer OIDC no publica token_endpoint")
        form = {
            "grant_type": "authorization_code", "code": code, "redirect_uri": pending.redirect_uri,
            "client_id": str(pending.issuer.client_id), "code_verifier": pending.code_verifier,
        }
        secret = getattr(self._settings, "oidc_client_secret", None)
        if secret:
            form["client_secret"] = str(secret)
        try:
            tokens = await self._post_form(str(endpoint), form)
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed("El intercambio de codigo OIDC fue rechazado") from exc
        id_token = tokens.get("id_token")
        access_token = tokens.get("access_token")
        if not isinstance(id_token, str) or not isinstance(access_token, str):
            raise AuthenticationFailed("Respuesta OIDC sin id_token o access_token")
        id_payload, issuer = await self._decode(id_token, nonce=pending.nonce)
        # El access token se valida tambien; es el que los clientes presentan a la API.
        await self._decode(access_token)
        principal = self._principal(id_payload, issuer)
        return AuthSession(access_token=access_token, refresh_token=tokens.get("refresh_token"), expires_at=principal.expires_at, principal=principal)

    async def login(self, email: str, password: str) -> AuthSession:
        raise AuthenticationFailed("Este despliegue usa SSO OIDC; inicie sesion mediante el proveedor hospitalario")

    async def refresh(self, refresh_token: str) -> AuthSession:
        raise AuthenticationFailed("La renovacion OIDC debe realizarse mediante el flujo del proveedor")

    async def logout(self, access_token: str) -> None:
        # La revocacion y el cierre de sesion central se delegan al IdP. No se
        # intenta llamar a endpoints no estandar desde un canal sin navegador.
        return None

    async def register(self, **kwargs: Any) -> Principal:
        raise AuthenticationFailed("Las cuentas se administran en el IdP hospitalario")

    async def reset_password(self, email: str) -> None:
        raise AuthenticationFailed("La recuperacion de credenciales se administra en el IdP hospitalario")

    async def has_active_patient_access(
        self, *, user_id: str, tenant_id: str, subject_id: int | str, service_id: str, at: datetime,
    ) -> bool:
        """Delegacion fail-closed de la relacion asistencial local.

        El IdP autentica y emite los claims; la concesion paciente-servicio se
        conserva en el store de autorizacion que el composition root conecta.
        """
        if self._patient_access is None:
            return False
        try:
            return bool(await self._patient_access.has_active_patient_access(
                user_id=user_id, tenant_id=tenant_id, subject_id=subject_id, service_id=service_id, at=at,
            ))
        except Exception:  # noqa: BLE001 - autorizacion debe fallar cerrada
            return False

    async def assign_roles(self, *, user_id: str, tenant_id: str, roles: FrozenSet[str]) -> None:
        # Los roles que decide RBAC se consumen del JWT firmado; actualizar un
        # store local no tendria efecto sobre un issuer OIDC y seria inseguro.
        raise AuthenticationFailed("Los roles OIDC se administran en el IdP hospitalario")

    async def grant_patient_access(
        self, *, user_id: str, tenant_id: str, subject_id: int | str, service_id: str,
        valid_from: datetime, valid_until: Optional[datetime], granted_by: str,
    ) -> None:
        if self._patient_access is None:
            raise AuthenticationFailed("No hay store de relacion asistencial configurado")
        await self._patient_access.grant_patient_access(
            user_id=user_id, tenant_id=tenant_id, subject_id=subject_id, service_id=service_id,
            valid_from=valid_from, valid_until=valid_until, granted_by=granted_by,
        )
