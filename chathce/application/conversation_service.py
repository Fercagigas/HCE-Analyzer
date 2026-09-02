"""ConversationService: sesiones, historial y persistencia del turno (movido de ui/unified_chat_interface.py)."""

from __future__ import annotations

from typing import Any, List, Optional

from chathce.domain.chat import ChatMessageIn, ChatResponse, ToolCallSummary
from chathce.domain.context import RequestContext
from chathce.domain.conversation import AnalysisRecord, ConversationSession, MessageMetadata, StoredMessage, classify_analysis
from chathce.ports.llm_provider import LLMMessage

MAX_HISTORY_CHARS = 40_000
MAX_MESSAGE_CHARS = 8_000


def default_title(message: str) -> str:
    text = " ".join(message.split())
    return (text[:57] + "...") if len(text) > 60 else (text or "Nueva conversación")


def stored_to_chat_messages(messages: List[StoredMessage]) -> List[ChatMessageIn]:
    out: List[ChatMessageIn] = []
    for m in messages:
        summaries = None
        if m.role == "assistant" and m.metadata.tools_used:
            summaries = [ToolCallSummary(tool_name=t, tool_use_id="", operation="", success=True) for t in m.metadata.tools_used]
        out.append(ChatMessageIn(role=m.role, content=m.content, tool_summaries=summaries))
    return out


def to_llm_history(messages: List[ChatMessageIn], *, max_messages: int, char_budget: int = MAX_HISTORY_CHARS) -> List[LLMMessage]:
    """Replay resumido: texto de cada turno mas la lista de herramientas usadas. Nunca datos de tools antiguos."""
    recent = messages[-max_messages:] if max_messages > 0 else []
    history: List[LLMMessage] = []
    used = 0
    for m in reversed(recent):
        text = m.content[:MAX_MESSAGE_CHARS]
        if m.role == "assistant" and m.tool_summaries:
            tools = sorted({s.tool_name for s in m.tool_summaries if s.tool_name})
            if tools:
                text += "\n\n[Herramientas usadas en este turno: " + ", ".join(tools) + "]"
        if used + len(text) > char_budget:
            break
        used += len(text)
        history.append(LLMMessage.user_text(text) if m.role == "user" else LLMMessage.assistant_text(text))
    history.reverse()
    # Anthropic exige alternancia y que el primer mensaje sea del usuario
    normalized: List[LLMMessage] = []
    for msg in history:
        if not normalized and msg.role != "user":
            continue
        if normalized and normalized[-1].role == msg.role:
            merged = normalized[-1].text() + "\n\n" + msg.text()
            normalized[-1] = LLMMessage.user_text(merged) if msg.role == "user" else LLMMessage.assistant_text(merged)
            continue
        normalized.append(msg)
    if normalized and normalized[-1].role == "user":
        normalized.pop()  # el mensaje actual del usuario se anade despues
    return normalized


class ConversationService:
    def __init__(self, conversations: Optional[Any], analyses: Optional[Any] = None):
        self._conversations = conversations
        self._analyses = analyses

    @property
    def enabled(self) -> bool:
        return self._conversations is not None

    async def ensure_session(self, ctx: RequestContext, *, first_message: str) -> Optional[ConversationSession]:
        if not self.enabled:
            return None
        if ctx.session_id:
            existing = await self._conversations.get_session(ctx, session_id=ctx.session_id)
            if existing is not None:
                return existing
        return await self._conversations.create_session(ctx, title=default_title(first_message))

    async def load_history(self, ctx: RequestContext, *, session_id: str) -> List[ChatMessageIn]:
        if not self.enabled:
            return []
        try:
            return stored_to_chat_messages(await self._conversations.list_messages(ctx, session_id=session_id))
        except Exception:  # noqa: BLE001 - historial no disponible no bloquea el chat
            return []

    async def list_sessions(self, ctx: RequestContext, *, limit: int = 3) -> List[ConversationSession]:
        return await self._conversations.list_sessions(ctx, limit=limit) if self.enabled else []

    async def persist_turn(self, ctx: RequestContext, *, session_id: str, user_message: str, response: ChatResponse) -> None:
        if not self.enabled:
            return
        tools_used = sorted({t.tool_name for t in response.tool_calls})
        try:
            await self._conversations.append_message(ctx, session_id=session_id, role="user", content=user_message)
            await self._conversations.append_message(
                ctx, session_id=session_id, role="assistant", content=response.content,
                metadata=MessageMetadata(
                    tools_used=tools_used,
                    sources=[{"filename": s.filename, "page": s.page, "specialty": s.specialty, "doc_type": s.doc_type} for s in response.sources],
                    execution_time_ms=response.metadata.latency_ms, has_visualization=bool(response.visualizations),
                    model_used=response.metadata.model_used, trace_id=response.metadata.trace_id,
                ),
            )
        except Exception:  # noqa: BLE001
            return
        if self._analyses is not None:
            await self._analyses.save(ctx, AnalysisRecord(
                user_id=ctx.user_id, analysis_type=classify_analysis(tools_used), content=user_message,
                results={"tools_used": tools_used, "execution_time_ms": response.metadata.latency_ms,
                         "has_visualization": bool(response.visualizations), "model_used": response.metadata.model_used,
                         "sources": [s.filename for s in response.sources], "session_id": session_id,
                         "trace_id": response.metadata.trace_id},
            ))
