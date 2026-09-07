"""ChatHCE core (Fase 1, ADR 0010).

Estructura:
- ``chathce.domain``: contratos y modelos (RequestContext, DTOs clinicos, Evidence/Claim, tools, chat, audit).
- ``chathce.ports``: interfaces (Protocol) que implementan los adapters.
- ``chathce.application``: casos de uso (ChatService, ScopeGuard, ...).
- ``chathce.gateway``: ModelGateway, ToolRegistry, politica de tools.
- ``chathce.adapters``: implementaciones concretas (anthropic, supabase, memory, logging).
- ``chathce.composition``: composition root.
- ``chathce.api`` / ``chathce.streamlit_adapter`` / ``chathce.legacy``: adapters de presentacion.

Regla verificada por ``tests/unit/test_architecture_boundaries.py``: fuera de
``chathce.adapters`` (y de los adapters de presentacion) no se importa
``streamlit``, ``supabase``, ``postgrest``, ``anthropic`` ni ``langchain*``.
"""

__version__ = "3.0.0-fase1"
