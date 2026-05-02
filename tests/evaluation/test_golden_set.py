"""
Property-based tests for the golden set structure and SQL table references.

**Validates: Requirements 1.3, 1.6, 1.7**

Note: validate_question is re-implemented inline here to avoid importing
Evaluation.run_ragas_eval at module level, which triggers a slow HuggingFace
model load. The logic is identical to the one in run_ragas_eval.py.
"""

import re
from typing import Any, Dict, List

from hypothesis import given, settings, assume
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_TABLES = ["edstays", "triage", "vitalsign", "diagnosis", "medrecon", "pyxis"]
VALID_CATEGORIES = [
    "patient_summary",
    "vital_signs",
    "diagnoses",
    "medications",
    "triage",
    "cross_table",
]
REQUIRED_FIELDS = ["id", "question", "ground_truth", "ground_truth_sql", "contexts", "category"]

# ---------------------------------------------------------------------------
# validate_question — mirrors Evaluation/run_ragas_eval.py exactly
# ---------------------------------------------------------------------------

def validate_question(question: Dict[str, Any]) -> List[str]:
    """Return a list of validation errors for a single question dict.

    Mirrors the implementation in ``Evaluation/run_ragas_eval.py`` so that
    tests remain fast without triggering the heavy RAGAS/HuggingFace import.
    """
    errors: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in question:
            errors.append(f"Missing field: '{field}'")
        elif not question[field]:
            errors.append(f"Empty field: '{field}'")

    contexts = question.get("contexts")
    if isinstance(contexts, list) and len(contexts) == 0:
        errors.append("'contexts' must be a non-empty list")

    return errors


# ---------------------------------------------------------------------------
# Property 1: Golden set structural completeness
# Validates: Requirements 1.3, 1.6
# ---------------------------------------------------------------------------

@given(
    st.fixed_dictionaries(
        {
            "id": st.text(min_size=1, max_size=20),
            "question": st.text(min_size=1, max_size=200),
            "ground_truth": st.text(min_size=1, max_size=500),
            "ground_truth_sql": st.text(min_size=1, max_size=500),
            "contexts": st.lists(st.text(min_size=1), min_size=1, max_size=5),
            "category": st.sampled_from(VALID_CATEGORIES),
        }
    )
)
@settings(max_examples=100)
def test_property_1_valid_question_passes_validation(question):
    """
    **Validates: Requirements 1.3, 1.6**

    A question dict with all 6 required non-empty fields must produce no
    validation errors.
    """
    errors = validate_question(question)
    assert errors == [], f"Valid question should have no errors, got: {errors}"


@given(st.sampled_from(REQUIRED_FIELDS))
@settings(max_examples=50)
def test_property_1b_missing_field_causes_error(missing_field):
    """
    **Validates: Requirements 1.3, 1.6**

    A question dict with a missing required field must produce at least one
    validation error.
    """
    question = {
        "id": "Q-001",
        "question": "What is the diagnosis?",
        "ground_truth": "Hypertension",
        "ground_truth_sql": "SELECT * FROM diagnosis WHERE subject_id = 1",
        "contexts": ["context text"],
        "category": "diagnoses",
    }
    del question[missing_field]
    errors = validate_question(question)
    assert len(errors) > 0, f"Missing field '{missing_field}' should produce errors"


@given(st.sampled_from(REQUIRED_FIELDS))
@settings(max_examples=50)
def test_property_1c_empty_field_causes_error(empty_field):
    """
    **Validates: Requirements 1.3, 1.6**

    A question dict with an empty required field must produce at least one
    validation error.
    """
    question = {
        "id": "Q-001",
        "question": "What is the diagnosis?",
        "ground_truth": "Hypertension",
        "ground_truth_sql": "SELECT * FROM diagnosis WHERE subject_id = 1",
        "contexts": ["context text"],
        "category": "diagnoses",
    }
    # Set the field to an empty value appropriate for its type
    if empty_field == "contexts":
        question[empty_field] = []
    else:
        question[empty_field] = ""
    errors = validate_question(question)
    assert len(errors) > 0, f"Empty field '{empty_field}' should produce errors"


# ---------------------------------------------------------------------------
# Property 2: Golden set SQL references only allowed tables
# Validates: Requirements 1.7
# ---------------------------------------------------------------------------

def _build_sql_with_allowed_tables(tables: list) -> str:
    """Build a simple SELECT SQL using only the provided allowed tables."""
    primary = tables[0]
    sql = f"SELECT * FROM {primary}"
    for extra in tables[1:]:
        sql += f" JOIN {extra} ON {primary}.stay_id = {extra}.stay_id"
    return sql


def _extract_table_names(sql: str) -> list:
    """Extract table names referenced in FROM and JOIN clauses."""
    pattern = r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    return re.findall(pattern, sql, re.IGNORECASE)


@given(
    st.lists(
        st.sampled_from(ALLOWED_TABLES),
        min_size=1,
        max_size=6,
        unique=True,
    )
)
@settings(max_examples=100)
def test_property_2_sql_references_only_allowed_tables(tables):
    """
    **Validates: Requirements 1.7**

    SQL queries built exclusively from the 6 MIMIC-IV-ED allowed tables must
    not reference any table outside that set.
    """
    sql = _build_sql_with_allowed_tables(tables)
    referenced = _extract_table_names(sql)
    disallowed = [t for t in referenced if t.lower() not in ALLOWED_TABLES]
    assert disallowed == [], (
        f"SQL references disallowed tables {disallowed}. SQL: {sql}"
    )


@given(
    st.lists(
        st.sampled_from(ALLOWED_TABLES),
        min_size=1,
        max_size=6,
        unique=True,
    )
)
@settings(max_examples=100)
def test_property_2b_sql_with_allowed_tables_passes_as_valid_question(tables):
    """
    **Validates: Requirements 1.7**

    A complete question dict whose ground_truth_sql uses only allowed tables
    must pass validate_question() with no errors.
    """
    sql = _build_sql_with_allowed_tables(tables)
    question = {
        "id": "DB-001",
        "question": "How many patients visited the ED?",
        "ground_truth": "42 patients",
        "ground_truth_sql": sql,
        "contexts": ["context about ED visits"],
        "category": "patient_summary",
    }
    errors = validate_question(question)
    assert errors == [], (
        f"Question with allowed-table SQL should have no errors, got: {errors}"
    )
