"""Streamlit recibe AuthSession OIDC, sin formulario ni contrasenas propias."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from chathce.domain.identity import AuthSession, Principal
from chathce.streamlit_adapter.auth_session import StreamlitAuthSession

pytestmark = pytest.mark.unit


def _run(coro):
    return asyncio.run(coro)


class FakeOidc:
    async def begin_authorization(self, *, redirect_uri, issuer=None):
        return SimpleNamespace(authorization_url=f"https://sso.test/login?redirect_uri={redirect_uri}")

    async def exchange_authorization_code(self, *, code, state):
        principal = Principal(user_id="doctor-1", roles=frozenset({"clinician"}), service="emergency")
        return AuthSession(access_token="oidc-token", expires_at=datetime.now(timezone.utc) + timedelta(minutes=5), principal=principal)


def test_streamlit_starts_and_accepts_oidc_session_without_passwords():
    state = {}
    auth = StreamlitAuthSession(FakeOidc(), state, None, _run)
    assert auth.supports_oidc()
    assert auth.start_oidc_login(redirect_uri="https://api.test/callback").startswith("https://sso.test/login")
    principal = auth.complete_oidc_login(code="code", state="state")
    assert principal.user_id == "doctor-1" and auth.access_token == "oidc-token"
