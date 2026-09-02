"""StreamlitAuthSession: identidad en Streamlit con cookie que solo transporta el refresh token (ADR 0100).

- La cookie ``hce_session`` guarda ``{"rt": <refresh_token>}``; nunca el usuario ni el access token.
- El access token y el Principal viven en ``st.session_state`` (memoria del servidor).
- ``ensure_authenticated`` revalida el token contra el IdentityProvider (cache 60 s) y, si
  expiro, renueva con el refresh token (rotacion). Si falla, limpia la sesion.
- Riesgo residual documentado: CookieManager fija la cookie desde JS (no HttpOnly); por eso la
  cookie solo contiene un refresh token rotatorio de un solo uso y caduca en 1 h.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, MutableMapping, Optional

from chathce.domain.errors import AuthenticationFailed, DomainError
from chathce.domain.identity import AuthSession, Principal

logger = logging.getLogger(__name__)

COOKIE_NAME = "hce_session"
COOKIE_HOURS = 1
VERIFY_INTERVAL_S = 60.0
REFRESH_MARGIN_S = 60.0

# claves en session_state
K_PRINCIPAL = "auth_principal"
K_ACCESS = "auth_access_token"
K_REFRESH = "auth_refresh_token"
K_EXPIRES = "auth_expires_at"
K_LAST_VERIFY = "auth_last_verify"


class StreamlitAuthSession:
    def __init__(self, identity: Any, state: MutableMapping[str, Any], cookies: Optional[Any], run) -> None:
        """
        identity: IdentityProvider (async); state: st.session_state (o dict en tests);
        cookies: gestor con get/set/delete (o None); run: callable que ejecuta corrutinas de forma sincrona.
        """
        self._identity = identity
        self._state = state
        self._cookies = cookies
        self._run = run

    # ------------------------------------------------------------------
    @property
    def principal(self) -> Optional[Principal]:
        return self._state.get(K_PRINCIPAL)

    @property
    def access_token(self) -> Optional[str]:
        return self._state.get(K_ACCESS)

    def is_authenticated(self) -> bool:
        return self.principal is not None and bool(self.access_token)

    def _store(self, session: AuthSession, *, remember: bool) -> None:
        self._state[K_PRINCIPAL] = session.principal
        self._state[K_ACCESS] = session.access_token
        self._state[K_REFRESH] = session.refresh_token
        self._state[K_EXPIRES] = session.expires_at
        self._state[K_LAST_VERIFY] = time.monotonic()
        if remember and session.refresh_token and self._cookies is not None:
            try:
                self._cookies.set(COOKIE_NAME, {"rt": session.refresh_token},
                                  expires_at=datetime.now() + timedelta(hours=COOKIE_HOURS))
            except Exception as exc:  # noqa: BLE001
                logger.debug("No se pudo fijar la cookie de sesion: %s", exc)

    def clear(self) -> None:
        for key in (K_PRINCIPAL, K_ACCESS, K_REFRESH, K_EXPIRES, K_LAST_VERIFY):
            self._state.pop(key, None)
        if self._cookies is not None:
            try:
                self._cookies.delete(COOKIE_NAME)
            except Exception as exc:  # noqa: BLE001
                logger.debug("No se pudo borrar la cookie de sesion: %s", exc)

    # ------------------------------------------------------------------
    def login(self, email: str, password: str, *, remember_me: bool = False) -> Principal:
        session = self._run(self._identity.login(email, password))
        self._store(session, remember=remember_me)
        return session.principal

    def register(self, **kwargs) -> Principal:
        return self._run(self._identity.register(**kwargs))

    def reset_password(self, email: str) -> None:
        self._run(self._identity.reset_password(email))

    def logout(self) -> None:
        token = self.access_token
        if token:
            try:
                self._run(self._identity.logout(token))
            except Exception as exc:  # noqa: BLE001
                logger.debug("logout remoto fallido: %s", exc)
        self.clear()

    def _refresh(self, refresh_token: str, *, remember: bool) -> Optional[Principal]:
        try:
            session = self._run(self._identity.refresh(refresh_token))
        except DomainError as exc:
            logger.info("Renovacion de sesion rechazada: %s", exc.code)
            self.clear()
            return None
        self._store(session, remember=remember)
        return session.principal

    def _cookie_refresh_token(self) -> Optional[str]:
        if self._cookies is None:
            return None
        try:
            raw = self._cookies.get(COOKIE_NAME)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(raw, dict):
            return raw.get("rt") or None
        return None

    def ensure_authenticated(self) -> Optional[Principal]:
        """Principal vigente, revalidando o renovando; None si no hay sesion valida."""
        principal = self.principal
        token = self.access_token
        if principal is not None and token:
            expires_at: Optional[datetime] = self._state.get(K_EXPIRES)
            now_utc = datetime.now(timezone.utc)
            if expires_at is not None and (expires_at - now_utc).total_seconds() < REFRESH_MARGIN_S:
                refresh_token = self._state.get(K_REFRESH) or self._cookie_refresh_token()
                return self._refresh(refresh_token, remember=self._cookie_refresh_token() is not None) if refresh_token else self._expire()
            last = self._state.get(K_LAST_VERIFY) or 0.0
            if time.monotonic() - last >= VERIFY_INTERVAL_S:
                try:
                    verified = self._run(self._identity.verify_access_token(token))
                except AuthenticationFailed:
                    refresh_token = self._state.get(K_REFRESH) or self._cookie_refresh_token()
                    return self._refresh(refresh_token, remember=self._cookie_refresh_token() is not None) if refresh_token else self._expire()
                self._state[K_PRINCIPAL] = verified
                self._state[K_LAST_VERIFY] = time.monotonic()
                return verified
            return principal

        refresh_token = self._cookie_refresh_token()
        if refresh_token:
            restored = self._refresh(refresh_token, remember=True)
            if restored is not None:
                logger.info("Sesion restaurada desde cookie (refresh token) para %s", restored.user_id)
            return restored
        return None

    def _expire(self) -> None:
        self.clear()
        return None

    def to_legacy_user(self) -> Optional[Dict[str, Any]]:
        principal = self.principal
        if principal is None:
            return None
        user = principal.to_legacy_user_dict()
        user.setdefault("email", "")
        return user
