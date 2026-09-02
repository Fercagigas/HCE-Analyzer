import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from chathce.domain.context import Channel, RequestContext
from chathce.domain.tools import (
    LLM_VISIBLE_FORBIDDEN_PATTERN,
    AuditCategory,
    ToolContract,
    ToolResult,
    assert_no_schema_leak,
)

pytestmark = pytest.mark.unit


class ClosedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: int
    limit: int = 50


class OpenInput(BaseModel):
    subject_id: int


class Output(BaseModel):
    count: int


def _contract(**overrides) -> ToolContract:
    base = dict(
        name="get_labs",
        description="Devuelve resultados de laboratorio del paciente activo.",
        input_model=ClosedInput,
        output_model=Output,
        requires_patient_scope=True,
        audit_category=AuditCategory.clinical_data,
    )
    base.update(overrides)
    return ToolContract(**base)


def test_contract_requires_closed_input_model():
    with pytest.raises(ValidationError, match="extra='forbid'"):
        _contract(input_model=OpenInput)


def test_contract_rejects_schema_leaks_in_description():
    with pytest.raises(ValidationError, match="prohibido"):
        _contract(description="Ejecuta SELECT sobre labevents del paciente.")
    with pytest.raises(ValidationError, match="prohibido"):
        _contract(description="Consulta la tabla mimiciv_hosp de admisiones.")


def test_contract_caps_max_rows_and_timeout():
    with pytest.raises(ValidationError):
        _contract(max_rows=201)
    with pytest.raises(ValidationError):
        _contract(timeout_s=0)
    assert _contract(max_rows=200, timeout_s=30).max_rows == 200


def test_input_schema_is_closed_and_has_no_title():
    schema = _contract().input_schema()
    assert schema["additionalProperties"] is False
    assert "title" not in schema
    assert set(schema["properties"]) == {"subject_id", "limit"}


@pytest.mark.parametrize("text", [
    "custom_query", "SELECT * FROM x", "table_name", "mimic_ed.edstays", "labevents", "d_items", "Prescriptions",
])
def test_forbidden_pattern_detects_schema_terms(text):
    assert LLM_VISIBLE_FORBIDDEN_PATTERN.search(text)
    with pytest.raises(ValueError):
        assert_no_schema_leak(text)


@pytest.mark.parametrize("text", [
    "Resultados de laboratorio del paciente activo",
    "Selecciona el episodio",  # 'selecciona' no es 'select' como palabra
    "Medicacion prescrita durante la admision",
])
def test_forbidden_pattern_allows_clinical_spanish(text):
    assert_no_schema_leak(text)


def test_tool_result_failure_helper():
    ctx = RequestContext(user_id="u", channel=Channel.api, patient_id="1")
    result = ToolResult.failure(
        tool_name="get_labs", tool_use_id="toolu_1", scope=ctx.scope(), code="scope_refused", message="fuera de scope",
    )
    assert result.success is False
    assert result.error is not None and result.error.code == "scope_refused"
    assert result.evidence_ids == []
    with pytest.raises(ValidationError):
        ToolResult(tool_name="x", tool_use_id="y", success=True, operation="o", scope=ctx.scope(), extra=1)  # type: ignore[call-arg]
