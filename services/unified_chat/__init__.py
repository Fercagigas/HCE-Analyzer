"""
Unified Chat System

This module provides a unified chat interface that integrates access to both
the MIMIC-IV-ED database and RAG-indexed clinical documents through a single
Claude-powered agent.
"""

# Import main agent
try:
    from services.unified_chat.unified_agent import UnifiedChatAgent, create_unified_agent
    _AGENT_AVAILABLE = True
except ImportError:
    _AGENT_AVAILABLE = False

# Import tools when they're available
try:
    from services.unified_chat.tools.database_tool import DatabaseTool, create_database_tool
    from services.unified_chat.tools.rag_tool import RAGTool, create_rag_tool
    _TOOLS_AVAILABLE = True
except ImportError:
    _TOOLS_AVAILABLE = False

# Import document manager
try:
    from services.unified_chat.document_manager import DocumentManager
    _DOCUMENT_MANAGER_AVAILABLE = True
except ImportError:
    _DOCUMENT_MANAGER_AVAILABLE = False

# Build __all__ based on what's available
__all__ = []

if _AGENT_AVAILABLE:
    __all__.extend(['UnifiedChatAgent', 'create_unified_agent'])

if _TOOLS_AVAILABLE:
    __all__.extend([
        'DatabaseTool', 'create_database_tool',
        'RAGTool', 'create_rag_tool'
    ])

if _DOCUMENT_MANAGER_AVAILABLE:
    __all__.extend(['DocumentManager'])
