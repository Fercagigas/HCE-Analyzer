from datetime import timedelta

import pytest

from chathce.adapters.memory import (
    FakeLLMProvider,
    InMemoryConversationRepository,
    InMemoryIdentityProvider,
    InMemoryVisualizationRepository,
    ScriptedTurn,
)
from chathce.domain.context import Channel, RequestContext
from chathce.domain.errors import AuthenticationFailed, NotFound
from chathce.domain.identity import Principal
from chathce.ports import ClinicalDataProvider, ConversationRepository, IdentityProvider, LLMProvider
from chathce.ports.llm_provider import LLMMessage, LLMMessageEnd, LLMTextDelta, LLMToolUseEnd, LLMUnavailable

pytestmark = pytest.mark.unit


def _ctx(user_id="u1", **kw) -> RequestContext:
    return RequestContext(user_id=user_id, channel=Channel.api, **kw)


async def _collect(agen):
    return [event async for event in agen]


async def test_fake_llm_provider_emits_text_then_tool_use_then_end():
    provider = FakeLLMProvider([ScriptedTurn(text="Consulto labs", tool_calls=[("get_labs", {"subject_id": 1})])])
    assert isinstance(provider, LLMProvider)

    events = await _collect(provider.generate([LLMMessage.user_text("hola")], tools=[], system="s", model="m", max_tokens=10))

    assert isinstance(events[0], LLMTextDelta)
    tool_end = next(e for e in events if isinstance(e, LLMToolUseEnd))
    assert tool_end.name == "get_labs" and tool_end.input == {"subject_id": 1}
    end = events[-1]
    assert isinstance(end, LLMMessageEnd) and end.stop_reason == "tool_use"
    assert [p.type for p in end.assistant_parts] == ["text", "tool_use"]
    assert provider.calls[0].system == "s" and provider.remaining == 0


async def test_fake_llm_provider_raises_scripted_errors():
    provider = FakeLLMProvider([LLMUnavailable("caido"), ScriptedTurn(text="ok")])
    with pytest.raises(LLMUnavailable):
        await _collect(provider.generate([], tools=[], system="", model="m", max_tokens=1))
    events = await _collect(provider.generate([], tools=[], system="", model="m", max_tokens=1))
    assert events[-1].stop_reason == "end_turn"


async def test_identity_provider_verifies_revokes_and_refreshes():
    identity = InMemoryIdentityProvider()
    assert isinstance(identity, IdentityProvider)
    identity.add_user("a@b.c", "pw", Principal(user_id="u1", roles=frozenset({"researcher"})))

    session = await identity.login("a@b.c", "pw")
    principal = await identity.verify_access_token(session.access_token)
    assert principal.user_id == "u1" and "researcher" in principal.roles

    refreshed = await identity.refresh(session.refresh_token)
    assert refreshed.access_token != session.access_token
    with pytest.raises(AuthenticationFailed):
        await identity.refresh(session.refresh_token)  # rotacion: un solo uso

    await identity.logout(session.access_token)
    with pytest.raises(AuthenticationFailed):
        await identity.verify_access_token(session.access_token)
    with pytest.raises(AuthenticationFailed):
        await identity.login("a@b.c", "mal")


async def test_conversation_repository_isolates_users():
    repo = InMemoryConversationRepository()
    assert isinstance(repo, ConversationRepository)
    owner, other = _ctx("owner"), _ctx("other")
    session = await repo.create_session(owner, title="t")
    await repo.append_message(owner, session_id=session.session_id, role="user", content="hola")

    assert len(await repo.list_messages(owner, session_id=session.session_id)) == 1
    with pytest.raises(NotFound):
        await repo.list_messages(other, session_id=session.session_id)
    assert await repo.get_session(other, session_id=session.session_id) is None
    assert await repo.delete_session(other, session_id=session.session_id) is False
    assert await repo.delete_session(owner, session_id=session.session_id) is True


async def test_visualization_repository_scopes_by_user_and_expires():
    repo = InMemoryVisualizationRepository(ttl_minutes=30)
    owner, other = _ctx("owner", session_id="s1"), _ctx("other")
    artifact = repo.new_artifact(owner, title="Labs", viz_type="timeline", figure_json="{}")
    await repo.put(owner, artifact)

    assert (await repo.get(owner, artifact.viz_id)) is not None
    assert (await repo.get(other, artifact.viz_id)) is None
    assert len(await repo.list_for_session(owner, "s1")) == 1

    expired = artifact.model_copy(update={"viz_id": "viz_old", "expires_at": artifact.created_at - timedelta(seconds=1)})
    await repo.put(owner, expired)
    assert (await repo.get(owner, "viz_old")) is None


def test_clinical_data_provider_protocol_is_runtime_checkable():
    class Incomplete:
        source_name = "x"

    assert not isinstance(Incomplete(), ClinicalDataProvider)
