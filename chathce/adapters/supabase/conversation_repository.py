"""SupabaseConversationRepository: chat_sessions / chat_messages en public.* (codigo movido de auth_service.py).

Todas las lecturas y escrituras se filtran por el usuario del contexto.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from chathce.adapters.supabase._common import parse_dt, run_blocking, sanitize_error
from chathce.domain.context import RequestContext
from chathce.domain.conversation import ConversationSession, MessageMetadata, StoredMessage
from chathce.domain.errors import NotFound, ProviderUnavailable

MAX_SESSIONS_PER_USER = 3  # el trigger enforce_max_sessions borra la mas antigua


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session(row: Dict[str, Any]) -> ConversationSession:
    return ConversationSession(
        session_id=str(row["id"]), user_id=str(row["user_id"]), title=str(row.get("title") or ""),
        created_at=parse_dt(row.get("created_at")), updated_at=parse_dt(row.get("updated_at")),
    )


def _message(row: Dict[str, Any]) -> StoredMessage:
    raw_meta = row.get("metadata") or {}
    allowed = {k: v for k, v in raw_meta.items() if k in MessageMetadata.model_fields}
    return StoredMessage(
        message_id=str(row.get("id")) if row.get("id") is not None else None,
        session_id=str(row["session_id"]), role=row.get("role", "user"), content=str(row.get("content") or ""),
        metadata=MessageMetadata(**allowed), created_at=parse_dt(row.get("created_at")),
    )


class SupabaseConversationRepository:
    def __init__(self, client: Any, *, timeout_s: float = 30.0):
        self._client = client
        self._timeout = timeout_s

    async def _run(self, fn, what: str):
        try:
            return await run_blocking(fn, what=what, timeout_s=self._timeout)
        except (NotFound, ProviderUnavailable):
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"Persistencia de conversaciones no disponible ({what}): {sanitize_error(exc)}") from exc

    def _owned_row(self, ctx: RequestContext, session_id: str) -> Dict[str, Any]:
        result = self._client.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", ctx.user_id).limit(1).execute()
        rows = result.data or []
        if not rows:
            raise NotFound("Sesión no encontrada o no autorizada")
        return rows[0]

    # ------------------------------------------------------------------
    async def create_session(self, ctx: RequestContext, *, title: str) -> ConversationSession:
        def do():
            record = {"user_id": ctx.user_id, "title": title, "created_at": _now(), "updated_at": _now()}
            result = self._client.table("chat_sessions").insert(record).execute()
            if not result.data:
                raise ProviderUnavailable("No se pudo crear la sesión")
            return _session(result.data[0])

        return await self._run(do, "creacion de sesion")

    async def list_sessions(self, ctx: RequestContext, *, limit: int = 3) -> List[ConversationSession]:
        def do():
            result = (
                self._client.table("chat_sessions").select("*").eq("user_id", ctx.user_id)
                .order("updated_at", desc=True).limit(min(limit, MAX_SESSIONS_PER_USER)).execute()
            )
            return [_session(r) for r in (result.data or [])]

        return await self._run(do, "listado de sesiones")

    async def get_session(self, ctx: RequestContext, *, session_id: str) -> Optional[ConversationSession]:
        def do():
            try:
                return _session(self._owned_row(ctx, session_id))
            except NotFound:
                return None

        return await self._run(do, "lectura de sesion")

    async def delete_session(self, ctx: RequestContext, *, session_id: str) -> bool:
        def do():
            try:
                self._owned_row(ctx, session_id)
            except NotFound:
                return False
            result = self._client.table("chat_sessions").delete().eq("id", session_id).eq("user_id", ctx.user_id).execute()
            return bool(result.data)

        return await self._run(do, "borrado de sesion")

    async def rename_session(self, ctx: RequestContext, *, session_id: str, title: str) -> bool:
        def do():
            result = (
                self._client.table("chat_sessions").update({"title": title, "updated_at": _now()})
                .eq("id", session_id).eq("user_id", ctx.user_id).execute()
            )
            return bool(result.data)

        return await self._run(do, "renombrado de sesion")

    async def append_message(self, ctx: RequestContext, *, session_id: str, role: str, content: str,
                             metadata: Optional[MessageMetadata] = None) -> StoredMessage:
        def do():
            self._owned_row(ctx, session_id)
            record = {
                "session_id": session_id, "content": content, "role": role,
                "metadata": (metadata or MessageMetadata()).model_dump(mode="json", exclude_none=True),
                "created_at": _now(),
            }
            result = self._client.table("chat_messages").insert(record).execute()
            if not result.data:
                raise ProviderUnavailable("No se pudo guardar el mensaje")
            return _message(result.data[0])

        return await self._run(do, "guardado de mensaje")

    async def list_messages(self, ctx: RequestContext, *, session_id: str) -> List[StoredMessage]:
        def do():
            self._owned_row(ctx, session_id)
            result = (
                self._client.table("chat_messages").select("id, session_id, content, role, metadata, created_at")
                .eq("session_id", session_id).order("created_at", desc=False).execute()
            )
            return [_message(r) for r in (result.data or [])]

        return await self._run(do, "lectura de mensajes")
