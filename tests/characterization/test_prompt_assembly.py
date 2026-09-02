"""Caracterizacion del ensamblado del system prompt (`PromptManager`).

Snapshot en `tests/fixtures/prompts/system_prompt_v0.txt`. Regenerar con
`UPDATE_SNAPSHOTS=1`. Los asserts estructurales fijan lo que WP6/WP8 deben
conservar (identidad, idioma, anti-alucinacion, nombres reales de tools) y lo que
deben eliminar (DDL y ejemplos SQL; `xfail` hasta WP4).
"""

import os
from pathlib import Path

import pytest

SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "prompts" / "system_prompt_v0.txt"
REAL_TOOL_NAMES = ("query_mimic_database", "search_clinical_documents", "request_visualization")


@pytest.fixture(scope="module")
def system_prompt() -> str:
    from services.medical_agent.prompt_manager import PromptManager

    manager = PromptManager(max_tokens=8000, anthropic_api_key=None, enable_caching=True)
    return manager.get_system_prompt()


def test_prompt_is_deterministic(system_prompt):
    from services.medical_agent.prompt_manager import PromptManager

    again = PromptManager(max_tokens=8000, anthropic_api_key=None, enable_caching=False).get_system_prompt()
    assert again == system_prompt


def test_prompt_matches_snapshot(system_prompt):
    if os.environ.get("UPDATE_SNAPSHOTS") == "1" or not SNAPSHOT.exists():
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(system_prompt, encoding="utf-8", newline="\n")
    assert system_prompt == SNAPSHOT.read_text(encoding="utf-8")


def test_prompt_keeps_core_directives(system_prompt):
    lowered = system_prompt.lower()
    assert "chathce" in lowered
    assert "español" in lowered or "espanol" in lowered
    assert "alucin" in lowered  # directivas anti-alucinacion
    for name in REAL_TOOL_NAMES:
        assert name in system_prompt, f"El prompt no menciona la tool real {name}"


@pytest.mark.xfail(strict=True, reason="Hasta WP4 el prompt expone DDL y ejemplos SQL al modelo")
def test_prompt_exposes_no_schema_or_sql(system_prompt):
    lowered = system_prompt.lower()
    assert "create table" not in lowered
    assert "mimiciv_hosp." not in lowered
    assert "custom_query" not in lowered
    assert "select " not in lowered
