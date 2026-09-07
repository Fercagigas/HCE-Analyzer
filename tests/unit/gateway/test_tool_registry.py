import pytest

from chathce.ports.llm_provider import ToolUsePart

pytestmark = pytest.mark.unit


def _call(name: str, **kwargs) -> ToolUsePart:
    return ToolUsePart(id=f"toolu_{name}", name=name, input=kwargs)


async def test_unknown_tool_returns_failure_without_raising(registry, ctx, audit):
    result = await registry.dispatch(ctx, _call("query_sql", sql="SELECT 1"))
    assert result.success is False and result.error.code == "unknown_tool"
    assert 'status="error"' in result.model_visible_text
    assert audit.actions() == ["tool_failed"]


async def test_invalid_input_is_reported_to_model_as_error(registry, ctx):
    result = await registry.dispatch(ctx, _call("get_labs", subject_id=10001217, custom_query="SELECT 1"))
    assert result.error.code == "invalid_input"
    assert "custom_query" in result.error.message
    result2 = await registry.dispatch(ctx, _call("get_labs", limit=5))
    assert result2.error.code == "invalid_input" and "subject_id" in result2.error.message


async def test_scope_refused_when_patient_mismatch_or_missing(registry, ctx, audit):
    other = await registry.dispatch(ctx, _call("get_labs", subject_id=99999999))
    assert other.error.code == "scope_refused"
    no_patient = await registry.dispatch(ctx.with_patient(None), _call("get_labs", subject_id=10001217))
    assert no_patient.error.code == "scope_refused" and "seleccione un paciente" in no_patient.error.message
    assert audit.actions() == ["tool_refused", "tool_refused"]


async def test_purpose_refused_for_aggregates_without_research(registry, ctx, research_ctx):
    refused = await registry.dispatch(ctx, _call("get_dataset_statistics", limit=5))
    assert refused.error.code == "purpose_refused"
    ok = await registry.dispatch(research_ctx, _call("get_dataset_statistics", limit=5))
    assert ok.success is True and ok.operation == "top_diagnoses"


async def test_rows_are_capped_to_contract_and_requested_limit(registry, ctx):
    result = await registry.dispatch(ctx, _call("get_labs", subject_id=10001217, limit=10))
    assert result.success and result.count == 10 and result.limit == 10 and result.truncated is True
    big = await registry.dispatch(ctx, _call("get_labs", subject_id=10001217, limit=200))
    assert big.count == 50 and big.limit == 50 and big.truncated is True  # max_rows del contrato


async def test_output_validation_rejects_rows_of_other_patients(registry, ctx, audit):
    result = await registry.dispatch(ctx, _call("leaky_labs", subject_id=10001217))
    assert result.success is False and result.error.code == "scope_refused"
    assert "otro paciente" in result.error.message
    assert audit.events[-1].action.value == "tool_refused"


async def test_timeout_and_provider_errors_become_results(registry, ctx):
    slow = await registry.dispatch(ctx, _call("slow_tool", subject_id=10001217))
    assert slow.error.code == "timeout" and slow.error.retryable is True
    failing = await registry.dispatch(ctx, _call("failing_tool", subject_id=10001217))
    assert failing.error.code == "provider_unavailable"


async def test_successful_result_is_rendered_and_audited(registry, ctx, audit):
    result = await registry.dispatch(ctx, _call("get_labs", subject_id=10001217, limit=3))
    assert result.model_visible_text.startswith('<tool_data tool="get_labs" operation="list_lab_observations" status="ok"')
    assert 'trust="untrusted_data"' in result.model_visible_text
    assert result.elapsed_ms >= 0
    event = audit.events[-1]
    assert event.action.value == "tool_call" and event.tool_name == "get_labs" and event.row_count == 3
    assert event.data_categories == ["labs"] and event.patient_id == "10001217"
    assert audit.phi_findings() == []


def test_specs_expose_only_contract_fields(registry):
    specs = registry.specs(registry.contracts(enabled=["get_labs"]))
    assert len(specs) == 1
    assert set(specs[0].input_schema["properties"]) == {"subject_id", "limit"}
    assert specs[0].input_schema["additionalProperties"] is False
