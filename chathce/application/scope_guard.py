"""ScopeGuard: enforcement determinista de scope y proposito delante de cualquier ClinicalDataProvider.

Implementa el mismo port y se coloca en el composition root, de modo que no exista
ruta de codigo que llegue al provider sin pasar por aqui (roadmap 05 P0.5/P0.6, 07 P0.3).
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, List, Literal, Optional, Sequence, Tuple, TypeVar

from chathce.application.audit_events import emit_safely, make_audit_event
from chathce.domain.audit import AuditAction
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
from chathce.domain.errors import DomainError, PurposeNotAllowed, ScopeViolation

T = TypeVar("T")

DATA_CATEGORIES = {
    "get_patient": ["demographics"],
    "get_patient_summary": ["demographics", "admissions", "diagnoses", "labs", "medications", "icu"],
    "list_admissions": ["admissions"],
    "get_admission_details": ["admissions", "diagnoses", "procedures", "transfers", "icu"],
    "list_conditions": ["diagnoses"],
    "list_lab_observations": ["labs"],
    "list_medications": ["medications"],
    "list_icu_stays": ["icu"],
    "list_icu_observations": ["icu"],
    "search_lab_items": [],
    "search_icu_items": [],
    "search_icd_codes": [],
    "get_dataset_summary": ["aggregate"],
    "top_diagnoses": ["aggregate"],
    "top_drugs": ["aggregate"],
    "admission_type_distribution": ["aggregate"],
}


def _row_count(result: Any) -> Optional[int]:
    if isinstance(result, Page):
        return result.count
    return None


def _truncated(result: Any) -> Optional[bool]:
    if isinstance(result, Page):
        return result.truncated
    return None


class ScopeGuard:
    """Envuelve un ClinicalDataProvider aplicando scope/proposito y emitiendo auditoria."""

    def __init__(self, inner: Any, audit: Optional[Any] = None):
        self._inner = inner
        self._audit = audit
        self.source_name = getattr(inner, "source_name", "unknown")

    # ------------------------------------------------------------------
    async def _guarded(self, ctx: RequestContext, operation: str, call: Callable[[], Awaitable[T]]) -> T:
        started = time.perf_counter()
        try:
            result = await call()
        except DomainError as exc:
            await emit_safely(self._audit, make_audit_event(
                ctx, action=AuditAction.clinical_query, outcome="failure", component="clinical_data",
                operation=operation, error_code=exc.code, error_class=exc.__class__.__name__,
                latency_ms=int((time.perf_counter() - started) * 1000),
                data_categories=DATA_CATEGORIES.get(operation, []),
            ))
            raise
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.clinical_query, outcome="success", component="clinical_data",
            operation=operation, row_count=_row_count(result), truncated=_truncated(result),
            latency_ms=int((time.perf_counter() - started) * 1000),
            data_categories=DATA_CATEGORIES.get(operation, []),
        ))
        return result

    async def _refuse(self, ctx: RequestContext, operation: str, exc: DomainError) -> None:
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.tool_refused, outcome="refused", component="clinical_data",
            operation=operation, error_code=exc.code, error_class=exc.__class__.__name__,
            attributes={"reason": getattr(exc, "reason", exc.code)},
        ))
        raise exc

    async def _require_patient(self, ctx: RequestContext, operation: str, subject_id: int) -> None:
        try:
            ctx.require_patient(subject_id)
        except ScopeViolation as exc:
            await self._refuse(ctx, operation, exc)

    async def _require_admission(self, ctx: RequestContext, operation: str, hadm_id: int) -> None:
        try:
            ctx.require_patient()
            owner_subject, owner_hadm = await self._inner.resolve_admission_owner(hadm_id)
            ctx.require_patient(owner_subject)
            ctx.require_encounter(owner_hadm)
        except ScopeViolation as exc:
            await self._refuse(ctx, operation, exc)

    async def _require_icu_stay(self, ctx: RequestContext, operation: str, stay_id: int) -> None:
        try:
            ctx.require_patient()
            owner_subject, owner_hadm = await self._inner.resolve_icu_stay_owner(stay_id)
            ctx.require_patient(owner_subject)
            ctx.require_encounter(owner_hadm)
        except ScopeViolation as exc:
            await self._refuse(ctx, operation, exc)

    async def _require_research(self, ctx: RequestContext, operation: str) -> None:
        try:
            ctx.require_research()
        except PurposeNotAllowed as exc:
            await self._refuse(ctx, operation, exc)

    # ------------------------------------------------------------------
    # port
    # ------------------------------------------------------------------
    async def get_patient(self, ctx: RequestContext, subject_id: int) -> Patient:
        await self._require_patient(ctx, "get_patient", subject_id)
        return await self._guarded(ctx, "get_patient", lambda: self._inner.get_patient(ctx, subject_id))

    async def get_patient_summary(self, ctx: RequestContext, subject_id: int) -> PatientSummary:
        await self._require_patient(ctx, "get_patient_summary", subject_id)
        return await self._guarded(ctx, "get_patient_summary", lambda: self._inner.get_patient_summary(ctx, subject_id))

    async def list_admissions(self, ctx: RequestContext, subject_id: int, *, limit: int = 50) -> Page[Admission]:
        await self._require_patient(ctx, "list_admissions", subject_id)
        return await self._guarded(ctx, "list_admissions", lambda: self._inner.list_admissions(ctx, subject_id, limit=limit))

    async def get_admission_details(self, ctx: RequestContext, hadm_id: int) -> AdmissionDetails:
        await self._require_admission(ctx, "get_admission_details", hadm_id)
        return await self._guarded(ctx, "get_admission_details", lambda: self._inner.get_admission_details(ctx, hadm_id))

    async def list_conditions(self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None,
                              limit: int = 100) -> Page[Condition]:
        await self._require_patient(ctx, "list_conditions", subject_id)
        if hadm_id is not None:
            await self._require_admission(ctx, "list_conditions", hadm_id)
        return await self._guarded(ctx, "list_conditions",
                                   lambda: self._inner.list_conditions(ctx, subject_id=subject_id, hadm_id=hadm_id, limit=limit))

    async def list_lab_observations(self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None,
                                    itemids: Optional[Sequence[int]] = None, label_contains: Optional[str] = None,
                                    time_range: Optional[TimeRange] = None, abnormal_only: bool = False,
                                    limit: int = 100) -> Page[LabObservation]:
        await self._require_patient(ctx, "list_lab_observations", subject_id)
        if hadm_id is not None:
            await self._require_admission(ctx, "list_lab_observations", hadm_id)
        return await self._guarded(ctx, "list_lab_observations", lambda: self._inner.list_lab_observations(
            ctx, subject_id=subject_id, hadm_id=hadm_id, itemids=itemids, label_contains=label_contains,
            time_range=time_range, abnormal_only=abnormal_only, limit=limit))

    async def search_lab_items(self, ctx: RequestContext, *, label_contains: str, limit: int = 50) -> Page[LabItem]:
        return await self._guarded(ctx, "search_lab_items",
                                   lambda: self._inner.search_lab_items(ctx, label_contains=label_contains, limit=limit))

    async def list_medications(self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None,
                               drug_contains: Optional[str] = None, include_emar: bool = False,
                               limit: int = 100) -> Page[Medication]:
        await self._require_patient(ctx, "list_medications", subject_id)
        if hadm_id is not None:
            await self._require_admission(ctx, "list_medications", hadm_id)
        return await self._guarded(ctx, "list_medications", lambda: self._inner.list_medications(
            ctx, subject_id=subject_id, hadm_id=hadm_id, drug_contains=drug_contains, include_emar=include_emar, limit=limit))

    async def list_icu_stays(self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None,
                             limit: int = 20) -> Page[IcuStay]:
        await self._require_patient(ctx, "list_icu_stays", subject_id)
        if hadm_id is not None:
            await self._require_admission(ctx, "list_icu_stays", hadm_id)
        return await self._guarded(ctx, "list_icu_stays",
                                   lambda: self._inner.list_icu_stays(ctx, subject_id=subject_id, hadm_id=hadm_id, limit=limit))

    async def list_icu_observations(self, ctx: RequestContext, *, stay_id: int, itemids: Optional[Sequence[int]] = None,
                                    label_contains: Optional[str] = None, time_range: Optional[TimeRange] = None,
                                    limit: int = 200) -> Page[IcuObservation]:
        await self._require_icu_stay(ctx, "list_icu_observations", stay_id)
        return await self._guarded(ctx, "list_icu_observations", lambda: self._inner.list_icu_observations(
            ctx, stay_id=stay_id, itemids=itemids, label_contains=label_contains, time_range=time_range, limit=limit))

    async def search_icu_items(self, ctx: RequestContext, *, label_contains: str, limit: int = 50) -> Page[IcuItem]:
        return await self._guarded(ctx, "search_icu_items",
                                   lambda: self._inner.search_icu_items(ctx, label_contains=label_contains, limit=limit))

    async def search_icd_codes(self, ctx: RequestContext, *, code_prefix: Optional[str] = None,
                               title_contains: Optional[str] = None, icd_version: Optional[int] = None,
                               kind: Literal["diagnosis", "procedure"] = "diagnosis", limit: int = 50) -> Page[IcdCodeEntry]:
        return await self._guarded(ctx, "search_icd_codes", lambda: self._inner.search_icd_codes(
            ctx, code_prefix=code_prefix, title_contains=title_contains, icd_version=icd_version, kind=kind, limit=limit))

    async def get_dataset_summary(self, ctx: RequestContext) -> DatasetSummary:
        await self._require_research(ctx, "get_dataset_summary")
        return await self._guarded(ctx, "get_dataset_summary", lambda: self._inner.get_dataset_summary(ctx))

    async def top_diagnoses(self, ctx: RequestContext, *, limit: int = 20, icd_version: Optional[int] = None) -> FrequencyResult:
        await self._require_research(ctx, "top_diagnoses")
        return await self._guarded(ctx, "top_diagnoses", lambda: self._inner.top_diagnoses(ctx, limit=limit, icd_version=icd_version))

    async def top_drugs(self, ctx: RequestContext, *, limit: int = 20) -> FrequencyResult:
        await self._require_research(ctx, "top_drugs")
        return await self._guarded(ctx, "top_drugs", lambda: self._inner.top_drugs(ctx, limit=limit))

    async def admission_type_distribution(self, ctx: RequestContext) -> FrequencyResult:
        await self._require_research(ctx, "admission_type_distribution")
        return await self._guarded(ctx, "admission_type_distribution", lambda: self._inner.admission_type_distribution(ctx))

    async def resolve_admission_owner(self, hadm_id: int) -> Tuple[int, int]:
        return await self._inner.resolve_admission_owner(hadm_id)

    async def resolve_icu_stay_owner(self, stay_id: int) -> Tuple[int, int]:
        return await self._inner.resolve_icu_stay_owner(stay_id)

    async def health(self) -> ProviderHealth:
        return await self._inner.health()
