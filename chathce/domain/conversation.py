"""Conversaciones persistidas y registros de analisis."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AnalysisType = Literal["mixed", "database_query", "rag_search", "visualization", "general"]


class MessageMetadata(BaseModel):
    """Allowlist de metadata persistida con un mensaje del asistente (sin datos clinicos)."""

    model_config = ConfigDict(extra="forbid")
    tools_used: List[str] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: int = 0
    has_visualization: bool = False
    model_used: str = ""
    trace_id: Optional[str] = None


class ConversationSession(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    user_id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class StoredMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: Optional[str] = None
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    created_at: Optional[datetime] = None


class AnalysisRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    analysis_type: AnalysisType
    content: str
    results: Dict[str, Any] = Field(default_factory=dict)


CLINICAL_TOOL_NAMES = frozenset({
    "get_patient_summary", "get_admission_details", "get_diagnoses", "get_labs", "search_lab_items", "get_medications",
    "get_icu_stays", "get_icu_observations", "search_icd_codes", "get_dataset_statistics", "query_mimic_database",
})
KNOWLEDGE_TOOL_NAMES = frozenset({"search_clinical_documents"})
VISUALIZATION_TOOL_NAMES = frozenset({"create_visualization", "request_visualization"})


def classify_analysis(tools_used: List[str]) -> AnalysisType:
    """Tipo de analisis a partir de las tools usadas (regla heredada de la UI, extendida a las tools del core)."""
    if len(tools_used) > 1:
        return "mixed"
    if not tools_used:
        return "general"
    tool = tools_used[0]
    lowered = tool.lower()
    if tool in CLINICAL_TOOL_NAMES or "database" in lowered:
        return "database_query"
    if tool in KNOWLEDGE_TOOL_NAMES or "rag" in lowered:
        return "rag_search"
    if tool in VISUALIZATION_TOOL_NAMES or "visualization" in lowered:
        return "visualization"
    return "general"
