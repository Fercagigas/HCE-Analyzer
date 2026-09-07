"""Identidad: principal autenticado y sesion de autenticacion."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, FrozenSet, Optional

from pydantic import BaseModel, ConfigDict, Field


class Principal(BaseModel):
    """Usuario autenticado. Nunca transporta email ni tokens."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    user_id: str = Field(min_length=1)
    tenant_id: str = "default"
    roles: FrozenSet[str] = frozenset()
    expires_at: Optional[datetime] = None
    display_name: Optional[str] = None

    def to_legacy_user_dict(self) -> Dict[str, object]:
        """Forma minima que espera la UI Streamlit actual."""
        return {"id": self.user_id, "name": self.display_name or "", "roles": sorted(self.roles)}


class AuthSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    access_token: str = Field(min_length=1)
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    principal: Principal
