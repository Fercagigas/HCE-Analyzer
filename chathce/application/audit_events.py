"""Fabrica de AuditEvent a partir de un RequestContext."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from chathce.domain.audit import AuditAction, AuditComponent, AuditEvent, AuditOutcome
from chathce.domain.context import RequestContext


def make_audit_event(
    ctx: RequestContext,
    *,
    action: AuditAction,
    outcome: AuditOutcome,
    component: AuditComponent,
    **fields: Any,
) -> AuditEvent:
    return AuditEvent(
        event_id=uuid.uuid4().hex,
        timestamp=datetime.now(timezone.utc),
        action=action,
        outcome=outcome,
        component=component,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        patient_id=ctx.patient_id,
        encounter_id=ctx.encounter_id,
        session_id=ctx.session_id,
        trace_id=ctx.trace_id,
        request_id=ctx.request_id,
        channel=ctx.channel,
        **fields,
    )


async def emit_safely(sink: Optional[Any], event: AuditEvent) -> None:
    """La auditoria nunca rompe el flujo principal."""
    if sink is None:
        return
    try:
        await sink.emit(event)
    except Exception:  # noqa: BLE001 - pragma: no cover
        return
