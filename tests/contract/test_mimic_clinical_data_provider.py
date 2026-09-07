"""Contrato de `MimicClinicalDataProvider` sobre las fixtures grabadas (WP1).

Compara la informacion devuelta por el adapter nuevo con las salidas del
`DatabaseService` legacy (`tests/fixtures/mimic/expected`), verifica el lookup en
lote de titulos ICD (<= 2 consultas), los filtros y la truncacion.
"""

from datetime import datetime

import pytest

from chathce.domain.clinical import Page, TimeRange
from chathce.domain.context import Channel, Purpose, RequestContext
from chathce.domain.errors import NotFound, ProviderUnavailable
from chathce.ports import ClinicalDataProvider
from tests.fakes.mimic_fixtures import fixtures_available, load_expected, load_manifest, make_memory_client, make_provider

pytestmark = [pytest.mark.contract, pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")]

MANIFEST = load_manifest() if fixtures_available() else {"subject_ids": []}
SUBJECTS = MANIFEST["subject_ids"]


def ctx_for(subject_id: int, **kw) -> RequestContext:
    return RequestContext(user_id="tester", channel=Channel.api, patient_id=str(subject_id), **kw)


def research_ctx() -> RequestContext:
    return RequestContext(user_id="tester", channel=Channel.api, purpose=Purpose.research, roles=frozenset({"researcher"}))


def test_provider_satisfies_port():
    assert isinstance(make_provider(), ClinicalDataProvider)


@pytest.mark.parametrize("subject_id", SUBJECTS)
async def test_patient_summary_matches_legacy_facts(subject_id):
    legacy = load_expected(f"get_patient_summary__{subject_id}")["result"]
    provider = make_provider()

    summary = await provider.get_patient_summary(ctx_for(subject_id), subject_id)

    assert summary.patient.subject_id == subject_id
    assert summary.patient.gender == legacy["demographics"]["gender"]
    assert summary.patient.anchor_age == legacy["demographics"]["anchor_age"]
    assert summary.patient.deceased == legacy["demographics"]["deceased"]
    assert {a.hadm_id for a in summary.admissions} == {a["hadm_id"] for a in legacy["admissions"]}
    assert summary.stats.total_admissions == legacy["summary_stats"]["total_admissions"]
    legacy_codes = {(d["icd_code"], d["icd_version"]) for d in legacy["diagnoses"]}
    assert {(c.icd_code, c.icd_version) for c in summary.conditions} <= legacy_codes
    assert summary.stats.distinct_diagnoses == len(legacy_codes)
    assert summary.stats.last_admission.isoformat() == legacy["summary_stats"]["last_admission"]
    assert all(c.title for c in summary.conditions), "todos los diagnosticos llevan titulo ICD"
    assert all(l.evidence_id.startswith("mimic-iv-demo-2.2:labevent:") for l in summary.recent_labs)
    assert len(summary.recent_labs) <= 20 and len(summary.medications) <= 30


@pytest.mark.parametrize("subject_id", SUBJECTS)
async def test_conditions_match_legacy_and_use_batched_dictionary_lookup(subject_id):
    legacy = load_expected(f"get_patient_diagnoses__{subject_id}")["result"]
    client = make_memory_client()
    provider = make_provider(client)

    page = await provider.list_conditions(ctx_for(subject_id), subject_id=subject_id, limit=200)

    assert {(c.icd_code, c.icd_version, c.title) for c in page.items} == {
        (d["icd_code"], d["icd_version"], d["long_title"]) for d in legacy
    }
    assert client.count_calls(table="d_icd_diagnoses") <= 2
    assert page.truncated is False


@pytest.mark.parametrize("subject_id", SUBJECTS)
async def test_lab_observations_match_legacy_ids(subject_id):
    legacy_all = load_expected(f"get_lab_results__{subject_id}")["result"]
    provider = make_provider()

    page = await provider.list_lab_observations(ctx_for(subject_id), subject_id=subject_id, limit=200)

    legacy_ids = {r["labevent_id"] for r in legacy_all}
    got_ids = {l.labevent_id for l in page.items}
    assert got_ids <= legacy_ids
    assert page.truncated == (len(legacy_ids) > 200)
    if not page.truncated:
        assert got_ids == legacy_ids
    assert all(l.label for l in page.items), "cada resultado lleva la etiqueta de d_labitems"
    times = [l.charttime for l in page.items if l.charttime]
    assert times == sorted(times, reverse=True), "mas recientes primero"


async def test_lab_filters_by_admission_label_time_and_abnormal():
    subject_id = SUBJECTS[0]
    legacy_adm = load_expected(f"get_lab_results__{subject_id}_{MANIFEST['expected_files'] and _first_hadm(subject_id)}")
    hadm_id = legacy_adm["args"][1]
    provider = make_provider()
    ctx = ctx_for(subject_id)

    by_adm = await provider.list_lab_observations(ctx, subject_id=subject_id, hadm_id=hadm_id, limit=200)
    assert {l.labevent_id for l in by_adm.items} <= {r["labevent_id"] for r in legacy_adm["result"]}
    assert all(l.hadm_id == hadm_id for l in by_adm.items)

    labels = {l.label for l in by_adm.items if l.label}
    some_label = sorted(labels)[0]
    by_label = await provider.list_lab_observations(ctx, subject_id=subject_id, label_contains=some_label[:5], limit=200)
    assert by_label.items and all(some_label[:5].lower() in (l.label or "").lower() for l in by_label.items)

    none = await provider.list_lab_observations(ctx, subject_id=subject_id, label_contains="zzz-no-existe", limit=10)
    assert none.items == [] and none.count == 0

    abnormal = await provider.list_lab_observations(ctx, subject_id=subject_id, abnormal_only=True, limit=200)
    assert all(l.flag == "abnormal" for l in abnormal.items)

    times = sorted(l.charttime for l in by_adm.items if l.charttime)
    if len(times) > 2:
        window = TimeRange(start=times[1], end=times[-2])
        ranged = await provider.list_lab_observations(ctx, subject_id=subject_id, hadm_id=hadm_id, time_range=window, limit=200)
        assert all(window.start <= l.charttime <= window.end for l in ranged.items)


def _first_hadm(subject_id: int) -> int:
    summary = load_expected(f"get_patient_summary__{subject_id}")["result"]
    return sorted(a["hadm_id"] for a in summary["admissions"])[0]


@pytest.mark.parametrize("subject_id", SUBJECTS)
async def test_admission_details_match_legacy(subject_id):
    hadm_id = _first_hadm(subject_id)
    legacy = load_expected(f"get_admission_details__{hadm_id}")["result"]
    provider = make_provider()

    details = await provider.get_admission_details(ctx_for(subject_id), hadm_id)

    assert details.admission.hadm_id == hadm_id
    assert details.admission.admission_type == legacy["admission_info"]["admission_type"]
    assert {(c.icd_code, c.icd_version) for c in details.conditions} == {(d["icd_code"], d["icd_version"]) for d in legacy["diagnoses"]}
    assert len(details.transfers) == len(legacy["transfers"])
    assert len(details.services) == len(legacy["services"])
    if details.admission.dischtime and details.admission.admittime:
        assert details.admission.length_of_stay_days is not None and details.admission.length_of_stay_days > 0


@pytest.mark.parametrize("subject_id", SUBJECTS)
async def test_medications_match_legacy_prescriptions(subject_id):
    legacy = load_expected(f"get_medication_history__{subject_id}")["result"]
    provider = make_provider()

    page = await provider.list_medications(ctx_for(subject_id), subject_id=subject_id, limit=200)

    legacy_rx = {m["drug"] for m in legacy if m["source"] == "prescriptions"}
    assert {m.drug for m in page.items} <= legacy_rx
    assert all(m.source == "prescription" for m in page.items)

    with_emar = await provider.list_medications(ctx_for(subject_id), subject_id=subject_id, include_emar=True, limit=200)
    assert any(m.source == "emar" for m in with_emar.items) == any(m["source"] == "emar" for m in legacy)


async def test_medications_filter_by_drug_substring():
    subject_id = SUBJECTS[0]
    provider = make_provider()
    all_meds = await provider.list_medications(ctx_for(subject_id), subject_id=subject_id, limit=200)
    needle = all_meds.items[0].drug.split(" ")[0]
    filtered = await provider.list_medications(ctx_for(subject_id), subject_id=subject_id, drug_contains=needle, limit=200)
    assert filtered.items and all(needle.lower() in m.drug.lower() for m in filtered.items)


@pytest.mark.parametrize("subject_id", SUBJECTS)
async def test_icu_observations_match_legacy_chartevents(subject_id):
    provider = make_provider()
    stays = await provider.list_icu_stays(ctx_for(subject_id), subject_id=subject_id)
    stay_id = sorted(s.stay_id for s in stays.items)[0]
    legacy = load_expected(f"get_icu_chartevents__{stay_id}")["result"]

    page = await provider.list_icu_observations(ctx_for(subject_id), stay_id=stay_id, limit=200)

    assert page.truncated == (len(legacy) > 200)
    legacy_keys = {(r["itemid"], str(r["charttime"])[:19]) for r in legacy}
    assert {(o.itemid, o.charttime.isoformat()[:19]) for o in page.items} <= legacy_keys
    assert all(o.label for o in page.items), "cada observacion lleva la etiqueta de d_items"

    by_item = await provider.list_icu_observations(ctx_for(subject_id), stay_id=stay_id, itemids=[220045], limit=200)
    assert all(o.itemid == 220045 for o in by_item.items)
    legacy_hr = load_expected(f"get_icu_chartevents__{stay_id}_itemid-220045")["result"]
    assert by_item.count == min(len(legacy_hr), 200)


async def test_truncation_respects_max_limit():
    subject_id = SUBJECTS[0]
    provider = make_provider(max_limit=5)
    page = await provider.list_lab_observations(ctx_for(subject_id), subject_id=subject_id, limit=999)
    assert isinstance(page, Page) and page.limit == 5 and page.count == 5 and page.truncated is True


async def test_icd_dictionary_search():
    provider = make_provider()
    legacy = load_expected("search_diagnoses__noargs_icd_code-04102")["result"]
    by_code = await provider.search_icd_codes(research_ctx(), code_prefix="0410", limit=50)
    assert {e.icd_code for e in by_code.items} >= {legacy[0]["icd_code"]}
    by_title = await provider.search_icd_codes(research_ctx(), title_contains="Streptococcus", limit=50)
    assert by_title.items and all("streptococcus" in e.long_title.lower() for e in by_title.items)
    empty = await provider.search_icd_codes(research_ctx())
    assert empty.items == []


async def test_dataset_aggregates_via_rpc():
    provider = make_provider()
    ctx = research_ctx()

    summary = await provider.get_dataset_summary(ctx)
    assert summary.patients == len(SUBJECTS) and summary.source == "mimic-iv-demo-2.2"

    top = await provider.top_diagnoses(ctx, limit=5)
    assert 0 < len(top.buckets) <= 5
    assert top.buckets[0].count >= top.buckets[-1].count
    assert all(b.label for b in top.buckets)

    drugs = await provider.top_drugs(ctx, limit=3)
    assert len(drugs.buckets) == 3 and drugs.truncated is True

    types = await provider.admission_type_distribution(ctx)
    assert sum(b.count for b in types.buckets) == 4  # admisiones en las fixtures


async def test_missing_rpc_degrades_with_actionable_message():
    provider = make_provider(make_memory_client(with_rpcs=False))
    with pytest.raises(ProviderUnavailable, match="0001_clinical_aggregates_v1"):
        await provider.top_drugs(research_ctx(), limit=3)


async def test_unknown_patient_and_admission_raise_not_found():
    provider = make_provider()
    with pytest.raises(NotFound):
        await provider.get_patient(ctx_for(99999999), 99999999)
    with pytest.raises(NotFound):
        await provider.resolve_admission_owner(1)
    owner = await provider.resolve_admission_owner(_first_hadm(SUBJECTS[0]))
    assert owner[0] == SUBJECTS[0]


async def test_adapter_always_filters_by_context_patient():
    """Defensa en profundidad: aunque se pida otro subject_id, la consulta lleva el paciente del contexto."""
    client = make_memory_client()
    provider = make_provider(client)
    other = SUBJECTS[1]
    page = await provider.list_conditions(ctx_for(SUBJECTS[0]), subject_id=other, limit=50)
    assert page.items == []
    filters = [f for c in client.calls if c.table == "diagnoses_icd" for f in c.filters]
    assert ("eq", "subject_id", SUBJECTS[0]) in filters


async def test_health_reports_latency():
    health = await make_provider().health()
    assert health.ok is True and health.latency_ms is not None
