"""Port de identidad: verificacion de tokens y ciclo de vida de sesion."""

from __future__ import annotations

from datetime import datetime
from typing import FrozenSet, Optional, Protocol, runtime_checkable

from chathce.domain.identity import AuthSession, Principal


@runtime_checkable
class IdentityProvider(Protocol):
    async def verify_access_token(self, token: str) -> Principal:
        """Principal o ``AuthenticationFailed``."""
        ...

    async def login(self, email: str, password: str) -> AuthSession: ...

    async def refresh(self, refresh_token: str) -> AuthSession: ...

    async def logout(self, access_token: str) -> None: ...

    async def register(
        self,
        *,
        email: str,
        password: str,
        name: str,
        specialty: Optional[str] = None,
        medical_license: Optional[str] = None,
    ) -> Principal: ...

    async def reset_password(self, email: str) -> None: ...

    async def has_active_patient_access(
        self, *, user_id: str, tenant_id: str, subject_id: int | str, service_id: str, at: datetime
    ) -> bool:
        """Comprueba en la fuente de concesiones la relacion asistencial vigente."""
        ...

    async def assign_roles(self, *, user_id: str, tenant_id: str, roles: FrozenSet[str]) -> None:
        """Actualiza exclusivamente los claims ``app_metadata`` del principal."""
        ...

    async def grant_patient_access(
        self, *, user_id: str, tenant_id: str, subject_id: int | str, service_id: str,
        valid_from: datetime, valid_until: Optional[datetime], granted_by: str,
    ) -> None:
        """Concede una relacion asistencial administrada y con vigencia."""
        ...

@runtime_checkable
class OidcCapableIdentityProvider(IdentityProvider, Protocol):
    """Extension opcional para el flujo Authorization Code + PKCE.

    El puerto base se conserva para no romper Supabase ni los fakes. Los canales
    que soporten OIDC pueden comprobar este protocolo antes de presentar login.
    """

    async def begin_authorization(self, *, redirect_uri: str, issuer: Optional[str] = None): ...

    async def exchange_authorization_code(self, *, code: str, state: str) -> AuthSession: ...
