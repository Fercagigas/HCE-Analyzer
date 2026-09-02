"""Sinks de auditoria en memoria."""

from __future__ import annotations

import re
from typing import List

from chathce.domain.audit import AuditEvent

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class NullAuditSink:
    async def emit(self, event: AuditEvent) -> None:  # pragma: no cover - trivial
        return None


class CollectingAuditSink:
    """Guarda los eventos para aseverar secuencias y ausencia de PHI en tests."""

    def __init__(self) -> None:
        self.events: List[AuditEvent] = []

    async def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    def actions(self) -> List[str]:
        return [e.action.value for e in self.events]

    def phi_findings(self) -> List[str]:
        """Heuristica: emails o cadenas largas en cualquier campo de texto."""
        findings: List[str] = []
        for event in self.events:
            payload = event.model_dump_json()
            if _EMAIL.search(payload):
                findings.append(f"{event.event_id}: email")
            for value in event.attributes.values():
                if isinstance(value, str) and len(value) > 200:
                    findings.append(f"{event.event_id}: texto largo en attributes")
        return findings
