"""Controles de seguridad y funcionales de las visualizaciones deterministas (ADR 0040).

El escaneo AST recorre todo el runtime (`services/`, `ui/`, `src/`, `chathce/`) en
lugar de una lista fija de ficheros, para que sobreviva a la reorganizacion de
Fase 1 y cubra el core nuevo.
"""

import ast
import builtins
import importlib.util
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

pytestmark = pytest.mark.security

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXECUTOR_PATH = PROJECT_ROOT / "services" / "medical_agent" / "code_executor.py"
AGENT_PATH = PROJECT_ROOT / "services" / "medical_agent" / "visualization_agent.py"
RUNTIME_DIRS = ("services", "ui", "src", "chathce")


def runtime_python_files():
    for directory in RUNTIME_DIRS:
        base = PROJECT_ROOT / directory
        if base.exists():
            yield from sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


@pytest.fixture(scope="module")
def executor_module():
    """Carga el modulo de trazado aislado sin inicializar servicios externos."""
    spec = importlib.util.spec_from_file_location("visualization_code_executor_under_test", EXECUTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def temporal_data():
    return pd.DataFrame({
        "charttime": pd.to_datetime(["2026-01-01T10:00:00", "2026-01-01T11:00:00", "2026-01-01T12:00:00"]),
        "heartrate": [80, 86, 83],
        "sbp": [120, 125, 122],
    })


@pytest.mark.parametrize("chart_type", ["timeline", "line", "trend", "timeseries"])
def test_timeseries_aliases_use_parameterized_plotter(executor_module, temporal_data, chart_type):
    result = executor_module.create_allowlisted_visualization(
        chart_type, temporal_data, metrics=["heartrate"], title="Frecuencia cardíaca",
    )
    assert result["success"] is True
    assert result["visualization_type"] == "timeline"
    assert result["method"] == "allowlisted_function"
    assert isinstance(result["figure"], go.Figure)
    assert len(result["figure"].data) == 1


def test_comparison_supports_multiple_validated_metrics(executor_module, temporal_data):
    result = executor_module.create_allowlisted_visualization("comparison", temporal_data, metrics=["heartrate", "sbp"])
    assert result["success"] is True
    assert [trace.name for trace in result["figure"].data] == ["Heartrate", "Sbp"]


def test_bar_supports_preaggregated_category_values(executor_module):
    data = pd.DataFrame({"categoria": ["Diagnóstico A", "Diagnóstico B"], "frecuencia": [12, 7]})
    result = executor_module.create_allowlisted_visualization(
        "bar", data, category_column="categoria", metrics=["frecuencia"],
    )
    assert result["success"] is True
    assert list(result["figure"].data[0].y) == [12, 7]


def test_bar_supports_deterministic_frequency_counts(executor_module):
    data = pd.DataFrame({"diagnostico": ["A", "B", "A", "A"]})
    result = executor_module.create_allowlisted_visualization("bar", data)
    assert result["success"] is True
    assert list(result["figure"].data[0].x) == ["A", "B"]
    assert list(result["figure"].data[0].y) == [3, 1]


def test_bar_supports_numeric_values_against_the_row_index(executor_module):
    data = pd.DataFrame({"acuity": [1, 3, 2]})
    result = executor_module.create_allowlisted_visualization("bar", data, metrics=["acuity"])
    assert result["success"] is True
    assert list(result["figure"].data[0].y) == [1, 3, 2]


@pytest.mark.parametrize("chart_type", ["histogram", "distribution"])
def test_distribution_aliases_use_histogram(executor_module, chart_type):
    data = pd.DataFrame({"acuity": [1, 2, 2, 3, 4]})
    result = executor_module.create_allowlisted_visualization(chart_type, data, metrics=["acuity"])
    assert result["success"] is True
    assert result["visualization_type"] == "histogram"
    assert isinstance(result["figure"].data[0], go.Histogram)


def test_categorical_distribution_uses_frequency_bars(executor_module):
    data = pd.DataFrame({"diagnostico": ["A", "B", "A"]})
    result = executor_module.create_allowlisted_visualization("distribution", data)
    assert result["success"] is True
    assert result["visualization_type"] == "bar"
    assert isinstance(result["figure"].data[0], go.Bar)


@pytest.mark.parametrize("chart_type", ["scatter", "3d_scatter", "sankey", "custom"])
def test_non_allowlisted_types_fail_closed(executor_module, chart_type):
    data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    result = executor_module.create_allowlisted_visualization(chart_type, data)
    assert result["success"] is False
    assert result["figure"] is None
    assert result["method"] == "rejected"
    assert "no permitido" in result["error"]


def test_model_supplied_python_is_never_executed(executor_module, monkeypatch, tmp_path):
    marker = tmp_path / "model-code-ran.txt"
    generated_code = f"open({str(marker)!r}, 'w').write('unsafe')"

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dynamic Python execution was attempted")

    monkeypatch.setattr(builtins, "exec", fail_if_called)
    if hasattr(executor_module, "execute_visualization_code"):
        result = executor_module.execute_visualization_code(generated_code)
        assert result["success"] is False
        assert result["method"] == "rejected"
    else:
        # Shims retirados (WP12): no debe quedar ninguna API que acepte codigo.
        assert not hasattr(executor_module, "SafeCodeExecutor")
        assert not hasattr(executor_module, "CodeValidator")
    assert not marker.exists()


def test_requested_columns_and_parameter_sizes_are_validated(executor_module):
    data = pd.DataFrame({"value": [1, 2, 3]})
    missing_column = executor_module.create_allowlisted_visualization("histogram", data, metrics=["does_not_exist"])
    too_long_title = executor_module.create_allowlisted_visualization(
        "histogram", data, metrics=["value"], title="x" * (executor_module.MAX_TITLE_LENGTH + 1),
    )
    assert missing_column["success"] is False
    assert "no existe" in missing_column["error"]
    assert too_long_title["success"] is False
    assert "no puede superar" in too_long_title["error"]


def test_runtime_has_no_dynamic_execution_calls():
    files = list(runtime_python_files())
    assert files, "No se encontraron ficheros de runtime que escanear"
    offenders = {}
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        forbidden_calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval", "compile"}
        ]
        if forbidden_calls:
            offenders[str(path.relative_to(PROJECT_ROOT))] = forbidden_calls
    assert offenders == {}


def test_visualization_agent_has_no_llm_code_generation_path():
    if not AGENT_PATH.exists():
        pytest.skip("visualization_agent.py retirado; la ruta determinista vive en chathce/adapters/visualization")
    source = AGENT_PATH.read_text(encoding="utf-8")
    assert "ChatAnthropic" not in source
    assert ".invoke(" not in source
    assert "_extract_code_from_response" not in source
    assert "execute_visualization_code" not in source
