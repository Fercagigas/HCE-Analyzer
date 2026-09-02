"""Port de preferencias de usuario."""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

from chathce.domain.context import RequestContext


@runtime_checkable
class UserPreferencesRepository(Protocol):
    async def load(self, ctx: RequestContext) -> Dict[str, Any]: ...

    async def save(self, ctx: RequestContext, preferences: Dict[str, Any]) -> bool: ...
