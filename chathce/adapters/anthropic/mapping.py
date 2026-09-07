"""Mapeo entre los tipos neutrales del port LLMProvider y el wire format de Anthropic.

Aqui (y solo aqui) se construyen los schemas de tools y bloques de mensaje del SDK.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from chathce.ports.llm_provider import (
    LLMAuthError,
    LLMBadRequest,
    LLMMessage,
    LLMOverloaded,
    LLMPart,
    LLMProviderError,
    LLMRateLimited,
    LLMTimeout,
    LLMToolSpec,
    LLMUnavailable,
    StopReason,
    TextPart,
    ToolResultPart,
    ToolUsePart,
)


def to_anthropic_messages(messages: Iterable[LLMMessage]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for message in messages:
        blocks: List[Dict[str, Any]] = []
        for part in message.parts:
            if isinstance(part, TextPart):
                if part.text:
                    blocks.append({"type": "text", "text": part.text})
            elif isinstance(part, ToolUsePart):
                blocks.append({"type": "tool_use", "id": part.id, "name": part.name, "input": part.input})
            elif isinstance(part, ToolResultPart):
                blocks.append({
                    "type": "tool_result",
                    "tool_use_id": part.tool_use_id,
                    "content": part.content,
                    "is_error": part.is_error,
                })
        if not blocks:
            blocks.append({"type": "text", "text": "(sin contenido)"})
        out.append({"role": message.role, "content": blocks})
    return out


def to_anthropic_tools(specs: Iterable[LLMToolSpec]) -> List[Dict[str, Any]]:
    return [{"name": s.name, "description": s.description, "input_schema": s.input_schema} for s in specs]


def from_anthropic_content(blocks: Iterable[Any]) -> List[LLMPart]:
    parts: List[LLMPart] = []
    for block in blocks:
        kind = getattr(block, "type", None)
        if kind == "text":
            parts.append(TextPart(text=getattr(block, "text", "") or ""))
        elif kind == "tool_use":
            parts.append(ToolUsePart(id=block.id, name=block.name, input=dict(block.input or {})))
        # thinking/redacted_thinking/otros: nunca se exponen fuera del adapter
    return parts


def map_stop_reason(value: Optional[str]) -> StopReason:
    if value in ("end_turn", "tool_use", "max_tokens", "refusal"):
        return value  # type: ignore[return-value]
    return "other"


def _retry_after(exc: Any) -> Optional[float]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    raw = headers.get("retry-after")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def translate_exception(exc: BaseException) -> LLMProviderError:
    """Excepcion del SDK -> jerarquia del dominio. Nunca filtra claves ni URLs completas."""
    import anthropic

    message = str(exc).split("http", 1)[0].strip()[:300] or exc.__class__.__name__
    if isinstance(exc, anthropic.RateLimitError):
        return LLMRateLimited(f"Limite de peticiones del proveedor: {message}", retry_after_s=_retry_after(exc))
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return LLMAuthError(f"Credenciales del proveedor rechazadas: {message}")
    if isinstance(exc, (anthropic.BadRequestError, anthropic.NotFoundError, anthropic.UnprocessableEntityError)):
        return LLMBadRequest(f"Peticion rechazada por el proveedor: {message}")
    if isinstance(exc, anthropic.APITimeoutError):
        return LLMTimeout(f"Tiempo de espera agotado con el proveedor: {message}")
    if isinstance(exc, anthropic.APIStatusError):
        status = getattr(exc, "status_code", 0) or 0
        if status == 529 or status >= 500:
            return LLMOverloaded(f"Proveedor sobrecargado o en error ({status}): {message}")
        return LLMBadRequest(f"Error del proveedor ({status}): {message}")
    if isinstance(exc, anthropic.APIConnectionError):
        return LLMUnavailable(f"No se pudo conectar con el proveedor: {message}")
    if isinstance(exc, TimeoutError):
        return LLMTimeout("Tiempo de espera agotado con el proveedor")
    return LLMUnavailable(f"Error inesperado del proveedor: {message}")
