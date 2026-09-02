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


def classify_analysis(tools_used: List[str]) -> AnalysisType:
    """Regla heredada de ui/unified_chat_interface.py::_save_analysis (caracterizada en WP1)."""
    if len(tools_used) > 1:
        return "mixed"
    joined = str(tools_used).lower()
    if "query_mimic_database" in tools_used or "database" in joined:
        return "database_query"
    if "rag" in joined:
        return "rag_search"
    if "visualization" in joined:
        return "visualization"
    return "general"
