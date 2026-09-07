"""Construccion de Evidence a partir de DTOs clinicos (Fase 1: solo referencias, no motor de evidencia)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional

from chathce.domain.context import RequestContext
from chathce.domain.evidence import Evidence, EvidenceType, Provenance

MAX_EVIDENCE_PER_RESULT = 50


def _first(obj: Any, *names: str) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def evidence_from_dtos(
    ctx: RequestContext,
    dtos: Iterable[Any],
    *,
    tool_name: str,
    provider: str,
    source_system: str,
    kind: EvidenceType = EvidenceType.clinical_record,
) -> List[Evidence]:
    now = datetime.now(timezone.utc)
    out: List[Evidence] = []
    for dto in dtos:
        evidence_id = getattr(dto, "evidence_id", None)
        if not evidence_id:
            continue
        parts = str(evidence_id).split(":", 2)
        resource_type = parts[1] if len(parts) > 1 else "record"
        resource_id = parts[2] if len(parts) > 2 else str(evidence_id)
        value = _first(dto, "valuenum", "value", "drug", "title", "admission_type", "first_careunit")
        hadm = _first(dto, "hadm_id")
        out.append(Evidence(
            evidence_id=str(evidence_id), type=kind, source_system=source_system, resource_type=resource_type,
            resource_id=resource_id, patient_id=(str(_first(dto, "subject_id")) if _first(dto, "subject_id") is not None else ctx.patient_id),
            encounter_id=str(hadm) if hadm is not None else None,
            timestamp=_first(dto, "charttime", "admittime", "starttime", "intime"),
            original_value=None if value is None else str(value), units=_first(dto, "valueuom"),
            provenance=Provenance(tool_name=tool_name, tool_use_id="", trace_id=ctx.trace_id, retrieved_at=now, provider=provider),
        ))
        if len(out) >= MAX_EVIDENCE_PER_RESULT:
            break
    return out
