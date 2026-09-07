"""Contrato de SupabaseIdentityProvider con un GoTrue simulado."""

from types import SimpleNamespace

import pytest

from chathce.adapters.memory.postgrest_client import InMemoryPostgrestClient
from chathce.adapters.supabase.identity_provider import SupabaseIdentityProvider
from chathce.domain.errors import AuthenticationFailed
from chathce.ports import IdentityProvider

pytestmark = pytest.mark.contract


class FakeGoTrue:
    def __init__(self):
        self.users = {"doc@example.invalid": ("secret6", SimpleNamespace(id="uid-1", email="doc@example.invalid", app_metadata={"roles": ["researcher"]}))}
        self.tokens = {}
        self.signed_out = []
        self.admin = SimpleNamespace(sign_out=lambda jwt: self.signed_out.append(jwt))

    def sign_in_with_password(self, creds):
        pw, user = self.users.get(creds["email"], (None, None))
        if user is None or pw != creds["password"]:
            raise Exception("Invalid login credentials")
        session = SimpleNamespace(access_token=f"acc-{user.id}", refresh_token=f"ref-{user.id}", expires_at=4102444800)
        self.tokens[session.access_token] = user
        return SimpleNamespace(user=user, session=session)

    def get_user(self, jwt=None):
        user = self.tokens.get(jwt)
        if user is None:
            raise Exception("invalid JWT")
        return SimpleNamespace(user=user)

    def refresh_session(self, refresh_token=None):
        for token, user in list(self.tokens.items()):
            if refresh_token == f"ref-{user.id}":
                new = SimpleNamespace(access_token=f"acc2-{user.id}", refresh_token=f"ref2-{user.id}", expires_at=4102444800)
                self.tokens[new.access_token] = user
                return SimpleNamespace(user=user, session=new)
        raise Exception("invalid refresh token")

    def sign_up(self, payload):
        if payload["email"] in self.users:
            raise Exception("User already registered")
        user = SimpleNamespace(id="uid-new", email=payload["email"], app_metadata={}, confirmed_at=None)
        self.users[payload["email"]] = (payload["password"], user)
        return SimpleNamespace(user=user, session=None)

    def reset_password_email(self, email):
        return None


@pytest.fixture
def identity():
    client = InMemoryPostgrestClient()
    client.rows("users").append({"id": "uid-1", "name": "Dra. Demo", "email": "doc@example.invalid", "role": "clinician"})
    client.auth = FakeGoTrue()  # type: ignore[attr-defined]
    return SupabaseIdentityProvider(client, cache_ttl_s=60), client


async def test_login_returns_session_and_principal_without_email(identity):
    provider, client = identity
    assert isinstance(provider, IdentityProvider)
    session = await provider.login("doc@example.invalid", "secret6")
    assert session.access_token == "acc-uid-1" and session.refresh_token == "ref-uid-1"
    principal = session.principal
    assert principal.user_id == "uid-1" and principal.display_name == "Dra. Demo"
    assert principal.roles == frozenset({"researcher", "clinician"})
    assert "email" not in principal.model_dump()
    assert client.rows("users")[0].get("last_login")


async def test_login_failure_is_friendly(identity):
    provider, _ = identity
    with pytest.raises(AuthenticationFailed, match="Correo o contraseña incorrectos"):
        await provider.login("doc@example.invalid", "mal")


async def test_verify_token_uses_remote_check_and_cache(identity):
    provider, client = identity
    session = await provider.login("doc@example.invalid", "secret6")
    principal = await provider.verify_access_token(session.access_token)
    assert principal.user_id == "uid-1"
    client.auth.tokens.clear()  # revocacion remota
    assert (await provider.verify_access_token(session.access_token)).user_id == "uid-1"  # cache 60 s
    provider._cache.clear()
    with pytest.raises(AuthenticationFailed):
        await provider.verify_access_token(session.access_token)
    with pytest.raises(AuthenticationFailed):
        await provider.verify_access_token("")


async def test_refresh_and_logout(identity):
    provider, client = identity
    session = await provider.login("doc@example.invalid", "secret6")
    refreshed = await provider.refresh(session.refresh_token)
    assert refreshed.access_token == "acc2-uid-1"
    with pytest.raises(AuthenticationFailed):
        await provider.refresh("ref-nope")
    await provider.logout(refreshed.access_token)
    assert client.auth.signed_out == ["acc2-uid-1"]


async def test_register_creates_profile_and_validates_input(identity):
    provider, client = identity
    with pytest.raises(AuthenticationFailed):
        await provider.register(email="x@y.z", password="123", name="n")
    principal = await provider.register(email="new@example.invalid", password="secret6", name="Nuevo", specialty="Cardio")
    assert principal.user_id == "uid-new" and principal.display_name == "Nuevo"
    assert any(r["email"] == "new@example.invalid" and r["specialty"] == "Cardio" for r in client.rows("users"))
    with pytest.raises(AuthenticationFailed, match="ya está registrado"):
        await provider.register(email="new@example.invalid", password="secret6", name="Nuevo")
