"""
Error Handler for Claude HCE Agent

This module provides comprehensive error handling with Spanish language support,
including error formatting, context logging, and user-friendly messages.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolExecutionError(Exception):
    """Exception for tool execution errors"""
    
    def __init__(self, message: str, tool_name: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.tool_name = tool_name
        self.details = details or {}
        self.timestamp = datetime.now()


class ErrorContext:
    """Container for error context information"""
    
    def __init__(
        self,
        error: Exception,
        operation: str,
        user_query: Optional[str] = None,
        model_name: Optional[str] = None,
        attempt_number: int = 1,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        self.error = error
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.operation = operation
        self.user_query = user_query
        self.model_name = model_name
        self.attempt_number = attempt_number
        self.additional_context = additional_context or {}
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error context to dictionary"""
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'operation': self.operation,
            'user_query': self.user_query,
            'model_name': self.model_name,
            'attempt_number': self.attempt_number,
            'timestamp': self.timestamp.isoformat(),
            'additional_context': self.additional_context,
            'stack_trace': self.stack_trace
        }


class SpanishErrorFormatter:
    """Formats errors with Spanish language messages and suggestions"""
    
    # Error message templates in Spanish
    ERROR_MESSAGES = {
        'RateLimitError': {
            'title': '🚦 Límite de Consultas Excedido',
            'message': 'Se han realizado demasiadas consultas al servicio de IA. Por favor, espere unos minutos antes de intentar nuevamente.',
            'suggestions': [
                'Espere 5-10 minutos antes de hacer nuevas consultas',
                'Intente consultas más simples que requieran menos procesamiento',
                'Considere dividir consultas complejas en partes más pequeñas'
            ],
            'severity': ErrorSeverity.MEDIUM
        },
        'AuthError': {
            'title': '🔐 Error de Autenticación',
            'message': 'No se pudo autenticar con el servicio de IA. Verifique la configuración de la clave API.',
            'suggestions': [
                'Contacte al administrador del sistema',
                'Verifique que la clave API de Claude esté configurada correctamente',
                'Compruebe que la clave API no haya expirado'
            ],
            'severity': ErrorSeverity.CRITICAL
        },
        'LLMError': {
            'title': '🤖 Problema con el Servicio de IA',
            'message': 'Hay un problema temporal con el servicio de inteligencia artificial. El sistema ha intentado usar modelos de respaldo.',
            'suggestions': [
                'El sistema intentará automáticamente usar modelos de respaldo',
                'Intente nuevamente en unos momentos',
                'Simplifique su consulta si es muy compleja'
            ],
            'severity': ErrorSeverity.HIGH
        },
        'AgentError': {
            'title': '🔧 Error de Procesamiento',
            'message': 'Hubo un problema procesando su consulta médica. Intente reformular su pregunta.',
            'suggestions': [
                'Reformule su pregunta de manera más específica',
                'Incluya IDs específicos de paciente o estancia si están disponibles',
                'Pregunte sobre tipos de consulta disponibles'
            ],
            'severity': ErrorSeverity.MEDIUM
        },
        'ToolExecutionError': {
            'title': '⚙️ Error en Herramienta',
            'message': 'Error al ejecutar una herramienta del sistema (base de datos o visualización).',
            'suggestions': [
                'Verifique que los parámetros de la consulta sean correctos',
                'Compruebe la conexión a la base de datos',
                'Intente una consulta más simple'
            ],
            'severity': ErrorSeverity.HIGH
        },
        'DatabaseError': {
            'title': '💾 Error de Base de Datos',
            'message': 'No se pudo conectar o consultar la base de datos médica.',
            'suggestions': [
                'Verifique su conexión a internet',
                'Compruebe que la base de datos MIMIC-IV-ED esté disponible',
                'Contacte al administrador si el problema persiste'
            ],
            'severity': ErrorSeverity.HIGH
        },
        'TimeoutError': {
            'title': '⏱️ Tiempo de Consulta Agotado',
            'message': 'Su consulta tardó demasiado en procesarse. Intente una pregunta más específica.',
            'suggestions': [
                'Intente consultar un ID de paciente específico',
                'Divida consultas complejas en preguntas más específicas',
                'Reduzca el rango de fechas o número de registros solicitados'
            ],
            'severity': ErrorSeverity.MEDIUM
        },
        'ValidationError': {
            'title': '📝 Error de Validación',
            'message': 'Los datos proporcionados no son válidos o están incompletos.',
            'suggestions': [
                'Verifique que los IDs de paciente o estancia sean correctos',
                'Asegúrese de proporcionar todos los parámetros requeridos',
                'Revise el formato de los datos ingresados'
            ],
            'severity': ErrorSeverity.LOW
        },
        'NetworkError': {
            'title': '🌐 Error de Conexión',
            'message': 'No se pudo establecer conexión con los servicios externos.',
            'suggestions': [
                'Verifique su conexión a internet',
                'Compruebe que no haya problemas de firewall',
                'Intente nuevamente en unos momentos'
            ],
            'severity': ErrorSeverity.HIGH
        }
    }
    
    @classmethod
    def format_error(
        cls,
        error: Exception,
        context: Optional[ErrorContext] = None,
        include_technical_details: bool = False
    ) -> Dict[str, Any]:
        """
        Format error with Spanish message and suggestions.
        
        Args:
            error: The exception to format
            context: Optional error context with additional information
            include_technical_details: Whether to include technical details
            
        Returns:
            Dict containing formatted error information
        """
        error_type = type(error).__name__
        
        # Get error template or use generic
        template = cls.ERROR_MESSAGES.get(error_type, {
            'title': '❌ Error Inesperado',
            'message': 'Ocurrió un error inesperado procesando su consulta.',
            'suggestions': [
                'Intente reformular su pregunta',
                'Contacte al soporte técnico si el problema persiste'
            ],
            'severity': ErrorSeverity.MEDIUM
        })
        
        # Build formatted error
        formatted_error = {
            'success': False,
            'error_type': error_type,
            'title': template['title'],
            'message': template['message'],
            'suggestions': template['suggestions'],
            'severity': template['severity'].value,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add context if available
        if context:
            formatted_error['context'] = {
                'operation': context.operation,
                'model_name': context.model_name,
                'attempt_number': context.attempt_number
            }
            
            if context.user_query:
                formatted_error['context']['user_query'] = context.user_query[:200]  # Truncate
        
        # Add technical details if requested
        if include_technical_details:
            formatted_error['technical_details'] = {
                'error_message': str(error),
                'error_class': error_type
            }
            
            if context:
                formatted_error['technical_details']['stack_trace'] = context.stack_trace
        
        # Add tool-specific information for ToolExecutionError
        if isinstance(error, ToolExecutionError):
            formatted_error['tool_name'] = error.tool_name
            formatted_error['tool_details'] = error.details
        
        return formatted_error
    
    @classmethod
    def format_user_message(cls, formatted_error: Dict[str, Any]) -> str:
        """
        Create user-friendly message from formatted error.
        
        Args:
            formatted_error: Formatted error dictionary
            
        Returns:
            User-friendly error message in Spanish
        """
        message_parts = [
            f"**{formatted_error['title']}**\n",
            f"{formatted_error['message']}\n",
            "\n**Sugerencias:**"
        ]
        
        for suggestion in formatted_error['suggestions']:
            message_parts.append(f"• {suggestion}")
        
        # Add context if available
        if 'context' in formatted_error and formatted_error['context'].get('model_name'):
            message_parts.append(
                f"\n*Modelo utilizado: {formatted_error['context']['model_name']}*"
            )
        
        return "\n".join(message_parts)


class ErrorLogger:
    """Handles comprehensive error logging with context"""
    
    @staticmethod
    def log_error(
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        """
        Log error with full context and appropriate severity level.
        
        Args:
            error: The exception to log
            context: Error context with additional information
            severity: Error severity level
        """
        # Determine log level based on severity
        log_level_map = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        
        log_level = log_level_map.get(severity, logging.ERROR)
        
        # Build log message
        log_message = (
            f"Error in {context.operation}: {context.error_type} - {context.error_message}"
        )
        
        # Log with appropriate level
        logger.log(
            log_level,
            log_message,
            extra={
                'error_context': context.to_dict(),
                'severity': severity.value
            }
        )
        
        # Log stack trace for high severity errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.log(log_level, f"Stack trace:\n{context.stack_trace}")
    
    @staticmethod
    def log_retry_attempt(
        error: Exception,
        attempt_number: int,
        max_attempts: int,
        delay: float,
        operation: str
    ):
        """
        Log retry attempt information.
        
        Args:
            error: The exception that triggered the retry
            attempt_number: Current attempt number
            max_attempts: Maximum number of attempts
            delay: Delay before next retry in seconds
            operation: Operation being retried
        """
        logger.warning(
            f"Retry attempt {attempt_number}/{max_attempts} for {operation} "
            f"after error: {type(error).__name__}. "
            f"Waiting {delay:.1f}s before retry..."
        )
    
    @staticmethod
    def log_fallback_switch(
        from_model: str,
        to_model: str,
        reason: str
    ):
        """
        Log model fallback switch.
        
        Args:
            from_model: Model being switched from
            to_model: Model being switched to
            reason: Reason for the switch
        """
        logger.info(
            f"Switching from model '{from_model}' to '{to_model}'. "
            f"Reason: {reason}"
        )


def handle_error(
    error: Exception,
    operation: str,
    user_query: Optional[str] = None,
    model_name: Optional[str] = None,
    attempt_number: int = 1,
    include_technical_details: bool = False
) -> Dict[str, Any]:
    """
    Comprehensive error handling function.
    
    This is the main entry point for error handling. It creates error context,
    formats the error for users, logs it appropriately, and returns a structured
    error response.
    
    Args:
        error: The exception to handle
        operation: Name of the operation that failed
        user_query: Optional user query that caused the error
        model_name: Optional name of the model being used
        attempt_number: Current attempt number (for retries)
        include_technical_details: Whether to include technical details in response
        
    Returns:
        Dict containing formatted error information
        
    Example:
        >>> try:
        ...     result = agent.process_message(query)
        ... except Exception as e:
        ...     error_response = handle_error(
        ...         e,
        ...         operation="process_message",
        ...         user_query=query,
        ...         model_name="claude-haiku-4-5-20251001"
        ...     )
    """
    # Create error context
    context = ErrorContext(
        error=error,
        operation=operation,
        user_query=user_query,
        model_name=model_name,
        attempt_number=attempt_number
    )
    
    # Format error for user
    formatted_error = SpanishErrorFormatter.format_error(
        error,
        context=context,
        include_technical_details=include_technical_details
    )
    
    # Determine severity
    error_type = type(error).__name__
    template = SpanishErrorFormatter.ERROR_MESSAGES.get(error_type, {})
    severity = template.get('severity', ErrorSeverity.MEDIUM)
    
    # Log error
    ErrorLogger.log_error(error, context, severity)
    
    # Add user-friendly message
    formatted_error['response'] = SpanishErrorFormatter.format_user_message(formatted_error)
    
    return formatted_error
