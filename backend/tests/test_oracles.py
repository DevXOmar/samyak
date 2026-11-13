from pydantic import ValidationError
import pytest
from samyak.contracts import TestCase, Execution, AnalysisRequest
from samyak.inference import infer
from samyak.repair import verdict


def result(status, output=None):
    return Execution(test_id="t", status=status, output=output)


def test_untyped_inputs_and_no_oracle_abstention():
    info, cases = infer("def average(nums):\n    return sum(nums) / len(nums)\n")
    assert info[0]["parameters"][0]["candidate_type"] == "list[int]"
    assert any(t.args == [[]] for t in cases)
    assert all(t.domain == "UNCONFIRMED" and t.tier == "C" and not t.has_expected for t in cases)
    t = cases[0]
    assert verdict([t], [result("ERROR")], [result("PASS", 0)]) == "INCONCLUSIVE_NO_OUTPUT_ORACLE"


def test_i_fault_only_is_not_output_validation():
    t = TestCase(function="f", tier="I", domain="CONFIRMED")
    assert verdict([t], [result("ERROR")], [result("PASS", 42)]) == "VALIDATED_RUNTIME_FAULT_ONLY"


def test_exact_oracle_and_regression_gate():
    a = TestCase(function="f", tier="A", domain="CONFIRMED", has_expected=True, expected=1)
    b = TestCase(function="g", tier="A", domain="CONFIRMED", has_expected=True, expected=2)
    assert verdict([a], [result("FAIL")], [result("PASS")]) == "VALIDATED_ON_TESTS"
    assert (
        verdict([a, b], [result("FAIL"), result("PASS")], [result("PASS"), result("FAIL")])
        == "REJECTED_REGRESSION"
    )
    assert verdict([a], [result("TIMEOUT")], [result("PASS")]) == "INCONCLUSIVE_TIMEOUT"
    assert verdict([a], [result("EXECUTION_UNAVAILABLE")], [result("PASS")]) == "EXECUTION_UNAVAILABLE"


def test_no_oracle_fabrication_and_payload_budgets():
    with pytest.raises(ValidationError):
        TestCase(function="f", tier="A")
    with pytest.raises(ValidationError):
        TestCase(function="f", tier="B")
    with pytest.raises(ValidationError):
        TestCase(function="f", args=[float("inf")])
    with pytest.raises(ValidationError):
        AnalysisRequest(source="x" * 60001)


def test_literal_call_sites_and_assertions():
    source = "def f(a):\n    return a[0]\nassert f([7]) == 7\n"
    info, tests = infer(source)
    assert info[0]["parameters"][0]["evidence_source"] == "STATIC_CALL_SITE"
    assert any(t.tier == "A" and t.expected == 7 and t.args == [[7]] for t in tests)


def test_shrinking_does_not_transfer_an_exact_confirmed_contract():
    from samyak.inference import shrink_fault

    class RestrictedObservationRunner:
        calls = 0

        def run(self, source, cases):
            self.calls += 1
            assert cases[0].domain == "UNCONFIRMED"
            assert not cases[0].has_expected and cases[0].tier == "C"
            return [
                Execution(
                    test_id=cases[0].id,
                    status="ERROR",
                    error="ZeroDivisionError: division by zero",
                    fault_lines=[1],
                )
            ]

    case = TestCase(
        id="authored",
        function="f",
        args=[[3, 4]],
        tier="A",
        domain="CONFIRMED",
        has_expected=True,
        expected=1,
    )
    original = Execution(
        test_id="authored",
        status="ERROR",
        error="ZeroDivisionError: division by zero",
        repeatable=True,
        fault_lines=[1],
    )
    runner = RestrictedObservationRunner()
    witness = shrink_fault("def f(xs): pass", [case], [original], runner)
    assert witness["minimal_args"] == [[]]
    assert witness["domain"] == "UNCONFIRMED"
    assert witness["observation"]["status"] == "ERROR"
    assert runner.calls <= 10


def test_unsupported_property_signature_never_confirms_guessed_inputs():
    info, cases = infer(
        "def sort_with_key(nums, key):\n    return nums\n",
        property_contracts={"sort_with_key": "sorted_multiset"},
    )
    assert "NOT_SUPPORTED" in info[0]["unsupported"]
    assert not cases
