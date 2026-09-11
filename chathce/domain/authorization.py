"""Matriz RBAC explicita para tools y endpoints (roadmap 05 P0.3)."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Mapping

from chathce.domain.context import Purpose
from chathce.domain.errors import AuthorizationDenied


class Role(str, Enum):
    clinician = "clinician"
    reviewer = "reviewer"
    admin = "admin"
    auditor = "auditor"
    knowledge_manager = "knowledge_manager"
    researcher = "researcher"


class EndpointAction(str, Enum):
    chat = "endpoint:chat"
    chat_stream = "endpoint:chat_stream"
    patient_summary = "endpoint:patient_summary"
    visualization_get = "endpoint:visualization_get"
    authorization_manage = "endpoint:authorization_manage"
    audit_read = "endpoint:audit_read"


CLINICAL_TOOLS = frozenset({
    "get_patient_summary", "get_admission_details", "get_diagnoses", "get_labs",
    "search_lab_items", "get_medications", "get_icu_stays", "get_icu_observations", "search_icd_codes",
    "create_visualization",
})
RESEARCH_TOOLS = frozenset({"get_dataset_statistics"})
KNOWLEDGE_TOOLS = frozenset({"search_clinical_documents"})


def tool_action(name: str) -> str:
    return f"tool:{name}"


ROLE_ACTIONS: Mapping[Role, FrozenSet[str]] = {
    Role.clinician: frozenset({EndpointAction.chat.value, EndpointAction.chat_stream.value,
                               EndpointAction.patient_summary.value, EndpointAction.visualization_get.value,
                               *(tool_action(name) for name in CLINICAL_TOOLS | KNOWLEDGE_TOOLS)}),
    Role.reviewer: frozenset({EndpointAction.chat.value, EndpointAction.chat_stream.value,
                              EndpointAction.patient_summary.value, EndpointAction.visualization_get.value,
                              *(tool_action(name) for name in CLINICAL_TOOLS | KNOWLEDGE_TOOLS)}),
    Role.admin: frozenset({EndpointAction.authorization_manage.value}),
    Role.auditor: frozenset({EndpointAction.audit_read.value}),
    # El hook de escritura/document governance queda deliberadamente fuera de este paquete.
    Role.knowledge_manager: frozenset({*(tool_action(name) for name in KNOWLEDGE_TOOLS)}),
    Role.researcher: frozenset({EndpointAction.chat.value, EndpointAction.chat_stream.value,
                                *(tool_action(name) for name in RESEARCH_TOOLS | KNOWLEDGE_TOOLS)}),
}

ROLE_PURPOSES: Mapping[Role, FrozenSet[Purpose]] = {
    Role.clinician: frozenset({Purpose.clinical_care}),
    Role.reviewer: frozenset({Purpose.clinical_care}),
    Role.admin: frozenset({Purpose.admin}),
    Role.auditor: frozenset({Purpose.audit}),
    Role.knowledge_manager: frozenset({Purpose.clinical_care}),
    Role.researcher: frozenset({Purpose.research}),
}


def normalize_roles(roles: FrozenSet[str] | set[str]) -> FrozenSet[Role]:
    try:
        return frozenset(Role(role) for role in roles)
    except ValueError as exc:
        raise AuthorizationDenied("El principal contiene un rol no reconocido.", reason="unknown_role") from exc


def is_allowed(roles: FrozenSet[str] | set[str], action: str) -> bool:
    return any(action in ROLE_ACTIONS[role] for role in normalize_roles(roles))


def require_action(roles: FrozenSet[str] | set[str], action: str) -> None:
    if not is_allowed(roles, action):
        raise AuthorizationDenied("El rol autenticado no tiene permiso para esta operacion.", reason="role_action_denied")


def require_purpose(roles: FrozenSet[str] | set[str], purpose: Purpose) -> None:
    if not any(purpose in ROLE_PURPOSES[role] for role in normalize_roles(roles)):
        raise AuthorizationDenied("El rol autenticado no permite el proposito de uso solicitado.", reason="purpose_denied")
