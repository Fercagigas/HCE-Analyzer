"""create_app: FastAPI sobre el composition root (un worker en Fase 1 por el singleton CUDA del RAG)."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chathce import __version__
from chathce.api.errors import install_exception_handlers
from chathce.api.middleware import CorrelationMiddleware, SecurityHeadersMiddleware
from chathce.api.routers import chat, health, patients, visualizations
from chathce.composition.container import Container, build_container

logger = logging.getLogger(__name__)


def _api_settings(settings: Any) -> Any:
    api = getattr(settings, "api", None)
    if api is None:
        from types import SimpleNamespace

        api = SimpleNamespace(cors_allowed_origins=[], docs_enabled=True, sse_ping_s=15, ready_cache_s=300, environment="dev")
    return api


def create_app(container: Optional[Container] = None, settings: Any = None) -> FastAPI:
    if settings is None and container is not None:
        settings = container.settings
    if settings is None:
        from config.settings import get_settings

        settings = get_settings()
    api = _api_settings(settings)
    production = str(getattr(api, "environment", "dev")).lower() == "prod"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if getattr(app.state, "container", None) is None:
            app.state.container = build_container(settings)
            logger.info("Contenedor construido para la API: %s", app.state.container.profile)
        knowledge = getattr(app.state.container, "knowledge", None)
        if knowledge is not None and hasattr(knowledge, "health"):
            try:  # precarga del RAG (embeddings) fuera del primer request
                await asyncio.wait_for(knowledge.health(), timeout=120)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Precarga de conocimiento no disponible: %s", exc.__class__.__name__)
        yield

    app = FastAPI(
        title="ChatHCE API", version=__version__, lifespan=lifespan,
        docs_url="/docs" if getattr(api, "docs_enabled", True) and not production else None,
        openapi_url="/openapi.json" if getattr(api, "docs_enabled", True) and not production else None,
        redoc_url=None,
    )
    app.state.container = container
    app.state.sse_ping_s = getattr(api, "sse_ping_s", 15)
    app.state.ready_cache_s = getattr(api, "ready_cache_s", 300)

    origins = list(getattr(api, "cors_allowed_origins", []) or [])
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                           allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Trace-Id"])
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationMiddleware, audit=container.audit if container is not None else None)

    install_exception_handlers(app, production=production)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(patients.router)
    app.include_router(visualizations.router)
    return app


# `python -m uvicorn chathce.api.app:app --host 127.0.0.1 --port 8000 --workers 1`
app = create_app()
