"""SupabaseAnalysisRepository: public.analyses (codigo movido de supabase_services.AnalysisService)."""

from __future__ import annotations

from typing import Any, Dict

from chathce.adapters.supabase._common import run_blocking
from chathce.domain.context import RequestContext
from chathce.domain.conversation import AnalysisRecord


class SupabaseAnalysisRepository:
    def __init__(self, client: Any, *, timeout_s: float = 30.0):
        self._client = client
        self._timeout = timeout_s

    async def save(self, ctx: RequestContext, record: AnalysisRecord) -> bool:
        def do():
            payload = {
                "user_id": record.user_id, "analysis_type": record.analysis_type,
                "content": record.content, "results": record.results,
            }
            result = self._client.table("analyses").insert(payload).execute()
            return bool(result.data)

        try:
            return await run_blocking(do, what="guardado de analisis", timeout_s=self._timeout)
        except Exception:  # noqa: BLE001 - el registro de analisis nunca bloquea el flujo
            return False

    async def stats(self, ctx: RequestContext) -> Dict[str, Any]:
        def do():
            result = self._client.table("analyses").select("analysis_type").eq("user_id", ctx.user_id).execute()
            rows = result.data or []
            by_type: Dict[str, int] = {}
            for row in rows:
                key = row.get("analysis_type", "unknown")
                by_type[key] = by_type.get(key, 0) + 1
            return {"total_analyses": len(rows), "by_type": by_type}

        try:
            return await run_blocking(do, what="estadisticas de analisis", timeout_s=self._timeout)
        except Exception as exc:  # noqa: BLE001
            return {"total_analyses": 0, "by_type": {}, "error": exc.__class__.__name__}
