"""Fixtures compartidas de caracterizacion: datos MIMIC grabados y cliente fake."""

import json
from pathlib import Path

import pytest

from tests.fakes.fake_supabase import FakeSupabaseClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "mimic"


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    monkeypatch.setenv("HCE_DISABLE_DOTENV", "1")
    for var in ("SUPABASE_URL", "SUPABASE_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def load_mimic_tables() -> dict:
    tables: dict = {}
    for path in sorted((FIXTURES / "tables").glob("*.json")):
        schema, table = path.stem.split("__", 1)
        tables.setdefault(schema, {})[table] = json.loads(path.read_text(encoding="utf-8"))
    return tables


@pytest.fixture(scope="session")
def mimic_manifest() -> dict:
    path = FIXTURES / "manifest.json"
    if not path.exists():
        pytest.skip("Fixtures MIMIC no grabadas: ejecute scripts/record_mimic_fixtures.py")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def mimic_client(mimic_manifest) -> FakeSupabaseClient:
    return FakeSupabaseClient.from_tables(load_mimic_tables())
