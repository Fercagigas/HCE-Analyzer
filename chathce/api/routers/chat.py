"""POST /api/v1/chat (JSON) y POST /api/v1/chat/stream (SSE)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sse_starlette import EventSourceResponse

from chathce.api.dependencies import get_container, get_principal, make_context
from chathce.api.sse import chat_event_stream
from chathce.composition.container import Container
from chathce.domain.chat import ChatRequest, ChatResponse
from chathce.domain.identity import Principal

router = APIRouter(prefix="/api/v1", tags=["chat"])


def _context(request: Request, principal: Principal, body: ChatRequest):
    return make_context(request, principal, patient_id=body.patient_id, encounter_id=body.encounter_id,
                        session_id=body.session_id, purpose=body.purpose)


@router.post("/chat", response_model=ChatResponse, response_model_exclude_none=True)
async def chat(request: Request, body: ChatRequest, principal: Principal = Depends(get_principal),
               container: Container = Depends(get_container)) -> ChatResponse:
    ctx = _context(request, principal, body)
    return await container.chat_service.handle_chat(body, ctx)


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest, principal: Principal = Depends(get_principal),
                      container: Container = Depends(get_container)) -> EventSourceResponse:
    ctx = _context(request, principal, body)
    ping = getattr(request.app.state, "sse_ping_s", 15)
    return EventSourceResponse(
        chat_event_stream(container.chat_service, body, ctx, request),
        ping=ping, send_timeout=60, headers={"Cache-Control": "no-cache", "X-Trace-Id": ctx.trace_id, "X-Request-Id": ctx.request_id},
    )
