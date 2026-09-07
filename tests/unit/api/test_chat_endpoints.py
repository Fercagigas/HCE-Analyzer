import json

import pytest

from chathce.adapters.memory import ScriptedTurn
from tests.unit.api.conftest import SUBJECT, auth

pytestmark = pytest.mark.unit


async def test_chat_json_returns_chat_response(client):
    response = await client.post("/api/v1/chat", json={"message": "hola", "patient_id": str(SUBJECT)}, headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True and body["content"] == "Hola desde la API"
    assert body["metadata"]["trace_id"] == response.headers["X-Trace-Id"]
    assert body["metadata"]["session_id"]


async def test_chat_rejects_unknown_fields_and_empty_message(client):
    response = await client.post("/api/v1/chat", json={"message": "hola", "sql": "select 1"}, headers=auth())
    assert response.status_code == 422 and response.json()["error"]["code"] == "VALIDATION_ERROR"
    response = await client.post("/api/v1/chat", json={"message": ""}, headers=auth())
    assert response.status_code == 422


async def test_research_purpose_requires_researcher_role(client):
    denied = await client.post("/api/v1/chat", json={"message": "top farmacos", "purpose": "research"}, headers=auth("tok-clinician"))
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "PURPOSE_NOT_ALLOWED"
    allowed = await client.post("/api/v1/chat", json={"message": "top farmacos", "purpose": "research"}, headers=auth("tok-researcher"))
    assert allowed.status_code == 200


@pytest.mark.parametrize("api", [[
    ScriptedTurn(text="Consulto", tool_calls=[("get_labs", {"subject_id": SUBJECT, "limit": 3})]),
    ScriptedTurn(text="Listo: 3 laboratorios."),
]], indirect=True)
async def test_chat_stream_emits_high_level_events(client):
    async with client.stream("POST", "/api/v1/chat/stream", json={"message": "labs", "patient_id": str(SUBJECT)}, headers=auth()) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        raw = ""
        async for chunk in response.aiter_text():
            raw += chunk
    events = []
    for block in raw.replace("\r\n", "\n").split("\n\n"):
        lines = [l for l in block.splitlines() if l and not l.startswith(":")]
        if not lines:
            continue
        fields = {}
        for line in lines:
            key, _, value = line.partition(": ")
            fields.setdefault(key, value)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    kinds = [k for k, _ in events]
    assert kinds[0] == "status" and kinds[-1] == "complete"
    assert "tool_call" in kinds and "tool_result_summary" in kinds and "text_delta" in kinds
    assert kinds.index("tool_call") < kinds.index("tool_result_summary") < kinds.index("complete")
    complete = events[-1][1]["response"]
    assert complete["success"] and complete["tool_calls"][0]["tool_name"] == "get_labs"
    for _, payload in events:
        assert not {"thinking", "reasoning", "chain_of_thought"} & set(payload)


async def test_patient_summary_endpoint_is_scoped_and_deterministic(client):
    response = await client.get(f"/api/v1/patients/{SUBJECT}/summary", headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert body["patient"]["subject_id"] == SUBJECT and body["stats"]["total_admissions"] >= 1
    missing = await client.get("/api/v1/patients/99999999/summary", headers=auth())
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("api", [[
    ScriptedTurn(tool_calls=[("create_visualization", {"visualization_type": "timeline", "source": "labs", "subject_id": SUBJECT})]),
    ScriptedTurn(text="grafica lista"),
]], indirect=True)
async def test_visualization_is_retrievable_only_by_owner(client):
    chat = await client.post("/api/v1/chat", json={"message": "grafica", "patient_id": str(SUBJECT)}, headers=auth())
    viz_id = chat.json()["visualizations"][0]["viz_id"]
    mine = await client.get(f"/api/v1/visualizations/{viz_id}", headers=auth())
    assert mine.status_code == 200 and mine.json()["format"] == "plotly_json" and "data" in mine.json()["figure"]
    other = await client.get(f"/api/v1/visualizations/{viz_id}", headers=auth("tok-researcher"))
    assert other.status_code == 404
