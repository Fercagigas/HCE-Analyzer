"""LLMProvider guionizable para tests del gateway y de la aplicacion."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Mapping, Optional, Sequence, Tuple, Union

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
    StopReason,
    TextPart,
    ToolUsePart,
)


@dataclass
class ScriptedTurn:
    """Una respuesta del modelo: texto y/o llamadas a tools, o un error."""

    text: str = ""
    tool_calls: Sequence[Tuple[str, Dict[str, Any]]] = ()
    stop_reason: Optional[StopReason] = None
    error: Optional[BaseException] = None
    model: Optional[str] = None
    input_tokens: int = 10
    output_tokens: int = 5


@dataclass
class RecordedGeneration:
    messages: List[LLMMessage]
    tools: List[LLMToolSpec]
    system: str
    model: str
    max_tokens: int
    metadata: Dict[str, str] = field(default_factory=dict)


class FakeLLMProvider:
    provider_name = "fake"

    def __init__(self, turns: Optional[Sequence[Union[ScriptedTurn, BaseException]]] = None, *, healthy: bool = True):
        self._turns: List[Union[ScriptedTurn, BaseException]] = list(turns or [])
        self.calls: List[RecordedGeneration] = []
        self.healthy = healthy

    def queue(self, *turns: Union[ScriptedTurn, BaseException]) -> "FakeLLMProvider":
        self._turns.extend(turns)
        return self

    @property
    def remaining(self) -> int:
        return len(self._turns)

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
        self.calls.append(RecordedGeneration(
            messages=list(messages), tools=list(tools), system=system, model=model,
            max_tokens=max_tokens, metadata=dict(metadata or {}),
        ))
        if not self._turns:
            turn: Union[ScriptedTurn, BaseException] = ScriptedTurn(text="(sin guion)")
        else:
            turn = self._turns.pop(0)
        if isinstance(turn, BaseException):
            raise turn
        if turn.error is not None:
            raise turn.error

        parts: List[Any] = []
        if turn.text:
            for i, word in enumerate(turn.text.split(" ")):
                delta = word if i == 0 else " " + word
                yield LLMTextDelta(text=delta)
            parts.append(TextPart(text=turn.text))
        for name, args in turn.tool_calls:
            tool_use_id = f"toolu_{uuid.uuid4().hex[:12]}"
            yield LLMToolUseStart(id=tool_use_id, name=name)
            yield LLMToolUseEnd(id=tool_use_id, name=name, input=dict(args))
            parts.append(ToolUsePart(id=tool_use_id, name=name, input=dict(args)))
        stop: StopReason = turn.stop_reason or ("tool_use" if turn.tool_calls else "end_turn")
        yield LLMMessageEnd(
            stop_reason=stop,
            usage=LLMUsage(input_tokens=turn.input_tokens, output_tokens=turn.output_tokens),
            model=turn.model or model,
            provider_request_id=f"req_{uuid.uuid4().hex[:8]}",
            assistant_parts=parts,
        )

    async def health(self, model: str) -> ProviderHealth:
        return ProviderHealth(ok=self.healthy, latency_ms=0, detail="fake provider")
