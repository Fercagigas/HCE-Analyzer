"""Contrato de los repositorios Supabase (conversacion, analisis, preferencias) sobre el cliente en memoria."""

import pytest

from chathce.adapters.memory.postgrest_client import InMemoryPostgrestClient
from chathce.adapters.supabase.analysis_repository import SupabaseAnalysisRepository
from chathce.adapters.supabase.conversation_repository import SupabaseConversationRepository
from chathce.adapters.supabase.user_preferences_repository import DEFAULT_PREFERENCES, SupabaseUserPreferencesRepository
from chathce.domain.context import Channel, RequestContext
from chathce.domain.conversation import AnalysisRecord, MessageMetadata
from chathce.domain.errors import NotFound
from chathce.ports import AnalysisRepository, ConversationRepository, UserPreferencesRepository

pytestmark = pytest.mark.contract

LEGACY_METADATA_ALLOWLIST = {"tools_used", "sources", "execution_time_ms", "has_visualization", "model_used"}


def _ctx(user="u1") -> RequestContext:
    return RequestContext(user_id=user, channel=Channel.api)


@pytest.fixture
def client() -> InMemoryPostgrestClient:
    return InMemoryPostgrestClient()


async def test_conversation_repository_round_trip_and_isolation(client):
    repo = SupabaseConversationRepository(client)
    assert isinstance(repo, ConversationRepository)
    owner, other = _ctx("owner"), _ctx("other")

    session = await repo.create_session(owner, title="Chat 1")
    assert session.user_id == "owner" and session.title == "Chat 1"
    stored = await repo.append_message(owner, session_id=session.session_id, role="user", content="hola")
    assert stored.role == "user" and stored.session_id == session.session_id
    meta = MessageMetadata(tools_used=["get_labs"], execution_time_ms=120, model_used="m", trace_id="t" * 8)
    await repo.append_message(owner, session_id=session.session_id, role="assistant", content="respuesta", metadata=meta)

    messages = await repo.list_messages(owner, session_id=session.session_id)
    assert [m.content for m in messages] == ["hola", "respuesta"]
    assert messages[1].metadata.tools_used == ["get_labs"] and messages[1].metadata.trace_id == "t" * 8
    persisted = client.rows("chat_messages")[1]["metadata"]
    assert set(persisted) <= LEGACY_METADATA_ALLOWLIST | {"trace_id"}

    with pytest.raises(NotFound):
        await repo.list_messages(other, session_id=session.session_id)
    assert await repo.get_session(other, session_id=session.session_id) is None
    assert await repo.delete_session(other, session_id=session.session_id) is False
    assert await repo.rename_session(owner, session_id=session.session_id, title="Nuevo") is True
    assert (await repo.get_session(owner, session_id=session.session_id)).title == "Nuevo"
    assert await repo.delete_session(owner, session_id=session.session_id) is True


async def test_conversation_list_is_capped_at_three_most_recent(client):
    repo = SupabaseConversationRepository(client)
    for i in range(5):
        client.rows("chat_sessions").append({"id": f"s{i}", "user_id": "u", "title": f"t{i}", "created_at": "2026", "updated_at": f"2026-01-0{i + 1}"})
    sessions = await repo.list_sessions(_ctx("u"), limit=10)
    assert [s.session_id for s in sessions] == ["s4", "s3", "s2"]


async def test_legacy_metadata_rows_are_read_with_allowlist(client):
    repo = SupabaseConversationRepository(client)
    client.rows("chat_sessions").append({"id": "s", "user_id": "u", "title": "t", "created_at": "2026", "updated_at": "2026"})
    client.rows("chat_messages").append({"id": "m", "session_id": "s", "role": "assistant", "content": "x",
                                         "metadata": {"tools_used": ["a"], "raw_output": {"secret": 1}}, "created_at": "2026-01-01T00:00:00"})
    messages = await repo.list_messages(_ctx("u"), session_id="s")
    assert messages[0].metadata.tools_used == ["a"]
    assert not hasattr(messages[0].metadata, "raw_output")


async def test_analysis_repository_saves_and_aggregates(client):
    repo = SupabaseAnalysisRepository(client)
    assert isinstance(repo, AnalysisRepository)
    ctx = _ctx("u")
    assert await repo.save(ctx, AnalysisRecord(user_id="u", analysis_type="database_query", content="q", results={"tools_used": ["get_labs"]}))
    assert await repo.save(ctx, AnalysisRecord(user_id="u", analysis_type="mixed", content="q2"))
    await repo.save(_ctx("other"), AnalysisRecord(user_id="other", analysis_type="general", content="z"))
    stats = await repo.stats(ctx)
    assert stats == {"total_analyses": 2, "by_type": {"database_query": 1, "mixed": 1}}


async def test_user_preferences_merge_defaults_and_upsert(client):
    repo = SupabaseUserPreferencesRepository(client)
    assert isinstance(repo, UserPreferencesRepository)
    ctx = _ctx("u")
    assert await repo.load(ctx) == DEFAULT_PREFERENCES
    assert await repo.save(ctx, {"theme": "dark", "max_context_messages": 5}) is True
    loaded = await repo.load(ctx)
    assert loaded["theme"] == "dark" and loaded["max_context_messages"] == 5 and loaded["show_sources"] is True
