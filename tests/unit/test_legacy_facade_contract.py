"""Contrato legacy `process_message(...) -> dict` preservado por LegacyAgentFacade / UnifiedChatAgent (caracterizado en WP1)."""

import pytest

from chathce.adapters.memory import ScriptedTurn
from chathce.legacy.agent_facade import LegacyAgentFacade
from tests.fakes.container_factory import build_test_container
from tests.fakes.mimic_fixtures import fixtures_available, load_manifest

pytestmark = [pytest.mark.unit, pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")]

SUBJECT = load_manifest()["subject_ids"][0] if fixtures_available() else 0
LEGACY_KEYS = {"success", "content", "tools_used", "tool_results", "visualizations", "sources", "tokens_used", "model_used", "metadata"}


def test_plain_answer_keeps_legacy_shape():
    facade = LegacyAgentFacade(build_test_container([ScriptedTurn(text="Hola")]))
    result = facade.process_message("hola", context=None, session_id="eval-1")
    assert LEGACY_KEYS <= set(result)
    assert result["success"] is True and result["content"] == "Hola"
    assert result["tools_used"] == [] and result["visualizations"] == [] and result["sources"] == []
    assert isinstance(result["tokens_used"], int) and result["model_used"] == "fake-primary"
    assert result["metadata"]["query_length"] == 4 and result["metadata"]["trace_id"]


def test_tool_call_is_summarized_never_raw_data():
    facade = LegacyAgentFacade(build_test_container([
        ScriptedTurn(tool_calls=[("get_labs", {"subject_id": SUBJECT, "limit": 3})]), ScriptedTurn(text="3 labs."),
    ]))
    result = facade.process_message("labs", session_id="s", patient_id=str(SUBJECT))
    assert result["tools_used"] == ["get_labs"]
    tool_result = result["tool_results"][0]
    assert tool_result["tool"] == "get_labs" and tool_result["success"] and tool_result["count"] == 3
    assert isinstance(tool_result["raw_output"], str) and "<tool_data" in tool_result["raw_output"]
    assert tool_result["summary"].startswith("[DATOS: get_labs]")


def test_scope_required_without_patient():
    facade = LegacyAgentFacade(build_test_container([
        ScriptedTurn(tool_calls=[("get_labs", {"subject_id": SUBJECT})]), ScriptedTurn(text="Necesito el paciente activo."),
    ]))
    result = facade.process_message("labs", session_id="s")  # sin patient_id
    assert result["success"] is True
    assert result["tool_results"][0]["success"] is False and result["tool_results"][0]["error_code"] == "scope_refused"
    assert result["uncertainty"]["scope_refusals"]


def test_legacy_context_list_is_replayed():
    container = build_test_container([ScriptedTurn(text="ok")])
    facade = LegacyAgentFacade(container)
    context = [
        {"role": "user", "content": "antes"},
        {"role": "assistant", "content": {"content": "respuesta previa", "tool_results": [{"tool": "get_labs"}]}},
    ]
    facade.process_message("ahora", context=context, session_id="s", patient_id=str(SUBJECT))
    sent = container.llm_provider.calls[0].messages
    assert [m.role for m in sent] == ["user", "assistant", "user"]
    assert "Herramientas usadas en este turno: get_labs" in sent[1].text()


def test_non_list_context_is_ignored():
    facade = LegacyAgentFacade(build_test_container([ScriptedTurn(text="ok")]))
    result = facade.process_message("hola", context={"_eval_run_id": "x"}, session_id="s")
    assert result["success"] is True


def test_research_purpose_is_granted_to_legacy_runtime():
    facade = LegacyAgentFacade(build_test_container([
        ScriptedTurn(tool_calls=[("get_dataset_statistics", {"statistic": "dataset_summary"})]), ScriptedTurn(text="100 pacientes"),
    ]))
    result = facade.process_message("cuantos pacientes", session_id="s", purpose="research")
    assert result["tool_results"][0]["success"] is True


def test_visualization_ids_point_to_core_repository():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("create_visualization", {"visualization_type": "timeline", "source": "labs", "subject_id": SUBJECT})]),
        ScriptedTurn(text="grafica"),
    ])
    facade = LegacyAgentFacade(container)
    result = facade.process_message("grafica", session_id="s", patient_id=str(SUBJECT))
    assert result["visualizations"] and result["visualizations"][0]["type"] == "visualization_ids"
    viz_id = result["visualizations"][0]["ids"][0]
    from chathce.domain.context import Channel, RequestContext

    artifact = container.run(container.visualizations.get(RequestContext(user_id="legacy-runtime", channel=Channel.evaluation), viz_id))
    assert artifact is not None and artifact.figure_json.startswith("{")


def test_unified_chat_agent_facade_accepts_injected_container():
    from services.unified_chat.unified_agent import UnifiedChatAgent, create_unified_agent

    agent = create_unified_agent(build_test_container([ScriptedTurn(text="hola")]))
    assert isinstance(agent, UnifiedChatAgent)
    assert agent.process_message("hola", session_id="s")["content"] == "hola"
    assert agent.get_performance_stats()["engine"] == "chathce.gateway"
