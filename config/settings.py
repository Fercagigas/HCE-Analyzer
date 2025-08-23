
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
    chroma_persist_directory: str = Field("./chroma_db", env="CHROMA_PERSIST_DIR")
    
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
    model_name: str = Field("gpt-4", env="MODEL_NAME")
    max_tokens: int = Field(4000, env="MAX_TOKENS")
    temperature: float = Field(0.1, env="TEMPERATURE")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }

class AppSettings(BaseSettings):
    """Application configuration"""
    app_name: str = "HCE Analyzer Pro"
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
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    
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
    
class Settings(BaseSettings):
    """Main settings class"""
    database: DatabaseSettings = DatabaseSettings()
    ai: AISettings = AISettings()
    app: AppSettings = AppSettings()
    security: SecuritySettings = SecuritySettings()
    notifications: NotificationSettings = NotificationSettings()
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"  # Permite campos extra
    }

# Global settings instance
settings = Settings()
