"""SupabaseUserPreferencesRepository: public.user_preferences (movido de supabase_services.UserPreferencesService)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from chathce.adapters.supabase._common import run_blocking
from chathce.domain.context import RequestContext

DEFAULT_PREFERENCES: Dict[str, Any] = {
    "show_tool_usage": True,
    "show_performance": True,
    "show_sources": True,
    "enable_visualizations": True,
    "max_context_messages": 10,
    "theme": "default",
    "language": "es",
}


class SupabaseUserPreferencesRepository:
    def __init__(self, client: Any, *, timeout_s: float = 30.0):
        self._client = client
        self._timeout = timeout_s

    async def load(self, ctx: RequestContext) -> Dict[str, Any]:
        def do():
            result = self._client.table("user_preferences").select("*").eq("user_id", ctx.user_id).limit(1).execute()
            merged = dict(DEFAULT_PREFERENCES)
            if result.data:
                merged.update(result.data[0].get("preferences") or {})
            return merged

        try:
            return await run_blocking(do, what="preferencias", timeout_s=self._timeout)
        except Exception:  # noqa: BLE001
            return dict(DEFAULT_PREFERENCES)

    async def save(self, ctx: RequestContext, preferences: Dict[str, Any]) -> bool:
        def do():
            record = {"user_id": ctx.user_id, "preferences": preferences, "updated_at": datetime.now(timezone.utc).isoformat()}
            self._client.table("user_preferences").upsert(record, on_conflict="user_id").execute()
            return True

        try:
            return await run_blocking(do, what="guardado de preferencias", timeout_s=self._timeout)
        except Exception:  # noqa: BLE001
            return False
