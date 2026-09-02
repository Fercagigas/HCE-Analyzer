"""Tests de integracion: requieren HCE_RUN_INTEGRATION=1 y credenciales reales.

Se saltan de forma automatica cuando faltan, de modo que `python -m pytest`
sin argumentos sigue siendo verde en cualquier maquina.
"""

import os
from pathlib import Path

import pytest

INTEGRATION_DIR = Path(__file__).resolve().parent


def _integration_enabled() -> bool:
    return os.environ.get("HCE_RUN_INTEGRATION", "").strip().lower() in {"1", "true", "yes"}


def pytest_collection_modifyitems(config, items):
    skip = pytest.mark.skip(reason="HCE_RUN_INTEGRATION=1 no definido; test de integracion omitido")
    for item in items:
        if INTEGRATION_DIR in Path(str(item.fspath)).resolve().parents:
            item.add_marker(pytest.mark.integration)
            if not _integration_enabled():
                item.add_marker(skip)


@pytest.fixture(scope="session")
def integration_settings():
    from config.settings import get_settings

    settings = get_settings()
    try:
        settings.require_database()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Credenciales de Supabase no disponibles: {exc}")
    return settings
