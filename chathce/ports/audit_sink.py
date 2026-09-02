"""Port de auditoria."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from chathce.domain.audit import AuditEvent


@runtime_checkable
class AuditSink(Protocol):
    async def emit(self, event: AuditEvent) -> None: ...
