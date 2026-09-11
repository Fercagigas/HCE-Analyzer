"""Pruebas offline de la matriz RBAC y del ABAC asistencial (roadmap 05 P0.3/P0.4)."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import BaseModel, ConfigDict

from chathce.adapters.memory import CollectingAuditSink, InMemoryIdentityProvider
from chathce.application.scope_guard import ScopeGuard
from chathce.domain.authorization import EndpointAction, Role, is_allowed, require_action, tool_action
from chathce.domain.context import Channel, Purpose, RequestContext, build_context
from chathce.domain.errors import AuthorizationDenied, ScopeViolation
from chathce.domain.tools import AuditCategory, ToolContract
from chathce.gateway.policy import ToolPolicy
from tests.fakes.mimic_fixtures import fixtures_available, load_manifest, make_memory_client, make_provider

pytestmark = pytest.mark.security


class ClosedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClosedOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


@pytest.mark.parametrize(
    ("role", "tool", "allowed"),
    [
        (Role.clinician, "get_labs", True), (Role.clinician, "get_dataset_statistics", False),
        (Role.reviewer, "get_labs", True), (Role.reviewer, "get_dataset_statistics", False),
        (Role.researcher, "get_dataset_statistics", True), (Role.researcher, "get_labs", False),
        (Role.admin, "get_labs", False), (Role.auditor, "get_labs", False),
        (Role.knowledge_manager, "search_clinical_documents", True),
        (Role.knowledge_manager, "get_labs", False),
    ],
)
def test_role_by_tool_matrix_is_explicit_and_denies_unlisted(role, tool, allowed):
    assert is_allowed({role.value}, tool_action(tool)) is allowed


@pytest.mark.parametrize(
    ("role", "endpoint", "allowed"),
    [
        (Role.clinician, EndpointAction.chat, True), (Role.clinician, EndpointAction.authorization_manage, False),
        (Role.admin, EndpointAction.authorization_manage, True), (Role.admin, EndpointAction.chat, False),
        (Role.auditor, EndpointAction.audit_read, True), (Role.auditor, EndpointAction.patient_summary, False),
    ],
)
def test_role_by_endpoint_matrix_is_explicit(role, endpoint, allowed):
    if allowed:
        require_action({role.value}, endpoint.value)
    else:
        with pytest.raises(AuthorizationDenied):
            require_action({role.value}, endpoint.value)


@pytest.mark.parametrize(
    ("role", "purpose", "allowed"),
    [("clinician", Purpose.clinical_care, True), ("clinician", Purpose.research, False),
     ("researcher", Purpose.research, True), ("admin", Purpose.admin, True), ("auditor", Purpose.audit, True)],
)
def test_purpose_of_use_is_bound_to_role(role, purpose, allowed):
    if allowed:
        assert build_context(user_id="u", channel=Channel.api, roles={role}, purpose=purpose).purpose == purpose
    else:
        with pytest.raises(AuthorizationDenied):
            build_context(user_id="u", channel=Channel.api, roles={role}, purpose=purpose)


def test_unknown_role_and_unlisted_tool_are_fail_closed():
    with pytest.raises(AuthorizationDenied):
        require_action({"superuser"}, EndpointAction.chat.value)
    contract = ToolContract(name="unlisted_tool", description="Herramienta de prueba sin permiso en la matriz.",
                            input_model=ClosedInput, output_model=ClosedOutput, requires_patient_scope=False,
                            audit_category=AuditCategory.clinical_data)
    error = ToolPolicy().check(RequestContext(user_id="u", channel=Channel.api, roles=frozenset({"clinician"})), contract, ClosedInput())
    assert error is not None and error.code == "authorization_refused"


@pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")
async def test_missing_expired_and_cross_tenant_relationships_are_refused():
    subject = load_manifest()["subject_ids"][0]
    now = datetime.now(timezone.utc)
    identity = InMemoryIdentityProvider()
    guard = ScopeGuard(make_provider(make_memory_client()), audit=CollectingAuditSink(), patient_access=identity)
    ctx = RequestContext(user_id="u", tenant_id="hospital-a", service_id="cardiology", channel=Channel.api,
                         patient_id=str(subject), roles=frozenset({"clinician"}))

    with pytest.raises(ScopeViolation, match="relacion asistencial"):
        await guard.get_patient_summary(ctx, subject)

    await identity.grant_patient_access(user_id="u", tenant_id="hospital-a", subject_id=subject, service_id="cardiology",
                                        valid_from=now - timedelta(days=2), valid_until=now - timedelta(seconds=1), granted_by="admin")
    with pytest.raises(ScopeViolation) as expired:
        await guard.get_patient_summary(ctx, subject)
    assert expired.value.reason == "care_relationship_missing"

    await identity.grant_patient_access(user_id="u", tenant_id="hospital-b", subject_id=subject, service_id="cardiology",
                                        valid_from=now - timedelta(minutes=1), valid_until=None, granted_by="admin")
    with pytest.raises(ScopeViolation) as cross_tenant:
        await guard.get_patient_summary(ctx, subject)
    assert cross_tenant.value.reason == "care_relationship_missing"

    await identity.grant_patient_access(user_id="u", tenant_id="hospital-a", subject_id=subject, service_id="cardiology",
                                        valid_from=now - timedelta(minutes=1), valid_until=None, granted_by="admin")
    assert (await guard.get_patient_summary(ctx, subject)).patient.subject_id == subject
