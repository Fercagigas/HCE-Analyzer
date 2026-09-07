"""Middlewares: correlacion (X-Trace-Id / X-Request-Id + audit http_request) y cabeceras de seguridad."""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from chathce.application.audit_events import emit_safely
from chathce.domain.audit import AuditAction, AuditEvent

_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


def _incoming_trace_id(request: Request) -> str:
    raw = request.headers.get("x-trace-id", "").strip()
    return raw if raw and _ID_PATTERN.match(raw) else uuid.uuid4().hex


class CorrelationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, *, audit: Optional[Any] = None, tenant_id: str = "default"):
        super().__init__(app)
        self._audit = audit
        self._tenant = tenant_id

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        request.state.trace_id = _incoming_trace_id(request)
        request.state.request_id = uuid.uuid4().hex
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            latency = int((time.perf_counter() - started) * 1000)
            route = request.scope.get("route")
            template = getattr(route, "path", request.url.path)
            await emit_safely(self._audit, AuditEvent(
                event_id=uuid.uuid4().hex, timestamp=datetime.now(timezone.utc), action=AuditAction.http_request,
                outcome="success" if status < 400 else "failure", component="api", tenant_id=self._tenant,
                user_id=getattr(request.state, "user_id", None), trace_id=request.state.trace_id,
                request_id=request.state.request_id, channel="api", latency_ms=latency,
                attributes={"method": request.method, "route_template": str(template)[:200], "status": status},
            ))
        response.headers["X-Trace-Id"] = request.state.trace_id
        response.headers["X-Request-Id"] = request.state.request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response
