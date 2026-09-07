"""SessionManager: fachada estatica para la UI Streamlit sobre el adapter de presentacion del core (WP10).

Conserva los nombres de metodo que usan `src/core/app.py`, `auth_pages.py` y `sidebar.py`.
La cookie ya no guarda el usuario: solo un refresh token rotatorio; la sesion se revalida
contra Supabase en cada restauracion (ADR 0100).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from chathce.domain.errors import DomainError
from chathce.streamlit_adapter.auth_session import StreamlitAuthSession
from chathce.streamlit_adapter.bootstrap import get_container
from chathce.streamlit_adapter.legacy_services import LegacyAuthServiceAdapter

logger = logging.getLogger(__name__)


def _cookie_manager():
    try:
        import extra_streamlit_components as stx

        if "cookie_manager" not in st.session_state:
            st.session_state.cookie_manager = stx.CookieManager(key="cookie_manager_hce")
        return st.session_state.cookie_manager
    except Exception as exc:  # noqa: BLE001
        logger.debug("CookieManager no disponible: %s", exc)
        return None


class SessionManager:
    """Gestor centralizado de sesion y autenticacion (adapter Streamlit)."""

    @staticmethod
    def _container():
        return get_container()

    @staticmethod
    def _auth() -> StreamlitAuthSession:
        container = SessionManager._container()
        return StreamlitAuthSession(container.identity, st.session_state, _cookie_manager(), container.run)

    @staticmethod
    def _sync_legacy_state() -> None:
        auth = SessionManager._auth()
        user = auth.to_legacy_user()
        st.session_state.authenticated = user is not None
        st.session_state.user = user

    # ------------------------------------------------------------------
    @staticmethod
    def init_session() -> None:
        try:
            container = SessionManager._container()
            st.session_state.setdefault("current_session", None)
            st.session_state.setdefault("current_mode", "welcome")
            st.session_state.setdefault("patient_context", None)
            st.session_state.setdefault("encounter_context", None)
            st.session_state.setdefault("research_mode", False)
            if "auth_service" not in st.session_state or not isinstance(st.session_state.auth_service, LegacyAuthServiceAdapter):
                st.session_state.auth_service = LegacyAuthServiceAdapter(
                    container, lambda: (st.session_state.get("user") or {}).get("id"))
            auth = SessionManager._auth()
            principal = auth.ensure_authenticated()
            SessionManager._sync_legacy_state()
            if principal is not None and "unified_config" not in st.session_state:
                SessionManager._load_user_preferences(principal.user_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error inicializando sesion: %s", exc)
            st.error("Error inicializando la aplicación")

    @staticmethod
    def is_authenticated() -> bool:
        return bool(st.session_state.get("authenticated")) and st.session_state.get("user") is not None

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        return st.session_state.get("user") if SessionManager.is_authenticated() else None

    @staticmethod
    def current_roles() -> set:
        return set((st.session_state.get("user") or {}).get("roles", []))

    # ------------------------------------------------------------------
    @staticmethod
    def login(email: str, password: str, remember_me: bool = False) -> Tuple[bool, str]:
        if not email or not password:
            return False, "Email y contraseña son requeridos"
        try:
            principal = SessionManager._auth().login(email, password, remember_me=remember_me)
        except DomainError as exc:
            return False, exc.message
        except Exception as exc:  # noqa: BLE001
            logger.error("Error en login: %s", exc)
            return False, "Error interno en autenticación"
        SessionManager._sync_legacy_state()
        st.session_state.current_mode = "welcome"
        SessionManager._load_user_preferences(principal.user_id)
        logger.info("Login correcto para el usuario %s", principal.user_id)
        return True, "Login exitoso"

    @staticmethod
    def logout() -> None:
        try:
            SessionManager._auth().logout()
        finally:
            for key in ("authenticated", "user", "current_session", "unified_messages", "patient_context", "encounter_context"):
                st.session_state.pop(key, None)
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.current_mode = "welcome"
            logger.info("Sesion cerrada")

    @staticmethod
    def register(email: str, password: str, name: str, specialty: Optional[str] = None,
                 medical_license: Optional[str] = None) -> Tuple[bool, str]:
        if not all([email, password, name]):
            return False, "Email, contraseña y nombre son requeridos"
        try:
            SessionManager._auth().register(email=email, password=password, name=name, specialty=specialty, medical_license=medical_license)
            return True, "Usuario registrado. Revisa tu correo si se requiere confirmación."
        except DomainError as exc:
            return False, exc.message
        except Exception as exc:  # noqa: BLE001
            logger.error("Error en registro: %s", exc)
            return False, "Error interno en registro"

    # ------------------------------------------------------------------
    @staticmethod
    def create_chat_session(title: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        if not SessionManager.is_authenticated():
            return False, None
        from datetime import datetime

        title = title or f"Sesión {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return st.session_state.auth_service.create_chat_session(st.session_state.user["id"], title)

    @staticmethod
    def get_user_sessions(limit: int = 10) -> Tuple[bool, List[Dict[str, Any]]]:
        if not SessionManager.is_authenticated():
            return False, []
        return st.session_state.auth_service.get_user_sessions(st.session_state.user["id"], limit)

    @staticmethod
    def get_session_messages(session_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        if not SessionManager.is_authenticated():
            return False, []
        return st.session_state.auth_service.get_session_messages(session_id)

    @staticmethod
    def save_message(session_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        return SessionManager.is_authenticated()

    @staticmethod
    def update_user_profile(updates: Dict[str, Any]) -> Tuple[bool, str]:
        return False, "La edición de perfil se gestiona en Supabase (pendiente en la API)"

    @staticmethod
    def get_user_stats() -> Dict[str, Any]:
        if not SessionManager.is_authenticated():
            return {}
        return st.session_state.auth_service.get_user_stats(st.session_state.user["id"])

    @staticmethod
    def check_session_limits() -> Dict[str, Any]:
        if not SessionManager.is_authenticated():
            return {"valid": False, "reason": "No autenticado"}
        return {"valid": True, "analyses_remaining": 15, "rag_queries_remaining": 50, "session_expires_at": None}

    # ------------------------------------------------------------------
    @staticmethod
    def _load_user_preferences(user_id: str) -> None:
        try:
            from chathce.domain.context import Channel, RequestContext

            container = SessionManager._container()
            prefs = container.run(container.preferences.load(RequestContext(user_id=user_id, channel=Channel.streamlit)))
            st.session_state.unified_config = prefs
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudieron cargar preferencias: %s", exc)

    @staticmethod
    def save_user_preferences(preferences: Dict[str, Any]) -> Tuple[bool, str]:
        if not SessionManager.is_authenticated():
            return False, "No autenticado"
        try:
            from chathce.domain.context import Channel, RequestContext

            container = SessionManager._container()
            ok = container.run(container.preferences.save(
                RequestContext(user_id=st.session_state.user["id"], channel=Channel.streamlit), dict(preferences)))
            return (True, "Preferencias guardadas") if ok else (False, "No se pudieron guardar las preferencias")
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
