"""Constructores de servicios legacy sobre el cliente Supabase en memoria.

Permiten ejecutar `DatabaseService` y `AuthService` sin red ni credenciales,
inyectando `FakeSupabaseClient` en lugar de pasar por sus constructores (que
abren conexiones reales).
"""

from __future__ import annotations

import time
from typing import Any

from tests.fakes.fake_supabase import FakeSupabaseClient


def make_database_service(client: FakeSupabaseClient) -> Any:
    """`DatabaseService` legacy con conexion directa al cliente fake."""
    from services.medical_agent.services.database_service import DatabaseService

    service = DatabaseService.__new__(DatabaseService)
    service.supabase = client
    service._connection_healthy = True
    service._last_health_check = time.time()
    service._health_check_interval = 10 ** 9
    service._use_connection_pool = False
    return service


def make_auth_service(client: FakeSupabaseClient) -> Any:
    """`AuthService` legacy apuntando al cliente fake (tablas public.*)."""
    from services.auth.auth_service import AuthService

    service = AuthService.__new__(AuthService)
    service.supabase_client = client
    service._use_connection_pool = False
    service._is_initialized = True
    return service
