"""Contenedor unico por proceso Streamlit (st.cache_resource) y utilidades de ejecucion."""

from __future__ import annotations

from typing import Any, Optional

from chathce.composition.container import Container


def _build() -> Container:
    from config.settings import get_settings
    from chathce.composition.container import build_container

    return build_container(get_settings())


def get_container() -> Container:
    """Devuelve el contenedor compartido; con Streamlit usa cache_resource, sin el un singleton de modulo."""
    try:
        import streamlit as st

        @st.cache_resource(show_spinner=False)
        def _cached() -> Container:
            return _build()

        return _cached()
    except Exception:  # noqa: BLE001 - fuera de Streamlit (tests, scripts)
        global _fallback
        if _fallback is None:
            _fallback = _build()
        return _fallback


_fallback: Optional[Container] = None


def run(container: Container, coro: Any, *, timeout: Optional[float] = 180.0):
    return container.run(coro, timeout=timeout)
