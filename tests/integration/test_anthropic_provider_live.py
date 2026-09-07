"""Integracion minima con Anthropic (una generacion corta). Requiere HCE_RUN_INTEGRATION=1 y ANTHROPIC_API_KEY."""

import pytest

from chathce.adapters.anthropic.provider import AnthropicLLMProvider
from chathce.ports.llm_provider import LLMMessage, LLMMessageEnd, LLMTextDelta


@pytest.fixture(scope="module")
def provider(integration_settings):
    try:
        key = integration_settings.require_anthropic()
    except Exception as exc:  # pragma: no cover
        pytest.skip(str(exc))
    return AnthropicLLMProvider(key)


async def test_health_and_short_generation(provider, integration_settings):
    model = integration_settings.llm.model_chain[0]
    health = await provider.health(model)
    assert health.ok, health.detail

    events = [e async for e in provider.generate(
        [LLMMessage.user_text("Responde exactamente: OK")], tools=[], system="Responde en una palabra.",
        model=model, max_tokens=16, temperature=0.0, timeout_s=30.0, stream=True,
    )]
    assert any(isinstance(e, LLMTextDelta) for e in events)
    end = events[-1]
    assert isinstance(end, LLMMessageEnd) and end.stop_reason in ("end_turn", "max_tokens")
    assert end.usage.output_tokens > 0
