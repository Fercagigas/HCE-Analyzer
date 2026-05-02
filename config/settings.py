
"""
Enhanced configuration management with Pydantic
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os
from pathlib import Path

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }
    
class AISettings(BaseSettings):
    """AI and ML configuration"""
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    huggingface_api_token: Optional[str] = Field(None, env="HUGGINFACEHUB_API_TOKEN")
    model_name: str = Field("claude-haiku-4-5-20251001", env="MODEL_NAME")
    max_tokens: int = Field(4000, env="MAX_TOKENS")
    temperature: float = Field(0.1, env="TEMPERATURE")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }

class AppSettings(BaseSettings):
    """Application configuration"""
    app_name: str = "ChatHCE"
    version: str = "2.0.0"
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    secret_key: str = Field(..., env="SECRET_KEY")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }
    
class SecuritySettings(BaseSettings):
    """Security configuration"""
    session_timeout: int = Field(3600, env="SESSION_TIMEOUT")
    max_login_attempts: int = Field(5, env="MAX_LOGIN_ATTEMPTS")
    rate_limit_per_minute: int = Field(30, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(300, env="RATE_LIMIT_PER_HOUR")
    max_message_length: int = Field(5000, env="MAX_MESSAGE_LENGTH")
    burst_limit: int = Field(5, env="BURST_LIMIT")
    burst_window_seconds: float = Field(10.0, env="BURST_WINDOW_SECONDS")
    lockout_duration_seconds: int = Field(900, env="LOCKOUT_DURATION_SECONDS")
    max_query_complexity: int = Field(10, env="MAX_QUERY_COMPLEXITY")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }
    
class NotificationSettings(BaseSettings):
    """Notification configuration"""
    smtp_server: Optional[str] = Field(None, env="SMTP_SERVER")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(None, env="SMTP_PASSWORD")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }

class RAGSettings(BaseSettings):
    """
    RAG (Retrieval-Augmented Generation) configuration
    Uses Claude API (Anthropic) for document retrieval and clinical guideline queries
    """
    # LLM Configuration - Uses Claude API (Anthropic)
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    rag_model: str = Field("claude-haiku-4-5-20251001", alias="RAG_MODEL")
    
    # Claude fallback chain for RAG queries
    primary_model: str = Field("claude-haiku-4-5-20251001", alias="PRIMARY_MODEL")
    secondary_model: str = Field("claude-sonnet-4-5-20250929", alias="SECONDARY_MODEL")
    tertiary_model: str = Field("claude-opus-4-20250514", alias="TERTIARY_MODEL")
    fallback_model: str = Field("claude-haiku-4-5-20251001", alias="FALLBACK_MODEL")
    
    # RAG-specific settings
    max_tokens: int = Field(4000, alias="RAG_MAX_TOKENS")
    temperature: float = Field(0.1, alias="RAG_TEMPERATURE")
    
    # Query Augmentation settings
    query_augmentation_enabled: bool = Field(
        True, alias="RAG_QUERY_AUGMENTATION_ENABLED"
    )
    query_augmentation_model: str = Field(
        "claude-haiku-4-5-20251001", alias="RAG_QUERY_AUGMENTATION_MODEL"
    )
    query_augmentation_max_queries: int = Field(
        3, alias="RAG_QUERY_AUGMENTATION_MAX_QUERIES"
    )

    # API configuration
    api_retry_attempts: int = Field(3, alias="RAG_API_RETRY_ATTEMPTS")
    api_retry_delay: float = Field(2.0, alias="RAG_API_RETRY_DELAY")
    api_timeout_seconds: int = Field(60, alias="RAG_API_TIMEOUT_SECONDS")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow",
        "populate_by_name": True
    }


class MedicalAgentSettings(BaseSettings):
    """
    Medical Agent configuration for database queries and visualization.
    """
    # Agent configuration
    agent_role: str = Field("Asistente de Datos Médicos", env="AGENT_ROLE")
    agent_goal: str = Field("Proporcionar información médica precisa y visualizaciones de datos MIMIC-IV-ED", env="AGENT_GOAL")
    agent_backstory: str = Field("Analista experto en datos médicos con acceso a registros de urgencias hospitalarias", env="AGENT_BACKSTORY")
    max_iterations: int = Field(10, env="AGENT_MAX_ITERATIONS")
    allow_delegation: bool = Field(False, env="AGENT_ALLOW_DELEGATION")
    verbose: bool = Field(True, env="AGENT_VERBOSE")
    
    # Database query configuration
    query_timeout_seconds: int = Field(30, env="QUERY_TIMEOUT_SECONDS")
    max_result_rows: int = Field(1000, env="MAX_RESULT_ROWS")
    connection_retry_attempts: int = Field(3, env="CONNECTION_RETRY_ATTEMPTS")
    connection_retry_delay: float = Field(1.0, env="CONNECTION_RETRY_DELAY")
    
    # Visualization configuration
    visualization_dpi: int = Field(150, env="VISUALIZATION_DPI")
    visualization_timeout_seconds: int = Field(15, env="VISUALIZATION_TIMEOUT_SECONDS")
    max_chart_data_points: int = Field(5000, env="MAX_CHART_DATA_POINTS")
    chart_width: int = Field(800, env="CHART_WIDTH")
    chart_height: int = Field(600, env="CHART_HEIGHT")
    chart_format: str = Field("png", env="CHART_FORMAT")
    
    # Security and validation
    enable_query_validation: bool = Field(True, env="ENABLE_QUERY_VALIDATION")
    allowed_schemas: List[str] = Field(["mimic_ed"], env="ALLOWED_SCHEMAS")
    
    # Agent health monitoring
    health_check_interval: int = Field(300, env="HEALTH_CHECK_INTERVAL")  # 5 minutes
    max_memory_usage_mb: int = Field(512, env="MAX_MEMORY_USAGE_MB")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }


class ClaudeAgentSettings(BaseSettings):
    """Claude Agent configuration for medical conversation agent"""
    # API Configuration
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    
    # Model Configuration - Primary Model (Claude Haiku 4.5)
    primary_model: str = Field("claude-haiku-4-5-20251001", alias="PRIMARY_CLAUDE_MODEL")
    primary_model_version: str = Field("claude-haiku-4-5-20251001", alias="PRIMARY_CLAUDE_MODEL_VERSION")
    
    # Model Configuration - Secondary Model (Claude Sonnet 4.5)
    secondary_model: str = Field("claude-sonnet-4-5", alias="SECONDARY_CLAUDE_MODEL")
    secondary_model_version: str = Field("claude-sonnet-4-5-20250929", alias="SECONDARY_CLAUDE_MODEL_VERSION")
    
    # Model Configuration - Tertiary Model (Claude Opus 4)
    tertiary_model: str = Field("claude-opus-4-0", alias="TERTIARY_CLAUDE_MODEL")
    tertiary_model_version: str = Field("claude-opus-4-20250514", alias="TERTIARY_CLAUDE_MODEL_VERSION")
    
    # Performance Configuration
    max_tokens: int = Field(4096, alias="CLAUDE_MAX_TOKENS")
    temperature: float = Field(0.1, alias="CLAUDE_TEMPERATURE")
    timeout_seconds: int = Field(30, alias="CLAUDE_TIMEOUT_SECONDS")
    
    # Retry Configuration
    max_retries: int = Field(3, alias="CLAUDE_MAX_RETRIES")
    retry_delay: float = Field(2.0, alias="CLAUDE_RETRY_DELAY")
    backoff_multiplier: float = Field(2.0, alias="CLAUDE_BACKOFF_MULTIPLIER")
    
    # Agent Configuration
    agent_role: str = Field("Asistente Médico Especializado", alias="CLAUDE_AGENT_ROLE")
    max_iterations: int = Field(15, alias="CLAUDE_MAX_ITERATIONS")
    verbose: bool = Field(True, alias="CLAUDE_VERBOSE")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow",
        "populate_by_name": True
    }


class PerformanceSettings(BaseSettings):
    """Performance monitoring and optimization configuration"""
    # Performance monitoring
    monitoring_enabled: bool = Field(True, env="PERFORMANCE_MONITORING_ENABLED")
    metrics_collection_enabled: bool = Field(True, env="METRICS_COLLECTION_ENABLED")
    monitoring_interval_seconds: int = Field(30, env="MONITORING_INTERVAL_SECONDS")
    slow_query_threshold_ms: float = Field(1000.0, env="SLOW_QUERY_THRESHOLD_MS")
    
    # Cache settings
    cache_enabled: bool = Field(True, env="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(300, env="CACHE_TTL_SECONDS")
    max_cache_size_mb: int = Field(512, env="MAX_CACHE_SIZE_MB")
    cache_cleanup_interval_seconds: int = Field(600, env="CACHE_CLEANUP_INTERVAL_SECONDS")
    
    # Connection pool settings
    db_pool_size: int = Field(10, env="DB_POOL_SIZE")
    db_pool_max_overflow: int = Field(20, env="DB_POOL_MAX_OVERFLOW")
    api_pool_size: int = Field(5, env="API_POOL_SIZE")
    connection_timeout_seconds: int = Field(30, env="CONNECTION_TIMEOUT_SECONDS")
    
    # Batch processing settings
    batch_size: int = Field(100, env="BATCH_SIZE")
    batch_timeout_seconds: int = Field(30, env="BATCH_TIMEOUT_SECONDS")
    max_batch_queue_size: int = Field(1000, env="MAX_BATCH_QUEUE_SIZE")
    
    # Memory settings
    max_memory_usage_mb: int = Field(2000, env="MAX_MEMORY_USAGE_MB")
    memory_warning_threshold_mb: int = Field(1500, env="MEMORY_WARNING_THRESHOLD_MB")
    gc_threshold: int = Field(1000, env="GC_THRESHOLD")
    memory_cleanup_interval_seconds: int = Field(300, env="MEMORY_CLEANUP_INTERVAL_SECONDS")
    
    # Performance thresholds
    document_upload_threshold_ms: float = Field(30000.0, env="DOCUMENT_UPLOAD_THRESHOLD_MS")
    rag_query_threshold_ms: float = Field(5000.0, env="RAG_QUERY_THRESHOLD_MS")
    hce_query_threshold_ms: float = Field(5000.0, env="HCE_QUERY_THRESHOLD_MS")
    ui_load_threshold_ms: float = Field(10000.0, env="UI_LOAD_THRESHOLD_MS")
    
    # Alert settings
    alerts_enabled: bool = Field(True, env="PERFORMANCE_ALERTS_ENABLED")
    alert_cooldown_seconds: int = Field(300, env="ALERT_COOLDOWN_SECONDS")
    cpu_usage_alert_threshold: float = Field(80.0, env="CPU_USAGE_ALERT_THRESHOLD")
    memory_usage_alert_threshold: float = Field(85.0, env="MEMORY_USAGE_ALERT_THRESHOLD")
    
    # Logging settings
    performance_log_level: str = Field("INFO", env="PERFORMANCE_LOG_LEVEL")
    log_slow_operations: bool = Field(True, env="LOG_SLOW_OPERATIONS")
    log_memory_usage: bool = Field(True, env="LOG_MEMORY_USAGE")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }
    
class VisualizationSettings(BaseSettings):
    """
    Visualization System Configuration
    
    Configuration for the visualization agent that generates
    medical data visualizations using Claude Sonnet 4.5.
    
    Performance targets:
    - End-to-end visualization: <5000ms
    - Template-based generation: <1000ms
    - LLM-based generation: <4000ms
    """
    
    # Model Configuration - Uses Claude Sonnet 4.5 for code generation
    model_name: str = Field("claude-sonnet-4-5", env="VISUALIZATION_MODEL")
    model_version: str = Field("claude-sonnet-4-5-20250929", env="VISUALIZATION_MODEL_VERSION")
    
    # Performance Configuration
    max_tokens: int = Field(8192, env="VISUALIZATION_MAX_TOKENS")
    temperature: float = Field(0.1, env="VISUALIZATION_TEMPERATURE")
    timeout_seconds: int = Field(45, env="VISUALIZATION_TIMEOUT_SECONDS")
    
    # Retry Configuration
    max_retries: int = Field(3, env="VISUALIZATION_MAX_RETRIES")
    retry_delay: float = Field(1.5, env="VISUALIZATION_RETRY_DELAY")  # Reduced from 2.0
    
    # Visualization Generation
    max_code_length: int = Field(5000, env="VISUALIZATION_MAX_CODE_LENGTH")
    enable_template_fallback: bool = Field(True, env="VISUALIZATION_ENABLE_TEMPLATE_FALLBACK")
    
    # Visual Configuration
    default_template: str = Field("plotly_white", env="VISUALIZATION_DEFAULT_TEMPLATE")
    default_width: int = Field(800, env="VISUALIZATION_DEFAULT_WIDTH")
    default_height: int = Field(600, env="VISUALIZATION_DEFAULT_HEIGHT")
    
    # Performance Targets (in milliseconds)
    target_end_to_end_ms: int = Field(5000, env="VISUALIZATION_TARGET_END_TO_END_MS")
    target_template_ms: int = Field(1000, env="VISUALIZATION_TARGET_TEMPLATE_MS")
    target_llm_ms: int = Field(4000, env="VISUALIZATION_TARGET_LLM_MS")
    
    # Cache Configuration
    template_cache_size: int = Field(100, env="VISUALIZATION_TEMPLATE_CACHE_SIZE")
    validation_cache_size: int = Field(50, env="VISUALIZATION_VALIDATION_CACHE_SIZE")
    enable_caching: bool = Field(True, env="VISUALIZATION_ENABLE_CACHING")
    
    # Preprocessing Configuration
    null_threshold: float = Field(0.5, env="VISUALIZATION_NULL_THRESHOLD")  # 50% null threshold
    
    # Medical Color Palette
    color_palette: List[str] = Field(
        [
            "#2E86AB",  # Azul médico
            "#06A77D",  # Verde clínico
            "#D62828",  # Rojo alerta
            "#F77F00",  # Naranja advertencia
            "#8338EC",  # Púrpura
            "#3A86FF"   # Azul cielo
        ],
        env="VISUALIZATION_COLOR_PALETTE"
    )
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }


class UnifiedChatSettings(BaseSettings):
    """
    Unified Chat System Configuration
    
    Configuration for the unified chat interface that integrates
    database queries and RAG document search.
    """
    
    # Context Management
    max_context_messages: int = Field(
        10,
        env="UNIFIED_CHAT_MAX_CONTEXT_MESSAGES"
    )
    
    # Caching Configuration
    enable_caching: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_CACHING"
    )
    
    cache_ttl: int = Field(
        300,
        env="UNIFIED_CHAT_CACHE_TTL"
    )
    
    # LLM Configuration
    max_tokens: int = Field(
        4000,
        env="UNIFIED_CHAT_MAX_TOKENS"
    )
    
    temperature: float = Field(
        0.1,
        env="UNIFIED_CHAT_TEMPERATURE"
    )
    
    # Feature Flags
    enable_visualizations: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_VISUALIZATIONS"
    )
    
    enable_document_upload: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_DOCUMENT_UPLOAD"
    )
    
    # Performance Settings
    query_timeout_seconds: int = Field(
        30,
        env="UNIFIED_CHAT_QUERY_TIMEOUT"
    )
    
    rag_search_timeout_seconds: int = Field(
        15,
        env="UNIFIED_CHAT_RAG_TIMEOUT"
    )
    
    # Response Format
    response_language: str = Field(
        "es",
        env="UNIFIED_CHAT_RESPONSE_LANGUAGE"
    )
    
    include_sources: bool = Field(
        True,
        env="UNIFIED_CHAT_INCLUDE_SOURCES"
    )
    
    # Tool Configuration
    enable_database_tool: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_DATABASE_TOOL"
    )
    
    enable_rag_tool: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_RAG_TOOL"
    )
    
    enable_visualization_tool: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_VISUALIZATION_TOOL"
    )
    
    # Safety and Validation
    enable_query_validation: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_QUERY_VALIDATION"
    )
    
    max_query_complexity: int = Field(
        5,
        env="UNIFIED_CHAT_MAX_QUERY_COMPLEXITY"
    )
    
    max_result_rows: int = Field(
        1000,
        env="UNIFIED_CHAT_MAX_RESULT_ROWS"
    )
    
    # Retry Configuration
    max_retries: int = Field(
        3,
        env="UNIFIED_CHAT_MAX_RETRIES"
    )
    
    retry_delay: float = Field(
        2.0,
        env="UNIFIED_CHAT_RETRY_DELAY"
    )
    
    # Logging and Monitoring
    enable_performance_tracking: bool = Field(
        True,
        env="UNIFIED_CHAT_ENABLE_PERFORMANCE_TRACKING"
    )
    
    log_tool_usage: bool = Field(
        True,
        env="UNIFIED_CHAT_LOG_TOOL_USAGE"
    )
    
    # Session Management
    session_timeout_minutes: int = Field(
        60,
        env="UNIFIED_CHAT_SESSION_TIMEOUT"
    )
    
    save_conversation_history: bool = Field(
        True,
        env="UNIFIED_CHAT_SAVE_HISTORY"
    )
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }


class Settings(BaseSettings):
    """
    Main settings class
    
    Service-to-LLM Provider Mapping:
    - RAG Service: Uses Claude API (rag_settings)
    - Medical Agent: Uses Claude API (claude_agent)
    - Unified Chat: Uses Claude API (unified_chat)
    - Visualization: Uses Claude Sonnet 4.5 (visualization)
    - Legacy Agent: Uses Claude API (medical_agent)
    """
    database: DatabaseSettings = DatabaseSettings()
    ai: AISettings = AISettings()
    app: AppSettings = AppSettings()
    security: SecuritySettings = SecuritySettings()
    notifications: NotificationSettings = NotificationSettings()
    rag: RAGSettings = RAGSettings()
    medical_agent: MedicalAgentSettings = MedicalAgentSettings()
    claude_agent: ClaudeAgentSettings = ClaudeAgentSettings()
    performance: PerformanceSettings = PerformanceSettings()
    visualization: VisualizationSettings = VisualizationSettings()
    unified_chat: UnifiedChatSettings = UnifiedChatSettings()
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"  # Permite campos extra
    }

# Global settings instance
settings = Settings()
