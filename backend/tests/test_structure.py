import ast
import pytest
from samyak.structure import analyze, localize
from samyak.repair import candidates, compatible, safety
from samyak.fixtures import fixture


def test_parser_never_executes_and_retains_spans(tmp_path):
    marker = tmp_path / "should-not-exist"
    source = f'open({str(marker)!r}, "w").write("bad")\n\ndef f(xs):\n    return xs[0]\n'
    structure, functions, findings = analyze(source)
    assert not marker.exists()
    assert functions[0].span.start_line == 3
    assert functions[0].source == ast.get_source_segment(source, ast.parse(source).body[1])
    assert structure["tokens"][0]["text"] == "open"
    assert any(f.rule_id == "INDEX_BOUNDARY" and f.span.start_line == 4 for f in findings)


def test_cfg_and_unresolved_calls():
    source = (
        "def f(x):\n    if x:\n        return 1\n    return 0\n\ndef g(x):\n    return f(x) + x.dynamic()\n"
    )
    structure, functions, findings = analyze(source)
    edges = structure["graph"]["edges"]
    assert any(e["kind"] == "TRUE_BRANCH" for e in edges)
    assert any(e["kind"] == "CALLS" and e["resolved"] for e in edges)
    assert any(e["kind"] == "CALLS" and not e["resolved"] for e in edges)
    ranks = localize(structure, functions, findings)
    assert all(r["signals"]["ochiai"] is None for r in ranks)


def test_severity_independent_of_probability_and_safe_divisor():
    _, functions, findings = analyze("def f(x):\n    return x / 2\n\ndef g(x):\n    return 1 / x\n")
    assert [f.function for f in findings if f.rule_id == "DIV_ZERO"] == ["g"]
    assert all(f.severity == "MEDIUM" for f in findings)
    functions[0].risk = 1
    assert all(f.severity == "MEDIUM" for f in findings)


def test_libcst_preserves_comments_original_and_context():
    source = fixture("binary_search")["source"].replace(
        "while left < right:", "while left < right:  # boundary comment"
    )
    structure, functions, findings = analyze(source)
    patches, context = candidates(source, structure, findings, [], [], [])
    patch = next(c for c in patches if "while left <= right:" in c.source)
    assert "# boundary comment" in patch.source
    assert "while left < right:" in source
    assert context["functions"] == ["binary_search"]
    assert compatible(source, patch.source) == (None, None)


@pytest.mark.parametrize(
    "source", ["import os\n", 'def f():\n return eval("1")', "def f(x):\n return x.__class__"]
)
def test_unsafe_changes_blocked(source):
    assert safety(source)[0] == "REJECTED_SECURITY"


def test_invalid_syntax_and_signature_change():
    assert safety("def :")[0] == "REJECTED_SYNTAX"
    assert compatible("def f(x):\n return x", "def f(y):\n return y")[0] == "REJECTED_SECURITY"


def test_type_annotations_are_not_runtime_index_findings():
    _, functions, findings = analyze("def f(nums: list[int]):\n    return len(nums)\n")
    assert functions[0].features["subscripts"] == 0
    assert not any(f.rule_id == "INDEX_BOUNDARY" for f in findings)


def test_none_operations_and_mixed_return_hypotheses():
    _, _, findings = analyze("def f(x: int | None):\n    if x:\n        return x + 1\n    return None\n")
    assert any(f.rule_id == "NONE_OPERATION" and f.evidence == "HYPOTHESIS" for f in findings)
    assert any(f.rule_id == "INCONSISTENT_RETURN" for f in findings)
