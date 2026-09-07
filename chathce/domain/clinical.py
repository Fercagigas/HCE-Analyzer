"""DTOs clinicos canonicos (ADR 0010 §3).

El agente y la aplicacion solo conocen estos tipos; nunca tablas ni columnas.
Cada recurso lleva ``evidence_id`` determinista ``"<source>:<resource>:<id>"``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

_frozen = ConfigDict(frozen=True, extra="forbid")


class Patient(BaseModel):
    model_config = _frozen
    subject_id: int
    gender: Optional[str] = None
    anchor_age: Optional[int] = None
    anchor_year_group: Optional[str] = None
    deceased: bool = False
    date_of_death: Optional[date] = None
    race: Optional[str] = None
    evidence_id: str


class Admission(BaseModel):
    """Encounter canonico (hospitalizacion)."""

    model_config = _frozen
    hadm_id: int
    subject_id: int
    admittime: Optional[datetime] = None
    dischtime: Optional[datetime] = None
    admission_type: Optional[str] = None
    admission_location: Optional[str] = None
    discharge_location: Optional[str] = None
    insurance: Optional[str] = None
    race: Optional[str] = None
    hospital_expire_flag: bool = False
    length_of_stay_days: Optional[float] = None
    evidence_id: str


class Transfer(BaseModel):
    model_config = _frozen
    transfer_id: int
    subject_id: int
    hadm_id: Optional[int] = None
    eventtype: Optional[str] = None
    careunit: Optional[str] = None
    intime: Optional[datetime] = None
    outtime: Optional[datetime] = None
    evidence_id: str


class ServiceEpisode(BaseModel):
    model_config = _frozen
    subject_id: int
    hadm_id: int
    transfertime: Optional[datetime] = None
    prev_service: Optional[str] = None
    curr_service: Optional[str] = None
    evidence_id: str


class Condition(BaseModel):
    model_config = _frozen
    subject_id: int
    hadm_id: int
    seq_num: int
    icd_code: str
    icd_version: int
    title: Optional[str] = None
    evidence_id: str


class Procedure(BaseModel):
    model_config = _frozen
    subject_id: int
    hadm_id: int
    seq_num: int
    chartdate: Optional[date] = None
    icd_code: str
    icd_version: int
    title: Optional[str] = None
    evidence_id: str


class LabObservation(BaseModel):
    model_config = _frozen
    labevent_id: int
    subject_id: int
    hadm_id: Optional[int] = None
    itemid: int
    label: Optional[str] = None
    fluid: Optional[str] = None
    category: Optional[str] = None
    charttime: Optional[datetime] = None
    value: Optional[str] = None
    valuenum: Optional[float] = None
    valueuom: Optional[str] = None
    ref_range_lower: Optional[float] = None
    ref_range_upper: Optional[float] = None
    flag: Optional[str] = None
    evidence_id: str


class Medication(BaseModel):
    model_config = _frozen
    source: Literal["prescription", "emar"]
    subject_id: int
    hadm_id: Optional[int] = None
    drug: str
    starttime: Optional[datetime] = None
    stoptime: Optional[datetime] = None
    dose_val_rx: Optional[str] = None
    dose_unit_rx: Optional[str] = None
    route: Optional[str] = None
    event_txt: Optional[str] = None
    evidence_id: str


class IcuStay(BaseModel):
    model_config = _frozen
    stay_id: int
    hadm_id: int
    subject_id: int
    first_careunit: Optional[str] = None
    last_careunit: Optional[str] = None
    intime: Optional[datetime] = None
    outtime: Optional[datetime] = None
    los_days: Optional[float] = None
    evidence_id: str


class IcuObservation(BaseModel):
    model_config = _frozen
    stay_id: int
    subject_id: int
    hadm_id: Optional[int] = None
    itemid: int
    label: Optional[str] = None
    category: Optional[str] = None
    param_type: Optional[str] = None
    charttime: Optional[datetime] = None
    value: Optional[str] = None
    valuenum: Optional[float] = None
    valueuom: Optional[str] = None
    evidence_id: str


class IcdCodeEntry(BaseModel):
    model_config = _frozen
    icd_code: str
    icd_version: int
    long_title: str
    kind: Literal["diagnosis", "procedure"] = "diagnosis"


class LabItem(BaseModel):
    model_config = _frozen
    itemid: int
    label: str
    fluid: Optional[str] = None
    category: Optional[str] = None


class IcuItem(BaseModel):
    model_config = _frozen
    itemid: int
    label: str
    category: Optional[str] = None
    unitname: Optional[str] = None
    param_type: Optional[str] = None


class TimeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class Page(BaseModel, Generic[T]):
    """Pagina acotada de resultados; ``truncated`` indica que habia mas filas."""

    model_config = ConfigDict(extra="forbid")
    items: List[T]
    count: int
    limit: int
    truncated: bool = False

    @classmethod
    def from_items(cls, items: List[T], limit: int) -> "Page[T]":
        truncated = len(items) > limit
        kept = items[:limit]
        return cls(items=kept, count=len(kept), limit=limit, truncated=truncated)


class PatientSummaryStats(BaseModel):
    model_config = _frozen
    total_admissions: int = 0
    total_icu_stays: int = 0
    distinct_diagnoses: int = 0
    distinct_medications: int = 0
    first_admission: Optional[datetime] = None
    last_admission: Optional[datetime] = None


class PatientSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient: Patient
    admissions: List[Admission] = Field(default_factory=list)
    conditions: List[Condition] = Field(default_factory=list)
    recent_labs: List[LabObservation] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)
    icu_stays: List[IcuStay] = Field(default_factory=list)
    stats: PatientSummaryStats = Field(default_factory=PatientSummaryStats)
    truncated: Dict[str, bool] = Field(default_factory=dict)


class AdmissionDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")
    admission: Admission
    conditions: List[Condition] = Field(default_factory=list)
    procedures: List[Procedure] = Field(default_factory=list)
    transfers: List[Transfer] = Field(default_factory=list)
    services: List[ServiceEpisode] = Field(default_factory=list)
    icu_stays: List[IcuStay] = Field(default_factory=list)


class FrequencyBucket(BaseModel):
    model_config = _frozen
    key: str
    label: Optional[str] = None
    count: int


class FrequencyResult(BaseModel):
    """Agregado fijo del dataset; nunca contiene identificadores de paciente."""

    model_config = ConfigDict(extra="forbid")
    operation: str
    buckets: List[FrequencyBucket]
    total_rows: int
    limit: int
    truncated: bool = False
    computed_at: datetime
    source: str


class DatasetSummary(BaseModel):
    model_config = _frozen
    patients: int
    admissions: int
    icu_stays: int
    diagnoses: int
    lab_events: int
    prescriptions: int
    source: str
    computed_at: datetime


class ProviderHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool
    latency_ms: Optional[int] = None
    detail: str = ""  # nunca incluye secretos ni URLs con credenciales


def evidence_id(source: str, resource_type: str, resource_id: object) -> str:
    return f"{source}:{resource_type}:{resource_id}"
