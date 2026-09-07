"""No existe cache de respuestas compartida entre usuarios (la legacy `unified_chat:{message}:{context}` se elimino)."""

import pytest

from chathce.adapters.memory import ScriptedTurn
from chathce.domain.chat import ChatRequest
from chathce.domain.context import Channel, RequestContext
from tests.fakes.container_factory import build_test_container

pytestmark = pytest.mark.security


async def test_same_message_from_two_users_hits_the_model_twice():
    container = build_test_container([ScriptedTurn(text="respuesta A"), ScriptedTurn(text="respuesta B")])
    a = await container.chat_service.handle_chat(ChatRequest(message="misma pregunta"), RequestContext(user_id="a", channel=Channel.api))
    b = await container.chat_service.handle_chat(ChatRequest(message="misma pregunta"), RequestContext(user_id="b", channel=Channel.api))
    assert a.content == "respuesta A" and b.content == "respuesta B"
    assert len(container.llm_provider.calls) == 2
    assert a.metadata.cached is False and b.metadata.cached is False
