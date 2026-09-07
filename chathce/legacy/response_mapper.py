"""Mapeo ChatResponse <-> dict legacy que consumen ui/unified_chat_interface.py y los runners de Evaluation."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from chathce.domain.chat import ChatMessageIn, ChatResponse, ToolCallSummary


def to_legacy_dict(response: ChatResponse, *, viz_id_map: Optional[Mapping[str, str]] = None, query_length: int = 0,
                   tool_outputs: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """tool_outputs: texto visible al modelo por tool_use_id (solo runtime legacy/evaluacion); rellena raw_output."""
    outputs = tool_outputs or {}
    viz_ids = [(viz_id_map or {}).get(v.viz_id, v.viz_id) for v in response.visualizations]
    tools_used: List[str] = []
    for call in response.tool_calls:
        if call.tool_name not in tools_used:
            tools_used.append(call.tool_name)
    legacy: Dict[str, Any] = {
        "success": response.success,
        "content": response.content if response.success or not response.error else f"**Error**\n\n{response.error.message}",
        "tools_used": tools_used,
        "tool_results": [
            {"tool": c.tool_name, "tool_use_id": c.tool_use_id, "operation": c.operation, "success": c.success,
             "count": c.count, "truncated": c.truncated, "elapsed_ms": c.elapsed_ms, "error_code": c.error_code,
             "evidence_ids": c.evidence_ids, "raw_output": outputs.get(c.tool_use_id),
             "summary": f"[DATOS: {c.tool_name}] {c.count} registro(s) ({c.operation})" if c.success else f"[ERROR: {c.tool_name}] {c.error_code}"}
            for c in response.tool_calls
        ],
        "visualizations": [{"type": "visualization_ids", "ids": viz_ids, "count": len(viz_ids), "metadata": None, "tool": "create_visualization"}] if viz_ids else [],
        "sources": [
            {"filename": s.filename, "page": str(s.page) if s.page is not None else None, "specialty": s.specialty,
             "doc_type": s.doc_type, "tool": s.tool, "retrieved_content": s.retrieved_content, "content": f"📄 {s.filename}",
             "evidence_id": s.evidence_id}
            for s in response.sources
        ],
        "tokens_used": response.metadata.tokens_input + response.metadata.tokens_output,
        "model_used": response.metadata.model_used or "none",
        "metadata": {
            "session_id": response.metadata.session_id, "timestamp": response.metadata.timestamp.isoformat(),
            "model_used": response.metadata.model_used or "none", "query_length": query_length,
            "trace_id": response.metadata.trace_id, "request_id": response.metadata.request_id,
            "prompt_version": response.metadata.prompt_version,
        },
        "processing_time_ms": response.metadata.latency_ms,
        "cached": response.metadata.cached,
        "facts": [c.model_dump(mode="json") for c in response.facts],
        "uncertainty": response.uncertainty.model_dump(mode="json"),
    }
    if response.error is not None:
        legacy["error"] = response.error.message
        legacy["error_type"] = response.error.code
        legacy["suggestions"] = list(response.error.suggestions)
        legacy["metadata"]["error_type"] = response.error.code
    return legacy


def from_legacy_history(context: Any) -> Optional[List[ChatMessageIn]]:
    """Convierte el formato de st.session_state.unified_messages a ChatMessageIn. None si no es una lista."""
    if not isinstance(context, list):
        return None
    messages: List[ChatMessageIn] = []
    for item in context:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in ("user", "assistant"):
            continue
        content = item.get("content")
        summaries = None
        if isinstance(content, dict):
            tools = content.get("tools_used") or [tr.get("tool") for tr in content.get("tool_results", []) if isinstance(tr, dict)]
            summaries = [ToolCallSummary(tool_name=str(t), tool_use_id="", operation="", success=True) for t in tools if t] or None
            content = str(content.get("content", ""))
        if not isinstance(content, str) or not content.strip():
            continue
        messages.append(ChatMessageIn(role=role, content=content, tool_summaries=summaries))
    return messages
