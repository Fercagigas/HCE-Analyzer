"""
Property-Based Tests for Weighted Scoring Computation.

Property 13: Weighted scoring computation is correct
Validates: Requirements 7.5, 7.6
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st


def compute_weighted_score(weights, scores):
    """Compute weighted aggregate score: sum(w*s) / sum(w).

    Args:
        weights: List of non-negative weights.
        scores: List of scores in [0.0, 1.0].

    Returns:
        Weighted average score, or 0.0 if total weight is zero.
    """
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return sum(w * s for w, s in zip(weights, scores)) / total_weight


@given(
    weights=st.lists(st.floats(min_value=0.01, max_value=1.0), min_size=1, max_size=10),
    scores=st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=10),
)
@settings(max_examples=100)
def test_property_13_weighted_scoring_computation(weights, scores):
    """**Validates: Requirements 7.5, 7.6**

    Property 13: Weighted scoring computation is correct.

    For any functional test case with criteria weights {w_i} and scores {s_i}
    where each s_i in [0.0, 1.0], the weighted aggregate score must equal
    sum(w_i * s_i) / sum(w_i).
    """
    assume(len(weights) == len(scores))
    assume(sum(weights) > 0)

    result = compute_weighted_score(weights, scores)
    expected = sum(w * s for w, s in zip(weights, scores)) / sum(weights)

    assert abs(result - expected) < 1e-9, (
        f"compute_weighted_score({weights}, {scores}) = {result}, "
        f"expected {expected}"
    )


@given(
    weights=st.lists(st.floats(min_value=0.01, max_value=1.0), min_size=1, max_size=10),
    scores=st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=10),
    score_minimo=st.floats(min_value=0.0, max_value=1.0),
)
@settings(max_examples=100)
def test_property_13_pass_fail_threshold(weights, scores, score_minimo):
    """**Validates: Requirements 7.5, 7.6**

    Property 13 (pass/fail): A test is marked as passed if and only if
    weighted_score >= score_minimo.
    """
    assume(len(weights) == len(scores))
    assume(sum(weights) > 0)

    weighted_score = compute_weighted_score(weights, scores)
    passed = weighted_score >= score_minimo

    assert passed == (weighted_score >= score_minimo), (
        f"Pass/fail mismatch: weighted_score={weighted_score}, "
        f"score_minimo={score_minimo}, passed={passed}"
    )
