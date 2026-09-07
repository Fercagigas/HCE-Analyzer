"""ModelGateway: bucle agentico sobre LLMProvider con fallback, reintentos, timeouts y eventos (ADR 0010 §5).

Reglas:
- Nunca ``time.sleep``; reintentos con ``asyncio.sleep`` y jitter.
- Estado de fallback por peticion (no global).
- Emite solo eventos de alto nivel; nunca chain-of-thought.
- Las tools se despachan a traves de ToolRegistry (contratos, politica, auditoria).
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple, Union

from chathce.application.audit_events import emit_safely, make_audit_event
from chathce.domain.audit import AuditAction
from chathce.domain.chat import (
    ErrorEvent,
    ErrorInfo,
    StatusEvent,
    TextDeltaEvent,
    ToolCallEvent,
    ToolCallSummary,
    ToolResultSummaryEvent,
)
from chathce.domain.context import RequestContext
from chathce.domain.tools import ToolResult
from chathce.gateway.tool_registry import ToolRegistry
from chathce.ports.llm_provider import (
    LLMMessage,
    LLMMessageEnd,
    LLMProvider,
    LLMProviderError,
    LLMTextDelta,
    LLMTimeout,
    LLMUnavailable,
    LLMToolUseStart,
    LLMUsage,
    TextPart,
    ToolResultPart,
    ToolUsePart,
)

SYNTHESIS_INSTRUCTION = (
    "Se ha alcanzado el maximo de pasos de herramientas. Responde ahora al usuario con la informacion ya "
    "recuperada e indica explicitamente que queda pendiente o no pudo verificarse."
)


@dataclass
class GatewayConfig:
    model_chain: Sequence[str]
    max_tokens: int = 4096
    temperature: Optional[float] = 0.1
    request_timeout_s: float = 60.0
    total_timeout_s: float = 120.0
    max_retries_per_model: int = 1
    max_iterations: int = 6
    backoff_base_s: float = 1.0
    backoff_max_s: float = 8.0
    provider_name: str = "unknown"
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_s: float = 30.0


@dataclass
class GatewayDone:
    final_text: str
    tool_results: List[ToolResult] = field(default_factory=list)
    usage: LLMUsage = field(default_factory=LLMUsage)
    model_requested: str = ""
    model_used: str = ""
    fallback_used: bool = False
    iterations: int = 0
    stop_reason: str = "end_turn"
    transcript: List[LLMMessage] = field(default_factory=list)
    llm_calls: int = 0


GatewayEvent = Union[StatusEvent, ToolCallEvent, ToolResultSummaryEvent, TextDeltaEvent, ErrorEvent, GatewayDone]


class _Attempt:
    """Resultado de una llamada al proveedor (con o sin streaming)."""

    def __init__(self) -> None:
        self.end: Optional[LLMMessageEnd] = None
        self.text: str = ""


@dataclass
class _CircuitState:
    failures: int = 0
    state: str = "closed"
    opened_at: float = 0.0


class ModelCircuitBreaker:
    """Circuit breaker en memoria, aislado por proveedor y modelo."""

    def __init__(self, *, provider_name: str, failure_threshold: int, recovery_s: float,
                 clock: Callable[[], float] = time.monotonic):
        self._provider_name = provider_name
        self._threshold = failure_threshold
        self._recovery_s = recovery_s
        self._clock = clock
        self._states: Dict[Tuple[str, str], _CircuitState] = {}

    def allow(self, model: str) -> Tuple[bool, Optional[Tuple[str, str]]]:
        state = self._states.setdefault((self._provider_name, model), _CircuitState())
        if state.state != "open":
            return True, None
        if self._clock() - state.opened_at < self._recovery_s:
            return False, None
        state.state = "half_open"
        return True, ("open", "half_open")

    def success(self, model: str) -> Optional[Tuple[str, str]]:
        state = self._states.setdefault((self._provider_name, model), _CircuitState())
        previous = state.state
        state.failures = 0
        state.state = "closed"
        return (previous, "closed") if previous != "closed" else None

    def failure(self, model: str) -> Optional[Tuple[str, str]]:
        state = self._states.setdefault((self._provider_name, model), _CircuitState())
        previous = state.state
        state.failures += 1
        if state.state == "half_open" or state.failures >= self._threshold:
            state.state = "open"
            state.opened_at = self._clock()
        return (previous, state.state) if previous != state.state else None

    def state_for(self, model: str) -> str:
        return self._states.get((self._provider_name, model), _CircuitState()).state


class ModelGateway:
    def __init__(
        self,
        provider: LLMProvider,
        registry: ToolRegistry,
        config: GatewayConfig,
        *,
        audit: Optional[Any] = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        stream: bool = True,
        circuit_breaker: Optional[ModelCircuitBreaker] = None,
    ):
        if not config.model_chain:
            raise ValueError("model_chain no puede estar vacia")
        self._provider = provider
        self._registry = registry
        self._config = config
        self._audit = audit
        self._sleep = sleep
        self._stream = stream
        self._circuit_breaker = circuit_breaker or ModelCircuitBreaker(
            provider_name=config.provider_name or getattr(provider, "provider_name", type(provider).__name__),
            failure_threshold=config.circuit_breaker_failure_threshold,
            recovery_s=config.circuit_breaker_recovery_s,
        )

    # ------------------------------------------------------------------
    async def run(
        self,
        ctx: RequestContext,
        *,
        system: str,
        prompt_version: str,
        history: List[LLMMessage],
        user_message: str,
        enabled_tools: Optional[Sequence[str]] = None,
    ) -> AsyncIterator[GatewayEvent]:
        cfg = self._config
        contracts = self._registry.contracts(enabled=enabled_tools)
        tool_specs = self._registry.specs(contracts)
        messages: List[LLMMessage] = list(history) + [LLMMessage.user_text(user_message)]
        deadline = time.monotonic() + cfg.total_timeout_s
        state = {"model_index": 0, "fallback_used": False, "llm_calls": 0}
        usage_total = LLMUsage()
        tool_results: List[ToolResult] = []
        final_text = ""
        stop_reason = "end_turn"
        iteration = 0

        yield StatusEvent(stage="thinking", message="Analizando la pregunta", model=cfg.model_chain[0], iteration=0)

        while True:
            iteration += 1
            synthesis = iteration > cfg.max_iterations
            specs = [] if synthesis else tool_specs
            if synthesis:
                messages.append(LLMMessage.user_text(SYNTHESIS_INSTRUCTION))
                yield StatusEvent(stage="generating", message="Sintetizando la respuesta", iteration=iteration)

            attempt = _Attempt()
            try:
                async for event in self._call_with_fallback(ctx, messages, specs, system, prompt_version, iteration, deadline, state, attempt, usage_total):
                    yield event
            except LLMProviderError as exc:
                yield ErrorEvent(
                    error=ErrorInfo(code=exc.code, message=exc.message, retryable=exc.retryable,
                                    suggestions=["Intentelo de nuevo en unos instantes."] if exc.retryable else []),
                    trace_id=ctx.trace_id, request_id=ctx.request_id,
                )
                return

            end = attempt.end
            assert end is not None
            assistant_parts = end.assistant_parts or ([TextPart(text=attempt.text)] if attempt.text else [])
            messages.append(LLMMessage(role="assistant", parts=assistant_parts))
            final_text = "".join(p.text for p in assistant_parts if isinstance(p, TextPart)) or attempt.text
            stop_reason = end.stop_reason
            tool_uses = [p for p in assistant_parts if isinstance(p, ToolUsePart)]

            if end.stop_reason == "tool_use" and tool_uses and not synthesis:
                yield StatusEvent(stage="retrieving_evidence", message="Consultando herramientas", model=end.model, iteration=iteration)
                for call in tool_uses:
                    yield ToolCallEvent(tool_use_id=call.id, tool_name=call.name, scope=ctx.scope(),
                                        arguments=dict(call.input), iteration=iteration)
                results = await asyncio.gather(*[self._registry.dispatch(ctx, call) for call in tool_uses])
                result_parts: List[ToolResultPart] = []
                for result in results:
                    tool_results.append(result)
                    result_parts.append(ToolResultPart(tool_use_id=result.tool_use_id, content=result.model_visible_text,
                                                       is_error=not result.success))
                    yield ToolResultSummaryEvent(summary=_summary(result), visualization_ids=list(result.artifacts.visualization_ids),
                                                 iteration=iteration)
                messages.append(LLMMessage(role="user", parts=result_parts))
                if time.monotonic() >= deadline:
                    stop_reason = "other"
                    final_text = final_text or "Se agoto el tiempo disponible antes de completar la respuesta."
                    break
                continue
            break

        yield GatewayDone(
            final_text=final_text, tool_results=tool_results, usage=usage_total,
            model_requested=cfg.model_chain[0], model_used=cfg.model_chain[state["model_index"]],
            fallback_used=state["fallback_used"], iterations=iteration, stop_reason=stop_reason,
            transcript=messages, llm_calls=state["llm_calls"],
        )

    # ------------------------------------------------------------------
    async def _call_with_fallback(self, ctx, messages, specs, system, prompt_version, iteration, deadline, state, attempt, usage_total):
        cfg = self._config
        while True:
            model = cfg.model_chain[state["model_index"]]
            allowed, transition = self._circuit_breaker.allow(model)
            if transition:
                await self._audit_circuit_transition(ctx, model, transition, prompt_version)
            if not allowed:
                error = LLMUnavailable("El circuito del modelo esta abierto temporalmente")
                if state["model_index"] + 1 >= len(cfg.model_chain):
                    raise error
                async for event in self._fallback(ctx, state, iteration, prompt_version, model):
                    yield event
                continue
            retries = 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise LLMTimeout("Se agoto el tiempo total de la peticion")
                timeout = min(cfg.request_timeout_s, remaining)
                started = time.perf_counter()
                attempt.end = None
                attempt.text = ""
                try:
                    async with asyncio.timeout(timeout + 1.0):
                        async for llm_event in self._provider.generate(
                            messages, tools=specs, system=system, model=model, max_tokens=cfg.max_tokens,
                            temperature=cfg.temperature, timeout_s=timeout, stream=self._stream,
                            metadata={"user_id": ctx.user_id},
                        ):
                            if isinstance(llm_event, LLMTextDelta):
                                attempt.text += llm_event.text
                                yield TextDeltaEvent(text=llm_event.text, iteration=iteration)
                            elif isinstance(llm_event, LLMToolUseStart):
                                yield StatusEvent(stage="retrieving_evidence", message=f"Preparando {llm_event.name}",
                                                  model=model, iteration=iteration)
                            elif isinstance(llm_event, LLMMessageEnd):
                                attempt.end = llm_event
                    if attempt.end is None:
                        raise LLMTimeout("El proveedor cerro el stream sin mensaje final")
                except (asyncio.TimeoutError, TimeoutError) as exc:
                    error: LLMProviderError = LLMTimeout("Tiempo de espera agotado esperando al proveedor")
                    error.__cause__ = exc
                except LLMProviderError as exc:
                    error = exc
                else:
                    state["llm_calls"] += 1
                    usage_total.input_tokens += attempt.end.usage.input_tokens
                    usage_total.output_tokens += attempt.end.usage.output_tokens
                    usage_total.cache_read_tokens += attempt.end.usage.cache_read_tokens
                    await emit_safely(self._audit, make_audit_event(
                        ctx, action=AuditAction.llm_call, outcome="success", component="gateway",
                        model_requested=cfg.model_chain[0], model_used=attempt.end.model or model, prompt_version=prompt_version,
                        tokens_input=attempt.end.usage.input_tokens, tokens_output=attempt.end.usage.output_tokens,
                        latency_ms=int((time.perf_counter() - started) * 1000),
                        attributes={"iteration": iteration, "stop_reason": attempt.end.stop_reason},
                    ))
                    transition = self._circuit_breaker.success(model)
                    if transition:
                        await self._audit_circuit_transition(ctx, model, transition, prompt_version)
                    return

                await emit_safely(self._audit, make_audit_event(
                    ctx, action=AuditAction.llm_call, outcome="failure", component="gateway",
                    model_requested=cfg.model_chain[0], model_used=model, prompt_version=prompt_version,
                    latency_ms=int((time.perf_counter() - started) * 1000), error_code=error.code,
                    error_class=error.__class__.__name__, attributes={"iteration": iteration},
                ))
                transition = self._circuit_breaker.failure(model)
                if transition:
                    await self._audit_circuit_transition(ctx, model, transition, prompt_version)
                if not error.retryable:
                    raise error
                if retries < cfg.max_retries_per_model:
                    retries += 1
                    delay = getattr(error, "retry_after_s", None) or min(cfg.backoff_base_s * (2 ** (retries - 1)), cfg.backoff_max_s)
                    await self._sleep(min(delay, cfg.backoff_max_s) + random.uniform(0, 0.25))
                    continue
                break  # agotado este modelo -> fallback

            if state["model_index"] + 1 >= len(cfg.model_chain):
                raise error
            async for event in self._fallback(ctx, state, iteration, prompt_version, model):
                yield event

    async def _fallback(self, ctx, state, iteration, prompt_version, previous):
        cfg = self._config
        state["model_index"] += 1
        state["fallback_used"] = True
        nxt = cfg.model_chain[state["model_index"]]
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.llm_fallback, outcome="success", component="gateway",
            model_requested=cfg.model_chain[0], model_used=nxt, prompt_version=prompt_version,
            attributes={"fallback_from": previous, "fallback_to": nxt, "iteration": iteration},
        ))
        yield StatusEvent(stage="fallback", message=f"Cambiando al modelo alternativo {nxt}", model=nxt, iteration=iteration)

    async def _audit_circuit_transition(self, ctx, model, transition, prompt_version):
        previous, current = transition
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.llm_circuit_breaker, outcome="success", component="gateway",
            model_requested=self._config.model_chain[0], model_used=model, prompt_version=prompt_version,
            attributes={"provider": self._config.provider_name, "reason": f"{previous}_to_{current}"},
        ))


def _summary(result: ToolResult) -> ToolCallSummary:
    return ToolCallSummary(
        tool_name=result.tool_name, tool_use_id=result.tool_use_id, operation=result.operation, success=result.success,
        count=result.count, truncated=result.truncated, elapsed_ms=result.elapsed_ms,
        error_code=result.error.code if result.error else None, evidence_ids=result.evidence_ids,
    )
