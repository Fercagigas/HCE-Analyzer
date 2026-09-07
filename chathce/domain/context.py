"""RequestContext: contexto obligatorio de toda operacion clinica o generacion (ADR 0010 §2).

Ninguna tool puede reconstruir este contexto desde globals ni desde el prompt.
Los identificadores son ``str`` (neutralidad FHIR); la conversion a ``int`` para
MIMIC vive en el adapter.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet, Optional

from pydantic import BaseModel, ConfigDict, Field

from chathce.domain.errors import PurposeNotAllowed, ScopeViolation


class Purpose(str, Enum):
    clinical_care = "clinical_care"
    research = "research"
    admin = "admin"


class Channel(str, Enum):
    api = "api"
    streamlit = "streamlit"
    evaluation = "evaluation"
    cli = "cli"


RESEARCH_ROLE = "researcher"


def new_id() -> str:
    return uuid.uuid4().hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScopeApplied(BaseModel):
    """Scope efectivo que se registra en cada ToolResult y AuditEvent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    purpose: Purpose


class RequestContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str = "default"
    user_id: str = Field(min_length=1)
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: str = Field(default_factory=new_id, min_length=8)
    request_id: str = Field(default_factory=new_id, min_length=8)
    purpose: Purpose = Purpose.clinical_care
    roles: FrozenSet[str] = frozenset()
    channel: Channel
    locale: str = "es"
    created_at: datetime = Field(default_factory=utc_now)

    # ------------------------------------------------------------------
    def allows_patient(self, subject_id: int | str) -> bool:
        return self.patient_id is not None and str(subject_id) == str(self.patient_id)

    def allows_encounter(self, hadm_id: int | str) -> bool:
        """True si no hay episodio fijado o coincide con el fijado."""
        return self.encounter_id is None or str(hadm_id) == str(self.encounter_id)

    def require_patient(self, subject_id: int | str | None = None) -> str:
        if self.patient_id is None:
            raise ScopeViolation(
                "No hay paciente activo en el contexto; seleccione un paciente antes de consultar datos clinicos.",
                reason="patient_scope_required",
            )
        if subject_id is not None and not self.allows_patient(subject_id):
            raise ScopeViolation(
                "El paciente solicitado no coincide con el paciente activo del contexto.",
                reason="patient_mismatch",
            )
        return self.patient_id

    def require_encounter(self, hadm_id: int | str) -> None:
        if not self.allows_encounter(hadm_id):
            raise ScopeViolation(
                "El episodio solicitado no coincide con el episodio activo del contexto.",
                reason="encounter_mismatch",
            )

    def require_research(self) -> None:
        if self.purpose != Purpose.research:
            raise PurposeNotAllowed(
                "Las estadisticas del conjunto de datos solo estan disponibles en modo investigacion."
            )

    def scope(self) -> ScopeApplied:
        return ScopeApplied(
            tenant_id=self.tenant_id,
            patient_id=self.patient_id,
            encounter_id=self.encounter_id,
            purpose=self.purpose,
        )

    def with_patient(self, patient_id: Optional[str], encounter_id: Optional[str] = None) -> "RequestContext":
        return self.model_copy(update={"patient_id": patient_id, "encounter_id": encounter_id})


def build_context(
    *,
    user_id: str,
    channel: Channel,
    roles: FrozenSet[str] | set[str] | None = None,
    purpose: Purpose | str = Purpose.clinical_care,
    patient_id: Optional[str] = None,
    encounter_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tenant_id: str = "default",
    trace_id: Optional[str] = None,
) -> RequestContext:
    """Construye un RequestContext aplicando la regla de autorizacion de proposito.

    ``purpose=research`` exige el rol ``researcher``; en caso contrario se rechaza.
    """
    roles_fs = frozenset(roles or ())
    purpose_enum = Purpose(purpose)
    if purpose_enum == Purpose.research and RESEARCH_ROLE not in roles_fs:
        raise PurposeNotAllowed("El usuario no tiene el rol 'researcher' necesario para el modo investigacion.")
    return RequestContext(
        tenant_id=tenant_id,
        user_id=user_id,
        patient_id=str(patient_id) if patient_id is not None else None,
        encounter_id=str(encounter_id) if encounter_id is not None else None,
        session_id=session_id,
        trace_id=trace_id or new_id(),
        purpose=purpose_enum,
        roles=roles_fs,
        channel=channel,
    )
