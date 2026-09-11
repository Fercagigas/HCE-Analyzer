"""OIDC offline: JWT sinteticos firmados localmente; nunca claves reales."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from chathce.adapters.oidc.identity_provider import OidcIdentityProvider
from chathce.adapters.memory import InMemoryIdentityProvider
from chathce.domain.errors import AuthenticationFailed
from chathce.ports import IdentityProvider

pytestmark = pytest.mark.unit

ISSUER = "https://sso.hospital.test/realms/demo"
CLIENT = "chathce-test"


@pytest.fixture
def oidc():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "test-key", "use": "sig", "alg": "RS256"})
    settings = SimpleNamespace(
        oidc_issuers=[SimpleNamespace(
            issuer=ISSUER, client_id=CLIENT, audiences=[], discovery_url=None,
            claims=SimpleNamespace(sub="sub", tenant="org.id", roles="realm_access.roles", service="department", display_name="name"),
        )],
        oidc_scopes=["openid", "profile"], oidc_redirect_uri="http://testserver/api/v1/auth/callback",
        oidc_client_secret=None, oidc_discovery_cache_s=3600, oidc_jwks_cache_s=300, oidc_state_ttl_s=600,
    )
    discovery = {
        "issuer": ISSUER, "authorization_endpoint": f"{ISSUER}/protocol/openid-connect/auth",
        "token_endpoint": f"{ISSUER}/protocol/openid-connect/token", "jwks_uri": f"{ISSUER}/protocol/openid-connect/certs",
    }
    calls = {"get": [], "form": None, "response": {}}

    async def fetch(url):
        calls["get"].append(url)
        return {"keys": [jwk]} if url == discovery["jwks_uri"] else discovery

    async def post(url, data):
        calls["form"] = (url, dict(data))
        return calls["response"]

    def token(**overrides):
        claims = {
            "iss": ISSUER, "aud": CLIENT, "sub": "doctor-1", "exp": int(time.time()) + 3600,
            "org": {"id": "hospital-a"}, "realm_access": {"roles": ["clinician", "researcher"]},
            "department": "cardiology", "name": "Dra. Demo",
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})

    return OidcIdentityProvider(settings, fetch_json=fetch, post_form=post), calls, token


async def test_verifies_jwks_claim_mapping_and_cache(oidc):
    provider, calls, token = oidc
    assert isinstance(provider, IdentityProvider)
    principal = await provider.verify_access_token(token())
    assert principal.user_id == "doctor-1" and principal.tenant_id == "hospital-a"
    assert principal.roles == frozenset({"clinician", "researcher"}) and principal.service == "cardiology"
    await provider.verify_access_token(token())
    assert calls["get"].count(f"{ISSUER}/protocol/openid-connect/certs") == 1


async def test_rejects_untrusted_issuer_bad_audience_and_expired_token(oidc):
    provider, _, token = oidc
    with pytest.raises(AuthenticationFailed):
        await provider.verify_access_token(token(iss="https://not-trusted.test"))
    with pytest.raises(AuthenticationFailed):
        await provider.verify_access_token(token(aud="different-client"))
    with pytest.raises(AuthenticationFailed):
        await provider.verify_access_token(token(exp=int(time.time()) - 1))
    with pytest.raises(AuthenticationFailed, match="tenant"):
        await provider.verify_access_token(token(org={"id": ""}))
    with pytest.raises(AuthenticationFailed, match="rol no reconocido"):
        await provider.verify_access_token(token(realm_access={"roles": ["superuser"]}))


async def test_authorization_code_pkce_validates_nonce_and_one_time_state(oidc):
    provider, calls, token = oidc
    request = await provider.begin_authorization(redirect_uri="http://testserver/api/v1/auth/callback")
    params = parse_qs(urlparse(request.authorization_url).query)
    assert params["response_type"] == ["code"] and params["code_challenge_method"] == ["S256"]
    calls["response"] = {"id_token": token(nonce=params["nonce"][0]), "access_token": token(), "refresh_token": "rotated"}
    session = await provider.exchange_authorization_code(code="code-from-idp", state=request.state)
    assert session.principal.user_id == "doctor-1" and session.refresh_token == "rotated"
    endpoint, form = calls["form"]
    assert endpoint.endswith("/token") and form["code"] == "code-from-idp" and form["code_verifier"]
    with pytest.raises(AuthenticationFailed, match="Estado OIDC"):
        await provider.exchange_authorization_code(code="again", state=request.state)


async def test_exchange_rejects_wrong_nonce_and_unconfigured_redirect(oidc):
    provider, calls, token = oidc
    with pytest.raises(AuthenticationFailed, match="Redirect URI"):
        await provider.begin_authorization(redirect_uri="https://evil.invalid/callback")
    request = await provider.begin_authorization(redirect_uri="http://testserver/api/v1/auth/callback")
    calls["response"] = {"id_token": token(nonce="wrong"), "access_token": token()}
    with pytest.raises(AuthenticationFailed, match="Nonce"):
        await provider.exchange_authorization_code(code="code", state=request.state)


async def test_delegates_care_relationships_but_not_oidc_role_administration(oidc):
    provider, _, _ = oidc
    store = InMemoryIdentityProvider()
    provider._patient_access = store
    now = datetime.now(timezone.utc)
    await provider.grant_patient_access(
        user_id="doctor-1", tenant_id="hospital-a", subject_id=101, service_id="cardiology",
        valid_from=now - timedelta(minutes=1), valid_until=None, granted_by="admin-1",
    )
    assert await provider.has_active_patient_access(
        user_id="doctor-1", tenant_id="hospital-a", subject_id=101, service_id="cardiology", at=now,
    )
    with pytest.raises(AuthenticationFailed, match="roles OIDC"):
        await provider.assign_roles(user_id="doctor-1", tenant_id="hospital-a", roles=frozenset({"clinician"}))
