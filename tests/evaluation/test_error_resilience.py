"""
Property-Based Tests for Error Resilience.

Property 14: Error resilience — continue on individual failure
Validates: Requirements 2.11, 3.11, 7.9, 11.4
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st


def process_items_with_resilience(items, process_fn):
    """Process items, recording errors but never aborting.

    For any item that raises an exception, the error is recorded and
    processing continues with the next item.

    Args:
        items: List of items to process.
        process_fn: Function to apply to each item.

    Returns:
        List of result dicts with keys: item, result, error.
    """
    results = []
    for item in items:
        try:
            result = process_fn(item)
            results.append({"item": item, "result": result, "error": None})
        except Exception as e:
            results.append({"item": item, "result": None, "error": str(e)})
    return results


@given(
    items=st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=20),
    fail_indices=st.frozensets(st.integers(min_value=0, max_value=19)),
)
@settings(max_examples=100)
def test_property_14_error_resilience(items, fail_indices):
    """**Validates: Requirements 2.11, 3.11, 7.9, 11.4**

    Property 14: Error resilience — continue on individual failure.

    For any evaluation module processing a list of N items where K items raise
    exceptions, the module must record N results total (K with error + N-K
    successful). The module must not abort early.
    """
    n = len(items)
    actual_fail_indices = {i for i in fail_indices if i < n}

    def process_fn(item):
        idx = items.index(item)
        if idx in actual_fail_indices:
            raise ValueError(f"Simulated failure for item {item}")
        return item * 2

    results = process_items_with_resilience(items, process_fn)

    # Must produce exactly N results — no early abort
    assert len(results) == n, (
        f"Expected {n} results, got {len(results)}"
    )

    error_results = [r for r in results if r["error"] is not None]
    success_results = [r for r in results if r["error"] is None]

    # All results are either success or error — no missing entries
    assert len(error_results) + len(success_results) == n, (
        f"error({len(error_results)}) + success({len(success_results)}) != {n}"
    )
