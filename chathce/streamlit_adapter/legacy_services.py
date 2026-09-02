"""Adaptador con la API que la UI Streamlit legacy espera de `auth_service` (sesiones/mensajes/estadisticas).

Sustituye al `AuthService` que vivia en `st.session_state.auth_service`, delegando en los
repositorios del core con el RequestContext del usuario autenticado.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from chathce.composition.container import Container
from chathce.domain.context import Channel, RequestContext


def _dt(value) -> Optional[str]:
    return value.isoformat() if value is not None else None


class LegacyAuthServiceAdapter:
    def __init__(self, container: Container, user_id_getter):
        self._container = container
        self._user_id = user_id_getter

    def _ctx(self, session_id: Optional[str] = None) -> RequestContext:
        return RequestContext(user_id=self._user_id() or "anonymous", channel=Channel.streamlit, session_id=session_id)

    def is_available(self) -> bool:
        return self._user_id() is not None

    @staticmethod
    def _session_dict(session) -> Dict[str, Any]:
        return {"id": session.session_id, "user_id": session.user_id, "title": session.title,
                "created_at": _dt(session.created_at), "updated_at": _dt(session.updated_at)}

    def create_chat_session(self, user_id: str, title: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        try:
            session = self._container.run(self._container.conversations.create_session(self._ctx(), title=title))
            return True, self._session_dict(session)
        except Exception:  # noqa: BLE001
            return False, None

    def get_user_sessions(self, user_id: str, limit: int = 3) -> Tuple[bool, List[Dict[str, Any]]]:
        try:
            sessions = self._container.run(self._container.conversations.list_sessions(self._ctx(), limit=limit))
            return True, [self._session_dict(s) for s in sessions]
        except Exception:  # noqa: BLE001
            return False, []

    def get_session_messages(self, session_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        try:
            messages = self._container.run(self._container.conversations.list_messages(self._ctx(session_id), session_id=session_id))
            return True, [
                {"id": m.message_id, "session_id": m.session_id, "content": m.content, "role": m.role,
                 "metadata": m.metadata.model_dump(mode="json", exclude_none=True), "created_at": _dt(m.created_at)}
                for m in messages
            ]
        except Exception:  # noqa: BLE001
            return False, []

    def delete_chat_session(self, session_id: str, user_id: str) -> Tuple[bool, str]:
        try:
            ok = self._container.run(self._container.conversations.delete_session(self._ctx(session_id), session_id=session_id))
            return (True, "Sesión eliminada correctamente") if ok else (False, "Sesión no encontrada o no autorizado")
        except Exception:  # noqa: BLE001
            return False, "Error de base de datos"

    def update_session_title(self, session_id: str, user_id: str, new_title: str) -> Tuple[bool, str]:
        try:
            ok = self._container.run(self._container.conversations.rename_session(self._ctx(session_id), session_id=session_id, title=new_title))
            return (True, "Título actualizado correctamente") if ok else (False, "Sesión no encontrada o no autorizado")
        except Exception:  # noqa: BLE001
            return False, "Error de base de datos"

    def save_message(self, session_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """La persistencia del turno la hace ChatService; se conserva por compatibilidad."""
        return True

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        try:
            sessions = self._container.run(self._container.conversations.list_sessions(self._ctx(), limit=3))
            total_messages = 0
            for s in sessions:
                total_messages += len(self._container.run(self._container.conversations.list_messages(self._ctx(s.session_id), session_id=s.session_id)))
            last = max((s.updated_at for s in sessions if s.updated_at), default=None)
            return {"total_sessions": len(sessions), "total_messages": total_messages, "last_activity": _dt(last), "max_sessions": 3}
        except Exception as exc:  # noqa: BLE001
            return {"total_sessions": 0, "total_messages": 0, "last_activity": None, "error": exc.__class__.__name__}

    def get_analysis_stats(self, user_id: str) -> Dict[str, Any]:
        try:
            return self._container.run(self._container.analyses.stats(self._ctx()))
        except Exception as exc:  # noqa: BLE001
            return {"error": exc.__class__.__name__}

    def reset_password(self, email: str) -> Tuple[bool, str]:
        try:
            self._container.run(self._container.identity.reset_password(email))
            return True, "Se ha enviado un correo con instrucciones para restablecer tu contraseña"
        except Exception:  # noqa: BLE001
            return False, "Error enviando el correo. Verifica que el email sea correcto."
