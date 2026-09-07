"""Artefactos de visualizacion (figura Plotly serializada, nunca codigo)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

ALLOWED_VISUALIZATION_TYPES = ("timeline", "comparison", "bar", "histogram")


class VisualizationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    viz_id: str
    tenant_id: str
    user_id: str
    session_id: Optional[str] = None
    title: str
    viz_type: str
    figure_json: str
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, str] = Field(default_factory=dict)
