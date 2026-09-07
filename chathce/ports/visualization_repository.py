"""Port de artefactos de visualizacion (figura serializada por viz_id, acotado por usuario)."""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from chathce.domain.context import RequestContext
from chathce.domain.visualization import VisualizationArtifact


@runtime_checkable
class VisualizationRepository(Protocol):
    async def put(self, ctx: RequestContext, artifact: VisualizationArtifact) -> str: ...

    async def get(self, ctx: RequestContext, viz_id: str) -> Optional[VisualizationArtifact]:
        """None si no existe, expiro o no pertenece al usuario del contexto."""
        ...

    async def list_for_session(self, ctx: RequestContext, session_id: str) -> List[VisualizationArtifact]: ...
