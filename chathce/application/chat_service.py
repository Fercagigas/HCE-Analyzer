"""ChatService: caso de uso de chat unico para FastAPI, Streamlit y Evaluation (ADR 0010 §8).

Flujo: validacion y rate limit -> sesion e historial -> system prompt desde contratos ->
ModelGateway (eventos) -> ChatResponse (facts/inferences/evidence/sources/visualizaciones)
-> persistencia -> auditoria. Nunca cachea respuestas entre usuarios.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Tuple

from chathce.application.audit_events import emit_safely, make_audit_event
from chathce.application.conversation_service import ConversationService, to_llm_history
from chathce.application.prompts.system_prompt import build_system_prompt
from chathce.application.rate_limit import RateLimiter
from chathce.domain.audit import AuditAction
from chathce.domain.chat import (
    ChatEvent,
    ChatMetadata,
    ChatRequest,
    ChatResponse,
    CompleteEvent,
    ErrorEvent,
    ErrorInfo,
    ToolCallSummary,
    Uncertainty,
    VisualizationRef,
)
from chathce.domain.context import RequestContext
from chathce.domain.correlation import bind_context
from chathce.domain.errors import RateLimited
from chathce.domain.evidence import Claim, ClaimType, Evidence
from chathce.domain.knowledge import Source
from chathce.domain.tools import AuditCategory, ToolResult
from chathce.gateway.model_gateway import GatewayDone, ModelGateway
from chathce.gateway.tool_registry import ToolRegistry

VISUALIZATION_TOOL = "create_visualization"

CLAIM_TYPE_BY_CATEGORY = {
    AuditCategory.clinical_data: ClaimType.OBSERVED_FACT,
    AuditCategory.knowledge: ClaimType.GUIDELINE_STATEMENT,
    AuditCategory.dataset_aggregate: ClaimType.CALCULATION,
    AuditCategory.visualization: ClaimType.CALCULATION,
}



@dataclass
class _ToolResultsEvent:
    """Evento interno de stream_chat con los ToolResult completos; lo consume handle_chat_detailed y nunca la API."""
    results: List[ToolResult] = field(default_factory=list)

@dataclass
class ChatServiceConfig:
    rate_limit_enabled: bool = True
    max_message_length: int = 5000


class ChatService:
    def __init__(
        self,
        gateway: ModelGateway,
        registry: ToolRegistry,
        conversations: ConversationService,
        visualizations: Optional[Any] = None,
        *,
        rate_limiter: Optional[RateLimiter] = None,
        audit: Optional[Any] = None,
        config: Optional[ChatServiceConfig] = None,
    ):
        self._gateway = gateway
        self._registry = registry
        self._conversations = conversations
        self._visualizations = visualizations
        self._rate_limiter = rate_limiter or RateLimiter()
        self._audit = audit
        self._config = config or ChatServiceConfig()

    # ------------------------------------------------------------------
    async def handle_chat(self, request: ChatRequest, ctx: RequestContext, *, persist: bool = True) -> ChatResponse:
        response, _ = await self.handle_chat_detailed(request, ctx, persist=persist)
        return response

    async def handle_chat_detailed(self, request: ChatRequest, ctx: RequestContext, *, persist: bool = True
                                   ) -> Tuple[ChatResponse, List[ToolResult]]:
        """Como handle_chat, pero devuelve ademas los ToolResult completos del turno.

        Los usa el runtime legacy (UI y Evaluation) para exponer el texto visible al modelo de cada tool
        como contexto de evaluacion. La API publica solo devuelve ChatResponse.
        """
        response: Optional[ChatResponse] = None
        tool_results: List[ToolResult] = []
        async for event in self._stream_internal(request, ctx, persist=persist):
            if isinstance(event, CompleteEvent):
                response = event.response
            elif isinstance(event, _ToolResultsEvent):
                tool_results = event.results
        assert response is not None
        return response, tool_results

    async def stream_chat(self, request: ChatRequest, ctx: RequestContext, *, persist: bool = True) -> AsyncIterator[ChatEvent]:
        """Eventos publicos del turno (status, tool_call, tool_result_summary, text_delta, error, complete)."""
        async for event in self._stream_internal(request, ctx, persist=persist):
            if not isinstance(event, _ToolResultsEvent):
                yield event

    async def _stream_internal(self, request: ChatRequest, ctx: RequestContext, *, persist: bool = True):
        started = time.perf_counter()
        with bind_context(ctx):
            await emit_safely(self._audit, make_audit_event(ctx, action=AuditAction.chat_started, outcome="success", component="chat_service"))

            # --- validacion y rate limit -------------------------------------
            error = self._validate(request, ctx)
            if error is not None:
                response = self._failure(ctx, request, error, started)
                await self._audit_failed(ctx, error, started)
                yield ErrorEvent(error=error, trace_id=ctx.trace_id, request_id=ctx.request_id)
                yield CompleteEvent(response=response)
                return

            # --- sesion e historial ------------------------------------------
            session_id = ctx.session_id
            if persist and self._conversations.enabled:
                try:
                    session = await self._conversations.ensure_session(ctx, first_message=request.message)
                    if session is not None:
                        session_id = session.session_id
                        ctx = ctx.model_copy(update={"session_id": session_id})
                except Exception:  # noqa: BLE001 - sin persistencia seguimos respondiendo
                    pass
            history_in = request.history
            if history_in is None and session_id and persist:
                history_in = await self._conversations.load_history(ctx, session_id=session_id)
            history = to_llm_history(history_in or [], max_messages=request.options.max_context_messages)

            # --- prompt y herramientas ---------------------------------------
            enabled = self._registry.names()
            if not request.options.enable_visualizations:
                enabled = [n for n in enabled if n != VISUALIZATION_TOOL]
            system, prompt_version = build_system_prompt(self._registry.contracts(enabled=enabled), ctx, request.options)

            # --- gateway ------------------------------------------------------
            done: Optional[GatewayDone] = None
            gateway_error: Optional[ErrorInfo] = None
            async for event in self._gateway.run(ctx, system=system, prompt_version=prompt_version, history=history,
                                                 user_message=request.message, enabled_tools=enabled):
                if isinstance(event, GatewayDone):
                    done = event
                elif isinstance(event, ErrorEvent):
                    gateway_error = event.error
                    yield event
                else:
                    yield event

            if done is None:
                error = gateway_error or ErrorInfo(code="INTERNAL_ERROR", message="El modelo no devolvio respuesta.")
                response = self._failure(ctx, request, error, started, session_id=session_id, prompt_version=prompt_version)
                await self._audit_failed(ctx, error, started)
                yield CompleteEvent(response=response)
                return

            response = await self._build_response(ctx, request, done, started, session_id=session_id, prompt_version=prompt_version)

            yield _ToolResultsEvent(results=list(done.tool_results))
            if persist and session_id:
                await self._conversations.persist_turn(ctx, session_id=session_id, user_message=request.message, response=response)
            await emit_safely(self._audit, make_audit_event(
                ctx, action=AuditAction.chat_completed, outcome="success", component="chat_service",
                model_requested=done.model_requested, model_used=done.model_used, prompt_version=prompt_version,
                tokens_input=done.usage.input_tokens, tokens_output=done.usage.output_tokens,
                latency_ms=response.metadata.latency_ms,
                attributes={"iteration": done.iterations, "stop_reason": done.stop_reason, "count": len(done.tool_results)},
            ))
            yield CompleteEvent(response=response)

    # ------------------------------------------------------------------
    def _validate(self, request: ChatRequest, ctx: RequestContext) -> Optional[ErrorInfo]:
        if len(request.message) > self._config.max_message_length:
            return ErrorInfo(code="VALIDATION_ERROR", message=f"El mensaje supera la longitud máxima de {self._config.max_message_length} caracteres.")
        if self._config.rate_limit_enabled:
            try:
                self._rate_limiter.check(ctx.user_id)
            except RateLimited as exc:
                return ErrorInfo(code="RATE_LIMITED", message=exc.message, retryable=True,
                                 suggestions=[f"Espere {int(exc.retry_after_s or 60)} segundos antes de reintentar."])
        return None

    async def _audit_failed(self, ctx: RequestContext, error: ErrorInfo, started: float) -> None:
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.chat_failed, outcome="failure", component="chat_service",
            error_code=error.code, latency_ms=int((time.perf_counter() - started) * 1000),
        ))

    def _metadata(self, ctx: RequestContext, started: float, *, session_id: Optional[str], prompt_version: str = "",
                  done: Optional[GatewayDone] = None) -> ChatMetadata:
        return ChatMetadata(
            session_id=session_id, trace_id=ctx.trace_id, request_id=ctx.request_id,
            model_requested=done.model_requested if done else "", model_used=done.model_used if done else "",
            fallback_used=done.fallback_used if done else False,
            tokens_input=done.usage.input_tokens if done else 0, tokens_output=done.usage.output_tokens if done else 0,
            iterations=done.iterations if done else 0, latency_ms=int((time.perf_counter() - started) * 1000),
            prompt_version=prompt_version, timestamp=datetime.now(timezone.utc),
        )

    def _failure(self, ctx: RequestContext, request: ChatRequest, error: ErrorInfo, started: float, *,
                 session_id: Optional[str] = None, prompt_version: str = "") -> ChatResponse:
        return ChatResponse(
            success=False, content=f"No se pudo completar la respuesta: {error.message}",
            uncertainty=Uncertainty(level="high", notes=[error.code]),
            metadata=self._metadata(ctx, started, session_id=session_id or ctx.session_id, prompt_version=prompt_version), error=error,
        )

    async def _build_response(self, ctx: RequestContext, request: ChatRequest, done: GatewayDone, started: float, *,
                              session_id: Optional[str], prompt_version: str) -> ChatResponse:
        contracts = {c.name: c for c in self._registry.contracts()}
        facts: List[Claim] = []
        evidence: List[Evidence] = []
        seen_evidence: set = set()
        sources: List[Source] = []
        visualizations: List[VisualizationRef] = []
        tool_calls: List[ToolCallSummary] = []
        unresolved: List[str] = []
        refusals: List[str] = []
        for result in done.tool_results:
            tool_calls.append(_summary(result))
            for ev in result.evidence:
                if ev.evidence_id not in seen_evidence:
                    seen_evidence.add(ev.evidence_id)
                    evidence.append(ev)
            sources.extend(result.artifacts.sources)
            for viz_id in result.artifacts.visualization_ids:
                visualizations.append(await self._viz_ref(ctx, viz_id, result))
            if result.success:
                contract = contracts.get(result.tool_name)
                claim_type = CLAIM_TYPE_BY_CATEGORY.get(contract.audit_category, ClaimType.UNKNOWN) if contract else ClaimType.UNKNOWN
                facts.append(Claim(claim_id=uuid.uuid4().hex, type=claim_type, text=_fact_text(result), evidence_ids=result.evidence_ids))
            elif result.error is not None:
                (refusals if result.error.code in ("scope_refused", "purpose_refused") else unresolved).append(
                    f"{result.tool_name}: {result.error.message}")

        notes: List[str] = []
        if done.stop_reason == "max_tokens":
            notes.append("La respuesta fue truncada por el limite de tokens.")
        if done.stop_reason == "refusal":
            notes.append("El modelo declino responder a la peticion.")
        if done.fallback_used:
            notes.append(f"Se uso el modelo alternativo {done.model_used}.")
        if done.iterations > self._gateway._config.max_iterations:
            notes.append("Se alcanzo el maximo de pasos de herramientas; la respuesta es una sintesis parcial.")
        level = "high" if (unresolved or done.stop_reason in ("max_tokens", "refusal")) else ("medium" if (refusals or not facts) else "low")
        inferences = [Claim(claim_id=uuid.uuid4().hex, type=ClaimType.AI_INFERENCE, text=done.final_text, evidence_ids=[e.evidence_id for e in evidence])] if done.final_text else []

        return ChatResponse(
            success=True, content=done.final_text, facts=facts, inferences=inferences, evidence=evidence,
            uncertainty=Uncertainty(level=level, notes=notes, unresolved_tool_errors=unresolved, scope_refusals=refusals),
            tool_calls=tool_calls, sources=sources if request.options.include_sources else [], visualizations=visualizations,
            metadata=self._metadata(ctx, started, session_id=session_id, prompt_version=prompt_version, done=done),
        )

    async def _viz_ref(self, ctx: RequestContext, viz_id: str, result: ToolResult) -> VisualizationRef:
        title, viz_type = "Visualización", "unknown"
        data = result.data if isinstance(result.data, dict) else {}
        title = str(data.get("title") or title)
        viz_type = str(data.get("viz_type") or viz_type)
        if self._visualizations is not None:
            artifact = await self._visualizations.get(ctx, viz_id)
            if artifact is not None:
                title, viz_type = artifact.title, artifact.viz_type
        return VisualizationRef(viz_id=viz_id, title=title, viz_type=viz_type)


def _summary(result: ToolResult) -> ToolCallSummary:
    return ToolCallSummary(
        tool_name=result.tool_name, tool_use_id=result.tool_use_id, operation=result.operation, success=result.success,
        count=result.count, truncated=result.truncated, elapsed_ms=result.elapsed_ms,
        error_code=result.error.code if result.error else None, evidence_ids=result.evidence_ids,
    )


def _fact_text(result: ToolResult) -> str:
    scope = result.scope
    where = f"del paciente {scope.patient_id}" if scope.patient_id else "del conjunto de datos"
    suffix = " (resultado truncado)" if result.truncated else ""
    return f"{result.tool_name}: {result.count} registro(s) recuperados {where} mediante la operacion {result.operation}{suffix}."
