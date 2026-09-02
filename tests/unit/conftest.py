"""Tests unitarios: sin red, sin .env, sin credenciales."""

import socket

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Bloquea la red y deja el entorno sin credenciales ni .env."""
    monkeypatch.setenv("HCE_DISABLE_DOTENV", "1")
    for var in ("SUPABASE_URL", "SUPABASE_KEY", "ANTHROPIC_API_KEY", "SECRET_KEY",
                "HUGGINFACEHUB_API_TOKEN", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    def _blocked(*args, **kwargs):
        raise RuntimeError("network disabled in unit tests")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield
