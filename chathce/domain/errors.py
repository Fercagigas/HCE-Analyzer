"""Jerarquia de errores del dominio.

Los adapters traducen las excepciones de sus SDKs a estas clases; la aplicacion y
la API solo conocen estas.
"""

from __future__ import annotations

from typing import Optional


class DomainError(Exception):
    """Base de todos los errores del dominio."""

    code: str = "INTERNAL_ERROR"
    retryable: bool = False

    def __init__(self, message: str, *, code: Optional[str] = None, retryable: Optional[bool] = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if retryable is not None:
            self.retryable = retryable


class ConfigurationError(DomainError):
    code = "CONFIGURATION_ERROR"


class ScopeViolation(DomainError):
    """La operacion pide datos fuera del paciente/episodio autorizado en el contexto."""

    code = "SCOPE_VIOLATION"

    def __init__(self, message: str, *, reason: str = "scope_refused"):
        super().__init__(message)
        self.reason = reason


class PurposeNotAllowed(DomainError):
    """El proposito del contexto no habilita la operacion (p. ej. agregados sin research)."""

    code = "PURPOSE_NOT_ALLOWED"


class ToolValidationError(DomainError):
    """Argumentos o resultado de una tool no cumplen su contrato."""

    code = "TOOL_VALIDATION_ERROR"


class ToolTimeout(DomainError):
    code = "TOOL_TIMEOUT"
    retryable = True


class ProviderUnavailable(DomainError):
    """Un proveedor externo (datos, LLM, conocimiento) no esta disponible."""

    code = "PROVIDER_UNAVAILABLE"
    retryable = True


class AuthenticationFailed(DomainError):
    code = "AUTH_INVALID_TOKEN"


class NotFound(DomainError):
    code = "NOT_FOUND"


class RateLimited(DomainError):
    code = "RATE_LIMITED"

    def __init__(self, message: str, *, retry_after_s: Optional[float] = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s
