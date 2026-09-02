"""Guardia de fronteras (ADR 0010 §1): el core no importa SDKs de proveedores ni Streamlit.

Se comprueba por AST (imports estaticos) y por ``sys.modules`` en un subproceso
(imports dinamicos). Solo ``chathce/adapters/**``, ``chathce/api``, ``chathce/streamlit_adapter``
y ``chathce/legacy`` pueden tocar proveedores.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIRS = ("chathce/domain", "chathce/ports", "chathce/application", "chathce/gateway", "chathce/composition")
FORBIDDEN_ROOTS = {"streamlit", "supabase", "postgrest", "anthropic", "langchain", "langchain_core",
                   "langchain_anthropic", "langchain_classic", "langchain_community", "langchain_huggingface",
                   "extra_streamlit_components", "fastapi", "starlette", "sse_starlette"}


def _core_files():
    for directory in CORE_DIRS:
        base = PROJECT_ROOT / directory
        if base.exists():
            yield from sorted(base.rglob("*.py"))


def _imported_roots(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module.split(".")[0]


def test_core_has_no_static_provider_imports():
    offenders = {}
    for path in _core_files():
        bad = sorted({root for root in _imported_roots(path) if root in FORBIDDEN_ROOTS})
        if bad:
            offenders[str(path.relative_to(PROJECT_ROOT))] = bad
    assert offenders == {}


def test_core_does_not_import_legacy_packages():
    """El core tampoco depende de services/ ni ui/ (arbol legacy en retirada)."""
    offenders = {}
    for path in _core_files():
        bad = sorted({root for root in _imported_roots(path) if root in {"services", "ui", "src"}})
        if bad:
            offenders[str(path.relative_to(PROJECT_ROOT))] = bad
    assert offenders == {}


def test_importing_core_loads_no_provider_modules():
    code = (
        "import sys, importlib\n"
        "for m in ['chathce.domain.context','chathce.domain.clinical','chathce.domain.tools','chathce.domain.chat',"
        "'chathce.domain.audit','chathce.ports','chathce.adapters.memory']:\n"
        "    importlib.import_module(m)\n"
        f"forbidden = {sorted(FORBIDDEN_ROOTS)!r}\n"
        "loaded = sorted(m for m in sys.modules if m.split('.')[0] in forbidden)\n"
        "print(loaded)\n"
        "raise SystemExit(1 if loaded else 0)\n"
    )
    completed = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stdout + completed.stderr
