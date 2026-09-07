"""GET /api/v1/patients/{subject_id}/summary: resumen determinista sin LLM."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request

from chathce.api.dependencies import get_container, get_principal, make_context
from chathce.composition.container import Container
from chathce.domain.clinical import PatientSummary
from chathce.domain.identity import Principal

router = APIRouter(prefix="/api/v1", tags=["patients"])


@router.get("/patients/{subject_id}/summary", response_model=PatientSummary, response_model_exclude_none=True)
async def patient_summary(request: Request, subject_id: int = Path(gt=0), principal: Principal = Depends(get_principal),
                          container: Container = Depends(get_container)) -> PatientSummary:
    ctx = make_context(request, principal, patient_id=str(subject_id))
    return await container.patient_summary_service.get_summary(ctx, subject_id)
