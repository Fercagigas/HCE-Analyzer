"""Politica PHI con valores sinteticos; no depende de credenciales ni fixtures reales."""

from datetime import datetime

from chathce.domain.clinical import Admission, Medication, PatientSummary
from chathce.domain.phi import PhiDetectionMode, PhiMinimizer


def test_catalog_minimizes_nested_clinical_dtos_per_session():
    admission = Admission(
        hadm_id=991122, subject_id=441122, admittime=datetime(2026, 3, 14, 9, 30),
        dischtime=datetime(2026, 3, 19, 11, 0), evidence_id="synthetic:admission:991122",
    )
    payload = PhiMinimizer(session_id="session-a").minimize(PatientSummary(patient={
        "subject_id": 441122, "evidence_id": "synthetic:patient:441122",
    }, admissions=[admission]))

    assert payload["patient"]["subject_id"].startswith("PATIENT_")
    assert payload["admissions"][0]["hadm_id"].startswith("ENCOUNTER_")
    assert payload["admissions"][0]["admittime"] == "2026-03"
    assert "991122" not in str(payload) and "441122" not in str(payload)


def test_free_text_detector_redacts_only_marked_names_and_identifiers():
    text = "Paciente: Ana Lopez; DNI 12345678Z; email ana.lopez@example.test; telefono +34 612 345 678."
    result = PhiMinimizer(mode=PhiDetectionMode.redact).inspect_text(text)

    assert {f.category for f in result.findings} == {"name", "dni", "email", "phone"}
    assert "Ana Lopez" not in result.text and "12345678Z" not in result.text
    assert "[PHI_NAME]" in result.text and "[PHI_EMAIL]" in result.text


def test_block_mode_reports_phi_without_retaining_text():
    result = PhiMinimizer(mode=PhiDetectionMode.block).inspect_text("Contactar a 612345678")
    assert result.blocked and result.text == ""


def test_catalog_removes_unbounded_clinical_free_text():
    medication = Medication(source="emar", subject_id=10, drug="farmaco", event_txt="Paciente: Ana Lopez", evidence_id="synthetic:med:1")
    payload = PhiMinimizer(session_id="s").minimize(medication)
    assert "event_txt" not in payload
