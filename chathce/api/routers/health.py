"""/health (liveness) y /ready (readiness por componente, sin secretos)."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from chathce import __version__
from chathce.api.dependencies import get_container
from chathce.composition.container import Container

router = APIRouter()


@router.get("/health", tags=["ops"])
async def health() -> Dict[str, Any]:
    return {"status": "ok", "version": __version__, "time": datetime.now(timezone.utc).isoformat()}


async def _check(name: str, coro, timeout: float = 10.0) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        ok = bool(getattr(result, "ok", True))
        detail = str(getattr(result, "detail", "") or "")[:200]
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"{exc.__class__.__name__}: {str(exc)[:160]}"
    return {"name": name, "ok": ok, "latency_ms": int((time.perf_counter() - started) * 1000), "detail": detail}


@router.get("/ready", tags=["ops"])
async def ready(request: Request, container: Container = Depends(get_container)) -> JSONResponse:
    cache = getattr(request.app.state, "ready_cache", None)
    ttl = getattr(request.app.state, "ready_cache_s", 300)
    now = time.monotonic()
    if cache and now - cache["at"] < ttl:
        payload = cache["payload"]
    else:
        model = container.gateway._config.model_chain[0]
        checks = await asyncio.gather(
            _check("clinical_data", container.clinical_provider.health()),
            _check("llm", container.llm_provider.health(model)),
            _check("knowledge", container.knowledge.health(), timeout=60.0),
        )
        checks = list(checks) + [{"name": "identity", "ok": container.identity is not None, "latency_ms": 0, "detail": type(container.identity).__name__}]
        critical_ok = all(c["ok"] for c in checks if c["name"] in ("clinical_data", "llm", "identity"))
        payload = {
            "status": "ready" if critical_ok else "degraded",
            "version": __version__,
            "profile": container.profile,
            "components": checks,
            "time": datetime.now(timezone.utc).isoformat(),
        }
        request.app.state.ready_cache = {"at": now, "payload": payload}
    return JSONResponse(status_code=200 if payload["status"] == "ready" else 503, content=payload)
