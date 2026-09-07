"""AsyncRunner: ejecuta corrutinas del core desde codigo sincrono (Streamlit, LangChain legacy, CLI).

Mantiene un unico event loop en un hilo dedicado para no crear un loop por llamada y
conservar vivos los clientes asincronos.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Awaitable, Optional, TypeVar

T = TypeVar("T")


class AsyncRunner:
    def __init__(self, *, name: str = "chathce-async-runner"):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._name = name

    def _ensure(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._loop is None or self._loop.is_closed():
                loop = asyncio.new_event_loop()
                thread = threading.Thread(target=loop.run_forever, name=self._name, daemon=True)
                thread.start()
                self._loop, self._thread = loop, thread
            return self._loop

    def run(self, coro: Awaitable[T], *, timeout: Optional[float] = None) -> T:
        """Bloquea el hilo llamante hasta que la corrutina termine (o expire)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("AsyncRunner.run no puede usarse dentro de un event loop activo; use await")
        loop = self._ensure()
        future: Future = asyncio.run_coroutine_threadsafe(coro, loop)  # type: ignore[arg-type]
        return future.result(timeout=timeout)

    def close(self) -> None:
        with self._lock:
            if self._loop is not None and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._loop.stop)
                if self._thread is not None:
                    self._thread.join(timeout=5)
                self._loop.close()
            self._loop, self._thread = None, None


_default_runner: Optional[AsyncRunner] = None
_default_lock = threading.Lock()


def get_default_runner() -> AsyncRunner:
    global _default_runner
    with _default_lock:
        if _default_runner is None:
            _default_runner = AsyncRunner()
        return _default_runner


def run_sync(coro: Awaitable[T], *, timeout: Optional[float] = 120.0) -> T:
    return get_default_runner().run(coro, timeout=timeout)
