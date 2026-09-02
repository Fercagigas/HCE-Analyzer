"""ToolPolicy: limites deterministas antes y despues de ejecutar una tool (roadmap 07 P0.3/P0.6)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from chathce.domain.clinical import Page
from chathce.domain.context import RequestContext
from chathce.domain.tools import ToolContract, ToolError, ToolResult


class ToolPolicy:
    def check(self, ctx: RequestContext, contract: ToolContract, args: BaseModel) -> Optional[ToolError]:
        """Rechazos previos a la ejecucion: scope de paciente y proposito."""
        if contract.requires_patient_scope:
            if ctx.patient_id is None:
                return ToolError(
                    code="scope_refused",
                    message="No hay paciente activo en el contexto. Pida al usuario que seleccione un paciente antes de consultar sus datos.",
                )
            subject_id = getattr(args, "subject_id", None)
            if subject_id is not None and not ctx.allows_patient(subject_id):
                return ToolError(
                    code="scope_refused",
                    message=(
                        f"El paciente {subject_id} no es el paciente activo del contexto. "
                        "Solo se pueden consultar datos del paciente seleccionado."
                    ),
                )
        if contract.requires_purpose is not None and ctx.purpose != contract.requires_purpose:
            return ToolError(
                code="purpose_refused",
                message="Esta operacion solo esta disponible en modo investigacion (proposito research).",
            )
        return None

    def cap_rows(self, contract: ToolContract, result: ToolResult, requested_limit: Optional[int]) -> ToolResult:
        """Recorta filas al minimo entre lo pedido y el maximo del contrato; marca truncated."""
        limit = min(requested_limit or contract.max_rows, contract.max_rows)
        data = result.data
        if isinstance(data, Page):
            if len(data.items) > limit:
                data = Page(items=data.items[:limit], count=limit, limit=limit, truncated=True)
            elif data.limit != limit:
                data = Page(items=list(data.items), count=data.count, limit=limit, truncated=data.truncated)
            return result.model_copy(update={"data": data, "count": data.count, "limit": limit, "truncated": data.truncated})
        if isinstance(data, list):
            truncated = len(data) > limit
            data = data[:limit]
            return result.model_copy(update={"data": data, "count": len(data), "limit": limit, "truncated": truncated or result.truncated})
        return result.model_copy(update={"limit": limit})

    def validate_output(self, ctx: RequestContext, contract: ToolContract, result: ToolResult) -> Optional[ToolError]:
        """Ninguna fila devuelta puede pertenecer a otro paciente (defensa en profundidad)."""
        if not contract.requires_patient_scope or ctx.patient_id is None:
            return None
        rows: Any = result.data.items if isinstance(result.data, Page) else result.data
        candidates = rows if isinstance(rows, list) else [rows]
        for row in candidates:
            subject = getattr(row, "subject_id", None)
            if subject is None and isinstance(row, dict):
                subject = row.get("subject_id")
            if subject is not None and not ctx.allows_patient(subject):
                return ToolError(
                    code="scope_refused",
                    message="El resultado contenia datos de otro paciente y ha sido descartado.",
                )
        return None
