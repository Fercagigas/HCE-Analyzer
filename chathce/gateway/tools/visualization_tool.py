"""Tool de visualizacion determinista: datos via ClinicalDataProvider, figura via plantillas Plotly (ADR 0040)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from chathce.domain.clinical import TimeRange
from chathce.domain.context import RequestContext
from chathce.domain.errors import ToolValidationError
from chathce.domain.tools import AuditCategory, ToolArtifacts, ToolContract, ToolResult
from chathce.gateway.tool_registry import Tool

MAX_POINTS = 5000


class VisualizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visualization_type: Literal["timeline", "comparison", "bar", "histogram"] = Field(description="Tipo de grafico")
    source: Literal["labs", "icu_observations", "medications"] = Field(description="Origen de los datos del paciente activo")
    subject_id: int = Field(description="Identificador del paciente activo", gt=0)
    hadm_id: Optional[int] = Field(None, description="Limitar a un ingreso", gt=0)
    stay_id: Optional[int] = Field(None, description="Estancia en UCI (obligatoria para icu_observations)", gt=0)
    itemids: Optional[List[int]] = Field(None, description="Identificadores de prueba/medicion a representar", max_length=5)
    label_contains: Optional[str] = Field(None, description="Nombre (o parte) de la prueba o medicion a representar", max_length=80)
    start: Optional[datetime] = Field(None, description="Inicio del intervalo temporal")
    end: Optional[datetime] = Field(None, description="Fin del intervalo temporal")
    title: Optional[str] = Field(None, description="Titulo del grafico", max_length=200)


class VisualizationOutput(BaseModel):
    model_config = ConfigDict(extra="allow")


def _time_range(start, end) -> Optional[TimeRange]:
    return TimeRange(start=start, end=end) if (start or end) else None


def _frame_from_observations(items: List[Any]) -> pd.DataFrame:
    rows = [{"charttime": o.charttime, "label": o.label or str(o.itemid), "valuenum": o.valuenum} for o in items if o.valuenum is not None]
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    wide = frame.pivot_table(index="charttime", columns="label", values="valuenum", aggfunc="mean").reset_index()
    wide.columns = [str(c) for c in wide.columns]
    return wide.sort_values("charttime")


def build_visualization_tool(provider: Any, visualizations: Any) -> Tool:
    from chathce.adapters.visualization.plotly_templates import create_allowlisted_visualization, figure_to_json

    async def create(ctx: RequestContext, args: VisualizationInput) -> ToolResult:
        if args.source == "icu_observations":
            if args.stay_id is None:
                raise ToolValidationError("icu_observations requiere stay_id")
            page = await provider.list_icu_observations(ctx, stay_id=args.stay_id, itemids=args.itemids,
                                                        label_contains=args.label_contains, time_range=_time_range(args.start, args.end),
                                                        limit=200)
            frame = _frame_from_observations(page.items)
            metrics = [c for c in frame.columns if c != "charttime"][:5] if not frame.empty else []
            kwargs: Dict[str, Any] = {"metrics": metrics or None, "time_column": "charttime"}
        elif args.source == "labs":
            page = await provider.list_lab_observations(ctx, subject_id=args.subject_id, hadm_id=args.hadm_id, itemids=args.itemids,
                                                        label_contains=args.label_contains, time_range=_time_range(args.start, args.end),
                                                        limit=200)
            frame = _frame_from_observations(page.items)
            metrics = [c for c in frame.columns if c != "charttime"][:5] if not frame.empty else []
            kwargs = {"metrics": metrics or None, "time_column": "charttime"}
        else:
            page = await provider.list_medications(ctx, subject_id=args.subject_id, hadm_id=args.hadm_id,
                                                   drug_contains=args.label_contains, limit=200)
            frame = pd.DataFrame([{"drug": m.drug} for m in page.items])
            kwargs = {"category_column": "drug" if not frame.empty else None}

        if frame.empty:
            return ToolResult(tool_name="", tool_use_id="", success=False, operation="create_visualization", scope=ctx.scope(),
                              error={"code": "not_found", "message": "No hay datos para representar con esos criterios."})  # type: ignore[arg-type]

        viz_type = args.visualization_type
        if args.source == "medications" and viz_type in ("timeline", "comparison"):
            viz_type = "bar"
        if viz_type == "histogram" and args.source != "medications":
            kwargs = {"metrics": (kwargs.get("metrics") or [None])[:1]}
        result = create_allowlisted_visualization(viz_type, frame.head(MAX_POINTS), title=args.title, **kwargs)
        if not result["success"]:
            return ToolResult(tool_name="", tool_use_id="", success=False, operation="create_visualization", scope=ctx.scope(),
                              error={"code": "invalid_input", "message": result["error"]})  # type: ignore[arg-type]

        title = args.title or f"{viz_type} - {args.source}"
        artifact = visualizations.new_artifact(ctx, title=title, viz_type=result["visualization_type"], figure_json=figure_to_json(result["figure"]),
                                               metadata={"source": args.source, "subject_id": str(args.subject_id)})
        viz_id = await visualizations.put(ctx, artifact)
        data = {"viz_id": viz_id, "title": title, "viz_type": result["visualization_type"], "points": int(min(len(frame), MAX_POINTS)),
                "series": [c for c in frame.columns if c != "charttime"][:5]}
        return ToolResult(tool_name="", tool_use_id="", success=True, operation="create_visualization", scope=ctx.scope(), data=data,
                          count=1, limit=1, artifacts=ToolArtifacts(visualization_ids=[viz_id]))

    contract = ToolContract(
        name="create_visualization",
        description="Genera un grafico determinista (timeline, comparison, bar, histogram) con datos del paciente activo: resultados de laboratorio, mediciones de UCI o medicacion. Devuelve el identificador de la visualizacion para mostrarla al usuario.",
        input_model=VisualizationInput, output_model=VisualizationOutput, requires_patient_scope=True,
        audit_category=AuditCategory.visualization, data_categories=("labs", "icu", "medications"), max_rows=1, timeout_s=45.0,
    )
    return Tool(contract, create)
