"""Evento de auditoria estructurado sin PHI (roadmap 12).

Se registran identificadores, categorias y metricas; nunca texto de mensajes,
resultados de tools, emails ni tokens. El validador de ``attributes`` rechaza
claves que sugieran contenido y valores largos.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chathce.domain.context import Channel

ALLOWED_ATTRIBUTE_KEYS = frozenset({
    "method", "route_template", "status", "iteration", "stop_reason", "fallback_from", "fallback_to",
    "viz_type", "statistic", "provider", "reason", "count", "limit", "component_detail",
})
FORBIDDEN_ATTRIBUTE_KEYS = frozenset({"message", "content", "query", "email", "token", "data", "prompt", "response"})
MAX_ATTRIBUTE_LENGTH = 200


class AuditAction(str, Enum):
    http_request = "http_request"
    chat_started = "chat_started"
    chat_completed = "chat_completed"
    chat_failed = "chat_failed"
    llm_call = "llm_call"
    llm_fallback = "llm_fallback"
    tool_call = "tool_call"
    tool_refused = "tool_refused"
    tool_failed = "tool_failed"
    clinical_query = "clinical_query"
    knowledge_query = "knowledge_query"
    auth_login = "auth_login"
    auth_verify_failed = "auth_verify_failed"
    session_restored = "session_restored"
    visualization_created = "visualization_created"


AuditOutcome = Literal["success", "failure", "refused"]
AuditComponent = Literal[
    "api", "streamlit", "chat_service", "gateway", "tool", "clinical_data", "knowledge", "identity", "evaluation",
]
AttributeValue = Union[str, int, float, bool]


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    timestamp: datetime
    action: AuditAction
    outcome: AuditOutcome
    component: AuditComponent
    tenant_id: str
    user_id: Optional[str] = None
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: str
    request_id: str
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    channel: Optional[Channel] = None
    tool_name: Optional[str] = None
    operation: Optional[str] = None
    data_categories: List[str] = Field(default_factory=list)
    row_count: Optional[int] = None
    truncated: Optional[bool] = None
    model_requested: Optional[str] = None
    model_used: Optional[str] = None
    prompt_version: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    latency_ms: Optional[int] = None
    error_code: Optional[str] = None
    error_class: Optional[str] = None
    attributes: Dict[str, AttributeValue] = Field(default_factory=dict)

    @field_validator("attributes")
    @classmethod
    def _attributes_are_safe(cls, value: Dict[str, AttributeValue]) -> Dict[str, AttributeValue]:
        for key, item in value.items():
            lowered = key.lower()
            if lowered in FORBIDDEN_ATTRIBUTE_KEYS or any(f in lowered for f in FORBIDDEN_ATTRIBUTE_KEYS):
                raise ValueError(f"attributes[{key!r}] podria contener PHI o secretos; clave no permitida")
            if key not in ALLOWED_ATTRIBUTE_KEYS:
                raise ValueError(f"attributes[{key!r}] no esta en la allowlist de auditoria")
            if isinstance(item, str) and len(item) > MAX_ATTRIBUTE_LENGTH:
                raise ValueError(f"attributes[{key!r}] supera {MAX_ATTRIBUTE_LENGTH} caracteres")
        return value
