"""Server-Sent Events: eventos de alto nivel del ChatService (nunca chain-of-thought)."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict

from starlette.requests import Request

from chathce.domain.chat import ChatRequest
from chathce.domain.context import RequestContext


async def chat_event_stream(chat_service: Any, request: ChatRequest, ctx: RequestContext, http_request: Request) -> AsyncIterator[Dict[str, str]]:
    seq = 0
    async for event in chat_service.stream_chat(request, ctx):
        if await http_request.is_disconnected():
            break
        seq += 1
        yield {"event": event.type, "data": event.model_dump_json(), "id": str(seq)}
