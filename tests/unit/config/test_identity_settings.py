"""Configuracion de seleccion Supabase/OIDC sin .env ni secretos."""

import pytest

from chathce.adapters.oidc import OidcIdentityProvider
from config.settings import ConfigurationError, get_settings

pytestmark = pytest.mark.unit


def test_oidc_settings_accept_multiple_trusted_issuers(monkeypatch):
    monkeypatch.setenv("IDENTITY_PROVIDER", "oidc")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "https://api.test/api/v1/auth/callback")
    monkeypatch.setenv(
        "OIDC_ISSUERS",
        '[{"issuer":"https://sso-a.test","client_id":"client-a"},{"issuer":"https://sso-b.test","client_id":"client-b","claims":{"tenant":"org","roles":"realm_access.roles"}}]',
    )
    settings = get_settings()
    assert settings.identity.provider == "oidc" and len(settings.require_oidc().oidc_issuers) == 2
    assert settings.identity.oidc_issuers[1].claims.tenant == "org"


def test_oidc_requires_issuers_and_callback(monkeypatch):
    monkeypatch.setenv("IDENTITY_PROVIDER", "oidc")
    settings = get_settings()
    with pytest.raises(ConfigurationError):
        settings.require_oidc()


def test_oidc_container_keeps_a_fail_closed_care_relationship_store(monkeypatch):
    monkeypatch.setenv("IDENTITY_PROVIDER", "oidc")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "https://api.test/api/v1/auth/callback")
    monkeypatch.setenv("OIDC_ISSUERS", '[{"issuer":"https://sso.test","client_id":"chathce"}]')
    monkeypatch.setenv("CLINICAL_PROVIDER", "memory")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("AUDIT_SINK", "null")
    from chathce.composition.container import build_container

    container = build_container(get_settings())
    assert isinstance(container.identity, OidcIdentityProvider)
    assert container.identity._patient_access is not None
    assert container.clinical_provider._patient_access is container.identity
