"""PatientSummaryService: resumen determinista del paciente sin LLM (para /api/v1/patients/{id}/summary)."""

from __future__ import annotations

from typing import Any

from chathce.domain.clinical import PatientSummary
from chathce.domain.context import RequestContext


class PatientSummaryService:
    def __init__(self, provider: Any):
        self._provider = provider

    async def get_summary(self, ctx: RequestContext, subject_id: int) -> PatientSummary:
        scoped = ctx if ctx.patient_id == str(subject_id) else ctx.with_patient(str(subject_id), ctx.encounter_id)
        return await self._provider.get_patient_summary(scoped, subject_id)
