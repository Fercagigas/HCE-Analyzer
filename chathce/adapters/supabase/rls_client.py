"""Resolucion de cliente RLS por RequestContext.

Los tests pueden seguir pasando un cliente en memoria; produccion recibe una
factoria que construye un cliente con el JWT de la peticion.
"""
from typing import Any

from chathce.domain.context import RequestContext


def client_for(client_or_factory: Any, ctx: RequestContext) -> Any:
    return client_or_factory(ctx) if callable(client_or_factory) else client_or_factory
