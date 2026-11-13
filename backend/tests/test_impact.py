from samyak.contracts import Report, Candidate, TestCase as Case, Execution
from samyak.structure import analyze
from samyak.impact import enrich_tournament


def test_bounded_reverse_callers_and_regression_policy():
    source = "def lookup(x):\n    return None\n\ndef contains(x):\n    return lookup(x) is not None\n"
    graph, functions, findings = analyze(source)
    t = Case(
        id="caller",
        function="contains",
        args=[1],
        tier="A",
        domain="CONFIRMED",
        has_expected=True,
        expected=False,
    )
    c = Candidate(
        id="bad",
        source_hash="x",
        source=source.replace("return None", "return -1"),
        diff="",
        operator="REPLACE_RETURN",
        line=2,
        prior=0,
        context={},
        changed_lines=2,
        verdict="REJECTED_REGRESSION",
        checks=[{"test_id": "caller", "regression": True}],
        results=[Execution(test_id="caller", status="FAIL")],
    )
    report = Report(
        job_id="j",
        source_hash="x",
        source=source,
        test_revision="t",
        structure=graph,
        functions=functions,
        findings=findings,
        tests=[t],
        original_results=[Execution(test_id="caller", status="PASS")],
        candidates=[c],
    )
    enrich_tournament(report)
    impact = report.intelligence["blast_radius"]["candidates"]["bad"]
    assert impact["affected_functions"] == ["contains", "lookup"]
    assert impact["caller_regression_ids"] == ["caller"]
    assert report.intelligence["risk_budget"]["candidates"]["bad"]["band"] == "DO_NOT_RECOMMEND"
    assert report.intelligence["tournament"]["winner_id"] is None


def test_runtime_only_repair_requires_review():
    source = "def f(x):\n return x\n"
    graph, functions, findings = analyze(source)
    c = Candidate(
        id="ok",
        source_hash="x",
        source=source,
        diff="",
        operator="GUARD",
        line=2,
        prior=0,
        context={},
        changed_lines=1,
        verdict="VALIDATED_RUNTIME_FAULT_ONLY",
    )
    r = Report(
        job_id="j",
        source_hash="x",
        source=source,
        test_revision="t",
        structure=graph,
        functions=functions,
        candidates=[c],
    )
    enrich_tournament(r)
    assert r.intelligence["risk_budget"]["candidates"]["ok"]["band"] == "REVIEW_REQUIRED"


def test_small_familiar_authoritative_repair_can_be_suggested_without_application():
    source = "def f(x):\n    return x\n"
    graph, functions, findings = analyze(source)
    test = Case(
        id="exact", function="f", args=[0], tier="A", domain="CONFIRMED", has_expected=True, expected=0
    )
    candidate = Candidate(
        id="accepted",
        source_hash="x",
        source=source,
        diff="",
        operator="GUARD",
        line=2,
        prior=0,
        context={},
        changed_lines=2,
        verdict="VALIDATED_ON_TESTS",
        results=[Execution(test_id="exact", status="PASS")],
    )
    report = Report(
        job_id="j",
        source_hash="x",
        source=source,
        test_revision="t",
        structure=graph,
        functions=functions,
        tests=[test],
        original_results=[Execution(test_id="exact", status="FAIL")],
        candidates=[candidate],
        intelligence={"novelty": {"abstain": False}},
    )
    enrich_tournament(report)
    policy = report.intelligence["risk_budget"]["candidates"]["accepted"]
    assert policy["band"] == "AUTO_SUGGEST" and policy["automatic_application"] is False
