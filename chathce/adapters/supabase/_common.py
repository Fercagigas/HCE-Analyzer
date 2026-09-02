"""Utilidades comunes de los adapters Supabase (ejecucion en hilo y traduccion de errores)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar

from chathce.domain.errors import ProviderUnavailable

T = TypeVar("T")


async def run_blocking(fn: Callable[[], T], *, what: str, timeout_s: float = 30.0) -> T:
    try:
        return await asyncio.wait_for(asyncio.to_thread(fn), timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        raise ProviderUnavailable(f"Tiempo de espera agotado en {what}") from exc


def sanitize_error(exc: BaseException) -> str:
    """Mensaje sin URLs ni claves."""
    text = str(exc).split("http", 1)[0].strip()
    return (text or exc.__class__.__name__)[:200]


def parse_dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
