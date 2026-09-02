import pytest
from pydantic import ValidationError

from chathce.domain.context import Channel, Purpose, RequestContext, build_context
from chathce.domain.errors import PurposeNotAllowed, ScopeViolation

pytestmark = pytest.mark.unit


def _ctx(**overrides) -> RequestContext:
    base = dict(user_id="u1", channel=Channel.api, patient_id="10001217")
    base.update(overrides)
    return RequestContext(**base)


def test_context_is_frozen_and_closed():
    ctx = _ctx()
    with pytest.raises(ValidationError):
        ctx.user_id = "otro"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        RequestContext(user_id="u", channel=Channel.api, extra_field=1)  # type: ignore[call-arg]


def test_ids_are_generated_when_absent():
    ctx = _ctx()
    assert len(ctx.trace_id) >= 8 and len(ctx.request_id) >= 8
    assert ctx.trace_id != ctx.request_id


def test_require_patient_accepts_matching_subject_as_int_or_str():
    ctx = _ctx()
    assert ctx.require_patient(10001217) == "10001217"
    assert ctx.require_patient("10001217") == "10001217"
    assert ctx.allows_patient(10001217) is True


def test_require_patient_without_scope_is_refused():
    ctx = _ctx(patient_id=None)
    with pytest.raises(ScopeViolation) as exc:
        ctx.require_patient(10001217)
    assert exc.value.reason == "patient_scope_required"


def test_require_patient_mismatch_is_refused():
    with pytest.raises(ScopeViolation) as exc:
        _ctx().require_patient(99999999)
    assert exc.value.reason == "patient_mismatch"


def test_encounter_scope_is_optional_but_enforced_when_set():
    assert _ctx().allows_encounter(1) is True
    ctx = _ctx(encounter_id="555")
    ctx.require_encounter(555)
    with pytest.raises(ScopeViolation):
        ctx.require_encounter(556)


def test_research_purpose_required_for_aggregates():
    with pytest.raises(PurposeNotAllowed):
        _ctx().require_research()
    _ctx(purpose=Purpose.research).require_research()


def test_build_context_requires_researcher_role_for_research():
    with pytest.raises(PurposeNotAllowed):
        build_context(user_id="u", channel=Channel.api, purpose="research")
    ctx = build_context(user_id="u", channel=Channel.api, purpose="research", roles={"researcher"})
    assert ctx.purpose == Purpose.research
    assert ctx.scope().purpose == Purpose.research


def test_build_context_coerces_ids_to_str():
    ctx = build_context(user_id="u", channel=Channel.streamlit, patient_id=10001217, encounter_id=22)
    assert ctx.patient_id == "10001217" and ctx.encounter_id == "22"
    assert ctx.with_patient(None).patient_id is None
