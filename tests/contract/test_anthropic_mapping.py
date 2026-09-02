"""Contrato del adapter Anthropic: schemas y mapeo de excepciones, sin red."""

from types import SimpleNamespace

import httpx
import pytest

from chathce.adapters.anthropic.mapping import (
    from_anthropic_content,
    map_stop_reason,
    to_anthropic_messages,
    to_anthropic_tools,
    translate_exception,
)
from chathce.ports.llm_provider import (
    LLMAuthError,
    LLMBadRequest,
    LLMMessage,
    LLMOverloaded,
    LLMRateLimited,
    LLMTimeout,
    LLMToolSpec,
    LLMUnavailable,
    TextPart,
    ToolResultPart,
    ToolUsePart,
)

pytestmark = pytest.mark.contract


def test_messages_map_to_anthropic_blocks():
    messages = [
        LLMMessage.user_text("hola"),
        LLMMessage(role="assistant", parts=[TextPart(text="consulto"), ToolUsePart(id="t1", name="get_labs", input={"subject_id": 1})]),
        LLMMessage(role="user", parts=[ToolResultPart(tool_use_id="t1", content="<tool_data/>", is_error=False)]),
    ]
    wire = to_anthropic_messages(messages)
    assert wire[0] == {"role": "user", "content": [{"type": "text", "text": "hola"}]}
    assert wire[1]["content"][1] == {"type": "tool_use", "id": "t1", "name": "get_labs", "input": {"subject_id": 1}}
    assert wire[2]["content"][0] == {"type": "tool_result", "tool_use_id": "t1", "content": "<tool_data/>", "is_error": False}


def test_tools_map_to_input_schema():
    spec = LLMToolSpec(name="get_labs", description="d", input_schema={"type": "object", "properties": {}, "additionalProperties": False})
    assert to_anthropic_tools([spec]) == [{"name": "get_labs", "description": "d", "input_schema": spec.input_schema}]


def test_content_blocks_drop_thinking_and_keep_text_and_tool_use():
    blocks = [
        SimpleNamespace(type="thinking", thinking="secreto"),
        SimpleNamespace(type="text", text="hola"),
        SimpleNamespace(type="tool_use", id="t", name="get_labs", input={"subject_id": 1}),
    ]
    parts = from_anthropic_content(blocks)
    assert [p.type for p in parts] == ["text", "tool_use"]
    assert map_stop_reason("pause_turn") == "other" and map_stop_reason("tool_use") == "tool_use"


def _response(status: int, headers=None) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"), headers=headers or {})


def test_exceptions_are_translated_without_leaking_urls():
    import anthropic

    rate = translate_exception(anthropic.RateLimitError("too many http://leak", response=_response(429, {"retry-after": "3"}), body=None))
    assert isinstance(rate, LLMRateLimited) and rate.retry_after_s == 3.0 and "http" not in rate.message
    assert isinstance(translate_exception(anthropic.AuthenticationError("bad key", response=_response(401), body=None)), LLMAuthError)
    assert isinstance(translate_exception(anthropic.BadRequestError("bad", response=_response(400), body=None)), LLMBadRequest)
    assert isinstance(translate_exception(anthropic.InternalServerError("boom", response=_response(529), body=None)), LLMOverloaded)
    assert isinstance(translate_exception(anthropic.APITimeoutError(request=httpx.Request("POST", "https://x"))), LLMTimeout)
    assert isinstance(translate_exception(anthropic.APIConnectionError(request=httpx.Request("POST", "https://x"))), LLMUnavailable)
    assert isinstance(translate_exception(RuntimeError("otro")), LLMUnavailable)


async def test_provider_non_streaming_path_with_stubbed_client():
    from chathce.adapters.anthropic.provider import AnthropicLLMProvider

    class Messages:
        async def create(self, **kwargs):
            assert kwargs["tools"][0]["name"] == "get_labs" and kwargs["system"] == "S"
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="ok"), SimpleNamespace(type="tool_use", id="t1", name="get_labs", input={"subject_id": 1})],
                stop_reason="tool_use", model="claude-test", usage=SimpleNamespace(input_tokens=5, output_tokens=2, cache_read_input_tokens=0),
            )

    provider = AnthropicLLMProvider("key", client=SimpleNamespace(messages=Messages()))
    spec = LLMToolSpec(name="get_labs", description="d", input_schema={"type": "object"})
    events = [e async for e in provider.generate([LLMMessage.user_text("hola")], tools=[spec], system="S", model="m", max_tokens=10, stream=False)]
    assert [e.type for e in events] == ["text_delta", "tool_use_start", "tool_use_end", "message_end"]
    assert events[-1].stop_reason == "tool_use" and events[-1].usage.input_tokens == 5 and events[-1].model == "claude-test"
