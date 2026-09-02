import pytest

from chathce.adapters.memory import FakeLLMProvider, ScriptedTurn
from chathce.domain.chat import ErrorEvent, StatusEvent, TextDeltaEvent, ToolCallEvent, ToolResultSummaryEvent
from chathce.gateway.model_gateway import SYNTHESIS_INSTRUCTION, GatewayConfig, GatewayDone, ModelGateway
from chathce.ports.llm_provider import LLMAuthError, LLMMessage, LLMRateLimited, LLMUnavailable, ToolResultPart

pytestmark = pytest.mark.unit


async def _no_sleep(_: float) -> None:
    return None


def _gateway(provider, registry, audit, **cfg) -> ModelGateway:
    config = GatewayConfig(model_chain=["fake-primary", "fake-secondary"], max_iterations=cfg.pop("max_iterations", 3), **cfg)
    return ModelGateway(provider, registry, config, audit=audit, sleep=_no_sleep)


async def _run(gateway, ctx, message="hola", history=None):
    events = []
    async for event in gateway.run(ctx, system="SYSTEM", prompt_version="v", history=history or [], user_message=message):
        events.append(event)
    return events


def _done(events) -> GatewayDone:
    assert isinstance(events[-1], GatewayDone)
    return events[-1]


async def test_plain_answer_streams_text_and_completes(registry, ctx, audit):
    provider = FakeLLMProvider([ScriptedTurn(text="Hola, soy ChatHCE")])
    events = await _run(_gateway(provider, registry, audit), ctx)

    deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
    assert "".join(d.text for d in deltas) == "Hola, soy ChatHCE"
    done = _done(events)
    assert done.final_text == "Hola, soy ChatHCE" and done.iterations == 1 and done.stop_reason == "end_turn"
    assert done.model_used == "fake-primary" and done.fallback_used is False
    assert done.usage.input_tokens == 10 and done.llm_calls == 1
    assert provider.calls[0].system == "SYSTEM" and [t.name for t in provider.calls[0].tools] == registry.names()
    assert audit.actions() == ["llm_call"]


async def test_tool_use_round_trip_replays_real_blocks(registry, ctx, audit):
    provider = FakeLLMProvider([
        ScriptedTurn(text="Consulto los laboratorios", tool_calls=[("get_labs", {"subject_id": 10001217, "limit": 3})]),
        ScriptedTurn(text="Aquí tienes 3 resultados."),
    ])
    events = await _run(_gateway(provider, registry, audit), ctx)

    calls = [e for e in events if isinstance(e, ToolCallEvent)]
    summaries = [e for e in events if isinstance(e, ToolResultSummaryEvent)]
    assert len(calls) == 1 and calls[0].tool_name == "get_labs" and calls[0].scope.patient_id == "10001217"
    assert summaries[0].summary.success is True and summaries[0].summary.count == 3
    done = _done(events)
    assert done.final_text == "Aquí tienes 3 resultados." and done.iterations == 2
    assert len(done.tool_results) == 1
    # segunda llamada al modelo: assistant real con tool_use + user con tool_result delimitado
    second = provider.calls[1].messages
    assert second[-2].role == "assistant" and any(p.type == "tool_use" for p in second[-2].parts)
    assert second[-1].role == "user" and isinstance(second[-1].parts[0], ToolResultPart)
    assert 'trust="untrusted_data"' in second[-1].parts[0].content
    assert [e.value for e in (a.action for a in audit.events)] == ["llm_call", "tool_call", "llm_call"]


async def test_scope_refusal_is_fed_back_as_error_result(registry, ctx):
    provider = FakeLLMProvider([
        ScriptedTurn(tool_calls=[("get_labs", {"subject_id": 99999999})]),
        ScriptedTurn(text="No puedo consultar otro paciente."),
    ])
    events = await _run(_gateway(provider, registry, None), ctx)
    summary = next(e for e in events if isinstance(e, ToolResultSummaryEvent)).summary
    assert summary.success is False and summary.error_code == "scope_refused"
    assert provider.calls[1].messages[-1].parts[0].is_error is True
    assert _done(events).final_text == "No puedo consultar otro paciente."


