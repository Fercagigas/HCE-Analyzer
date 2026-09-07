"""
Configuracion global de pytest para ChatHCE.

Reglas:
- Ningun test debe depender de que exista .env: los tests unitarios fijan
  HCE_DISABLE_DOTENV=1 (ver tests/unit/conftest.py) y los de integracion se
  saltan sin HCE_RUN_INTEGRATION=1.
- La instancia cacheada de Settings se descarta antes de cada test para que
  los cambios de entorno hechos con monkeypatch tengan efecto.
"""

import os
import sys
import warnings
from pathlib import Path

import pytest

# Raiz del proyecto en sys.path (permite `import config`, `import services`, ...)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Filtros de warnings de librerias externas y entorno de test."""
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
    warnings.filterwarnings("ignore", message="Using extra keyword arguments on `Field` is deprecated")
    warnings.filterwarnings("ignore", message=".*PydanticDeprecatedSince20.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="supabase")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="postgrest")
    warnings.filterwarnings("ignore", message=".*'timeout' parameter is deprecated.*")
    warnings.filterwarnings("ignore", message=".*'verify' parameter is deprecated.*")
    warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
    warnings.filterwarnings("ignore", category=pytest.PytestUnraisableExceptionWarning)

    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("LOG_LEVEL", "ERROR")


@pytest.fixture(scope="session", autouse=True)
def suppress_warnings():
    """Silencia warnings de dependencias durante toda la sesion."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
        warnings.filterwarnings("ignore", category=pytest.PytestUnraisableExceptionWarning)
        yield


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Descarta la instancia cacheada de Settings antes y despues de cada test."""
    from config.settings import reset_settings_cache as _reset

    _reset()
    yield
    _reset()
