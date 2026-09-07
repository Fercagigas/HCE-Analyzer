"""
Unified Chat Agent (fachada legacy sobre el core chathce).

Desde WP8 (ADR 0080) el bucle agentico vive en ``chathce.gateway.ModelGateway`` y el caso
de uso en ``chathce.application.ChatService``. Este modulo conserva el contrato
``UnifiedChatAgent.process_message(message, context=None, session_id=None, ...) -> dict``
que consumen ``ui/unified_chat_interface.py`` y los runners de ``Evaluation/``.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from chathce.composition.container import Container, build_container
from chathce.domain.context import Channel
from chathce.legacy.agent_facade import LegacyAgentFacade

logger = logging.getLogger(__name__)

_container: Optional[Container] = None
_container_lock = threading.Lock()


def get_shared_container() -> Container:
    """Contenedor unico por proceso (RAG/CUDA y clientes HTTP se comparten)."""
    global _container
    with _container_lock:
        if _container is None:
            from config.settings import get_settings

            _container = build_container(get_settings())
            logger.info("Contenedor chathce construido: %s", _container.profile)
        return _container


class UnifiedChatAgent(LegacyAgentFacade):
    """Fachada fina: mismo nombre y contrato que el agente LangChain retirado."""

    def __init__(self, container: Optional[Container] = None, *, channel: Channel = Channel.streamlit, persist: bool = False):
        super().__init__(container or get_shared_container(), channel=channel, persist=persist)

    # process_message, get_performance_stats y reset_to_primary_model heredados de LegacyAgentFacade


def create_unified_agent(container: Optional[Container] = None) -> UnifiedChatAgent:
    return UnifiedChatAgent(container)
