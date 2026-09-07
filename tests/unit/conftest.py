"""Tests unitarios: sin red, sin .env, sin credenciales.

Se bloquea cualquier conexion que no sea loopback (asyncio en Windows crea un
socketpair local para su event loop y debe seguir funcionando).
"""

import socket

import pytest

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _is_loopback(address) -> bool:
    try:
        host = address[0]
    except (TypeError, IndexError):
        return False
    return host in _LOOPBACK


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Bloquea la red externa y deja el entorno sin credenciales ni .env."""
    monkeypatch.setenv("HCE_DISABLE_DOTENV", "1")
    for var in ("SUPABASE_URL", "SUPABASE_KEY", "ANTHROPIC_API_KEY", "SECRET_KEY",
                "HUGGINFACEHUB_API_TOKEN", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection

    def guarded_connect(self, address, *args, **kwargs):
        if _is_loopback(address):
            return original_connect(self, address, *args, **kwargs)
        raise RuntimeError(f"network disabled in unit tests (attempted {address!r})")

    def guarded_create_connection(address, *args, **kwargs):
        if _is_loopback(address):
            return original_create_connection(address, *args, **kwargs)
        raise RuntimeError(f"network disabled in unit tests (attempted {address!r})")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    yield
