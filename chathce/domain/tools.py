"""Contratos de tools (roadmap 07 P0.1) y envoltorio de resultado.

El contrato es la unica fuente de lo que el modelo ve de una tool (nombre,
descripcion, schema de entrada). Ninguno de esos textos puede contener SQL,
nombres de esquema ni de tabla; ``assert_no_schema_leak`` lo verifica al
construir el contrato y los tests lo vuelven a comprobar sobre el prompt.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from chathce.domain.context import Purpose, ScopeApplied
from chathce.domain.evidence import Evidence
from chathce.domain.knowledge import Source

MAX_TOOL_ROWS = 200
DEFAULT_TOOL_ROWS = 100

MIMIC_TABLE_NAMES: Tuple[str, ...] = (
    "patients", "admissions", "transfers", "services", "diagnoses_icd", "procedures_icd",
    "d_icd_diagnoses", "d_icd_procedures", "labevents", "d_labitems", "microbiologyevents",
    "omr", "prescriptions", "pharmacy", "emar", "icustays", "chartevents", "d_items",
)

LLM_VISIBLE_FORBIDDEN_PATTERN = re.compile(
    r"\b(sql|select|custom_query|table_name|mimic_ed|mimiciv_hosp|mimiciv_icu|"
    + "|".join(re.escape(t) for t in MIMIC_TABLE_NAMES)
    + r")\b",
    re.IGNORECASE,
)


def assert_no_schema_leak(text: str, *, where: str = "texto visible al modelo") -> None:
    match = LLM_VISIBLE_FORBIDDEN_PATTERN.search(text or "")
    if match:
        raise ValueError(f"{where} expone un termino prohibido al modelo: {match.group(0)!r}")


class ToolPermission(str, Enum):
    read_only = "read_only"
    compute = "compute"


class AuditCategory(str, Enum):
    clinical_data = "clinical_data"
    dataset_aggregate = "dataset_aggregate"
    knowledge = "knowledge"
    visualization = "visualization"


class ToolContract(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    version: str = "1"
    description: str = Field(min_length=10)
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    permissions: ToolPermission = ToolPermission.read_only
    requires_patient_scope: bool
    requires_purpose: Optional[Purpose] = None
    timeout_s: float = Field(default=30.0, gt=0, le=120)
    max_rows: int = Field(default=DEFAULT_TOOL_ROWS, ge=1, le=MAX_TOOL_ROWS)
    audit_category: AuditCategory
    data_categories: Tuple[str, ...] = ()

    @field_validator("description")
    @classmethod
    def _description_has_no_schema(cls, value: str) -> str:
        assert_no_schema_leak(value, where="La descripcion de la tool")
        return value

    @model_validator(mode="after")
    def _input_model_is_closed(self) -> "ToolContract":
        extra = self.input_model.model_config.get("extra")
        if extra != "forbid":
            raise ValueError(f"input_model de {self.name!r} debe declarar extra='forbid' (tiene {extra!r})")
        schema_text = str(self.input_schema())
        assert_no_schema_leak(schema_text, where=f"El schema de entrada de {self.name!r}")
        return self

    def input_schema(self) -> Dict[str, Any]:
        schema = self.input_model.model_json_schema()
        schema.pop("title", None)
        schema["additionalProperties"] = False
        return schema

    def output_schema(self) -> Dict[str, Any]:
        return self.output_model.model_json_schema()


ToolErrorCode = Literal[
    "unknown_tool", "invalid_input", "scope_refused", "purpose_refused",
    "timeout", "provider_unavailable", "not_found", "internal",
]


class ToolError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: ToolErrorCode
    message: str
    retryable: bool = False


class ToolArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visualization_ids: List[str] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)


class ToolResult(BaseModel):
    """Resultado de una invocacion de tool. Nunca se lanza: los fallos van en ``error``."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    tool_name: str
    tool_use_id: str
    contract_version: str = "1"
    success: bool
    operation: str
    permissions: ToolPermission = ToolPermission.read_only
    scope: ScopeApplied
    data: Any = None
    count: int = 0
    limit: int = DEFAULT_TOOL_ROWS
    truncated: bool = False
    timeout_s: float = 30.0
    elapsed_ms: int = 0
    error: Optional[ToolError] = None
    evidence: List[Evidence] = Field(default_factory=list)
    artifacts: ToolArtifacts = Field(default_factory=ToolArtifacts)
    model_visible_text: str = ""

    @property
    def evidence_ids(self) -> List[str]:
        return [e.evidence_id for e in self.evidence]

    @classmethod
    def failure(
        cls,
        *,
        tool_name: str,
        tool_use_id: str,
        scope: ScopeApplied,
        code: ToolErrorCode,
        message: str,
        operation: str = "unknown",
        retryable: bool = False,
        timeout_s: float = 30.0,
        elapsed_ms: int = 0,
        contract_version: str = "1",
    ) -> "ToolResult":
        return cls(
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            contract_version=contract_version,
            success=False,
            operation=operation,
            scope=scope,
            timeout_s=timeout_s,
            elapsed_ms=elapsed_ms,
            error=ToolError(code=code, message=message, retryable=retryable),
        )
