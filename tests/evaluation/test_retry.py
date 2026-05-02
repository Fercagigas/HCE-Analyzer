"""
Property-Based Tests for Retry Logic.

Property 15: Rate limit retry behavior
Validates: Requirements 2.12, 11.1

Property 16: Exponential backoff on connection errors
Validates: Requirements 11.2
"""

from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from Evaluation.eval_helpers import retry_on_rate_limit, retry_on_connection_error


# ---------------------------------------------------------------------------
# Property 15: Rate limit retry behavior
# Validates: Requirements 2.12, 11.1
# ---------------------------------------------------------------------------

@given(st.integers(min_value=0, max_value=3))
@settings(max_examples=20)
def test_property_15_retry_on_rate_limit(n_failures):
    """**Validates: Requirements 2.12, 11.1**

    Property 15: Rate limit retry behavior.

    For any number of rate-limit failures in [0, 3], retry_on_rate_limit must
    retry up to max_retries=3 times and succeed when n_failures <= max_retries.
    The total call count must equal n_failures + 1 (failures + final success).
    """
    call_count = 0

    def mock_func():
        nonlocal call_count
        call_count += 1
        if call_count <= n_failures:
            raise Exception("rate limit 429")
        return "success"

    with patch("time.sleep"):
        result = retry_on_rate_limit(mock_func, max_retries=3, wait_seconds=60)

    assert result == "success", f"Expected 'success', got {result!r}"
    assert call_count == n_failures + 1, (
        f"Expected {n_failures + 1} calls, got {call_count}"
    )


def test_property_15_retry_exhausted_raises():
    """**Validates: Requirements 2.12, 11.1**

    Property 15 (exhaustion): When all retries are exhausted (4 failures for
    max_retries=3), retry_on_rate_limit must re-raise the original exception.
    """
    call_count = 0

    def always_fails():
        nonlocal call_count
        call_count += 1
        raise Exception("rate limit 429")

    with patch("time.sleep"):
        try:
            retry_on_rate_limit(always_fails, max_retries=3, wait_seconds=60)
            assert False, "Should have raised an exception"
        except Exception as exc:
            assert "rate limit" in str(exc).lower() or "429" in str(exc), (
                f"Expected rate-limit exception, got: {exc}"
            )

    # Called once initially + 3 retries = 4 total
    assert call_count == 4, f"Expected 4 calls (1 + 3 retries), got {call_count}"


@given(st.integers(min_value=0, max_value=3))
@settings(max_examples=20)
def test_property_15_sleep_called_between_retries(n_failures):
    """**Validates: Requirements 2.12, 11.1**

    Property 15 (sleep): retry_on_rate_limit must call time.sleep exactly
    n_failures times (once per retry) with the configured wait_seconds.
    """
    call_count = 0
    sleep_calls = []

    def mock_func():
        nonlocal call_count
        call_count += 1
        if call_count <= n_failures:
            raise Exception("rate limit 429")
        return "success"

    def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("time.sleep", side_effect=mock_sleep):
        retry_on_rate_limit(mock_func, max_retries=3, wait_seconds=60)

    assert len(sleep_calls) == n_failures, (
        f"Expected {n_failures} sleep calls, got {len(sleep_calls)}"
    )
    for s in sleep_calls:
        assert s == 60, f"Expected sleep(60), got sleep({s})"


# ---------------------------------------------------------------------------
# Property 16: Exponential backoff on connection errors
# Validates: Requirements 11.2
# ---------------------------------------------------------------------------

@given(st.integers(min_value=1, max_value=3))
@settings(max_examples=20)
def test_property_16_exponential_backoff(n_failures):
    """**Validates: Requirements 11.2**

    Property 16: Exponential backoff on connection errors.

    For any number of ConnectionError failures in [1, 3], the retry delays
    must follow exponential backoff: 2s, 4s, 8s (base_wait=2, factor=2^attempt).
    The function must succeed after n_failures retries.
    """
    call_count = 0
    sleep_calls = []

    def mock_func():
        nonlocal call_count
        call_count += 1
        if call_count <= n_failures:
            raise ConnectionError("Supabase connection error")
        return "success"

    def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("time.sleep", side_effect=mock_sleep):
        result = retry_on_connection_error(mock_func, max_retries=3, base_wait=2)

    assert result == "success", f"Expected 'success', got {result!r}"

    # Verify exponential backoff: base_wait * 2^attempt for attempt in 0..n_failures-1
    expected_delays = [2 * (2 ** i) for i in range(n_failures)]
    assert sleep_calls == expected_delays, (
        f"Expected delays {expected_delays}, got {sleep_calls}"
    )


def test_property_16_backoff_exhausted_raises():
    """**Validates: Requirements 11.2**

    Property 16 (exhaustion): When all retries are exhausted, the original
    ConnectionError must be re-raised.
    """
    call_count = 0

    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Supabase connection error")

    with patch("time.sleep"):
        try:
            retry_on_connection_error(always_fails, max_retries=3, base_wait=2)
            assert False, "Should have raised ConnectionError"
        except ConnectionError as exc:
            assert "connection" in str(exc).lower(), (
                f"Expected ConnectionError, got: {exc}"
            )

    # 1 initial + 3 retries = 4 total
    assert call_count == 4, f"Expected 4 calls, got {call_count}"


def test_property_16_non_connection_error_not_retried():
    """**Validates: Requirements 11.2**

    Property 16 (non-connection errors): retry_on_connection_error must NOT
    retry on non-ConnectionError exceptions — it should re-raise immediately.
    """
    call_count = 0

    def raises_value_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("not a connection error")

    with patch("time.sleep") as mock_sleep:
        try:
            retry_on_connection_error(raises_value_error, max_retries=3, base_wait=2)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    assert call_count == 1, f"Non-connection errors should not be retried, got {call_count} calls"
    mock_sleep.assert_not_called()
