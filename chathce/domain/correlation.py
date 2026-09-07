"""Propagacion del RequestContext por ContextVar (trazas y logging)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from chathce.domain.context import RequestContext, new_id

current_context: ContextVar[Optional[RequestContext]] = ContextVar("chathce_current_context", default=None)


def new_trace_id() -> str:
    return new_id()


def new_request_id() -> str:
    return new_id()


@contextmanager
def bind_context(ctx: RequestContext) -> Iterator[RequestContext]:
    token = current_context.set(ctx)
    try:
        yield ctx
    finally:
        current_context.reset(token)


class TraceLogFilter(logging.Filter):
    """Anade trace_id/request_id/tenant_id a cada registro de logging."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = current_context.get()
        record.trace_id = ctx.trace_id if ctx else "-"
        record.request_id = ctx.request_id if ctx else "-"
        record.tenant_id = ctx.tenant_id if ctx else "-"
        return True
