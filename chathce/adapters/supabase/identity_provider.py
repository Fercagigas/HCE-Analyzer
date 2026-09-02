"""SupabaseIdentityProvider: Supabase Auth + perfil en public.users (ADR 0100).

- ``verify_access_token`` valida el JWT contra Supabase (``auth.get_user(jwt)``), respetando
  revocaciones; cache en memoria 60 s por hash del token.
- Roles: ``app_metadata.roles`` del usuario de Auth y, si no existen, ``users.role`` del perfil.
- Nunca devuelve email ni tokens dentro de ``Principal``.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Optional, Tuple

from chathce.adapters.supabase._common import run_blocking, sanitize_error
from chathce.domain.errors import AuthenticationFailed
from chathce.domain.identity import AuthSession, Principal

FRIENDLY_ERRORS = (
    ("Invalid login credentials", "Correo o contraseña incorrectos"),
    ("Email not confirmed", "Por favor confirma tu correo electrónico antes de iniciar sesión"),
    ("Too many requests", "Demasiados intentos. Espera unos minutos e intenta de nuevo"),
    ("User already registered", "Este correo ya está registrado. Intenta iniciar sesión."),
    ("Password should be at least", "La contraseña debe tener al menos 6 caracteres"),
    ("Unable to validate email", "Correo electrónico inválido"),
)


def _friendly(exc: BaseException, default: str) -> str:
    text = str(exc)
    for needle, message in FRIENDLY_ERRORS:
        if needle in text:
            return message
    return default


def _roles_from(user: Any, profile: Optional[Dict[str, Any]]) -> FrozenSet[str]:
    roles: set = set()
    app_meta = getattr(user, "app_metadata", None) or {}
    raw = app_meta.get("roles") if isinstance(app_meta, dict) else None
    if isinstance(raw, (list, tuple, set)):
        roles.update(str(r) for r in raw)
    elif isinstance(raw, str):
        roles.add(raw)
    if profile:
        role = profile.get("role")
        if isinstance(role, str) and role:
            roles.add(role)
        if profile.get("is_researcher") is True:
            roles.add("researcher")
    return frozenset(roles)


def _expires_at(session: Any) -> Optional[datetime]:
    raw = getattr(session, "expires_at", None)
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


class SupabaseIdentityProvider:
    def __init__(self, client: Any, *, cache_ttl_s: float = 60.0, timeout_s: float = 30.0, tenant_id: str = "default"):
        self._client = client
        self._ttl = cache_ttl_s
        self._timeout = timeout_s
        self._tenant = tenant_id
        self._cache: Dict[str, Tuple[float, Principal]] = {}

    # ------------------------------------------------------------------
    def _profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self._client.table("users").select("*").eq("id", user_id).limit(1).execute()
            return (result.data or [None])[0]
        except Exception:  # noqa: BLE001
            return None

    def _ensure_profile(self, user: Any) -> Dict[str, Any]:
        profile = self._profile(user.id)
        if profile:
            return profile
        email = getattr(user, "email", "") or ""
        record = {
            "id": user.id, "auth_id": user.id, "email": email, "name": email.split("@")[0] if email else "usuario",
            "is_active": True, "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            inserted = self._client.table("users").insert(record).execute()
            return (inserted.data or [record])[0]
        except Exception:  # noqa: BLE001
            return record

    def _principal(self, user: Any, profile: Optional[Dict[str, Any]], expires_at: Optional[datetime]) -> Principal:
        return Principal(
            user_id=str(user.id), tenant_id=self._tenant, roles=_roles_from(user, profile),
            expires_at=expires_at, display_name=(profile or {}).get("name"),
        )

    def _session(self, response: Any, profile: Optional[Dict[str, Any]]) -> AuthSession:
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        if user is None or session is None or not getattr(session, "access_token", None):
            raise AuthenticationFailed("Credenciales inválidas")
        expires = _expires_at(session)
        return AuthSession(
            access_token=session.access_token, refresh_token=getattr(session, "refresh_token", None),
            expires_at=expires, principal=self._principal(user, profile, expires),
        )

    # ------------------------------------------------------------------
    async def verify_access_token(self, token: str) -> Principal:
        if not token:
            raise AuthenticationFailed("Token ausente")
        key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        now = time.monotonic()
        if cached and now - cached[0] < self._ttl:
            return cached[1]

        def verify():
            response = self._client.auth.get_user(token)
            user = getattr(response, "user", None)
            if user is None:
                raise AuthenticationFailed("Token inválido o expirado")
            return user, self._profile(user.id)

        try:
            user, profile = await run_blocking(verify, what="verificacion de token", timeout_s=self._timeout)
        except AuthenticationFailed:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed(f"Token inválido o expirado ({sanitize_error(exc)})") from exc
        principal = self._principal(user, profile, None)
        self._cache[key] = (now, principal)
        if len(self._cache) > 1000:
            self._cache = {k: v for k, v in self._cache.items() if now - v[0] < self._ttl}
        return principal

    async def login(self, email: str, password: str) -> AuthSession:
        def do_login():
            response = self._client.auth.sign_in_with_password({"email": email, "password": password})
            user = getattr(response, "user", None)
            profile = self._ensure_profile(user) if user is not None else None
            if user is not None:
                try:
                    self._client.table("users").update({"last_login": datetime.now(timezone.utc).isoformat()}).eq("id", user.id).execute()
                except Exception:  # noqa: BLE001
                    pass
            return response, profile

        try:
            response, profile = await run_blocking(do_login, what="inicio de sesion", timeout_s=self._timeout)
        except AuthenticationFailed:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed(_friendly(exc, "Error de autenticación. Intenta de nuevo más tarde")) from exc
        return self._session(response, profile)

    async def refresh(self, refresh_token: str) -> AuthSession:
        def do_refresh():
            response = self._client.auth.refresh_session(refresh_token)
            user = getattr(response, "user", None)
            return response, (self._profile(user.id) if user is not None else None)

        try:
            response, profile = await run_blocking(do_refresh, what="refresco de sesion", timeout_s=self._timeout)
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed(f"No se pudo renovar la sesión ({sanitize_error(exc)})") from exc
        session = self._session(response, profile)
        self._cache.clear()
        return session

    async def logout(self, access_token: str) -> None:
        def do_logout():
            admin = getattr(self._client.auth, "admin", None)
            if admin is not None and hasattr(admin, "sign_out"):
                admin.sign_out(access_token)
            else:
                self._client.auth.sign_out()

        try:
            await run_blocking(do_logout, what="cierre de sesion", timeout_s=self._timeout)
        except Exception:  # noqa: BLE001 - el logout nunca falla hacia el usuario
            pass
        self._cache.pop(hashlib.sha256(access_token.encode("utf-8")).hexdigest(), None)

    async def register(self, *, email: str, password: str, name: str, specialty: Optional[str] = None,
                       medical_license: Optional[str] = None) -> Principal:
        if len(password) < 6:
            raise AuthenticationFailed("La contraseña debe tener al menos 6 caracteres")
        if not email or "@" not in email:
            raise AuthenticationFailed("Correo electrónico inválido")

        def do_register():
            response = self._client.auth.sign_up({
                "email": email, "password": password, "options": {"data": {"name": name, "specialty": specialty}},
            })
            user = getattr(response, "user", None)
            if user is None:
                raise AuthenticationFailed("Error en el registro. Intenta de nuevo.")
            record = {
                "id": user.id, "auth_id": user.id, "email": email, "name": name, "specialty": specialty,
                "medical_license": medical_license, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                self._client.table("users").insert(record).execute()
            except Exception:  # noqa: BLE001 - perfil opcional
                pass
            return user, record

        try:
            user, record = await run_blocking(do_register, what="registro", timeout_s=self._timeout)
        except AuthenticationFailed:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed(_friendly(exc, "Error en el registro. Intenta de nuevo más tarde.")) from exc
        return self._principal(user, record, None)

    async def reset_password(self, email: str) -> None:
        try:
            await run_blocking(lambda: self._client.auth.reset_password_email(email), what="recuperacion", timeout_s=self._timeout)
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed("Error enviando el correo. Verifica que el email sea correcto.") from exc
