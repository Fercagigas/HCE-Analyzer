"""Schemas Evidence y Claim (roadmap 09, Fase 1: solo schemas; el Evidence Engine es Fase 3)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EvidenceType(str, Enum):
    clinical_record = "clinical_record"
    guideline_document = "guideline_document"
    dataset_aggregate = "dataset_aggregate"
    calculation = "calculation"


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tool_name: str
    tool_use_id: str
    trace_id: str
    retrieved_at: datetime
    provider: str


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    evidence_id: str
    type: EvidenceType
    source_system: str
    resource_type: str
    resource_id: str
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    original_value: Optional[str] = None
    units: Optional[str] = None
    excerpt: Optional[str] = None
    page: Optional[int] = None
    provenance: Provenance


class ClaimType(str, Enum):
    OBSERVED_FACT = "OBSERVED_FACT"
    GUIDELINE_STATEMENT = "GUIDELINE_STATEMENT"
    CALCULATION = "CALCULATION"
    AI_INFERENCE = "AI_INFERENCE"
    UNKNOWN = "UNKNOWN"


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    type: ClaimType
    text: str
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    uncertainty_note: Optional[str] = None
