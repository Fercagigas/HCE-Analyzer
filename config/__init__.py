"""Modulo de configuracion.

Acceso canonico: ``from config import get_settings``.
``from config import settings`` sigue funcionando como shim temporal (PEP 562).
"""
from .settings import ConfigurationError, Settings, get_settings, reset_settings_cache


def __getattr__(name: str):
    if name == "settings":
        return get_settings()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Settings", "ConfigurationError", "get_settings", "reset_settings_cache"]
