"""Port de acceso clinico read-only con operaciones allowlisted (ADR 0010 §3, roadmap 04).

Toda operacion recibe ``ctx: RequestContext`` como primer argumento. No existe
ninguna operacion generica por tabla ni acepta SQL. El enforcement de scope lo
aplica ``ScopeGuard`` envolviendo cualquier implementacion; el adapter, ademas,
filtra siempre por paciente (defensa en profundidad).
"""

from __future__ import annotations

from typing import Literal, Optional, Protocol, Sequence, Tuple, runtime_checkable

from chathce.domain.clinical import (
    Admission,
    AdmissionDetails,
    Condition,
    DatasetSummary,
    FrequencyResult,
    IcdCodeEntry,
    IcuItem,
    IcuObservation,
    IcuStay,
    LabItem,
    LabObservation,
    Medication,
    Page,
    Patient,
    PatientSummary,
    ProviderHealth,
    TimeRange,
)
from chathce.domain.context import RequestContext

# Nombres canonicos de operacion (se usan en ToolResult.operation, audit y golden set).
CLINICAL_OPERATIONS: Tuple[str, ...] = (
    "get_patient",
    "get_patient_summary",
    "list_admissions",
    "get_admission_details",
    "list_conditions",
    "list_lab_observations",
    "search_lab_items",
    "list_medications",
    "list_icu_stays",
    "list_icu_observations",
    "search_icu_items",
    "search_icd_codes",
    "get_dataset_summary",
    "top_diagnoses",
    "top_drugs",
    "admission_type_distribution",
)

PATIENT_SCOPED_OPERATIONS = frozenset({
    "get_patient", "get_patient_summary", "list_admissions", "get_admission_details", "list_conditions",
    "list_lab_observations", "list_medications", "list_icu_stays", "list_icu_observations",
})
RESEARCH_OPERATIONS = frozenset({"get_dataset_summary", "top_diagnoses", "top_drugs", "admission_type_distribution"})


@runtime_checkable
class ClinicalDataProvider(Protocol):
    source_name: str

    # Paciente / episodio -------------------------------------------------
    async def get_patient(self, ctx: RequestContext, subject_id: int) -> Patient: ...

    async def get_patient_summary(self, ctx: RequestContext, subject_id: int) -> PatientSummary: ...

    async def list_admissions(self, ctx: RequestContext, subject_id: int, *, limit: int = 50) -> Page[Admission]: ...

    async def get_admission_details(self, ctx: RequestContext, hadm_id: int) -> AdmissionDetails: ...

    # Diagnosticos --------------------------------------------------------
    async def list_conditions(
        self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None, limit: int = 100,
    ) -> Page[Condition]: ...

    # Laboratorio ---------------------------------------------------------
    async def list_lab_observations(
        self,
        ctx: RequestContext,
        *,
        subject_id: int,
        hadm_id: Optional[int] = None,
        itemids: Optional[Sequence[int]] = None,
        label_contains: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
        abnormal_only: bool = False,
        limit: int = 100,
    ) -> Page[LabObservation]: ...

    async def search_lab_items(self, ctx: RequestContext, *, label_contains: str, limit: int = 50) -> Page[LabItem]: ...

    # Medicacion ----------------------------------------------------------
    async def list_medications(
        self,
        ctx: RequestContext,
        *,
        subject_id: int,
        hadm_id: Optional[int] = None,
        drug_contains: Optional[str] = None,
        include_emar: bool = False,
        limit: int = 100,
    ) -> Page[Medication]: ...

    # UCI -----------------------------------------------------------------
    async def list_icu_stays(
        self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None, limit: int = 20,
    ) -> Page[IcuStay]: ...

    async def list_icu_observations(
        self,
        ctx: RequestContext,
        *,
        stay_id: int,
        itemids: Optional[Sequence[int]] = None,
        label_contains: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
        limit: int = 200,
    ) -> Page[IcuObservation]: ...

    async def search_icu_items(self, ctx: RequestContext, *, label_contains: str, limit: int = 50) -> Page[IcuItem]: ...

    # Diccionario ICD (sin scope de paciente) -----------------------------
    async def search_icd_codes(
        self,
        ctx: RequestContext,
        *,
        code_prefix: Optional[str] = None,
        title_contains: Optional[str] = None,
        icd_version: Optional[int] = None,
        kind: Literal["diagnosis", "procedure"] = "diagnosis",
        limit: int = 50,
    ) -> Page[IcdCodeEntry]: ...

    # Agregados fijos (purpose=research) ---------------------------------
    async def get_dataset_summary(self, ctx: RequestContext) -> DatasetSummary: ...

    async def top_diagnoses(
        self, ctx: RequestContext, *, limit: int = 20, icd_version: Optional[int] = None,
    ) -> FrequencyResult: ...

    async def top_drugs(self, ctx: RequestContext, *, limit: int = 20) -> FrequencyResult: ...

    async def admission_type_distribution(self, ctx: RequestContext) -> FrequencyResult: ...

    # Resolucion de propietario (uso interno del ScopeGuard) --------------
    async def resolve_admission_owner(self, hadm_id: int) -> Tuple[int, int]:
        """(subject_id, hadm_id) o NotFound."""
        ...

    async def resolve_icu_stay_owner(self, stay_id: int) -> Tuple[int, int]:
        """(subject_id, hadm_id) o NotFound."""
        ...

    async def health(self) -> ProviderHealth: ...
