"""Superficie visible al modelo: ningun schema, descripcion ni prompt expone SQL o nombres de tabla.

Desde WP8 la fuente de verdad es el ToolRegistry del core y `build_system_prompt`.
"""

import json

import pytest

from chathce.application.prompts.system_prompt import build_system_prompt
from chathce.domain.context import Channel, RequestContext
from chathce.domain.tools import LLM_VISIBLE_FORBIDDEN_PATTERN
from tests.fakes.container_factory import build_test_container
from tests.fakes.mimic_fixtures import fixtures_available

pytestmark = [pytest.mark.security, pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")]


def _assert_clean(text: str, where: str) -> None:
    match = LLM_VISIBLE_FORBIDDEN_PATTERN.search(text)
    assert match is None, f"{where} expone {match.group(0)!r} al modelo"


def test_every_registered_tool_schema_is_closed_and_clean():
    registry = build_test_container().registry
    for spec in registry.specs(registry.contracts()):
        _assert_clean(json.dumps(spec.input_schema, ensure_ascii=False), f"el schema de {spec.name}")
        _assert_clean(spec.description, f"la descripcion de {spec.name}")
        assert spec.input_schema.get("additionalProperties") is False
        assert not {"custom_query", "params", "table_name", "filters", "sql"} & set(spec.input_schema.get("properties", {}))


def test_system_prompt_is_clean_and_names_real_tools():
    registry = build_test_container().registry
    ctx = RequestContext(user_id="u", channel=Channel.api, patient_id="10001217")
    prompt, _ = build_system_prompt(registry.contracts(), ctx)
    _assert_clean(prompt, "el system prompt")
    assert "CREATE TABLE" not in prompt and "query_mimic_database" not in prompt
    for name in ("get_patient_summary", "get_labs", "search_clinical_documents", "create_visualization"):
        assert name in prompt


def test_no_langchain_agent_loop_remains():
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "-c", "import sys, services.unified_chat.unified_agent; "
         "print(sorted(m for m in sys.modules if m.startswith(('langchain_classic','langchain_anthropic'))))"],
        capture_output=True, text=True, timeout=120, env={**__import__('os').environ, "HCE_DISABLE_DOTENV": "1"},
    )
    assert completed.returncode == 0, completed.stderr[-500:]
    assert completed.stdout.strip().splitlines()[-1] == "[]"
