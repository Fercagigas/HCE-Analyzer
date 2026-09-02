"""Contratos del caso de uso de chat: request, response y eventos de streaming (roadmap 03 P0.3/P0.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from chathce.domain.context import Purpose, ScopeApplied
from chathce.domain.evidence import Claim, Evidence
from chathce.domain.knowledge import Source


class ToolCallSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_name: str
    tool_use_id: str
    operation: str
    success: bool
    count: int = 0
    truncated: bool = False
    elapsed_ms: int = 0
    error_code: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class ChatMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str
    tool_summaries: Optional[List[ToolCallSummary]] = None


class ChatOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_context_messages: int = Field(default=10, ge=0, le=30)
    include_sources: bool = True
    enable_visualizations: bool = True
    language: str = "es"


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=5000)
    session_id: Optional[str] = None
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    purpose: Purpose = Purpose.clinical_care
    history: Optional[List[ChatMessageIn]] = None
    options: ChatOptions = Field(default_factory=ChatOptions)


class VisualizationRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    viz_id: str
    title: str
    viz_type: str
    format: Literal["plotly_json"] = "plotly_json"


class Uncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: Literal["low", "medium", "high"] = "low"
    notes: List[str] = Field(default_factory=list)
    unresolved_tool_errors: List[str] = Field(default_factory=list)
    scope_refusals: List[str] = Field(default_factory=list)


class ChatMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: Optional[str] = None
    trace_id: str
    request_id: str
    model_requested: str = ""
    model_used: str = ""
    fallback_used: bool = False
    tokens_input: int = 0
    tokens_output: int = 0
    iterations: int = 0
    latency_ms: int = 0
    prompt_version: str = ""
    timestamp: datetime
    cached: bool = False


class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    suggestions: List[str] = Field(default_factory=list)
    retryable: bool = False


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    content: str
    facts: List[Claim] = Field(default_factory=list)
    inferences: List[Claim] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)
    tool_calls: List[ToolCallSummary] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    visualizations: List[VisualizationRef] = Field(default_factory=list)
    metadata: ChatMetadata
    error: Optional[ErrorInfo] = None


# ---------------------------------------------------------------------------
# Eventos de streaming (alto nivel; nunca chain-of-thought)
# ---------------------------------------------------------------------------

class StatusEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["status"] = "status"
    stage: Literal["thinking", "retrieving_evidence", "generating", "fallback"]
    message: str = ""
    model: Optional[str] = None
    iteration: int = 0


class ToolCallEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["tool_call"] = "tool_call"
    tool_use_id: str
    tool_name: str
    operation: str = ""
    scope: ScopeApplied
    arguments: Dict[str, Any] = Field(default_factory=dict)
    iteration: int = 0


class ToolResultSummaryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["tool_result_summary"] = "tool_result_summary"
    summary: ToolCallSummary
    visualization_ids: List[str] = Field(default_factory=list)
    iteration: int = 0


class TextDeltaEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text_delta"] = "text_delta"
    text: str
    iteration: int = 0


class CompleteEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["complete"] = "complete"
    response: ChatResponse


class ErrorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["error"] = "error"
    error: ErrorInfo
    trace_id: str
    request_id: str


ChatEvent = Annotated[
    Union[StatusEvent, ToolCallEvent, ToolResultSummaryEvent, TextDeltaEvent, CompleteEvent, ErrorEvent],
    Field(discriminator="type"),
]
