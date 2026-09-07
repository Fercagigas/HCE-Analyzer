"""Integracion (lectura) de `MimicClinicalDataProvider` contra Supabase demo.

Requiere HCE_RUN_INTEGRATION=1 y credenciales. Los agregados se saltan si las RPC de
`db/migrations/0001` aun no estan aplicadas.
"""

import pytest

from chathce.adapters.supabase.client_factory import SupabaseClients
from chathce.adapters.supabase.mimic_clinical_data_provider import MimicClinicalDataProvider
from chathce.domain.context import Channel, Purpose, RequestContext
from chathce.domain.errors import ProviderUnavailable
from tests.fakes.mimic_fixtures import fixtures_available, load_manifest


@pytest.fixture(scope="module")
def provider(integration_settings):
    db = integration_settings.database
    clients = SupabaseClients(url=db.supabase_url, service_key=db.supabase_key,
                              clinical_key=integration_settings.clinical.supabase_clinical_key)
    return MimicClinicalDataProvider(clients.clinical_client())


def _subject() -> int:
    return load_manifest()["subject_ids"][0] if fixtures_available() else 10001217


async def test_health(provider):
    health = await provider.health()
    assert health.ok, health.detail


async def test_patient_summary_live(provider):
    sid = _subject()
    ctx = RequestContext(user_id="it", channel=Channel.cli, patient_id=str(sid))
    summary = await provider.get_patient_summary(ctx, sid)
    assert summary.patient.subject_id == sid
    assert summary.stats.total_admissions >= 1
    assert all(c.title for c in summary.conditions)


async def test_label_filter_uses_dictionary_live(provider):
    sid = _subject()
    ctx = RequestContext(user_id="it", channel=Channel.cli, patient_id=str(sid))
    page = await provider.list_lab_observations(ctx, subject_id=sid, label_contains="Hemoglobin", limit=20)
    assert all("hemoglobin" in (l.label or "").lower() for l in page.items)


async def test_aggregates_live_or_skip(provider):
    ctx = RequestContext(user_id="it", channel=Channel.cli, purpose=Purpose.research, roles=frozenset({"researcher"}))
    try:
        top = await provider.top_diagnoses(ctx, limit=5)
    except ProviderUnavailable as exc:
        pytest.skip(f"RPC de agregados no aplicada: {exc}")
    assert top.buckets and top.buckets[0].count >= top.buckets[-1].count
    summary = await provider.get_dataset_summary(ctx)
    assert summary.patients == 100
