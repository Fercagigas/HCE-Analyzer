"""Port de identidad: verificacion de tokens y ciclo de vida de sesion."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

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
