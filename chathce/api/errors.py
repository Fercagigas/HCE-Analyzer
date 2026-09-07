"""Modelo de error de la API y traduccion de excepciones del dominio a HTTP."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from chathce.domain.errors import (
    AuthenticationFailed,
    ConfigurationError,
    DomainError,
    NotFound,
    ProviderUnavailable,
    PurposeNotAllowed,
    RateLimited,
    ScopeViolation,
    ToolTimeout,
)

logger = logging.getLogger(__name__)

STATUS_BY_CODE: Dict[str, int] = {
    "AUTH_REQUIRED": 401,
    "AUTH_INVALID_TOKEN": 401,
    "PURPOSE_NOT_ALLOWED": 403,
    "SCOPE_VIOLATION": 403,
    "NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "RATE_LIMITED": 429,
    "PROVIDER_UNAVAILABLE": 503,
    "LLM_UNAVAILABLE": 503,
    "CLINICAL_DATA_UNAVAILABLE": 503,
    "TOOL_TIMEOUT": 504,
    "CONFIGURATION_ERROR": 503,
    "INTERNAL_ERROR": 500,
}


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    trace_id: str
    request_id: str
    details: Optional[List[Dict[str, Any]]] = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorBody


def _ids(request: Request) -> tuple[str, str]:
    return getattr(request.state, "trace_id", "-"), getattr(request.state, "request_id", "-")


def error_response(request: Request, *, code: str, message: str, status: Optional[int] = None,
                   details: Optional[List[Dict[str, Any]]] = None, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    trace_id, request_id = _ids(request)
    body = ErrorResponse(error=ErrorBody(code=code, message=message, trace_id=trace_id, request_id=request_id, details=details))
    return JSONResponse(status_code=status or STATUS_BY_CODE.get(code, 500), content=body.model_dump(mode="json"), headers=headers)


def install_exception_handlers(app: FastAPI, *, production: bool = False) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        headers = None
        if isinstance(exc, RateLimited) and exc.retry_after_s:
            headers = {"Retry-After": str(int(exc.retry_after_s) + 1)}
        code = exc.code
        if isinstance(exc, ProviderUnavailable) and code == "PROVIDER_UNAVAILABLE":
            code = "PROVIDER_UNAVAILABLE"
        message = exc.message
        if production and code in ("INTERNAL_ERROR", "CONFIGURATION_ERROR"):
            message = "Error interno"
        return error_response(request, code=code, message=message, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": [str(p) for p in e.get("loc", [])], "msg": e.get("msg", "")} for e in exc.errors()[:10]]
        return error_response(request, code="VALIDATION_ERROR", message="Peticion invalida", details=None if production else details)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        trace_id, _ = _ids(request)
        logger.exception("Error no controlado (trace_id=%s)", trace_id)
        message = "Error interno" if production else f"Error interno: {exc.__class__.__name__}"
        return error_response(request, code="INTERNAL_ERROR", message=message)


__all__ = ["ErrorBody", "ErrorResponse", "error_response", "install_exception_handlers", "STATUS_BY_CODE",
           "AuthenticationFailed", "ConfigurationError", "NotFound", "PurposeNotAllowed", "ScopeViolation", "ToolTimeout"]
