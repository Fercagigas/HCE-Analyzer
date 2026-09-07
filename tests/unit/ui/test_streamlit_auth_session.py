"""StreamlitAuthSession: cookie solo con refresh token, revalidacion y renovacion (ADR 0100)."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from chathce.adapters.memory import InMemoryIdentityProvider
from chathce.domain.identity import Principal
from chathce.streamlit_adapter.auth_session import COOKIE_NAME, K_ACCESS, K_EXPIRES, K_LAST_VERIFY, StreamlitAuthSession

pytestmark = pytest.mark.unit


class FakeCookies:
    def __init__(self):
        self.store = {}

    def get(self, name):
        return self.store.get(name)

    def set(self, name, value, expires_at=None):
        self.store[name] = value

    def delete(self, name):
        self.store.pop(name, None)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def identity():
    provider = InMemoryIdentityProvider()
    provider.add_user("doc@example.invalid", "secret6", Principal(user_id="u1", roles=frozenset({"clinician"}), display_name="Doc"))
    return provider


def test_login_stores_only_refresh_token_in_cookie(identity):
    state, cookies = {}, FakeCookies()
    auth = StreamlitAuthSession(identity, state, cookies, _run)
    principal = auth.login("doc@example.invalid", "secret6", remember_me=True)
    assert principal.user_id == "u1" and auth.is_authenticated()
    cookie = cookies.store[COOKIE_NAME]
    assert set(cookie) == {"rt"} and cookie["rt"].startswith("refresh_")
    assert "access" not in str(cookie) and "u1" not in str(cookie)
    assert state[K_ACCESS].startswith("access_")
    legacy = auth.to_legacy_user()
    assert legacy["id"] == "u1" and legacy["name"] == "Doc" and legacy["roles"] == ["clinician"]


def test_session_is_restored_from_cookie_with_rotation(identity):
    cookies = FakeCookies()
    first = StreamlitAuthSession(identity, {}, cookies, _run)
    first.login("doc@example.invalid", "secret6", remember_me=True)
    old_refresh = cookies.store[COOKIE_NAME]["rt"]

    restored = StreamlitAuthSession(identity, {}, cookies, _run)  # nueva pestana: session_state vacio
    principal = restored.ensure_authenticated()
    assert principal is not None and principal.user_id == "u1"
    assert cookies.store[COOKIE_NAME]["rt"] != old_refresh  # rotacion de un solo uso

    stale = StreamlitAuthSession(identity, {}, FakeCookies(), _run)
    stale._cookies.store[COOKIE_NAME] = {"rt": old_refresh}
    assert stale.ensure_authenticated() is None and COOKIE_NAME not in stale._cookies.store


def test_revoked_token_is_not_trusted_after_verify_interval(identity):
    state, cookies = {}, FakeCookies()
    auth = StreamlitAuthSession(identity, state, cookies, _run)
    auth.login("doc@example.invalid", "secret6", remember_me=False)
    identity.revoked.add(state[K_ACCESS])
    identity.refresh_tokens.clear()
    state[K_LAST_VERIFY] = -10_000.0  # fuerza la revalidacion
    assert auth.ensure_authenticated() is None
    assert not auth.is_authenticated()


def test_expiring_token_is_refreshed(identity):
    state, cookies = {}, FakeCookies()
    auth = StreamlitAuthSession(identity, state, cookies, _run)
    auth.login("doc@example.invalid", "secret6", remember_me=True)
    previous = state[K_ACCESS]
    state[K_EXPIRES] = datetime.now(timezone.utc) + timedelta(seconds=10)
    principal = auth.ensure_authenticated()
    assert principal is not None and state[K_ACCESS] != previous


def test_logout_clears_state_and_cookie(identity):
    state, cookies = {}, FakeCookies()
    auth = StreamlitAuthSession(identity, state, cookies, _run)
    auth.login("doc@example.invalid", "secret6", remember_me=True)
    token = state[K_ACCESS]
    auth.logout()
    assert not auth.is_authenticated() and COOKIE_NAME not in cookies.store and token in identity.revoked
