"""GET /api/v1/visualizations/{viz_id}: figura Plotly (JSON) del usuario autenticado."""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from chathce.api.dependencies import get_container, get_principal, make_context
from chathce.composition.container import Container
from chathce.domain.errors import NotFound
from chathce.domain.identity import Principal

router = APIRouter(prefix="/api/v1", tags=["visualizations"])


@router.get("/visualizations/{viz_id}")
async def get_visualization(request: Request, viz_id: str, principal: Principal = Depends(get_principal),
                            container: Container = Depends(get_container)) -> Dict[str, Any]:
    ctx = make_context(request, principal)
    artifact = await container.visualizations.get(ctx, viz_id)
    if artifact is None:
        raise NotFound("Visualizacion no encontrada o expirada")
    return {
        "viz_id": artifact.viz_id, "title": artifact.title, "viz_type": artifact.viz_type, "format": "plotly_json",
        "created_at": artifact.created_at.isoformat(), "expires_at": artifact.expires_at.isoformat(),
        "figure": json.loads(artifact.figure_json),
    }
