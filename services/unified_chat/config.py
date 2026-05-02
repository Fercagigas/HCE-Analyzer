"""
Unified Chat Configuration

Configuration settings for the unified chat system that integrates
database queries and RAG document search.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class UnifiedChatSettings(BaseSettings):
    """
    Configuration for the Unified Chat System
    
    This configuration manages settings for the unified chat interface that
    combines MIMIC-IV-ED database access and RAG document search capabilities.
    """
    
    # Context Management
    max_context_messages: int = Field(
        10,
        env="UNIFIED_CHAT_MAX_CONTEXT_MESSAGES",
        description="Maximum number of messages to keep in conversation context"
    )
    
    # Caching Configuration
    enable_caching: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_CACHING",
        description="Enable caching for agent responses"
    )
    
    cache_ttl: int = Field(
        300,
        env="UNIFIED_CHAT_CACHE_TTL",
        description="Cache time-to-live in seconds"
    )
    
    # LLM Configuration
    max_tokens: int = Field(
        4000,
        env="UNIFIED_CHAT_MAX_TOKENS",
        description="Maximum tokens for LLM responses"
    )
    
    temperature: float = Field(
        0.1,
        env="UNIFIED_CHAT_TEMPERATURE",
        description="Temperature for LLM responses (0.0-1.0)"
    )
    
    # Feature Flags
    enable_visualizations: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_VISUALIZATIONS",
        description="Enable visualization generation"
    )
    
    enable_document_upload: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_DOCUMENT_UPLOAD",
        description="Enable document upload functionality"
    )
    
    # Performance Settings
    query_timeout_seconds: int = Field(
        30,
        env="UNIFIED_CHAT_QUERY_TIMEOUT",
        description="Timeout for database queries in seconds"
    )
    
    rag_search_timeout_seconds: int = Field(
        15,
        env="UNIFIED_CHAT_RAG_TIMEOUT",
        description="Timeout for RAG searches in seconds"
    )
    
    # Response Format
    response_language: str = Field(
        "es",
        env="UNIFIED_CHAT_RESPONSE_LANGUAGE",
        description="Response language (es=Spanish, en=English)"
    )
    
    include_sources: bool = Field(
        True,
        env="UNIFIED_CHAT_INCLUDE_SOURCES",
        description="Include source citations in RAG responses"
    )
    
    # Tool Configuration
    enable_database_tool: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_DATABASE_TOOL",
        description="Enable database query tool"
    )
    
    enable_rag_tool: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_RAG_TOOL",
        description="Enable RAG document search tool"
    )
    
    enable_visualization_tool: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_VISUALIZATION_TOOL",
        description="Enable visualization generation tool"
    )
    
    # Safety and Validation
    enable_query_validation: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_QUERY_VALIDATION",
        description="Enable SQL query validation for safety"
    )
    
    max_query_complexity: int = Field(
        5,
        env="UNIFIED_CHAT_MAX_QUERY_COMPLEXITY",
        description="Maximum allowed query complexity level"
    )
    
    max_result_rows: int = Field(
        1000,
        env="UNIFIED_CHAT_MAX_RESULT_ROWS",
        description="Maximum number of rows to return from queries"
    )
    
    # Retry Configuration
    max_retries: int = Field(
        3,
        env="UNIFIED_CHAT_MAX_RETRIES",
        description="Maximum number of retry attempts for failed operations"
    )
    
    retry_delay: float = Field(
        2.0,
        env="UNIFIED_CHAT_RETRY_DELAY",
        description="Delay between retry attempts in seconds"
    )
    
    # Logging and Monitoring
    enable_performance_tracking: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_PERFORMANCE_TRACKING",
        description="Enable performance tracking for agent operations"
    )
    
    log_tool_usage: bool = Field(
        True,
        env="UNIFIED_CHAT_LOG_TOOL_USAGE",
        description="Log which tools are used for each query"
    )
    
    # Session Management
    session_timeout_minutes: int = Field(
        60,
        env="UNIFIED_CHAT_SESSION_TIMEOUT",
        description="Session timeout in minutes"
    )
    
    save_conversation_history: bool = Field(
        True,
        env="UNIFIED_CHAT_SAVE_HISTORY",
        description="Save conversation history to database"
    )
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }


# Global instance
unified_chat_settings = UnifiedChatSettings()
