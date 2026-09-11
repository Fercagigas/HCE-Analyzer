import sys
from types import SimpleNamespace

import pytest

from chathce.adapters.supabase.client_factory import SupabaseClients
from chathce.domain.context import Channel, RequestContext


def test_product_client_for_requires_public_key_and_user_jwt():
    clients = SupabaseClients(url="https://example.invalid", service_key="service")
    with pytest.raises(ValueError, match="ANON"):
        clients.product_client_for(RequestContext(user_id="u", channel=Channel.api, access_token="jwt"))


def test_product_client_for_forwards_the_request_jwt(monkeypatch):
    observed = {}

    class Postgrest:
        def auth(self, token):
            observed["token"] = token

    def fake_create(url, key, options):
        observed.update(url=url, key=key, schema=options.schema)
        return SimpleNamespace(postgrest=Postgrest())

    fake_module = SimpleNamespace(create_client=fake_create, ClientOptions=lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setitem(sys.modules, "supabase", fake_module)
    clients = SupabaseClients(url="https://example.invalid", service_key="service", anon_key="anon")
    client = clients.product_client_for(RequestContext(user_id="u", channel=Channel.api, access_token="jwt-user"))
    assert client is not None and observed == {"url": "https://example.invalid", "key": "anon", "schema": "public", "token": "jwt-user"}
