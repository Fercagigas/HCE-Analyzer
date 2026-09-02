"""ToolRegistry: registro de tools con contrato y despacho validado (nunca lanza)."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from pydantic import BaseModel, ValidationError

from chathce.application.audit_events import emit_safely, make_audit_event
from chathce.domain.audit import AuditAction
from chathce.domain.context import RequestContext
from chathce.domain.errors import DomainError, NotFound, ProviderUnavailable, PurposeNotAllowed, ScopeViolation, ToolTimeout
from chathce.domain.tools import ToolContract, ToolResult
from chathce.gateway.policy import ToolPolicy
from chathce.gateway.rendering import render_for_model
from chathce.ports.llm_provider import LLMToolSpec, ToolUsePart

ToolHandler = Callable[[RequestContext, BaseModel], Awaitable[ToolResult]]


@dataclass(frozen=True)
class Tool:
    contract: ToolContract
    handler: ToolHandler


def _error_code_for(exc: DomainError) -> str:
    if isinstance(exc, ScopeViolation):
        return "scope_refused"
    if isinstance(exc, PurposeNotAllowed):
        return "purpose_refused"
    if isinstance(exc, ToolTimeout):
        return "timeout"
    if isinstance(exc, ProviderUnavailable):
        return "provider_unavailable"
    if isinstance(exc, NotFound):
        return "not_found"
    return "internal"


class ToolRegistry:
    def __init__(self, *, policy: Optional[ToolPolicy] = None, audit: Optional[Any] = None, max_visible_chars: int = 12000):
        self._tools: Dict[str, Tool] = {}
        self._policy = policy or ToolPolicy()
        self._audit = audit
        self._max_visible_chars = max_visible_chars

    # ------------------------------------------------------------------
    def register(self, tool: Tool) -> None:
        if tool.contract.name in self._tools:
            raise ValueError(f"Tool duplicada: {tool.contract.name}")
        self._tools[tool.contract.name] = tool

    def names(self) -> List[str]:
        return list(self._tools)

    def contracts(self, *, enabled: Optional[Iterable[str]] = None) -> List[ToolContract]:
        allowed = set(enabled) if enabled is not None else None
        return [t.contract for name, t in self._tools.items() if allowed is None or name in allowed]

    def specs(self, contracts: Iterable[ToolContract]) -> List[LLMToolSpec]:
        return [LLMToolSpec(name=c.name, description=c.description, input_schema=c.input_schema()) for c in contracts]

    # ------------------------------------------------------------------
    async def dispatch(self, ctx: RequestContext, call: ToolUsePart) -> ToolResult:
        started = time.perf_counter()
        tool = self._tools.get(call.name)
        scope = ctx.scope()
        if tool is None:
            result = ToolResult.failure(tool_name=call.name, tool_use_id=call.id, scope=scope, code="unknown_tool",
                                        message=f"La herramienta '{call.name}' no existe.")
            return await self._finish(ctx, None, result, started)

        contract = tool.contract
        try:
            args = contract.input_model.model_validate(call.input)
        except ValidationError as exc:
            detail = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:5])
            result = ToolResult.failure(tool_name=call.name, tool_use_id=call.id, scope=scope, code="invalid_input",
                                        message=f"Argumentos invalidos: {detail}", contract_version=contract.version,
                                        timeout_s=contract.timeout_s)
            return await self._finish(ctx, contract, result, started)

        refusal = self._policy.check(ctx, contract, args)
        if refusal is not None:
            result = ToolResult.failure(tool_name=call.name, tool_use_id=call.id, scope=scope, code=refusal.code,
                                        message=refusal.message, contract_version=contract.version,
                                        timeout_s=contract.timeout_s)
            return await self._finish(ctx, contract, result, started, refused=True)

        try:
            result = await asyncio.wait_for(tool.handler(ctx, args), timeout=contract.timeout_s)
        except asyncio.TimeoutError:
            result = ToolResult.failure(tool_name=call.name, tool_use_id=call.id, scope=scope, code="timeout",
                                        message=f"La herramienta supero el tiempo maximo ({contract.timeout_s:.0f}s).",
                                        retryable=True, contract_version=contract.version, timeout_s=contract.timeout_s)
            return await self._finish(ctx, contract, result, started)
        except DomainError as exc:
            code = _error_code_for(exc)
            result = ToolResult.failure(tool_name=call.name, tool_use_id=call.id, scope=scope, code=code,  # type: ignore[arg-type]
                                        message=exc.message, retryable=exc.retryable, contract_version=contract.version,
                                        timeout_s=contract.timeout_s)
            return await self._finish(ctx, contract, result, started, refused=code in ("scope_refused", "purpose_refused"))
        except Exception as exc:  # noqa: BLE001 - la tool nunca debe tumbar el bucle
            result = ToolResult.failure(tool_name=call.name, tool_use_id=call.id, scope=scope, code="internal",
                                        message=f"Error interno en la herramienta: {exc.__class__.__name__}",
                                        contract_version=contract.version, timeout_s=contract.timeout_s)
            return await self._finish(ctx, contract, result, started)

        result = result.model_copy(update={"tool_name": call.name, "tool_use_id": call.id, "scope": scope,
                                           "contract_version": contract.version, "timeout_s": contract.timeout_s})
        if result.success:
            requested_limit = getattr(args, "limit", None)
            result = self._policy.cap_rows(contract, result, requested_limit)
            violation = self._policy.validate_output(ctx, contract, result)
            if violation is not None:
                result = ToolResult.failure(tool_name=call.name, tool_use_id=call.id, scope=scope, code=violation.code,
                                            message=violation.message, contract_version=contract.version,
                                            timeout_s=contract.timeout_s)
                return await self._finish(ctx, contract, result, started, refused=True)
        return await self._finish(ctx, contract, result, started)

    # ------------------------------------------------------------------
    async def _finish(self, ctx: RequestContext, contract: Optional[ToolContract], result: ToolResult,
                      started: float, *, refused: bool = False) -> ToolResult:
        elapsed = int((time.perf_counter() - started) * 1000)
        result = result.model_copy(update={"elapsed_ms": elapsed})
        result = result.model_copy(update={"model_visible_text": render_for_model(result, max_chars=self._max_visible_chars)})
        if refused:
            action, outcome = AuditAction.tool_refused, "refused"
        elif result.success:
            action, outcome = AuditAction.tool_call, "success"
        else:
            action, outcome = AuditAction.tool_failed, "failure"
        await emit_safely(self._audit, make_audit_event(
            ctx, action=action, outcome=outcome, component="tool",
            tool_name=result.tool_name, operation=result.operation, span_id=result.tool_use_id,
            data_categories=list(contract.data_categories) if contract else [],
            row_count=result.count if result.success else None, truncated=result.truncated if result.success else None,
            latency_ms=elapsed, error_code=result.error.code if result.error else None,
        ))
        return result
