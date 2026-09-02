"""Caracterizacion de `DatabaseService` (legacy) sobre fixtures MIMIC grabadas.

Congela la salida actual de cada operacion clinica antes de sustituir el
servicio por `MimicClinicalDataProvider` (WP3). Las salidas esperadas se
generaron con `scripts/record_mimic_fixtures.py` ejecutando este mismo servicio
sobre el cliente en memoria, por lo que la comparacion es determinista.
"""

import json
from pathlib import Path

import pytest

from tests.characterization.conftest import FIXTURES
from tests.fakes.legacy_factories import make_database_service
from tests.fakes.normalize import normalize

EXPECTED_FILES = sorted((FIXTURES / "expected").glob("*.json")) if (FIXTURES / "expected").exists() else []


@pytest.mark.parametrize("expected_path", EXPECTED_FILES, ids=lambda p: p.stem)
def test_database_service_matches_recorded_output(mimic_client, expected_path: Path):
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    service = make_database_service(mimic_client)

    result = getattr(service, expected["method"])(*expected["args"], **expected["kwargs"])

    assert normalize(result) == expected["result"]


def test_expected_outputs_exist(mimic_manifest):
    assert EXPECTED_FILES, "No hay salidas esperadas grabadas"
    assert {p.stem for p in EXPECTED_FILES} == set(mimic_manifest["expected_files"])


def test_diagnosis_enrichment_issues_one_dictionary_query_per_code(mimic_client, mimic_manifest):
    """Documenta el N+1 actual: una consulta a d_icd_diagnoses por codigo distinto.

    WP3 debe reducirlo a <= 2 consultas (lookup en lote); este test se ajusta
    entonces en el test de contrato del adapter.
    """
    service = make_database_service(mimic_client)
    subject_id = mimic_manifest["subject_ids"][0]

    diagnoses = service.get_patient_diagnoses(subject_id)

    distinct_codes = {(d["icd_code"], d["icd_version"]) for d in diagnoses}
    dictionary_calls = mimic_client.count_calls(table="d_icd_diagnoses", operation="select")
    assert dictionary_calls == len(distinct_codes)
    assert all("long_title" in d for d in diagnoses)


def test_unknown_table_is_rejected_before_any_query(mimic_client):
    from services.medical_agent.services.database_service import ValidationError

    service = make_database_service(mimic_client)
    with pytest.raises(ValidationError):
        service.get_table_data("edstays", {"subject_id": 1})
    assert mimic_client.calls == []
