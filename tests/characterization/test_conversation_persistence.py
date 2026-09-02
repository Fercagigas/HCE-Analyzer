"""Caracterizacion de la persistencia de conversaciones (`AuthService` legacy).

Fija: tablas `chat_sessions`/`chat_messages`, allowlist de metadata del mensaje
del asistente, orden de lectura y la clasificacion de `analysis_type` que hoy vive
en `ui/unified_chat_interface.py::_save_analysis`. WP7/WP8 deben conservar estas
reglas en `ConversationRepository` / `ConversationService.classify_analysis`.
"""

import pytest

from tests.fakes.fake_supabase import FakeSupabaseClient
from tests.fakes.legacy_factories import make_auth_service

METADATA_ALLOWLIST = {"tools_used", "sources", "execution_time_ms", "has_visualization", "model_used"}


@pytest.fixture
def client() -> FakeSupabaseClient:
    return FakeSupabaseClient()


def test_create_session_inserts_into_chat_sessions(client):
    service = make_auth_service(client)

    ok, session = service.create_chat_session("user-1", "Chat de prueba")

    assert ok is True
    assert session["user_id"] == "user-1"
    assert session["title"] == "Chat de prueba"
    assert "id" in session
    rows = client.rows("chat_sessions")
    assert len(rows) == 1 and set(rows[0]) >= {"user_id", "title", "created_at", "updated_at"}


def test_save_message_applies_metadata_allowlist(client):
    service = make_auth_service(client)
    metadata = {
        "tools_used": ["query_mimic_database"],
        "sources": [{"filename": "guia.pdf"}],
        "execution_time_ms": 1200,
        "has_visualization": False,
        "model_used": "claude-haiku-4-5-20251001",
        "raw_output": {"data": "no debe persistirse"},
        "image": "data:image/png;base64,AAAA",
    }

    assert service.save_message("session-1", "Respuesta", "assistant", metadata=metadata) is True

    stored = client.rows("chat_messages")[0]
    assert stored["session_id"] == "session-1"
    assert stored["role"] == "assistant"
    assert stored["content"] == "Respuesta"
    assert set(stored["metadata"]) == METADATA_ALLOWLIST
    assert "raw_output" not in stored["metadata"] and "image" not in stored["metadata"]


def test_user_message_without_metadata_stores_empty_metadata(client):
    service = make_auth_service(client)
    assert service.save_message("session-1", "Hola", "user") is True
    assert client.rows("chat_messages")[0]["metadata"] == {}


def test_get_session_messages_returns_chronological_order(client):
    service = make_auth_service(client)
    client.rows("chat_messages").extend([
        {"id": "m2", "session_id": "s", "content": "segundo", "role": "assistant", "metadata": {}, "created_at": "2026-01-01T10:00:01"},
        {"id": "m1", "session_id": "s", "content": "primero", "role": "user", "metadata": {}, "created_at": "2026-01-01T10:00:00"},
        {"id": "x", "session_id": "otra", "content": "ajeno", "role": "user", "metadata": {}, "created_at": "2026-01-01T09:00:00"},
    ])

    ok, messages = service.get_session_messages("s")

    assert ok is True
    assert [m["content"] for m in messages] == ["primero", "segundo"]
    assert set(messages[0]) == {"id", "session_id", "content", "role", "metadata", "created_at"}


def test_get_user_sessions_caps_limit_at_three(client):
    service = make_auth_service(client)
    for i in range(5):
        client.rows("chat_sessions").append(
            {"id": f"s{i}", "user_id": "u", "title": f"t{i}", "created_at": "2026", "updated_at": f"2026-01-0{i + 1}"}
        )

    ok, sessions = service.get_user_sessions("u", limit=10)

    assert ok is True
    assert [s["id"] for s in sessions] == ["s4", "s3", "s2"]


def legacy_classify_analysis(tools_used) -> str:
    """Copia literal de la regla de ui/unified_chat_interface.py::_save_analysis."""
    if len(tools_used) > 1:
        return "mixed"
    if "query_mimic_database" in tools_used or "database" in str(tools_used).lower():
        return "database_query"
    if "rag" in str(tools_used).lower():
        return "rag_search"
    if "visualization" in str(tools_used).lower():
        return "visualization"
    return "general"


ANALYSIS_TYPE_CASES = [
    ([], "general"),
    (["query_mimic_database"], "database_query"),
    (["search_clinical_documents"], "general"),  # hoy no contiene 'rag': queda como general
    (["request_visualization"], "visualization"),
    (["query_mimic_database", "search_clinical_documents"], "mixed"),
    (["rag_tool"], "rag_search"),
]


@pytest.mark.parametrize("tools_used, expected", ANALYSIS_TYPE_CASES)
def test_analysis_type_classification_contract(tools_used, expected):
    """Tabla de referencia que `ConversationService.classify_analysis` debe reproducir (WP8)."""
    assert legacy_classify_analysis(tools_used) == expected
