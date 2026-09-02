"""Sinks de auditoria: JSONL en fichero (rotacion diaria) y stdout. Sin PHI (garantizado por AuditEvent)."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Optional

from chathce.adapters.memory.audit import NullAuditSink
from chathce.domain.audit import AuditEvent

AUDIT_LOGGER_NAME = "chathce.audit"


class JsonlFileAuditSink:
    def __init__(self, directory: Path | str, *, filename: str = "audit.jsonl", backup_days: int = 30):
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger(AUDIT_LOGGER_NAME)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        if not any(isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in self._logger.handlers):
            handler = logging.handlers.TimedRotatingFileHandler(
                self._directory / filename, when="midnight", backupCount=backup_days, encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    async def emit(self, event: AuditEvent) -> None:
        self._logger.info(event.model_dump_json())


class StdoutAuditSink:
    def __init__(self, stream: Any = None):
        self._stream = stream or sys.stdout

    async def emit(self, event: AuditEvent) -> None:
        self._stream.write(event.model_dump_json() + "\n")


def build_audit_sink(settings: Any) -> Any:
    """Selecciona el sink segun ``AUDIT_SINK`` (jsonl | stdout | null). Por defecto jsonl en logs/audit."""
    kind = str(getattr(getattr(settings, "audit", None), "sink", "jsonl") or "jsonl").lower()
    directory = getattr(getattr(settings, "audit", None), "directory", "logs/audit")
    if kind == "null":
        return NullAuditSink()
    if kind == "stdout":
        return StdoutAuditSink()
    try:
        return JsonlFileAuditSink(directory)
    except OSError:  # pragma: no cover - sistema de ficheros no escribible
        return StdoutAuditSink()
