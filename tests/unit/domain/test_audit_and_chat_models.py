from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from chathce.domain.audit import AuditAction, AuditEvent
from chathce.domain.chat import (
    ChatEvent,
    ChatMetadata,
    ChatRequest,
    ChatResponse,
    CompleteEvent,
    TextDeltaEvent,
)
from chathce.domain.conversation import MessageMetadata, classify_analysis

pytestmark = pytest.mark.unit


def _event(**attrs) -> AuditEvent:
    return AuditEvent(
        event_id="e1", timestamp=datetime.now(timezone.utc), action=AuditAction.tool_call, outcome="success",
        component="tool", tenant_id="default", trace_id="t" * 8, request_id="r" * 8, attributes=attrs,
    )


def test_audit_event_accepts_allowlisted_attributes():
    event = _event(method="POST", status=200, iteration=1)
    assert event.attributes["status"] == 200


@pytest.mark.parametrize("key", ["message", "content", "query", "email", "token", "data", "user_message", "prompt"])
def test_audit_event_rejects_phi_like_attribute_keys(key):
    with pytest.raises(ValidationError):
        _event(**{key: "x"})


def test_audit_event_rejects_unknown_keys_and_long_values():
    with pytest.raises(ValidationError):
        _event(note="x")
    with pytest.raises(ValidationError):
        _event(reason="x" * 201)


def test_chat_request_limits_and_closed():
    with pytest.raises(ValidationError):
        ChatRequest(message="")
    with pytest.raises(ValidationError):
        ChatRequest(message="hola", sql="select")  # type: ignore[call-arg]
    request = ChatRequest(message="hola", patient_id="10001217")
    assert request.options.max_context_messages == 10


def test_chat_events_are_discriminated_by_type():
    adapter = TypeAdapter(ChatEvent)
    delta = adapter.validate_python({"type": "text_delta", "text": "hola", "iteration": 1})
    assert isinstance(delta, TextDeltaEvent)
    metadata = ChatMetadata(trace_id="t" * 8, request_id="r" * 8, timestamp=datetime.now(timezone.utc))
    response = ChatResponse(success=True, content="ok", metadata=metadata)
    complete = adapter.validate_python({"type": "complete", "response": response.model_dump()})
    assert isinstance(complete, CompleteEvent)


def test_message_metadata_is_allowlisted():
    with pytest.raises(ValidationError):
        MessageMetadata(raw_output={"x": 1})  # type: ignore[call-arg]
    assert MessageMetadata(tools_used=["get_labs"]).has_visualization is False


@pytest.mark.parametrize("tools_used, expected", [
    ([], "general"),
    (["query_mimic_database"], "database_query"),
    (["search_clinical_documents"], "rag_search"),
    (["get_labs"], "database_query"),
    (["create_visualization"], "visualization"),
    (["get_labs", "create_visualization"], "mixed"),
    (["request_visualization"], "visualization"),
    (["query_mimic_database", "search_clinical_documents"], "mixed"),
    (["rag_tool"], "rag_search"),
])
def test_classify_analysis_covers_legacy_and_core_tools(tools_used, expected):
    assert classify_analysis(tools_used) == expected
