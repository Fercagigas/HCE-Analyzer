
"""
Advanced logging system
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import sys

class StructuredLogger:
    """Advanced structured logging with multiple handlers"""
    
    def __init__(self, name: str = "hce_analyzer", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers"""
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler for general logs
        file_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Error handler
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "error.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        
        # Audit handler for security events
        audit_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "audit.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10
        )
        audit_handler.setLevel(logging.INFO)
        audit_formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        
        # Separate audit logger
        self.audit_logger = logging.getLogger(f"{self.logger.name}.audit")
        self.audit_logger.addHandler(audit_handler)
        self.audit_logger.setLevel(logging.INFO)
    
    def log_structured(self, level: str, message: str, **kwargs):
        """Log structured data"""
        structured_data = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'level': level.upper(),
            **kwargs
        }
        
        log_message = json.dumps(structured_data, ensure_ascii=False)
        getattr(self.logger, level.lower())(log_message)
    
    def log_user_action(self, user_id: str, action: str, details: Optional[Dict[str, Any]] = None):
        """Log user actions for audit"""
        audit_data = {
            'user_id': user_id,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        self.audit_logger.info(json.dumps(audit_data, ensure_ascii=False))
    
    def log_analysis_request(self, user_id: str, patient_id: str, document_type: str):
        """Log analysis requests"""
        self.log_structured(
            'info',
            'Analysis request initiated',
            user_id=user_id,
            patient_id=patient_id,
            document_type=document_type,
            event_type='analysis_request'
        )
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any]):
        """Log errors with additional context"""
        self.log_structured(
            'error',
            f'Error occurred: {str(error)}',
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            event_type='error'
        )
    
    def log_performance_metric(self, operation: str, duration: float, **kwargs):
        """Log performance metrics"""
        self.log_structured(
            'info',
            f'Performance metric: {operation}',
            operation=operation,
            duration_seconds=duration,
            event_type='performance',
            **kwargs
        )

# Global logger instance
logger = StructuredLogger()
