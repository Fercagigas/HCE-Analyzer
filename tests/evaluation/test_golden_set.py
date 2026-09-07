"""Tests del golden set DB v2 (estructura, operaciones allowlisted y JSON real).

Usa `Evaluation.golden_set` (modulo ligero, sin RAGAS/HuggingFace).
"""

import json
import os

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from Evaluation.golden_set import (
    ALLOWED_OPERATIONS,
    DB_REQUIRED_FIELDS,
    EXPECTED_TOOLS,
    SQL_LIKE_PATTERN,
    VALID_CATEGORIES,
    default_golden_set_path,
    scope_kwargs,
    validate_question,
)

pytestmark = pytest.mark.unit


def _base_question(**overrides):
    q = {
        "id": "DB-LAB-001",
        "category": "labs",
        "question": "¿Cuál es el último valor de Hemoglobin del paciente 10001217?",
        "ground_truth": "El último valor es 12.1 g/dL.",
        "ground_truth_operation": {"operation": "list_lab_observations", "arguments": {"subject_id": 10001217}},
        "scope": {"subject_id": 10001217, "hadm_id": None, "stay_id": None},
        "expected_tool": "get_labs",
        "contexts": ["labevent ..."],
        "clinical_validation": {"required": True, "status": "pending", "notes": ""},
    }
    q.update(overrides)
    return q


@given(
    st.fixed_dictionaries({
        "id": st.text(min_size=1, max_size=20),
        "question": st.text(min_size=1, max_size=200).filter(lambda t: not SQL_LIKE_PATTERN.search(t)),
        "ground_truth": st.text(min_size=1, max_size=500).filter(lambda t: not SQL_LIKE_PATTERN.search(t)),
        "ground_truth_operation": st.fixed_dictionaries({
            "operation": st.sampled_from(ALLOWED_OPERATIONS),
            "arguments": st.dictionaries(st.sampled_from(["subject_id", "hadm_id", "limit"]), st.integers(1, 10**8), max_size=3),
        }),
        "contexts": st.lists(st.text(min_size=1), min_size=1, max_size=5),
        "category": st.sampled_from(VALID_CATEGORIES),
    })
)
@settings(max_examples=100)
def test_property_valid_question_passes_validation(question):
    assert validate_question(question) == []


@given(st.sampled_from(DB_REQUIRED_FIELDS))
@settings(max_examples=30)
def test_property_missing_required_field_causes_error(missing_field):
    question = _base_question()
    del question[missing_field]
    assert validate_question(question)


@given(st.sampled_from(DB_REQUIRED_FIELDS))
@settings(max_examples=30)
def test_property_empty_required_field_causes_error(empty_field):
    question = _base_question()
    question[empty_field] = [] if empty_field == "contexts" else ("" if empty_field != "ground_truth_operation" else {})
    assert validate_question(question)


@pytest.mark.parametrize("operation", ["execute_custom_query", "custom", "select_rows"])
def test_non_allowlisted_operation_is_rejected(operation):
    q = _base_question(ground_truth_operation={"operation": operation, "arguments": {}})
    assert any("not allowlisted" in e for e in validate_question(q))


@pytest.mark.parametrize("text", ["SELECT subject_id FROM patients", "consulta mimiciv_hosp.labevents", "tabla mimic_ed.edstays"])
def test_sql_like_text_is_rejected(text):
    assert any("looks like SQL" in e for e in validate_question(_base_question(ground_truth=text)))


def test_unknown_category_and_tool_are_rejected():
    assert any("Unknown category" in e for e in validate_question(_base_question(category="triage")))
    assert any("Unknown expected_tool" in e for e in validate_question(_base_question(expected_tool="query_sql")))


def test_scope_kwargs_maps_scope_to_agent_arguments():
    q = _base_question(scope={"subject_id": 10001217, "hadm_id": 24597018, "stay_id": None})
    assert scope_kwargs(q) == {"patient_id": "10001217", "encounter_id": "24597018"}
    assert scope_kwargs(_base_question(category="aggregates", scope={})) == {"purpose": "research"}


# ---------------------------------------------------------------------------
# JSON real
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def golden_set():
    path = default_golden_set_path()
    if not os.path.exists(path):
        pytest.skip("golden set no generado")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_real_golden_set_is_v2_and_valid(golden_set):
    meta = golden_set["metadata"]
    assert meta["version"] == "2.0"
    questions = golden_set["questions"]
    assert len(questions) == meta["total_preguntas"] == 40
    errors = {q["id"]: validate_question(q) for q in questions}
    assert all(not e for e in errors.values()), {k: v for k, v in errors.items() if v}
    assert len({q["id"] for q in questions}) == len(questions)


def test_real_golden_set_distribution_and_scope(golden_set):
    meta = golden_set["metadata"]
    questions = golden_set["questions"]
    counts = {}
    for q in questions:
        counts[q["category"]] = counts.get(q["category"], 0) + 1
    assert counts == meta["distribucion"]
    subjects = set(meta["subject_ids_usados"])
    for q in questions:
        sid = q["scope"]["subject_id"]
        if q["category"] == "aggregates":
            assert sid is None
        else:
            assert sid in subjects
        assert q["expected_tool"] in EXPECTED_TOOLS
        assert q["ground_truth_operation"]["operation"] in meta["operaciones_referenciadas"]
        for field in ("question", "ground_truth"):
            assert not SQL_LIKE_PATTERN.search(q[field]), q["id"]
    pending = {q["id"] for q in questions if q["clinical_validation"]["required"]}
    assert pending == set(meta["requiere_validacion_clinica"])
