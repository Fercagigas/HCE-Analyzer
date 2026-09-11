"""Administracion minima de roles y relaciones asistenciales, reservada a admin."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import FrozenSet, Optional

from fastapi import APIRouter, Depends, Path, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from chathce.api.dependencies import get_container, get_principal, make_context, require_endpoint
from chathce.application.audit_events import emit_safely, make_audit_event
from chathce.composition.container import Container
from chathce.domain.audit import AuditAction
from chathce.domain.authorization import EndpointAction, normalize_roles
from chathce.domain.context import Purpose
from chathce.domain.identity import Principal

router = APIRouter(prefix="/api/v1/admin", tags=["authorization"])


class RoleAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    roles: FrozenSet[str] = Field(min_length=1)


class PatientAccessGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=100)
    subject_id: int = Field(gt=0)
    service_id: str = Field(min_length=1, max_length=100)
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None

    @field_validator("valid_from", "valid_until")
    @classmethod
    def timezone_required(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and value.tzinfo is None:
            raise ValueError("las fechas deben incluir zona horaria")
        return value

    @model_validator(mode="after")
    def valid_window(self) -> "PatientAccessGrant":
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until debe ser posterior a valid_from")
        return self


@router.put("/users/{user_id}/roles", status_code=204)
async def assign_roles(request: Request, body: RoleAssignment, user_id: str = Path(min_length=1, max_length=100),
                       principal: Principal = Depends(get_principal), container: Container = Depends(get_container)) -> None:
    require_endpoint(principal, EndpointAction.authorization_manage)
    roles = frozenset(role.value for role in normalize_roles(body.roles))
    ctx = make_context(request, principal, purpose=Purpose.admin)
    await container.identity.assign_roles(user_id=user_id, tenant_id=ctx.tenant_id, roles=roles)
    await emit_safely(container.audit, make_audit_event(
        ctx, action=AuditAction.authorization_changed, outcome="success", component="identity",
        operation="assign_roles", attributes={"component_detail": "roles"},
    ))


@router.put("/patient-access", status_code=204)
async def grant_patient_access(request: Request, body: PatientAccessGrant, principal: Principal = Depends(get_principal),
                               container: Container = Depends(get_container)) -> None:
    require_endpoint(principal, EndpointAction.authorization_manage)
    ctx = make_context(request, principal, purpose=Purpose.admin)
    await container.identity.grant_patient_access(
        user_id=body.user_id, tenant_id=ctx.tenant_id, subject_id=body.subject_id, service_id=body.service_id,
        valid_from=body.valid_from, valid_until=body.valid_until, granted_by=principal.user_id,
    )
    await emit_safely(container.audit, make_audit_event(
        ctx, action=AuditAction.authorization_changed, outcome="success", component="identity",
        operation="grant_patient_access", attributes={"component_detail": "patient_access"},
    ))