async def test_fallback_to_next_model_after_retryable_errors(registry, ctx, audit):
    provider = FakeLLMProvider([LLMUnavailable("caido"), LLMUnavailable("caido"), ScriptedTurn(text="ok desde secundario")])
    events = await _run(_gateway(provider, registry, audit, max_retries_per_model=1), ctx)

    fallback = [e for e in events if isinstance(e, StatusEvent) and e.stage == "fallback"]
    assert len(fallback) == 1 and fallback[0].model == "fake-secondary"
    done = _done(events)
    assert done.model_used == "fake-secondary" and done.fallback_used is True and done.model_requested == "fake-primary"
    assert [c.model for c in provider.calls] == ["fake-primary", "fake-primary", "fake-secondary"]
    assert "llm_fallback" in audit.actions()


async def test_rate_limit_retries_same_model_then_succeeds(registry, ctx):
    provider = FakeLLMProvider([LLMRateLimited("429", retry_after_s=0.01), ScriptedTurn(text="ok")])
    events = await _run(_gateway(provider, registry, None), ctx)
    assert _done(events).model_used == "fake-primary"
    assert [c.model for c in provider.calls] == ["fake-primary", "fake-primary"]


async def test_non_retryable_error_emits_error_event_and_stops(registry, ctx):
    provider = FakeLLMProvider([LLMAuthError("clave invalida")])
    events = await _run(_gateway(provider, registry, None), ctx)
    assert isinstance(events[-1], ErrorEvent) and events[-1].error.code == "LLM_AUTH_ERROR"
    assert not any(isinstance(e, GatewayDone) for e in events)


async def test_exhausting_all_models_emits_error(registry, ctx):
    provider = FakeLLMProvider([LLMUnavailable("x")] * 4)
    events = await _run(_gateway(provider, registry, None, max_retries_per_model=1), ctx)
    assert isinstance(events[-1], ErrorEvent) and events[-1].error.retryable is True


async def test_max_iterations_triggers_final_synthesis_without_tools(registry, ctx):
    turns = [ScriptedTurn(tool_calls=[("get_labs", {"subject_id": 10001217, "limit": 1})]) for _ in range(3)]
    turns.append(ScriptedTurn(text="Resumen final con lo recuperado."))
    provider = FakeLLMProvider(turns)
    events = await _run(_gateway(provider, registry, None, max_iterations=3), ctx)

    done = _done(events)
    assert done.final_text == "Resumen final con lo recuperado." and done.iterations == 4
    last_call = provider.calls[-1]
    assert last_call.tools == []
    assert any(SYNTHESIS_INSTRUCTION in p.text for m in last_call.messages for p in m.parts if p.type == "text")


async def test_refusal_and_max_tokens_stop_reasons_are_reported(registry, ctx):
    events = await _run(_gateway(FakeLLMProvider([ScriptedTurn(text="No puedo.", stop_reason="refusal")]), registry, None), ctx)
    assert _done(events).stop_reason == "refusal"
    events = await _run(_gateway(FakeLLMProvider([ScriptedTurn(text="texto cortado", stop_reason="max_tokens")]), registry, None), ctx)
    assert _done(events).stop_reason == "max_tokens"


async def test_history_is_replayed_before_user_message(registry, ctx):
    provider = FakeLLMProvider([ScriptedTurn(text="ok")])
    history = [LLMMessage.user_text("antes"), LLMMessage.assistant_text("respuesta previa")]
    await _run(_gateway(provider, registry, None), ctx, message="ahora", history=history)
    sent = provider.calls[0].messages
    assert [m.role for m in sent] == ["user", "assistant", "user"] and sent[-1].text() == "ahora"


async def test_events_never_contain_reasoning_fields(registry, ctx):
    provider = FakeLLMProvider([ScriptedTurn(text="ok", tool_calls=[("get_labs", {"subject_id": 10001217})]), ScriptedTurn(text="fin")])
    events = await _run(_gateway(provider, registry, None), ctx)
    for event in events:
        if isinstance(event, GatewayDone):
            continue
        dumped = event.model_dump()
        assert "thinking" not in dumped and "reasoning" not in dumped
