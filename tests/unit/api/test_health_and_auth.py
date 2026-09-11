import pytest

from tests.unit.api.conftest import auth

pytestmark = pytest.mark.unit


async def test_health_is_public_and_carries_correlation_headers(client):
    response = await client.get("/health")
    assert response.status_code == 200 and response.json()["status"] == "ok"
    assert response.headers["X-Trace-Id"] and response.headers["X-Request-Id"]
    assert response.headers["X-Content-Type-Options"] == "nosniff" and response.headers["Cache-Control"] == "no-store"


async def test_incoming_trace_id_is_propagated(client):
    response = await client.get("/health", headers={"X-Trace-Id": "trace-abc-12345"})
    assert response.headers["X-Trace-Id"] == "trace-abc-12345"
    bad = await client.get("/health", headers={"X-Trace-Id": "x y z"})
    assert bad.headers["X-Trace-Id"] != "x y z"


async def test_ready_reports_components(client, api):
    response = await client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready" and {c["name"] for c in body["components"]} == {"clinical_data", "llm", "knowledge", "identity", "ai_generation"}
    api.container.llm_provider.healthy = False
    api.app.state.ready_cache = None
    degraded = await client.get("/ready")
    assert degraded.status_code == 503 and degraded.json()["status"] == "degraded"


async def test_chat_requires_bearer_token(client):
    response = await client.post("/api/v1/chat", json={"message": "hola"})
    assert response.status_code == 401
    body = response.json()["error"]
    assert body["code"] == "AUTH_REQUIRED" and body["trace_id"] and body["request_id"]


async def test_invalid_token_is_rejected(client):
    response = await client.post("/api/v1/chat", json={"message": "hola"}, headers=auth("tok-nope"))
    assert response.status_code == 401 and response.json()["error"]["code"] == "AUTH_INVALID_TOKEN"


async def test_http_requests_are_audited_without_phi(client, api):
    await client.post("/api/v1/chat", json={"message": "dato sensible"}, headers=auth())
    events = [e for e in api.container.audit.events if e.action.value == "http_request"]
    assert events and events[-1].attributes["route_template"] == "/api/v1/chat" and events[-1].user_id.startswith("TOKEN_")
    assert "dato sensible" not in "".join(e.model_dump_json() for e in api.container.audit.events)


async def test_admin_can_manage_roles_and_relationships_but_clinician_cannot(client, api):
    denied = await client.put("/api/v1/admin/users/u2/roles", json={"roles": ["reviewer"]}, headers=auth())
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "AUTHORIZATION_DENIED"
    assigned = await client.put("/api/v1/admin/users/u2/roles", json={"roles": ["reviewer"]}, headers=auth("tok-admin"))
    granted = await client.put("/api/v1/admin/patient-access", json={"user_id": "u2", "subject_id": api.subject,
                                                                        "service_id": "cardiology"}, headers=auth("tok-admin"))
    assert assigned.status_code == 204 and granted.status_code == 204
    events = [e for e in api.container.audit.events if e.action.value == "authorization_changed"]
    assert len(events) == 2 and all("u2" not in e.model_dump_json() for e in events)
