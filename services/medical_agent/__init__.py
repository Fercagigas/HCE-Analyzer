"""
Medical Agent Module for HCE Analyzer

This module provides Claude-based conversational agents for medical data analysis
and visualization using the MIMIC-IV-ED dataset.
"""

# Import error classes
try:
    from .error_handler import (
        ToolExecutionError,
        ErrorContext,
        SpanishErrorFormatter,
        handle_error
    )
    from .llm_manager import LLMError, RateLimitError, AuthError
    
    __all__ = [
        "ToolExecutionError",
        "ErrorContext",
        "SpanishErrorFormatter",
        "handle_error",
        "LLMError",
        "RateLimitError",
        "AuthError"
    ]
except ImportError as e:
    print(f"Warning: Could not import error classes: {e}")
    __all__ = []

# Import performance monitoring
try:
    from .agent_performance_monitor import (
        get_performance_monitor,
        track_performance,
        log_performance_summary
    )
    if __all__:
        __all__.extend([
            "get_performance_monitor",
            "track_performance",
            "log_performance_summary"
        ])
    else:
        __all__ = [
            "get_performance_monitor",
            "track_performance",
            "log_performance_summary"
        ]
except ImportError as e:
    print(f"Warning: Could not import performance monitoring: {e}")

# Import Claude tools and services
try:
    from .tools.database_tool_claude import create_claude_database_tool
    from .tools.visualization_collaboration_tool import create_visualization_collaboration_tool
    from .services.database_service import DatabaseService
    if __all__:
        __all__.extend([
            "create_claude_database_tool",
            "create_visualization_collaboration_tool",
            "DatabaseService"
        ])
    else:
        __all__ = [
            "create_claude_database_tool",
            "create_visualization_collaboration_tool",
            "DatabaseService"
        ]
except ImportError as e:
    print(f"Warning: Could not import tools/services: {e}")