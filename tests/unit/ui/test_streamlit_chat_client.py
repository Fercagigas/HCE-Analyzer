"""StreamlitChatClient y LegacyAuthServiceAdapter sobre el contenedor de fakes."""

import pytest

from chathce.adapters.memory import ScriptedTurn
from chathce.streamlit_adapter.chat_client import StreamlitChatClient
from chathce.streamlit_adapter.legacy_services import LegacyAuthServiceAdapter
from tests.fakes.container_factory import build_test_container
from tests.fakes.mimic_fixtures import fixtures_available, load_manifest

pytestmark = [pytest.mark.unit, pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")]

SUBJECT = load_manifest()["subject_ids"][0] if fixtures_available() else 0


def test_send_persists_turn_and_returns_session_id():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("get_diagnoses", {"subject_id": SUBJECT})]), ScriptedTurn(text="Diagnósticos listados."),
    ])
    client = StreamlitChatClient(container)
    result = client.send("dx", user_id="u1", roles=["clinician"], session_id=None, patient_id=str(SUBJECT), encounter_id=None,
                         research_mode=False, options={"show_sources": True, "enable_visualizations": True, "max_context_messages": 10})
    assert result["success"] and result["tools_used"] == ["get_diagnoses"] and result["session_id"]

    adapter = LegacyAuthServiceAdapter(container, lambda: "u1")
    ok, sessions = adapter.get_user_sessions("u1", limit=3)
    assert ok and sessions[0]["id"] == result["session_id"] and sessions[0]["title"] == "dx"
    ok, messages = adapter.get_session_messages(result["session_id"])
    assert ok and [m["role"] for m in messages] == ["user", "assistant"] and messages[1]["metadata"]["tools_used"] == ["get_diagnoses"]
    stats = adapter.get_user_stats("u1")
    assert stats["total_sessions"] == 1 and stats["total_messages"] == 2
    assert adapter.get_analysis_stats("u1")["total_analyses"] == 1


def test_research_mode_requires_role():
    container = build_test_container([ScriptedTurn(text="ok")])
    client = StreamlitChatClient(container)
    denied = client.send("stats", user_id="u1", roles=["clinician"], session_id=None, patient_id=None, encounter_id=None, research_mode=True)
    assert denied["success"] is False and denied["error_type"] == "PURPOSE_NOT_ALLOWED"
    allowed = client.send("stats", user_id="u2", roles=["researcher"], session_id=None, patient_id=None, encounter_id=None, research_mode=True)
    assert allowed["success"] is True


def test_figure_json_is_scoped_to_user():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("create_visualization", {"visualization_type": "timeline", "source": "labs", "subject_id": SUBJECT})]),
        ScriptedTurn(text="grafica"),
    ])
    client = StreamlitChatClient(container)
    result = client.send("grafica", user_id="u1", roles=[], session_id=None, patient_id=str(SUBJECT), encounter_id=None, research_mode=False)
    viz_id = result["visualizations"][0]["ids"][0]
    assert client.figure_json(user_id="u1", viz_id=viz_id).startswith("{")
    assert client.figure_json(user_id="otro", viz_id=viz_id) is None
