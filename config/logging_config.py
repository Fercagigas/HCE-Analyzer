"""
Logging configuration for ChatHCE
Provides detailed logging setup for debugging and monitoring
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
import structlog
from typing import Dict, Any

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Log levels mapping
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Add color to levelname
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        
        return super().format(record)

def setup_logging(
    level: str = "INFO",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    enable_structured_logging: bool = True,
    log_file_max_size: int = 10 * 1024 * 1024,  # 10MB
    log_file_backup_count: int = 5
) -> None:
    """
    Setup comprehensive logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Enable file logging
        enable_console_logging: Enable console logging
        enable_structured_logging: Enable structured logging with structlog
        log_file_max_size: Maximum size of log files in bytes
        log_file_backup_count: Number of backup log files to keep
    """
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set root logger level
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    colored_formatter = ColoredFormatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(colored_formatter)
        root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_file_logging:
        # Main application log
        app_log_file = LOGS_DIR / "hce_analyzer.log"
        app_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=log_file_max_size,
            backupCount=log_file_backup_count,
            encoding='utf-8'
        )
        app_handler.setLevel(log_level)
        app_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(app_handler)
        
        # Error log (only errors and critical)
        error_log_file = LOGS_DIR / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=log_file_max_size,
            backupCount=log_file_backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # Performance log
        perf_log_file = LOGS_DIR / "performance.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=log_file_max_size,
            backupCount=log_file_backup_count,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(simple_formatter)
        
        # Add filter for performance logs
        class PerformanceFilter(logging.Filter):
            def filter(self, record):
                return 'performance' in record.name.lower() or 'monitor' in record.name.lower()
        
        perf_handler.addFilter(PerformanceFilter())
        root_logger.addHandler(perf_handler)
    
    # Setup structured logging with structlog
    if enable_structured_logging:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    # Configure specific loggers
    configure_specific_loggers(log_level)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"🔧 Logging configured - Level: {level}, File: {enable_file_logging}, Console: {enable_console_logging}")

def configure_specific_loggers(log_level: int) -> None:
    """Configure specific loggers with appropriate levels"""
    
    # Unified chat components - detailed logging
    unified_chat_loggers = [
        'services.unified_chat',
        'services.unified_chat.unified_agent',
        'services.unified_chat.tools',
        'ui.components.message_handler',
        'services.medical_agent',
        'services.rag_service',
    ]
    
    for logger_name in unified_chat_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
    
    # Performance monitoring - info level
    performance_loggers = [
        'services.performance_monitor',
        'services.real_time_performance_monitor',
        'services.performance_metrics_collector',
        'services.performance_analytics'
    ]
    
    for logger_name in performance_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
    
    # External libraries - warning level to reduce noise
    external_loggers = [
        'httpx',
        'urllib3',
        'requests',
        'openai',
        'langchain',
        'sentence_transformers'
    ]
    
    for logger_name in external_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
    
    # Streamlit - warning level
    streamlit_loggers = [
        'streamlit',
        'streamlit.runtime',
        'streamlit.web'
    ]
    
    for logger_name in streamlit_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    return logging.getLogger(name)

def get_structured_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)

def log_system_info() -> None:
    """Log system information for debugging"""
    logger = get_logger(__name__)
    
    import platform
    import sys
    import os
    
    logger.info("🖥️ System Information:")
    logger.info(f"   Platform: {platform.platform()}")
    logger.info(f"   Python: {sys.version}")
    logger.info(f"   Working Directory: {os.getcwd()}")
    logger.info(f"   Process ID: {os.getpid()}")

def log_configuration_info() -> None:
    """Log configuration information"""
    logger = get_logger(__name__)
    
    try:
        from config.settings import settings
        logger.info("⚙️ Configuration loaded successfully")
        logger.info(f"   Debug mode: {getattr(settings, 'debug', False)}")
        logger.info(f"   Environment: {getattr(settings, 'environment', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Error loading configuration: {e}")

def create_debug_session(session_name: str = None) -> Dict[str, Any]:
    """Create a debug session with detailed logging"""
    if not session_name:
        session_name = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger = get_logger(__name__)
    
    debug_info = {
        'session_name': session_name,
        'start_time': datetime.now().isoformat(),
        'log_level': logging.getLevelName(logger.level),
        'handlers': [type(h).__name__ for h in logger.handlers]
    }
    
    logger.info(f"🐛 Debug session started: {session_name}")
    logger.debug(f"Debug session info: {debug_info}")
    
    return debug_info

# Auto-setup logging when module is imported
def auto_setup_logging():
    """Auto-setup logging with default configuration"""
    try:
        # Try to get log level from environment
        import os
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        setup_logging(
            level=log_level,
            enable_file_logging=True,
            enable_console_logging=True,
            enable_structured_logging=True
        )
        
        # Log system and configuration info
        log_system_info()
        log_configuration_info()
        
    except Exception as e:
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to setup advanced logging: {e}")

# Setup logging when module is imported
auto_setup_logging()