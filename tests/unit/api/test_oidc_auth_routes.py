"""Endpoints minimos del login OIDC sin red ni IdP real."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from chathce.api.app import create_app
from chathce.api.dependencies import make_context
from chathce.domain.context import Channel
from chathce.domain.identity import AuthSession, Principal
from tests.fakes.container_factory import build_test_container

pytestmark = pytest.mark.unit


class FakeOidc:
    def __init__(self):
        self.begun = None
        self.exchanged = None

    async def begin_authorization(self, *, redirect_uri, issuer=None):
        self.begun = (redirect_uri, issuer)
        return SimpleNamespace(authorization_url="https://sso.test/authorize?state=opaque")

    async def exchange_authorization_code(self, *, code, state):
        self.exchanged = (code, state)
        principal = Principal(user_id="doctor-1", tenant_id="hospital-a", roles=frozenset({"clinician"}), service="icu")
        return AuthSession(access_token="oidc-access", expires_at=datetime.now(timezone.utc) + timedelta(minutes=5), principal=principal)


@pytest.fixture
async def oidc_client():
    container = build_test_container()
    provider = FakeOidc()
    container.identity = provider
    container.settings = SimpleNamespace(identity=SimpleNamespace(oidc_redirect_uri="http://testserver/api/v1/auth/callback"))
    settings = SimpleNamespace(api=SimpleNamespace(cors_allowed_origins=[], docs_enabled=True, sse_ping_s=1, ready_cache_s=0, environment="dev"))
    app = create_app(container, settings=settings)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", follow_redirects=False) as client:
        yield client, provider


async def test_login_redirects_to_idp_with_only_configured_callback(oidc_client):
    client, provider = oidc_client
    response = await client.get("/api/v1/auth/login?issuer=https://sso.test")
    assert response.status_code == 307 and response.headers["location"] == "https://sso.test/authorize?state=opaque"
    assert provider.begun == ("http://testserver/api/v1/auth/callback", "https://sso.test")


async def test_callback_exchanges_code_once_and_returns_session(oidc_client):
    client, provider = oidc_client
    response = await client.get("/api/v1/auth/callback?code=code-one&state=opaque")
    assert response.status_code == 200 and provider.exchanged == ("code-one", "opaque")
    assert response.json()["principal"] == {"user_id": "doctor-1", "tenant_id": "hospital-a", "roles": ["clinician"], "service": "icu"}


def test_principal_service_is_propagated_to_request_context():
    request = SimpleNamespace(state=SimpleNamespace(trace_id="trace-test-123", request_id="request-test-123", access_token="oidc-access"))
    principal = Principal(user_id="doctor-1", tenant_id="hospital-a", roles=frozenset({"clinician"}), service="icu")
    context = make_context(request, principal)
    assert context.channel == Channel.api and context.tenant_id == "hospital-a"
    assert context.service == "icu" and context.service_id == "icu"
