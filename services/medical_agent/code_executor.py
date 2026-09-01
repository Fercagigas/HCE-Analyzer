"""Deterministic, allowlisted visualization functions.

The visualization pipeline must never execute Python supplied by a model. This
module keeps the former public rejection entry point for fail-closed backwards
compatibility, while all supported charts are built through typed parameters.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 200
MAX_METRICS = 5
TIME_COLUMN_NAMES = ("charttime", "time", "date", "datetime", "timestamp")

SUPPORTED_VISUALIZATION_TYPES = frozenset({
    "timeline",
    "comparison",
    "bar",
    "histogram",
})

VISUALIZATION_TYPE_ALIASES = {
    "line": "timeline",
    "timeseries": "timeline",
    "time_series": "timeline",
    "temporal": "timeline",
    "trend": "timeline",
    "distribution": "histogram",
}


class VisualizationParameterError(ValueError):
    """Raised when a visualization request is outside the safe contract."""


class CodeExecutionError(RuntimeError):
    """Retained for compatibility; arbitrary code execution is disabled."""


def _validated_data(data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise VisualizationParameterError("Los datos deben ser un DataFrame")
    if data.empty:
        raise VisualizationParameterError("No hay datos para visualizar")
    return data


def _validated_title(title: Optional[str]) -> str:
    if title is None:
        return "Gráfico de Datos Médicos"
    if not isinstance(title, str):
        raise VisualizationParameterError("El título debe ser texto")
    title = title.strip()
    if not title:
        return "Gráfico de Datos Médicos"
    if len(title) > MAX_TITLE_LENGTH:
        raise VisualizationParameterError(
            f"El título no puede superar {MAX_TITLE_LENGTH} caracteres"
        )
    return title


def _validated_column(
    data: pd.DataFrame,
    column: Optional[str],
    parameter_name: str,
    *,
    numeric: bool = False,
) -> str:
    if not isinstance(column, str) or not column:
        raise VisualizationParameterError(
            f"El parámetro {parameter_name} debe identificar una columna"
        )
    if column not in data.columns:
        raise VisualizationParameterError(
            f"La columna solicitada para {parameter_name} no existe: {column}"
        )
    if numeric and not pd.api.types.is_numeric_dtype(data[column]):
        raise VisualizationParameterError(f"La columna {column} debe ser numérica")
    return column


def _validated_metrics(
    data: pd.DataFrame,
    metrics: Optional[Sequence[str]],
    *,
    minimum: int = 1,
) -> List[str]:
    if metrics is None:
        selected = data.select_dtypes(include=["number"]).columns.tolist()
        selected = [
            column
            for column in selected
            if not column.endswith("_id") and column != "seq_num"
        ]
    else:
        if isinstance(metrics, (str, bytes)) or not isinstance(metrics, Sequence):
            raise VisualizationParameterError("metrics debe ser una lista de columnas")
        selected = list(metrics)

    if len(selected) < minimum:
        raise VisualizationParameterError(
            f"Se necesitan al menos {minimum} métricas numéricas"
        )
    if len(selected) > MAX_METRICS:
        raise VisualizationParameterError(
            f"No se permiten más de {MAX_METRICS} métricas por gráfico"
        )

    validated: List[str] = []
    for metric in selected:
        column = _validated_column(data, metric, "metrics", numeric=True)
        if column not in validated:
            validated.append(column)

    if len(validated) < minimum:
        raise VisualizationParameterError(
            f"Se necesitan al menos {minimum} métricas numéricas distintas"
        )
    return validated


def _default_time_column(data: pd.DataFrame) -> Optional[str]:
    for column in TIME_COLUMN_NAMES:
        if column in data.columns:
            return column
    return None


def _default_category_column(data: pd.DataFrame) -> Optional[str]:
    categorical = data.select_dtypes(include=["object", "category", "string"]).columns
    return categorical[0] if len(categorical) else None


def plot_timeseries(
    data: pd.DataFrame,
    *,
    time_column: str,
    metrics: Sequence[str],
    title: Optional[str] = None,
) -> go.Figure:
    """Plot one or more numeric metrics against a validated data column."""
    data = _validated_data(data)
    if time_column not in TIME_COLUMN_NAMES:
        raise VisualizationParameterError(
            f"Columna temporal no permitida: {time_column}"
        )
    time_column = _validated_column(data, time_column, "time_column")
    metrics = _validated_metrics(data, metrics)

    figure = go.Figure()
    ordered = data.sort_values(time_column)
    for metric in metrics:
        figure.add_trace(
            go.Scatter(
                x=ordered[time_column],
                y=ordered[metric],
                mode="lines+markers",
                name=metric.replace("_", " ").title(),
                connectgaps=False,
            )
        )

    figure.update_layout(
        title=_validated_title(title),
        xaxis_title=time_column.replace("_", " ").title(),
        yaxis_title="Valor",
        template="plotly_white",
        hovermode="x unified",
        height=600,
    )
    return figure


def plot_bar(
    data: pd.DataFrame,
    *,
    category_column: Optional[str] = None,
    metric: Optional[str] = None,
    title: Optional[str] = None,
) -> go.Figure:
    """Plot category values or deterministic category frequencies."""
    data = _validated_data(data)

    if category_column is None and metric is None:
        raise VisualizationParameterError(
            "El gráfico de barras necesita una categoría o una métrica"
        )

    if category_column is not None:
        category_column = _validated_column(data, category_column, "category_column")

    if metric is None and category_column is not None:
        values = (
            data[category_column]
            .dropna()
            .astype(str)
            .value_counts()
            .sort_values(ascending=False)
        )
        x_values = values.index
        y_values = values.values
        y_title = "Frecuencia"
        x_title = category_column.replace("_", " ").title()
    elif category_column is None:
        metric = _validated_column(data, metric, "metric", numeric=True)
        chart_data = data[[metric]].dropna()
        x_values = chart_data.index.astype(str)
        y_values = chart_data[metric]
        x_title = "Registro"
        y_title = metric.replace("_", " ").title()
    else:
        metric = _validated_column(data, metric, "metric", numeric=True)
        chart_data = data[[category_column, metric]].dropna()
        x_values = chart_data[category_column]
        y_values = chart_data[metric]
        x_title = category_column.replace("_", " ").title()
        y_title = metric.replace("_", " ").title()

    figure = go.Figure(
        data=[go.Bar(x=x_values, y=y_values, marker_color="#2E86AB")]
    )
    figure.update_layout(
        title=_validated_title(title),
        xaxis_title=x_title,
        yaxis_title=y_title,
        template="plotly_white",
        height=600,
    )
    return figure


def plot_histogram(
    data: pd.DataFrame,
    *,
    metric: str,
    title: Optional[str] = None,
) -> go.Figure:
    """Plot the distribution of one validated numeric metric."""
    data = _validated_data(data)
    metric = _validated_column(data, metric, "metric", numeric=True)

    figure = go.Figure(
        data=[go.Histogram(x=data[metric].dropna(), marker_color="#2E86AB")]
    )
    figure.update_layout(
        title=_validated_title(title),
        xaxis_title=metric.replace("_", " ").title(),
        yaxis_title="Frecuencia",
        template="plotly_white",
        height=600,
    )
    return figure


def create_allowlisted_visualization(
    visualization_type: str,
    data: pd.DataFrame,
    *,
    title: Optional[str] = None,
    metrics: Optional[Sequence[str]] = None,
    time_column: Optional[str] = None,
    category_column: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a Plotly figure through the explicit visualization allowlist."""
    try:
        if not isinstance(visualization_type, str):
            raise VisualizationParameterError("El tipo de visualización debe ser texto")
        normalized_type = visualization_type.lower().strip().replace(" ", "_")
        requested_type = normalized_type
        normalized_type = VISUALIZATION_TYPE_ALIASES.get(normalized_type, normalized_type)
        if normalized_type not in SUPPORTED_VISUALIZATION_TYPES:
            allowed = ", ".join(sorted(SUPPORTED_VISUALIZATION_TYPES))
            raise VisualizationParameterError(
                f"Tipo de visualización no permitido: {visualization_type}. "
                f"Tipos permitidos: {allowed}"
            )

        data = _validated_data(data)
        if requested_type == "distribution" and _default_category_column(data):
            normalized_type = "bar"
        if normalized_type in {"timeline", "comparison"}:
            selected_time = time_column or _default_time_column(data)
            if selected_time is None:
                raise VisualizationParameterError(
                    "No existe una columna temporal permitida para la serie"
                )
            selected_metrics = _validated_metrics(data, metrics)
            figure = plot_timeseries(
                data,
                time_column=selected_time,
                metrics=selected_metrics,
                title=title,
            )
        elif normalized_type == "bar":
            selected_category = category_column or _default_category_column(data)
            selected_metrics = _validated_metrics(data, metrics) if metrics else []
            figure = plot_bar(
                data,
                category_column=selected_category,
                metric=selected_metrics[0] if selected_metrics else None,
                title=title,
            )
        else:
            selected_metrics = _validated_metrics(data, metrics)
            figure = plot_histogram(data, metric=selected_metrics[0], title=title)

        return {
            "success": True,
            "figure": figure,
            "visualization_type": normalized_type,
            "method": "allowlisted_function",
        }
    except (VisualizationParameterError, TypeError, ValueError) as exc:
        logger.warning("Rejected visualization request: %s", exc)
        return {
            "success": False,
            "error": str(exc),
            "figure": None,
            "method": "rejected",
        }


class CodeValidator:
    """Compatibility shim that rejects every Python source string."""

    @classmethod
    def validate_code(cls, code: str) -> tuple[bool, Optional[str]]:
        return False, "La ejecución de código Python está deshabilitada"


class ImprovedCodeValidator(CodeValidator):
    """Compatibility alias for the former AST validator."""


class SafeCodeExecutor:
    """Compatibility shim that fails closed without evaluating its input."""

    def execute(
        self,
        code: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        logger.warning("Rejected attempt to execute visualization code")
        return {
            "success": False,
            "error": "La ejecución de código Python está deshabilitada",
            "figure": None,
            "method": "rejected",
        }


def execute_visualization_code(
    code: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Reject the legacy code-string API without interpreting its contents."""
    return SafeCodeExecutor().execute(code, data)
