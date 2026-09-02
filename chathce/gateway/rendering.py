"""Render de resultados de tools para el modelo con delimitacion de datos no confiables (roadmap 07 P0.5).

Todo lo que una tool devuelve viaja al modelo dentro de ``<tool_data ... trust="untrusted_data">``.
El system prompt instruye que ese contenido son datos, nunca instrucciones.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

from chathce.domain.tools import ToolResult

TRUNCATION_MARKER = "\n[...truncado por limite de tamano...]"
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_CLOSE_TAG = re.compile(r"</\s*(tool_data|document)", re.IGNORECASE)


def _to_jsonable(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_to_jsonable(d) for d in data]
    if isinstance(data, dict):
        return {str(k): _to_jsonable(v) for k, v in data.items()}
    return data


def sanitize_untrusted_text(text: str) -> str:
    """Elimina caracteres de control y neutraliza cierres de nuestros delimitadores."""
    cleaned = _CONTROL_CHARS.sub("", text or "")
    return _CLOSE_TAG.sub(lambda m: "<\\/" + m.group(1), cleaned)


def cap_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - len(TRUNCATION_MARKER))] + TRUNCATION_MARKER


def render_for_model(result: ToolResult, *, max_chars: int = 12000) -> str:
    """Texto que recibe el modelo como tool_result."""
    if not result.success and result.error is not None:
        body = json.dumps(
            {"error": result.error.code, "message": result.error.message, "retryable": result.error.retryable},
            ensure_ascii=False,
        )
        return (
            f'<tool_data tool="{result.tool_name}" operation="{result.operation}" status="error" '
            f'trust="untrusted_data">\n{sanitize_untrusted_text(body)}\n</tool_data>'
        )
    payload = json.dumps(_to_jsonable(result.data), ensure_ascii=False, sort_keys=True, default=str)
    payload = cap_text(sanitize_untrusted_text(payload), max_chars)
    return (
        f'<tool_data tool="{result.tool_name}" operation="{result.operation}" status="ok" '
        f'count="{result.count}" truncated="{str(result.truncated).lower()}" trust="untrusted_data">\n'
        f"{payload}\n</tool_data>"
    )


def render_document(filename: str, page: Any, content: str, *, max_chars: int = 3000) -> str:
    """Fragmento documental (RAG) delimitado como no confiable."""
    body = cap_text(sanitize_untrusted_text(content), max_chars)
    page_attr = f' page="{page}"' if page not in (None, "") else ""
    return f'<document filename="{sanitize_untrusted_text(str(filename))}"{page_attr} trust="untrusted_data">\n{body}\n</document>'
