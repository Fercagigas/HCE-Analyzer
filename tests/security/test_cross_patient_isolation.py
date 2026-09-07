"""Aislamiento entre pacientes y proposito: `ScopeGuard` delante del provider (roadmap 05 P0.7).

Ninguna consulta clinica llega al provider si el contexto no autoriza al paciente o
al episodio; los rechazos quedan auditados como `tool_refused`.
"""

import pytest

from chathce.adapters.memory import CollectingAuditSink
from chathce.application.scope_guard import ScopeGuard
from chathce.domain.context import Channel, Purpose, RequestContext
from chathce.domain.errors import PurposeNotAllowed, ScopeViolation
from tests.fakes.mimic_fixtures import fixtures_available, load_expected, load_manifest, make_memory_client, make_provider

pytestmark = [pytest.mark.security, pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")]

SUBJECTS = load_manifest()["subject_ids"] if fixtures_available() else [0, 0, 0]
A, B = SUBJECTS[0], SUBJECTS[1]


def _hadm(subject_id: int) -> int:
    return sorted(a["hadm_id"] for a in load_expected(f"get_patient_summary__{subject_id}")["result"]["admissions"])[0]


def _ctx(patient=None, **kw) -> RequestContext:
    return RequestContext(user_id="clinician", channel=Channel.api, patient_id=None if patient is None else str(patient), **kw)


@pytest.fixture
def guarded():
    client = make_memory_client()
    audit = CollectingAuditSink()
    return ScopeGuard(make_provider(client), audit=audit), client, audit


async def test_without_active_patient_clinical_queries_are_refused(guarded):
    guard, client, audit = guarded
    with pytest.raises(ScopeViolation) as exc:
        await guard.get_patient_summary(_ctx(), A)
    assert exc.value.reason == "patient_scope_required"
    assert client.calls == [], "no se consulto la base de datos"
    assert audit.actions() == ["tool_refused"]
    assert audit.events[0].outcome == "refused"


async def test_patient_a_cannot_read_patient_b(guarded):
    guard, client, audit = guarded
    ctx = _ctx(A)
    for call in (
        lambda: guard.get_patient(ctx, B),
        lambda: guard.list_conditions(ctx, subject_id=B),
        lambda: guard.list_lab_observations(ctx, subject_id=B),
        lambda: guard.list_medications(ctx, subject_id=B),
        lambda: guard.list_icu_stays(ctx, subject_id=B),
    ):
        with pytest.raises(ScopeViolation) as exc:
            await call()
        assert exc.value.reason == "patient_mismatch"
    assert client.calls == []
    assert set(audit.actions()) == {"tool_refused"} and len(audit.events) == 5


async def test_admission_of_another_patient_is_refused_after_owner_resolution(guarded):
    guard, client, audit = guarded
    with pytest.raises(ScopeViolation) as exc:
        await guard.get_admission_details(_ctx(A), _hadm(B))
    assert exc.value.reason == "patient_mismatch"
    assert [c.table for c in client.calls] == ["admissions"], "solo la resolucion del propietario"
    assert "tool_refused" in audit.actions()


async def test_icu_stay_of_another_patient_is_refused(guarded):
    guard, client, _ = guarded
    provider = make_provider(make_memory_client())
    stays_b = await provider.list_icu_stays(_ctx(B), subject_id=B)
    stay_b = stays_b.items[0].stay_id
    with pytest.raises(ScopeViolation):
        await guard.list_icu_observations(_ctx(A), stay_id=stay_b)
    assert [c.table for c in client.calls] == ["icustays"]


async def test_encounter_scope_is_enforced_when_set(guarded):
    guard, _, _ = guarded
    hadms = sorted(a["hadm_id"] for a in load_expected(f"get_patient_summary__{A}")["result"]["admissions"])
    if len(hadms) < 2:
        pytest.skip("el paciente de prueba solo tiene una admision")
    ctx = _ctx(A, encounter_id=str(hadms[0]))
    await guard.get_admission_details(ctx, hadms[0])
    with pytest.raises(ScopeViolation) as exc:
        await guard.get_admission_details(ctx, hadms[1])
    assert exc.value.reason == "encounter_mismatch"


async def test_authorized_patient_queries_pass_and_are_audited(guarded):
    guard, _, audit = guarded
    summary = await guard.get_patient_summary(_ctx(A), A)
    assert summary.patient.subject_id == A
    event = audit.events[-1]
    assert event.action.value == "clinical_query" and event.outcome == "success"
    assert event.patient_id == str(A) and event.operation == "get_patient_summary"
    assert "labs" in event.data_categories
    assert audit.phi_findings() == []


async def test_dataset_aggregates_require_research_purpose(guarded):
    guard, client, audit = guarded
    with pytest.raises(PurposeNotAllowed):
        await guard.top_diagnoses(_ctx(A), limit=5)
    assert client.calls == []
    assert audit.actions() == ["tool_refused"]

    research = RequestContext(user_id="r", channel=Channel.api, purpose=Purpose.research, roles=frozenset({"researcher"}))
    result = await guard.top_diagnoses(research, limit=5)
    assert result.buckets
    assert not any(hasattr(b, "subject_id") for b in result.buckets)


async def test_dictionary_searches_do_not_require_patient(guarded):
    guard, _, _ = guarded
    page = await guard.search_icd_codes(_ctx(), title_contains="infection", limit=5)
    assert page.limit == 5
