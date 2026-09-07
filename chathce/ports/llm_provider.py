"""Port LLMProvider: generacion agnostica del SDK (ADR 0010 §5).

Tipos neutrales de mensaje y eventos. Los schemas concretos del proveedor
(Anthropic) se construyen unicamente en ``chathce.adapters.anthropic``.
"""

from __future__ import annotations

from typing import Annotated, Any, AsyncIterator, Dict, List, Literal, Mapping, Optional, Protocol, Union, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from chathce.domain.clinical import ProviderHealth
from chathce.domain.errors import DomainError


# ---- mensajes -----------------------------------------------------------
class TextPart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text"] = "text"
    text: str


class ToolUsePart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any] = Field(default_factory=dict)


class ToolResultPart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


LLMPart = Annotated[Union[TextPart, ToolUsePart, ToolResultPart], Field(discriminator="type")]


class LLMMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    parts: List[LLMPart]

    @classmethod
    def user_text(cls, text: str) -> "LLMMessage":
        return cls(role="user", parts=[TextPart(text=text)])

    @classmethod
    def assistant_text(cls, text: str) -> "LLMMessage":
        return cls(role="assistant", parts=[TextPart(text=text)])

    def text(self) -> str:
        return "".join(p.text for p in self.parts if isinstance(p, TextPart))


class LLMToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    input_schema: Dict[str, Any]


class LLMUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0


# ---- eventos ------------------------------------------------------------
StopReason = Literal["end_turn", "tool_use", "max_tokens", "refusal", "other"]


class LLMTextDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text_delta"] = "text_delta"
    text: str


class LLMToolUseStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["tool_use_start"] = "tool_use_start"
    id: str
    name: str


class LLMToolUseEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["tool_use_end"] = "tool_use_end"
    id: str
    name: str
    input: Dict[str, Any] = Field(default_factory=dict)


class LLMMessageEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["message_end"] = "message_end"
    stop_reason: StopReason
    usage: LLMUsage = Field(default_factory=LLMUsage)
    model: str
    provider_request_id: Optional[str] = None
    assistant_parts: List[LLMPart] = Field(default_factory=list)


LLMEvent = Annotated[Union[LLMTextDelta, LLMToolUseStart, LLMToolUseEnd, LLMMessageEnd], Field(discriminator="type")]


# ---- errores ------------------------------------------------------------
class LLMProviderError(DomainError):
    code = "LLM_UNAVAILABLE"
    retryable = False


class LLMRateLimited(LLMProviderError):
    code = "LLM_RATE_LIMITED"
    retryable = True

    def __init__(self, message: str, *, retry_after_s: Optional[float] = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class LLMOverloaded(LLMProviderError):
    code = "LLM_OVERLOADED"
    retryable = True


class LLMTimeout(LLMProviderError):
    code = "LLM_TIMEOUT"
    retryable = True


class LLMUnavailable(LLMProviderError):
    code = "LLM_UNAVAILABLE"
    retryable = True


class LLMAuthError(LLMProviderError):
    code = "LLM_AUTH_ERROR"
    retryable = False


class LLMBadRequest(LLMProviderError):
    code = "LLM_BAD_REQUEST"
    retryable = False


# ---- port ---------------------------------------------------------------
@runtime_checkable
class LLMProvider(Protocol):
    provider_name: str

    def generate(
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
    ) -> AsyncIterator[LLMEvent]: ...

    async def health(self, model: str) -> ProviderHealth: ...
