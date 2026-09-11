"""Dependencias FastAPI: contenedor, principal autenticado (Bearer Supabase JWT) y RequestContext."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chathce.composition.container import Container
from chathce.domain.context import Channel, Purpose, RequestContext, build_context
from chathce.domain.errors import AuthenticationFailed, DomainError
from chathce.domain.identity import Principal
from chathce.domain.authorization import EndpointAction, require_action

_bearer = HTTPBearer(auto_error=False)


class AuthRequired(DomainError):
    code = "AUTH_REQUIRED"


def get_container(request: Request) -> Container:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise DomainError("La aplicacion no esta inicializada", code="CONFIGURATION_ERROR")
    return container


async def get_principal(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    container: Container = Depends(get_container),
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise AuthRequired("Se requiere un token Bearer de Supabase Auth")
    try:
        principal = await container.identity.verify_access_token(credentials.credentials)
    except AuthenticationFailed:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AuthenticationFailed("Token invalido") from exc
    request.state.user_id = principal.user_id
    request.state.access_token = credentials.credentials
    return principal


def make_context(
    request: Request,
    principal: Principal,
    *,
    patient_id: Optional[str] = None,
    encounter_id: Optional[str] = None,
    session_id: Optional[str] = None,
    purpose: Purpose | str = Purpose.clinical_care,
) -> RequestContext:
    return build_context(
        user_id=principal.user_id, channel=Channel.api, roles=principal.roles, purpose=purpose,
        patient_id=patient_id, encounter_id=encounter_id, session_id=session_id,
        tenant_id=principal.tenant_id, trace_id=getattr(request.state, "trace_id", None),
        # Un servicio emitido por el IdP se usa como contexto firmado. Para
        # proveedores legacy se conserva la seleccion explicita, que ScopeGuard
        # contrasta siempre contra una relacion asistencial vigente.
        service_id=principal.service or getattr(request, "headers", {}).get("X-Service-Id", "default"),
        access_token=getattr(request.state, "access_token", None),
        service=principal.service,
    ).model_copy(update={"request_id": getattr(request.state, "request_id", None) or RequestContext.model_fields["request_id"].default_factory()})


def require_endpoint(principal: Principal, action: EndpointAction) -> Principal:
    """Aplica la matriz por endpoint sobre los roles resueltos del JWT validado."""
    require_action(principal.roles, action.value)
    return principal
