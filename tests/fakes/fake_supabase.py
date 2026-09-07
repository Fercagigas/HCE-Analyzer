"""Alias de compatibilidad: el cliente en memoria vive en ``chathce.adapters.memory.postgrest_client``."""

from chathce.adapters.memory.postgrest_client import (  # noqa: F401
    InMemoryAPIError as FakeAPIError,
    InMemoryPostgrestClient as FakeSupabaseClient,
    RecordedCall,
    register_clinical_aggregate_rpcs,
)

__all__ = ["FakeAPIError", "FakeSupabaseClient", "RecordedCall", "register_clinical_aggregate_rpcs"]
