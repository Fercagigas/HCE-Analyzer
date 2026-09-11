"""Comprobacion opcional contra el Keycloak reproducible de docker-compose.oidc.yml."""

from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import pytest

from chathce.adapters.oidc import OidcIdentityProvider

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_keycloak_discovery_and_authorization_endpoint_are_available():
    base = os.environ.get("HCE_KEYCLOAK_URL", "http://127.0.0.1:8081").rstrip("/")
    discovery_url = f"{base}/realms/chathce-test/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(discovery_url)
    except httpx.HTTPError:
        pytest.skip("Keycloak no disponible; ejecute docker compose -f docker-compose.oidc.yml up -d")
    if response.status_code != 200:
        pytest.skip("Keycloak no esta listo; reintente cuando el healthcheck sea healthy")
    document = response.json()
    assert document["issuer"] == f"{base}/realms/chathce-test"
    assert document["authorization_endpoint"].startswith(document["issuer"])
    assert document["jwks_uri"].startswith(document["issuer"])

    settings = SimpleNamespace(
        oidc_issuers=[SimpleNamespace(
            issuer=document["issuer"], client_id="chathce-api", audiences=[], discovery_url=discovery_url,
            claims=SimpleNamespace(sub="sub", tenant="tenant_id", roles="realm_access.roles", service="service", display_name="name"),
        )],
        oidc_scopes=["openid", "profile"], oidc_redirect_uri="http://localhost:8000/api/v1/auth/callback",
        oidc_client_secret=None, oidc_discovery_cache_s=60, oidc_jwks_cache_s=60, oidc_state_ttl_s=60,
    )
    request = await OidcIdentityProvider(settings).begin_authorization(redirect_uri=settings.oidc_redirect_uri)
    assert "code_challenge_method=S256" in request.authorization_url and "nonce=" in request.authorization_url
