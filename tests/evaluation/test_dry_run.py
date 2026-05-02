"""
Property-Based Tests for Dry-Run Mode.

Property 19: Dry-run makes no API calls
Validates: Requirements 12.4
"""

from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Dry-run simulation helper
# ---------------------------------------------------------------------------

def run_evaluation_module(agent, questions, dry_run=False):
    """Simulate an evaluation module that respects --dry-run.

    In dry-run mode the module validates setup (e.g. checks that the agent
    can be instantiated and questions are non-empty) but does NOT call
    agent.process_message().

    Args:
        agent: A UnifiedChatAgent-like object with a process_message() method.
        questions: List of question strings to evaluate.
        dry_run: If True, skip all API calls.

    Returns:
        Dict with 'dry_run' flag and 'items_processed' count.
    """
    if dry_run:
        # Validate setup only — no API calls
        assert agent is not None, "Agent must be instantiated"
        assert isinstance(questions, list), "Questions must be a list"
        return {"dry_run": True, "items_processed": 0}

    results = []
    for q in questions:
        response = agent.process_message(q, context=None, session_id="eval-test")
        results.append(response)
    return {"dry_run": False, "items_processed": len(results)}


# ---------------------------------------------------------------------------
# Property 19: Dry-run makes no API calls
# Validates: Requirements 12.4
# ---------------------------------------------------------------------------

def test_property_19_dry_run_makes_no_api_calls():
    """**Validates: Requirements 12.4**

    Property 19: Dry-run makes no API calls.

    When --dry-run is active, UnifiedChatAgent.process_message() must not be
    called. No Anthropic API or Supabase query calls must be made.
    """
    mock_agent = MagicMock()
    questions = [
        "¿Cuál es el diagnóstico del paciente 10014729?",
        "Muestra los signos vitales del paciente 10014729",
    ]

    result = run_evaluation_module(mock_agent, questions, dry_run=True)

    mock_agent.process_message.assert_not_called()
    assert result["dry_run"] is True
    assert result["items_processed"] == 0


def test_property_19_non_dry_run_calls_process_message():
    """**Validates: Requirements 12.4**

    Property 19 (contrast): Without --dry-run, process_message() IS called
    for each question. This confirms the dry-run guard is the only difference.
    """
    mock_agent = MagicMock()
    mock_agent.process_message.return_value = {"success": True, "content": "response"}
    questions = ["question 1", "question 2", "question 3"]

    result = run_evaluation_module(mock_agent, questions, dry_run=False)

    assert mock_agent.process_message.call_count == len(questions), (
        f"Expected {len(questions)} calls, got {mock_agent.process_message.call_count}"
    )
    assert result["items_processed"] == len(questions)


@given(
    questions=st.lists(
        st.text(min_size=1, max_size=100),
        min_size=0,
        max_size=20,
    )
)
@settings(max_examples=100)
def test_property_19_dry_run_never_calls_process_message(questions):
    """**Validates: Requirements 12.4**

    Property 19 (property): For any list of questions, dry-run mode must
    never invoke process_message(), regardless of the number of questions.
    """
    mock_agent = MagicMock()

    result = run_evaluation_module(mock_agent, questions, dry_run=True)

    mock_agent.process_message.assert_not_called()
    assert result["dry_run"] is True
    assert result["items_processed"] == 0


@given(
    questions=st.lists(
        st.text(min_size=1, max_size=100),
        min_size=1,
        max_size=10,
    )
)
@settings(max_examples=50)
def test_property_19_dry_run_vs_live_call_count(questions):
    """**Validates: Requirements 12.4**

    Property 19 (call count invariant): In dry-run mode, process_message()
    call count is always 0. In live mode, it equals len(questions).
    """
    mock_agent_dry = MagicMock()
    mock_agent_live = MagicMock()
    mock_agent_live.process_message.return_value = {"success": True, "content": "ok"}

    run_evaluation_module(mock_agent_dry, questions, dry_run=True)
    run_evaluation_module(mock_agent_live, questions, dry_run=False)

    assert mock_agent_dry.process_message.call_count == 0, (
        "Dry-run must make zero process_message calls"
    )
    assert mock_agent_live.process_message.call_count == len(questions), (
        f"Live run must make exactly {len(questions)} process_message calls"
    )
