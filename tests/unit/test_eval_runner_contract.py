"""Los runners de Evaluation solo dependen de process_message(...) -> dict{content, tools_used, sources}."""

import pytest

from chathce.adapters.memory import ScriptedTurn
from chathce.legacy.agent_facade import LegacyAgentFacade
from tests.fakes.container_factory import build_test_container
from tests.fakes.mimic_fixtures import fixtures_available

pytestmark = [pytest.mark.unit, pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")]


def test_security_runner_verifiers_accept_facade_output():
    from Evaluation.run_security_tests import SECURITY_TESTS, run_security_test

    facade = LegacyAgentFacade(build_test_container([ScriptedTurn(text="No puedo ejecutar consultas libres; no existe ese dato.")] * len(SECURITY_TESTS)))
    results = [run_security_test(facade, t) for t in SECURITY_TESTS]
    assert all(r["error"] is None for r in results)
    assert all(r["passed"] for r in results if r["category"] in ("sql_injection", "prompt_injection", "anti_hallucination"))


def test_functional_runner_scores_facade_output():
    from Evaluation.run_test_cases import TC_DB_CASES, run_test_case

    assert TC_DB_CASES, "TC-DB derivados del golden set"
    case = TC_DB_CASES[0]
    facade = LegacyAgentFacade(build_test_container([ScriptedTurn(text=f"Respuesta con {case.verification_data['expected_values'][0]}")]))
    result = run_test_case(facade, case)
    assert result.error is None and 0.0 <= result.weighted_score <= 1.0
