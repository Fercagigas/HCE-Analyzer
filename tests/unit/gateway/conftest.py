"""Fixtures del gateway: registro con tools de prueba y contexto."""

import asyncio
from typing import Optional

import pytest
from pydantic import BaseModel, ConfigDict, Field

from chathce.adapters.memory import CollectingAuditSink
from chathce.domain.clinical import Page
from chathce.domain.context import Channel, Purpose, RequestContext
from chathce.domain.errors import ProviderUnavailable
from chathce.domain.tools import AuditCategory, ToolContract, ToolResult
from chathce.gateway.tool_registry import Tool, ToolRegistry


class LabsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: int = Field(description="Identificador del paciente")
    limit: int = Field(default=20, ge=1, le=200, description="Maximo de resultados")


class Row(BaseModel):
    subject_id: int
    value: float


class LabsOutput(BaseModel):
    items: list


class StatsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=10, ge=1, le=50)


class SlowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: int


def _result(ctx: RequestContext, operation: str, data) -> ToolResult:
    return ToolResult(tool_name="", tool_use_id="", success=True, operation=operation, scope=ctx.scope(), data=data)


@pytest.fixture
def ctx() -> RequestContext:
    return RequestContext(user_id="u1", channel=Channel.api, patient_id="10001217", session_id="s1")


@pytest.fixture
def research_ctx() -> RequestContext:
    return RequestContext(user_id="u1", channel=Channel.api, purpose=Purpose.research, roles=frozenset({"researcher"}))


@pytest.fixture
def audit() -> CollectingAuditSink:
    return CollectingAuditSink()


@pytest.fixture
def registry(audit) -> ToolRegistry:
    reg = ToolRegistry(audit=audit, max_visible_chars=500)

    async def labs_handler(ctx: RequestContext, args: LabsInput) -> ToolResult:
        rows = [Row(subject_id=args.subject_id, value=float(i)) for i in range(args.limit + 5)]
        return _result(ctx, "list_lab_observations", Page.from_items(rows, args.limit + 5))

    async def leaky_handler(ctx: RequestContext, args: LabsInput) -> ToolResult:
        rows = [Row(subject_id=99999999, value=1.0)]
        return _result(ctx, "list_lab_observations", Page.from_items(rows, 10))

    async def stats_handler(ctx: RequestContext, args: StatsInput) -> ToolResult:
        return _result(ctx, "top_diagnoses", [{"key": "A", "count": 3}])

    async def slow_handler(ctx: RequestContext, args: SlowInput) -> ToolResult:
        await asyncio.sleep(5)
        return _result(ctx, "slow", None)

    async def failing_handler(ctx: RequestContext, args: SlowInput) -> ToolResult:
        raise ProviderUnavailable("backend caido")

    reg.register(Tool(ToolContract(name="get_labs", description="Resultados de laboratorio del paciente activo.",
                                   input_model=LabsInput, output_model=LabsOutput, requires_patient_scope=True,
                                   audit_category=AuditCategory.clinical_data, data_categories=("labs",), max_rows=50), labs_handler))
    reg.register(Tool(ToolContract(name="leaky_labs", description="Tool de prueba que devuelve filas de otro paciente.",
                                   input_model=LabsInput, output_model=LabsOutput, requires_patient_scope=True,
                                   audit_category=AuditCategory.clinical_data), leaky_handler))
    reg.register(Tool(ToolContract(name="get_dataset_statistics", description="Estadisticas fijas del conjunto de datos.",
                                   input_model=StatsInput, output_model=LabsOutput, requires_patient_scope=False,
                                   requires_purpose=Purpose.research, audit_category=AuditCategory.dataset_aggregate), stats_handler))
    reg.register(Tool(ToolContract(name="slow_tool", description="Tool lenta de prueba para el timeout.",
                                   input_model=SlowInput, output_model=LabsOutput, requires_patient_scope=True,
                                   audit_category=AuditCategory.clinical_data, timeout_s=0.2), slow_handler))
    reg.register(Tool(ToolContract(name="failing_tool", description="Tool de prueba que falla en el proveedor.",
                                   input_model=SlowInput, output_model=LabsOutput, requires_patient_scope=True,
                                   audit_category=AuditCategory.clinical_data), failing_handler))
    return reg
