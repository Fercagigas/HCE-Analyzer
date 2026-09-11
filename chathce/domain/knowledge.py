"""Modelos de conocimiento documental (RAG) y fuentes citadas."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(str, Enum):
    """Estado de gobierno de un documento del corpus clinico."""

    draft = "draft"
    approved = "approved"
    retired = "retired"


class Source(BaseModel):
    """Fuente documental citada; formato compatible con el render actual de la UI."""

    model_config = ConfigDict(extra="forbid")
    filename: str
    page: Optional[int] = None
    specialty: Optional[str] = None
    doc_type: Optional[str] = None
    tool: str = "search_clinical_documents"
    retrieved_content: str = ""
    evidence_id: str
    score: Optional[float] = None
    version: str = "legacy-test"
    status: DocumentStatus = DocumentStatus.approved
    effective_from: date = date(1970, 1, 1)
    effective_to: Optional[date] = None


class KnowledgeHit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    document_id: Optional[str] = None
    filename: str
    page: Optional[int] = None
    specialty: Optional[str] = None
    doc_type: Optional[str] = None
    content: str
    score: Optional[float] = None
    tenant_id: str = "default"
    document_key: Optional[str] = None
    version: str = "legacy-test"
    effective_from: date = date(1970, 1, 1)
    effective_to: Optional[date] = None
    status: DocumentStatus = DocumentStatus.approved
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    content_hash: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    filename: str
    title: Optional[str] = None
    doc_type: Optional[str] = None
    specialty: Optional[str] = None
    chunks: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    tenant_id: str = "default"
    document_key: Optional[str] = None
    version: str = "legacy-test"
    effective_from: date = date(1970, 1, 1)
    effective_to: Optional[date] = None
    status: DocumentStatus = DocumentStatus.approved
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    content_hash: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UploadResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    document_id: Optional[str] = None
    filename: str
    chunks_processed: int = 0
    message: str = ""
    error: Optional[str] = None
    status: DocumentStatus = DocumentStatus.draft
    content_hash: Optional[str] = None
    security_flags: List[str] = Field(default_factory=list)


class KnowledgeStats(BaseModel):
    model_config = ConfigDict(extra="allow")
    total_documents: int = 0
    unique_sources: int = 0
    sources: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
