"""Limitador de peticiones por usuario (en memoria; movido y simplificado desde services/rate_limiter.py).

Se aplica en ChatService por ``ctx.user_id`` (nunca por session_id), de modo que
Streamlit y la API comparten la misma politica.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict

from chathce.domain.errors import RateLimited


@dataclass
class RateLimitConfig:
    per_minute: int = 30
    per_hour: int = 300
    burst: int = 5
    burst_window_s: float = 10.0
    max_message_length: int = 5000
    lockout_s: float = 60.0


@dataclass
class _Entry:
    hits: Deque[float] = field(default_factory=deque)
    blocked_until: float = 0.0


class RateLimiter:
    def __init__(self, config: RateLimitConfig | None = None, *, clock=time.monotonic):
        self.config = config or RateLimitConfig()
        self._clock = clock
        self._entries: Dict[str, _Entry] = defaultdict(_Entry)
        self._lock = threading.Lock()

    def validate_message_length(self, message: str) -> None:
        if len(message) > self.config.max_message_length:
            raise ValueError(f"El mensaje supera la longitud máxima de {self.config.max_message_length} caracteres")

    def check(self, user_id: str) -> None:
        now = self._clock()
        cfg = self.config
        with self._lock:
            entry = self._entries[user_id]
            if entry.blocked_until > now:
                raise RateLimited(
                    f"Demasiadas solicitudes. Intente de nuevo en {int(entry.blocked_until - now) + 1} segundos.",
                    retry_after_s=entry.blocked_until - now,
                )
            while entry.hits and now - entry.hits[0] > 3600:
                entry.hits.popleft()
            last_minute = sum(1 for t in entry.hits if now - t <= 60)
            last_burst = sum(1 for t in entry.hits if now - t <= cfg.burst_window_s)
            if len(entry.hits) >= cfg.per_hour or last_minute >= cfg.per_minute or last_burst >= cfg.burst:
                entry.blocked_until = now + cfg.lockout_s
                raise RateLimited(
                    f"Demasiadas solicitudes. Intente de nuevo en {int(cfg.lockout_s)} segundos.",
                    retry_after_s=cfg.lockout_s,
                )
            entry.hits.append(now)

    def usage(self, user_id: str) -> Dict[str, int]:
        now = self._clock()
        with self._lock:
            entry = self._entries.get(user_id)
            hits = list(entry.hits) if entry else []
        return {"last_minute": sum(1 for t in hits if now - t <= 60), "last_hour": len(hits)}
