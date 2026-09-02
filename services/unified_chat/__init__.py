"""
Unified Chat System (capa legacy de compatibilidad).

El agente vive en el core ``chathce`` (ModelGateway + ChatService). Aqui queda la fachada
``UnifiedChatAgent``/``create_unified_agent`` y el ``DocumentManager`` de ingesta.
"""

from services.unified_chat.unified_agent import UnifiedChatAgent, create_unified_agent

try:
    from services.unified_chat.document_manager import DocumentManager
    __all__ = ["UnifiedChatAgent", "create_unified_agent", "DocumentManager"]
except ImportError:  # pragma: no cover
    __all__ = ["UnifiedChatAgent", "create_unified_agent"]
