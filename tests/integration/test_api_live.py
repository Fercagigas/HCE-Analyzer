"""API en vivo: login real con un usuario de prueba (HCE_TEST_USER_EMAIL / HCE_TEST_USER_PASSWORD) y una pregunta."""

import os

import httpx
import pytest

from tests.fakes.mimic_fixtures import fixtures_available, load_manifest


@pytest.fixture(scope="module")
def credentials():
    email, password = os.environ.get("HCE_TEST_USER_EMAIL"), os.environ.get("HCE_TEST_USER_PASSWORD")
    if not email or not password:
        pytest.skip("HCE_TEST_USER_EMAIL / HCE_TEST_USER_PASSWORD no definidos")
    return email, password


async def test_login_chat_and_summary_live(integration_settings, credentials):
    from chathce.api.app import create_app
    from chathce.composition.container import build_container

    container = build_container(integration_settings)
    app = create_app(container)
    session = await container.identity.login(*credentials)
    headers = {"Authorization": f"Bearer {session.access_token}"}
    subject = load_manifest()["subject_ids"][0] if fixtures_available() else 10001217

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", timeout=180) as client:
        health = await client.get("/health")
        assert health.status_code == 200
        summary = await client.get(f"/api/v1/patients/{subject}/summary", headers=headers)
        assert summary.status_code == 200 and summary.json()["patient"]["subject_id"] == subject
        chat = await client.post("/api/v1/chat", json={"message": "¿Cuántos ingresos tiene el paciente activo?", "patient_id": str(subject)}, headers=headers)
        assert chat.status_code == 200, chat.text
        assert chat.json()["success"] is True
