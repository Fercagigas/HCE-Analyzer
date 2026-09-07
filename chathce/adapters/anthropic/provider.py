"""AnthropicLLMProvider: implementacion del port sobre ``anthropic.AsyncAnthropic`` (streaming nativo).

- ``max_retries=0`` en el SDK: los reintentos y el fallback los gobierna el ModelGateway.
- Nunca expone bloques de razonamiento; solo texto y tool_use.
- ``health`` usa ``models.retrieve`` (sin generar tokens).
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator, List, Mapping, Optional

from chathce.adapters.anthropic.mapping import (
    from_anthropic_content,
    map_stop_reason,
    to_anthropic_messages,
    to_anthropic_tools,
    translate_exception,
)
from chathce.domain.clinical import ProviderHealth
from chathce.ports.llm_provider import (
    LLMEvent,
    LLMMessage,
    LLMMessageEnd,
    LLMTextDelta,
    LLMToolSpec,
    LLMToolUseEnd,
    LLMToolUseStart,
    LLMUsage,
)


def _usage(message: Any) -> LLMUsage:
    usage = getattr(message, "usage", None)
    return LLMUsage(
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        cache_read_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
    )


class AnthropicLLMProvider:
    provider_name = "anthropic"

    def __init__(self, api_key: str, *, default_timeout_s: float = 60.0, client: Any = None):
        if client is None:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=api_key, max_retries=0, timeout=default_timeout_s)
        self._client = client

    async def generate(
        self,
        messages: List[LLMMessage],
        *,
        tools: List[LLMToolSpec],
        system: str,
        model: str,
        max_tokens: int,
        temperature: Optional[float] = None,
        timeout_s: float = 60.0,
        stream: bool = True,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> AsyncIterator[LLMEvent]:
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": to_anthropic_messages(messages),
            "timeout": timeout_s,
        }
        if tools:
            kwargs["tools"] = to_anthropic_tools(tools)
        if temperature is not None:
            kwargs["temperature"] = temperature
        if metadata:
            kwargs["metadata"] = {"user_id": str(metadata.get("user_id", ""))[:256]} if metadata.get("user_id") else dict(metadata)

        try:
            if not stream:
                message = await self._client.messages.create(**kwargs)
                parts = from_anthropic_content(message.content)
                for part in parts:
                    if part.type == "text" and part.text:
                        yield LLMTextDelta(text=part.text)
                    elif part.type == "tool_use":
                        yield LLMToolUseStart(id=part.id, name=part.name)
                        yield LLMToolUseEnd(id=part.id, name=part.name, input=part.input)
                yield LLMMessageEnd(
                    stop_reason=map_stop_reason(getattr(message, "stop_reason", None)), usage=_usage(message),
                    model=getattr(message, "model", model), provider_request_id=getattr(message, "_request_id", None),
                    assistant_parts=parts,
                )
                return

            async with self._client.messages.stream(**kwargs) as stream_ctx:
                async for event in stream_ctx:
                    kind = getattr(event, "type", None)
                    if kind == "text":
                        if event.text:
                            yield LLMTextDelta(text=event.text)
                    elif kind == "content_block_start":
                        block = getattr(event, "content_block", None)
                        if getattr(block, "type", None) == "tool_use":
                            yield LLMToolUseStart(id=block.id, name=block.name)
                    elif kind == "content_block_stop":
                        block = getattr(event, "content_block", None)
                        if getattr(block, "type", None) == "tool_use":
                            yield LLMToolUseEnd(id=block.id, name=block.name, input=dict(block.input or {}))
                final = await stream_ctx.get_final_message()
            yield LLMMessageEnd(
                stop_reason=map_stop_reason(getattr(final, "stop_reason", None)),
                usage=_usage(final),
                model=getattr(final, "model", model),
                provider_request_id=getattr(stream_ctx, "request_id", None),
                assistant_parts=from_anthropic_content(final.content),
            )
        except Exception as exc:  # noqa: BLE001 - se traduce al dominio
            translated = translate_exception(exc)
            if translated is exc:  # pragma: no cover
                raise
            raise translated from exc

    async def health(self, model: str) -> ProviderHealth:
        started = time.perf_counter()
        try:
            await self._client.models.retrieve(model)
        except Exception as exc:  # noqa: BLE001
            translated = translate_exception(exc)
            return ProviderHealth(ok=False, latency_ms=int((time.perf_counter() - started) * 1000), detail=translated.message[:200])
        return ProviderHealth(ok=True, latency_ms=int((time.perf_counter() - started) * 1000), detail=f"modelo {model} disponible")
