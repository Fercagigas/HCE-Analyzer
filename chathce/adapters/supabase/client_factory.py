"""Construccion de clientes Supabase por funcion (ADR 0010 §10: credenciales separadas).

- ``clinical_client``: lectura de ``mimiciv_hosp``/``mimiciv_icu`` con la clave de solo lectura
  (``SUPABASE_CLINICAL_KEY``) si existe; si no, la clave general (transitorio, documentado).
- ``product_client``: tablas ``public.*`` (sesiones, mensajes, analisis, preferencias, rag_chunks).
- ``auth_client``: Supabase Auth (login, verificacion de tokens).
"""

from __future__ import annotations

from typing import Any, Optional


class SupabaseClients:
    def __init__(
        self,
        *,
        url: str,
        service_key: str,
        clinical_key: Optional[str] = None,
        postgrest_timeout_s: float = 30.0,
    ):
        if not url or not service_key:
            raise ValueError("SUPABASE_URL y SUPABASE_KEY son obligatorias para construir clientes")
        self._url = url
        self._service_key = service_key
        self._clinical_key = clinical_key or service_key
        self._timeout = postgrest_timeout_s
        self._clinical: Any = None
        self._product: Any = None

    @property
    def uses_dedicated_clinical_key(self) -> bool:
        return self._clinical_key != self._service_key

    def _create(self, key: str, schema: str = "public") -> Any:
        from supabase import ClientOptions, create_client

        options = ClientOptions(schema=schema, postgrest_client_timeout=self._timeout)
        return create_client(self._url, key, options)

    def clinical_client(self) -> Any:
        if self._clinical is None:
            self._clinical = self._create(self._clinical_key, schema="mimiciv_hosp")
        return self._clinical

    def product_client(self) -> Any:
        if self._product is None:
            self._product = self._create(self._service_key, schema="public")
        return self._product

    def auth_client(self) -> Any:
        return self.product_client()
