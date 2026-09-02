"""Carga de fixtures MIMIC grabadas y construccion del provider sobre el cliente en memoria."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from chathce.adapters.memory.postgrest_client import InMemoryPostgrestClient, register_clinical_aggregate_rpcs
from chathce.adapters.supabase.mimic_clinical_data_provider import MimicClinicalDataProvider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "mimic"


def fixtures_available() -> bool:
    return (FIXTURES / "manifest.json").exists()


def load_manifest() -> dict:
    return json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def load_tables() -> Dict[str, Dict[str, list]]:
    tables: Dict[str, Dict[str, list]] = {}
    for path in sorted((FIXTURES / "tables").glob("*.json")):
        schema, table = path.stem.split("__", 1)
        tables.setdefault(schema, {})[table] = json.loads(path.read_text(encoding="utf-8"))
    return tables


def load_expected(name: str) -> dict:
    return json.loads((FIXTURES / "expected" / f"{name}.json").read_text(encoding="utf-8"))


def make_memory_client(with_rpcs: bool = True) -> InMemoryPostgrestClient:
    client = InMemoryPostgrestClient.from_tables(load_tables())
    if with_rpcs:
        register_clinical_aggregate_rpcs(client)
    return client


def make_provider(client: Optional[InMemoryPostgrestClient] = None, **kwargs) -> MimicClinicalDataProvider:
    return MimicClinicalDataProvider(client or make_memory_client(), **kwargs)
