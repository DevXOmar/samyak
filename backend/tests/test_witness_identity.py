from samyak.contracts import TestCase, Execution
from samyak.inference import shrink_fault
from samyak.investigations import witnessed_case
from samyak.contracts import Report


def test_unrelated_exception_and_source_location_cannot_shrink():
    class Runner:
        def run(self, source, tests):
            return [
                Execution(
                    test_id=t.id,
                    status="ERROR",
                    error="ZeroDivisionError: division by zero",
                    fault_lines=[99],
                )
                for t in tests
            ]

    t = TestCase(id="x", function="f", args=[[7, 8, 9], 7])
    r = Execution(test_id="x", status="ERROR", error="ZeroDivisionError: division by zero", fault_lines=[2])
    proof = shrink_fault("def f(a,b): return 1/0", [t], [r], Runner())
    assert proof["minimal_args"] == t.args


def test_logical_mismatch_never_turns_into_type_error():
    class Runner:
        def run(self, source, tests):
            assert tests[0].args == [[7], 7]
            return [Execution(test_id="x", status="FAIL", output=-1, fault_lines=[], lines=[2])]

    t = TestCase(
        id="x", function="f", args=[[7], 7], tier="A", domain="CONFIRMED", has_expected=True, expected=0
    )
    r = Execution(test_id="x", status="FAIL", output=-1, lines=[2])
    report = Report(
        job_id="j",
        source_hash="h",
        test_revision="t",
        source="def f(a,b): return -1",
        tests=[t],
        original_results=[r],
    )
    proof = witnessed_case(report, Runner(), "x")
    assert proof["minimal_args"] == proof["original_args"] == [[7], 7]
    assert proof["result"]["status"] == "FAIL" and proof["reduction_status"] == "INCONCLUSIVE_REDUCTION"
