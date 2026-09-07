"""Port de conversaciones (sesiones y mensajes). Todas las lecturas exigen el usuario del contexto."""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from chathce.domain.context import RequestContext
from chathce.domain.conversation import ConversationSession, MessageMetadata, StoredMessage


@runtime_checkable
class ConversationRepository(Protocol):
    async def create_session(self, ctx: RequestContext, *, title: str) -> ConversationSession: ...

    async def list_sessions(self, ctx: RequestContext, *, limit: int = 3) -> List[ConversationSession]: ...

    async def get_session(self, ctx: RequestContext, *, session_id: str) -> Optional[ConversationSession]: ...

    async def delete_session(self, ctx: RequestContext, *, session_id: str) -> bool: ...

    async def rename_session(self, ctx: RequestContext, *, session_id: str, title: str) -> bool: ...

    async def append_message(
        self,
        ctx: RequestContext,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[MessageMetadata] = None,
    ) -> StoredMessage: ...

    async def list_messages(self, ctx: RequestContext, *, session_id: str) -> List[StoredMessage]: ...
