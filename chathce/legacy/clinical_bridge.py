"""Puente TRANSITORIO (WP4 -> WP8) entre las tools legacy y el ClinicalDataProvider nuevo.

Las tools de `services/` aun no reciben RequestContext. Mientras existan, obtienen
aqui un provider protegido por ScopeGuard y un contexto explicito:

- ``legacy_research_context()``: proposito investigacion para los agregados del dataset
  (unica capacidad que las tools legacy delegan ya en el core).
- ``legacy_patient_context(subject_id)``: scope de un paciente concreto.

Se elimina en WP8 cuando el ChatService construya el contexto real.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from chathce.application.scope_guard import ScopeGuard
from chathce.domain.context import Channel, Purpose, RequestContext

_lock = threading.Lock()
_provider: Optional[Any] = None
_provider_error: Optional[str] = None


def _build_provider() -> Any:
    from config.settings import get_settings
    from chathce.adapters.logging.audit_sink import build_audit_sink
    from chathce.adapters.memory.postgrest_client import InMemoryPostgrestClient, register_clinical_aggregate_rpcs
    from chathce.adapters.supabase.mimic_clinical_data_provider import MimicClinicalDataProvider

    settings = get_settings()
    clinical = settings.clinical
    if clinical.provider == "memory":
        client = register_clinical_aggregate_rpcs(InMemoryPostgrestClient())
    else:
        from chathce.adapters.supabase.client_factory import SupabaseClients

        db = settings.require_database()
        clients = SupabaseClients(
            url=db.supabase_url,
            service_key=db.supabase_key,
            clinical_key=clinical.supabase_clinical_key,
            postgrest_timeout_s=clinical.timeout_s,
        )
        client = clients.clinical_client()
    provider = MimicClinicalDataProvider(
        client,
        source_name=clinical.source_name,
        default_limit=clinical.default_limit,
        max_limit=clinical.max_limit,
        aggregate_limit=clinical.aggregate_limit,
        timeout_s=clinical.timeout_s,
    )
    return ScopeGuard(provider, audit=build_audit_sink(settings))


def get_legacy_clinical_provider() -> Any:
    """Provider protegido, construido una vez por proceso."""
    global _provider, _provider_error
    with _lock:
        if _provider is None:
            _provider = _build_provider()
        return _provider


def legacy_research_context(*, session_id: Optional[str] = None) -> RequestContext:
    return RequestContext(
        user_id="legacy-runtime",
        channel=Channel.streamlit,
        purpose=Purpose.research,
        roles=frozenset({"researcher"}),
        session_id=session_id,
    )


def legacy_patient_context(subject_id: int, *, session_id: Optional[str] = None) -> RequestContext:
    return RequestContext(
        user_id="legacy-runtime",
        channel=Channel.streamlit,
        patient_id=str(int(subject_id)),
        session_id=session_id,
    )
