"""Inicio de sesion federado: Authorization Code con PKCE (OIDC)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from chathce.api.dependencies import get_container
from chathce.composition.container import Container
from chathce.domain.errors import ConfigurationError
from chathce.domain.identity import AuthSession

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _oidc(container: Container):
    identity = container.identity
    if not hasattr(identity, "begin_authorization") or not hasattr(identity, "exchange_authorization_code"):
        raise ConfigurationError("El login OIDC no esta habilitado en este despliegue")
    return identity


@router.get("/login", status_code=307)
async def login(
    issuer: Optional[str] = None,
    container: Container = Depends(get_container),
) -> RedirectResponse:
    """Redirige al IdP. El state, nonce y verifier se conservan solo en memoria."""
    identity = _oidc(container)
    redirect_uri = container.settings.identity.oidc_redirect_uri
    request = await identity.begin_authorization(redirect_uri=redirect_uri, issuer=issuer)
    return RedirectResponse(url=request.authorization_url, status_code=307, headers={"Cache-Control": "no-store"})


@router.get("/callback", response_model=AuthSession, response_model_exclude_none=True)
async def callback(
    code: str,
    state: str,
    container: Container = Depends(get_container),
) -> AuthSession:
    """Intercambia el codigo una sola vez y devuelve la sesion para un cliente confiable.

    Para una UI web se recomienda que un BFF/proxy transforme esta respuesta en
    una cookie HttpOnly. Streamlit usa ``accept_oidc_session`` y no contrasenas.
    """
    identity = _oidc(container)
    return await identity.exchange_authorization_code(code=code, state=state)
