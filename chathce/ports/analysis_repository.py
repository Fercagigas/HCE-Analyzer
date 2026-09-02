"""Port de registro de analisis (tabla public.analyses)."""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

from chathce.domain.context import RequestContext
from chathce.domain.conversation import AnalysisRecord


@runtime_checkable
class AnalysisRepository(Protocol):
    async def save(self, ctx: RequestContext, record: AnalysisRecord) -> bool: ...

    async def stats(self, ctx: RequestContext) -> Dict[str, Any]: ...
