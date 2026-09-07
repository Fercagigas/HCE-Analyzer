"""
Configuracion centralizada con pydantic-settings.

Reglas (Fase 1, ADR 0010 / ADR 0120):
- Importar este modulo NUNCA exige credenciales ni abre red. Las credenciales se
  validan de forma explicita en el composition root mediante ``require_*``.
- El acceso canonico es ``get_settings()`` (perezoso y cacheado). No existe instancia global.
- ``HCE_DISABLE_DOTENV=1`` impide leer ``.env`` (tests sin credenciales).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field
from typing import Optional, List
import os
from pathlib import Path


def _env_file() -> Optional[str]:
    """Ruta del fichero .env, o None si esta deshabilitado por entorno."""
    if os.environ.get("HCE_DISABLE_DOTENV", "").strip().lower() in {"1", "true", "yes"}:
        return None
    return ".env"


_ENV_FILE = _env_file()


class ConfigurationError(RuntimeError):
    """Falta una variable de configuracion obligatoria para la operacion pedida."""

    def __init__(self, variables: List[str], purpose: str):
        self.variables = variables
        self.purpose = purpose
        names = ", ".join(variables)
        super().__init__(
            f"Configuracion incompleta para {purpose}: faltan {names}. "
            "Defina las variables en el entorno o en .env."
        )

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    supabase_url: Optional[str] = Field(None, env="SUPABASE_URL")
    supabase_key: Optional[str] = Field(None, env="SUPABASE_KEY")

    model_config = {
        "env_file": _ENV_FILE,
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
        "env_file": _ENV_FILE,
        "case_sensitive": False,
        "extra": "allow"
    }

class AppSettings(BaseSettings):
    """Application configuration"""
    app_name: str = "ChatHCE"
    version: str = "2.0.0"
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    model_config = {
        "env_file": _ENV_FILE,
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

    model_config = {
        "env_file": _ENV_FILE,
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
        "env_file": _ENV_FILE,
        "case_sensitive": False,
        "extra": "allow"
    }

class RAGSettings(BaseSettings):
    """
    RAG (Retrieval-Augmented Generation) configuration
    Uses Claude API (Anthropic) for document retrieval and clinical guideline queries
    """
    # LLM Configuration - Uses Claude API (Anthropic)
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
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
        "env_file": _ENV_FILE,
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
        "env_file": _ENV_FILE,
        "case_sensitive": False,
        "extra": "allow"
    }

class ClinicalDataSettings(BaseSettings):
    """Clinical Data Gateway (Fase 1): proveedor, limites y clave de solo lectura."""
    provider: str = Field("supabase_mimic", env="CLINICAL_PROVIDER")  # supabase_mimic | memory
    source_name: str = Field("mimic-iv-demo-2.2", env="CLINICAL_SOURCE_NAME")
    default_limit: int = Field(100, env="CLINICAL_DEFAULT_LIMIT")
    max_limit: int = Field(200, env="CLINICAL_MAX_LIMIT")
    aggregate_limit: int = Field(50, env="CLINICAL_AGGREGATE_LIMIT")
    timeout_s: float = Field(30.0, env="CLINICAL_TIMEOUT_S")
    # Clave de un rol de solo lectura sobre mimiciv_hosp/mimiciv_icu (db/README.md). Si falta,
    # se usa SUPABASE_KEY (transitorio, documentado en ADR 0100).
    supabase_clinical_key: Optional[str] = Field(None, validation_alias="SUPABASE_CLINICAL_KEY")

    model_config = {
        "env_file": _ENV_FILE,
        "case_sensitive": False,
        "extra": "allow",
        "env_prefix": "CLINICAL_"
    }


class LLMGatewaySettings(BaseSettings):
    """Model Gateway (Fase 1): cadena de modelos, timeouts, reintentos e iteraciones."""
    provider: str = Field("anthropic", env="LLM_PROVIDER")  # anthropic | fake
    model_chain: List[str] = Field(
        ["claude-haiku-4-5-20251001", "claude-sonnet-4-5", "claude-opus-4-0"], env="LLM_MODEL_CHAIN"
    )
    max_tokens: int = Field(4096, env="LLM_MAX_TOKENS")
    temperature: float = Field(0.1, env="LLM_TEMPERATURE")
    request_timeout_s: float = Field(60.0, env="LLM_REQUEST_TIMEOUT_S")
    total_timeout_s: float = Field(120.0, env="LLM_TOTAL_TIMEOUT_S")
    max_retries_per_model: int = Field(1, env="LLM_MAX_RETRIES_PER_MODEL")
    max_iterations: int = Field(6, env="LLM_MAX_ITERATIONS")
    max_tool_visible_chars: int = Field(12000, env="LLM_MAX_TOOL_VISIBLE_CHARS")
    query_augmentation_enabled: bool = Field(True, env="LLM_QUERY_AUGMENTATION_ENABLED")

    model_config = {
        "env_file": _ENV_FILE,
        "case_sensitive": False,
        "extra": "allow",
        "env_prefix": "LLM_"
    }


class APISettings(BaseSettings):
    """FastAPI (Fase 1): bind local, CORS cerrado por defecto, SSE."""
    host: str = Field("127.0.0.1", env="API_HOST")
    port: int = Field(8000, env="API_PORT")
    cors_allowed_origins: List[str] = Field(["http://localhost:8501", "http://127.0.0.1:8501"], env="API_CORS_ALLOWED_ORIGINS")
    docs_enabled: bool = Field(True, env="API_DOCS_ENABLED")
    sse_ping_s: int = Field(15, env="API_SSE_PING_S")
    ready_cache_s: int = Field(300, env="API_READY_CACHE_S")
    max_body_bytes: int = Field(64 * 1024, env="API_MAX_BODY_BYTES")
    environment: str = Field("dev", env="API_ENVIRONMENT")  # dev | prod (mensajes de error genericos)

    model_config = {
        "env_file": _ENV_FILE,
        "case_sensitive": False,
        "extra": "allow",
        "env_prefix": "API_"
    }


class AuditSettings(BaseSettings):
    """Auditoria estructurada sin PHI (roadmap 12)."""
    sink: str = Field("jsonl", env="AUDIT_SINK")  # jsonl | stdout | null
    directory: str = Field("logs/audit", env="AUDIT_DIRECTORY")

    model_config = {
        "env_file": _ENV_FILE,
        "case_sensitive": False,
        "extra": "allow",
        "env_prefix": "AUDIT_"
    }


class Settings(BaseSettings):
    """
    Main settings class

    Secciones: database, ai, app, security, notifications, rag, performance, clinical, llm, audit, api.
    """
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ai: AISettings = Field(default_factory=AISettings)
    app: AppSettings = Field(default_factory=AppSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    clinical: ClinicalDataSettings = Field(default_factory=ClinicalDataSettings)
    llm: LLMGatewaySettings = Field(default_factory=LLMGatewaySettings)
    audit: AuditSettings = Field(default_factory=AuditSettings)
    api: APISettings = Field(default_factory=APISettings)

    model_config = {
        "env_file": _ENV_FILE,
        "case_sensitive": False,
        "extra": "allow"  # Permite campos extra
    }

    # ------------------------------------------------------------------
    # Validacion explicita de credenciales (se invoca en el composition
    # root o en los adapters, nunca al importar).
    # ------------------------------------------------------------------
    def require_database(self) -> "DatabaseSettings":
        missing = [
            name for name, value in (
                ("SUPABASE_URL", self.database.supabase_url),
                ("SUPABASE_KEY", self.database.supabase_key),
            ) if not value
        ]
        if missing:
            raise ConfigurationError(missing, "acceso a Supabase")
        return self.database

    def require_anthropic(self) -> str:
        key = self.rag.anthropic_api_key or self.ai.anthropic_api_key
        if not key:
            raise ConfigurationError(["ANTHROPIC_API_KEY"], "acceso a Anthropic")
        return key


_SETTINGS_CLASSES = (
    DatabaseSettings, AISettings, AppSettings, SecuritySettings, NotificationSettings,
    RAGSettings, PerformanceSettings, ClinicalDataSettings, LLMGatewaySettings, AuditSettings, APISettings, Settings,
)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la instancia unica de Settings, construida en el primer uso.

    ``HCE_DISABLE_DOTENV`` se evalua aqui (no al importar) para que los tests
    puedan fijarlo con monkeypatch antes del primer acceso.
    """
    env_file = _env_file()
    for cls in _SETTINGS_CLASSES:
        cls.model_config["env_file"] = env_file
    return Settings()


def reset_settings_cache() -> None:
    """Descarta la instancia cacheada (tests que cambian el entorno)."""
    get_settings.cache_clear()


__all__ = [
    "Settings",
    "ConfigurationError",
    "get_settings",
    "reset_settings_cache",
    "DatabaseSettings",
    "AISettings",
    "AppSettings",
    "SecuritySettings",
    "NotificationSettings",
    "RAGSettings",
    "PerformanceSettings",
    "ClinicalDataSettings",
    "LLMGatewaySettings",
    "AuditSettings",
    "APISettings",
]
