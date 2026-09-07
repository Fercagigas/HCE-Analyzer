"""Validacion de resultados de tools: limites de filas, tamano visible y filas fuera de scope (roadmap 07 P0.6)."""

import pytest

from chathce.domain.chat import ChatRequest
from chathce.domain.context import Channel, RequestContext
from chathce.adapters.memory import ScriptedTurn
from tests.fakes.container_factory import build_test_container
from tests.fakes.mimic_fixtures import fixtures_available, load_manifest

pytestmark = [pytest.mark.security, pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")]

SUBJECT = load_manifest()["subject_ids"][0] if fixtures_available() else 0


async def test_rows_are_capped_and_visible_text_is_bounded():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("get_labs", {"subject_id": SUBJECT, "limit": 200})]), ScriptedTurn(text="ok"),
    ])
    response = await container.chat_service.handle_chat(ChatRequest(message="todos los labs"), RequestContext(user_id="u", channel=Channel.api, patient_id=str(SUBJECT)))
    call = response.tool_calls[0]
    assert call.count <= 200
    delivered = container.llm_provider.calls[1].messages[-1].parts[0].content
    assert len(delivered) <= 4000 + 200  # max_visible_chars del contenedor de pruebas + envoltorio


async def test_invalid_arguments_are_rejected_before_execution():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("get_labs", {"subject_id": SUBJECT, "limit": 999999, "sql": "x"})]), ScriptedTurn(text="ok"),
    ])
    response = await container.chat_service.handle_chat(ChatRequest(message="labs"), RequestContext(user_id="u", channel=Channel.api, patient_id=str(SUBJECT)))
    assert response.tool_calls[0].error_code == "invalid_input"
    assert not any(e.action.value == "clinical_query" for e in container.audit.events)
