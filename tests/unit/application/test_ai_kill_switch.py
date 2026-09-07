import json

import pytest

from chathce.adapters.memory import ScriptedTurn
from chathce.application.ai_kill_switch import AIGenerationGate
from chathce.domain.chat import ChatRequest, CompleteEvent, ErrorEvent
from chathce.domain.context import Channel, build_context
from tests.fakes.container_factory import build_test_container

pytestmark = pytest.mark.unit


def _ctx():
    return build_context(user_id="clin-1", channel=Channel.api, patient_id="10001217")


async def test_kill_switch_returns_degraded_response_without_llm_or_tools():
    container = build_test_container([ScriptedTurn(text="no debe usarse")])
    container.ai_gate = AIGenerationGate(enabled=False)
    container.chat_service._ai_gate = container.ai_gate

    events = [event async for event in container.chat_service.stream_chat(ChatRequest(message="hola"), _ctx())]
    assert isinstance(events[0], ErrorEvent) and events[0].error.code == "AI_DISABLED"
    assert isinstance(events[-1], CompleteEvent)
    assert events[-1].response.success is False and "deshabilitada" in events[-1].response.content
    assert container.llm_provider.calls == []
    assert container.audit.actions() == ["chat_started", "ai_kill_switch_rejected"]


async def test_runtime_kill_switch_change_is_audited_without_request_content(tmp_path):
    flag = tmp_path / "ai.flag"
    flag.write_text("enabled", encoding="utf-8")
    container = build_test_container([ScriptedTurn(text="primera"), ScriptedTurn(text="no debe usarse")])
    container.ai_gate = AIGenerationGate(state_file=str(flag))
    container.chat_service._ai_gate = container.ai_gate
    await container.chat_service.handle_chat(ChatRequest(message="hola"), _ctx())
    flag.write_text("disabled", encoding="utf-8")
    response = await container.chat_service.handle_chat(ChatRequest(message="dato clinico sensible"), _ctx())

    assert response.error.code == "AI_DISABLED" and len(container.llm_provider.calls) == 1
    changed = [e for e in container.audit.events if e.action.value == "ai_kill_switch_changed"]
    rejected = [e for e in container.audit.events if e.action.value == "ai_kill_switch_rejected"]
    assert changed and rejected and changed[-1].attributes == {"reason": "runtime_file"}
    assert "dato clinico sensible" not in json.dumps(rejected[-1].model_dump(), default=str)
