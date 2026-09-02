"""Superficie visible al modelo: ningun schema, descripcion ni prompt expone SQL o nombres de tabla.

Aplica al runtime legacy (WP4) y, desde WP8, al ToolRegistry del core. La lista de
terminos prohibidos vive en `chathce.domain.tools.LLM_VISIBLE_FORBIDDEN_PATTERN`.
"""

import json

import pytest
from pydantic import ValidationError

from chathce.domain.tools import LLM_VISIBLE_FORBIDDEN_PATTERN

pytestmark = pytest.mark.security


def _assert_clean(text: str, where: str) -> None:
    match = LLM_VISIBLE_FORBIDDEN_PATTERN.search(text)
    assert match is None, f"{where} expone {match.group(0)!r} al modelo"


def test_legacy_database_tool_schema_is_closed_and_clean():
    from services.unified_chat.tools.database_tool import TOOL_DESCRIPTION, DatabaseToolInput

    schema = DatabaseToolInput.model_json_schema()
    _assert_clean(json.dumps(schema, ensure_ascii=False), "el schema de query_mimic_database")
    _assert_clean(TOOL_DESCRIPTION, "la descripcion de query_mimic_database")
    assert not {"custom_query", "params", "table_name", "filters", "sql"} & set(schema["properties"])
    with pytest.raises(ValidationError):
        DatabaseToolInput(query_type="custom", custom_query="SELECT 1")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        DatabaseToolInput(query_type="labs", subject_id=1, table_name="x")  # type: ignore[call-arg]


def test_legacy_visualization_tool_schema_is_clean():
    from services.medical_agent.tools.visualization_collaboration_tool import (
        VISUALIZATION_TOOL_DESCRIPTION,
        VisualizationRequest,
    )

    schema = VisualizationRequest.model_json_schema()
    _assert_clean(json.dumps(schema, ensure_ascii=False), "el schema de request_visualization")
    _assert_clean(VISUALIZATION_TOOL_DESCRIPTION, "la descripcion de request_visualization")
    with pytest.raises(ValidationError):
        VisualizationRequest(visualization_type="bar", data_source="prescriptions")  # nombre de tabla no admitido


def test_legacy_system_prompt_is_clean():
    from services.medical_agent.prompt_manager import PromptManager

    prompt = PromptManager(max_tokens=8000, anthropic_api_key=None, enable_caching=False).get_system_prompt()
    _assert_clean(prompt, "el system prompt")
    assert "CREATE TABLE" not in prompt
    assert "database_query_tool" not in prompt, "nombre de tool inexistente"
    assert "query_mimic_database" in prompt


def test_legacy_database_service_has_no_free_sql_path():
    from services.medical_agent.services.database_service import DatabaseService

    for name in ("execute_custom_query", "execute_query", "_validate_query", "_sanitize_params", "ALLOWED_SCHEMAS"):
        assert not hasattr(DatabaseService, name), f"DatabaseService.{name} sigue existiendo"
