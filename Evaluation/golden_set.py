"""Estructura y validacion del golden set (v2, MIMIC-IV hosp/icu).

Modulo ligero (sin imports de RAGAS ni HuggingFace) compartido por los runners de
`Evaluation/` y por `tests/evaluation/test_golden_set.py`.

Formato v2 de una pregunta DB::

    {
      "id": "DB-LAB-001",
      "category": "labs",
      "question": "...",
      "ground_truth": "...",
      "ground_truth_operation": {"operation": "list_lab_observations", "arguments": {...}},
      "scope": {"subject_id": 10001217, "hadm_id": null, "stay_id": null},
      "expected_tool": "get_labs",
      "contexts": ["..."],
      "clinical_validation": {"required": true, "status": "pending", "notes": "..."}
    }

Las preguntas del golden set RAG (`golden_set_ragas_rag.json`) usan nombres en
castellano (`pregunta`, `respuesta_referencia`, `contextos`) y se normalizan en
`run_ragas_eval._normalize_question`; para ellas solo aplican los campos comunes.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from chathce.ports.clinical_data_provider import CLINICAL_OPERATIONS

GOLDEN_SET_VERSION = "2.0"

# Campos comunes a cualquier golden set (DB y RAG).
REQUIRED_QUESTION_FIELDS: List[str] = ["id", "question", "ground_truth", "contexts"]
# Campos adicionales obligatorios en el golden set DB v2.
DB_REQUIRED_FIELDS: List[str] = REQUIRED_QUESTION_FIELDS + ["ground_truth_operation", "category"]
OPTIONAL_QUESTION_FIELDS: List[str] = [
    "ground_truth_operation", "category", "scope", "expected_tool", "clinical_validation",
]

VALID_CATEGORIES: List[str] = [
    "patient_summary", "admission", "diagnoses", "labs", "medications", "icu", "aggregates",
]
CATEGORY_ID_PREFIX: Dict[str, str] = {
    "patient_summary": "DB-PS-",
    "admission": "DB-ADM-",
    "diagnoses": "DB-DX-",
    "labs": "DB-LAB-",
    "medications": "DB-MED-",
    "icu": "DB-ICU-",
    "aggregates": "DB-AGG-",
}
ALLOWED_OPERATIONS: List[str] = list(CLINICAL_OPERATIONS)
EXPECTED_TOOLS: List[str] = [
    "get_patient_summary", "get_admission_details", "get_diagnoses", "get_labs", "search_lab_items",
    "get_medications", "get_icu_stays", "get_icu_observations", "search_icd_codes", "get_dataset_statistics",
]

# Nada del golden set debe parecer SQL ni referenciar esquemas fisicos. Los valores MIMIC pueden
# contener palabras inglesas sueltas ("TRANSFER FROM HOSPITAL"), por eso se exige la forma
# `select ... from` completa o un nombre de esquema fisico.
SQL_LIKE_PATTERN = re.compile(
    r"(\bselect\b[\s\S]{0,200}?\bfrom\b|\bmimic_ed\b|\bmimiciv_hosp\b|\bmimiciv_icu\b|\bcustom_query\b)",
    re.IGNORECASE,
)


def validate_question(question: Dict[str, Any], *, kind: str = "db") -> List[str]:
    """Errores de validacion de una pregunta (lista vacia = valida)."""
    errors: List[str] = []
    required = DB_REQUIRED_FIELDS if kind == "db" else REQUIRED_QUESTION_FIELDS
    for field in required:
        if field not in question:
            errors.append(f"Missing field: '{field}'")
        elif not question[field]:
            errors.append(f"Empty field: '{field}'")

    contexts = question.get("contexts")
    if isinstance(contexts, list) and len(contexts) == 0:
        errors.append("'contexts' must be a non-empty list")

    if kind == "db":
        category = question.get("category")
        if category and category not in VALID_CATEGORIES:
            errors.append(f"Unknown category: '{category}'")
        op = question.get("ground_truth_operation")
        if isinstance(op, dict):
            if op.get("operation") not in ALLOWED_OPERATIONS:
                errors.append(f"Operation not allowlisted: '{op.get('operation')}'")
            if not isinstance(op.get("arguments", {}), dict):
                errors.append("'ground_truth_operation.arguments' must be a dict")
        elif op is not None:
            errors.append("'ground_truth_operation' must be a dict")
        tool = question.get("expected_tool")
        if tool and tool not in EXPECTED_TOOLS:
            errors.append(f"Unknown expected_tool: '{tool}'")
        for field in ("question", "ground_truth"):
            value = question.get(field)
            if isinstance(value, str) and SQL_LIKE_PATTERN.search(value):
                errors.append(f"'{field}' looks like SQL or references a physical schema")
    return errors


def load_golden_set(path: str) -> Dict[str, Any]:
    """Carga el JSON (formatos `questions` o `golden_set`) sin normalizar nombres."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Golden set file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "questions" not in data and "golden_set" in data:
        data["questions"] = data["golden_set"]
    if "questions" not in data:
        raise ValueError("Golden set JSON is missing both 'questions' and 'golden_set' keys.")
    return data


def scope_kwargs(question: Dict[str, Any]) -> Dict[str, Any]:
    """Argumentos de contexto que los runners pasan al agente (patient_id, purpose)."""
    kwargs: Dict[str, Any] = {}
    scope = question.get("scope") or {}
    if scope.get("subject_id"):
        kwargs["patient_id"] = str(scope["subject_id"])
    if scope.get("hadm_id"):
        kwargs["encounter_id"] = str(scope["hadm_id"])
    if question.get("category") == "aggregates":
        kwargs["purpose"] = "research"
    return kwargs


def default_golden_set_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_set_ragas.json")
