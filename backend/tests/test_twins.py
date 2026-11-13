import ast
from samyak.twins import semantic_twin


def test_twin_is_ast_identical_and_preserves_lines():
    source = "def f(values):\n    return sum(values) / len(values)\n"
    twin = semantic_twin(source)
    assert twin["status"] == "ELIGIBLE"
    assert twin["source"] != source
    assert ast.dump(ast.parse(source)) == ast.dump(ast.parse(twin["source"]))
    assert source.count("\n") == twin["source"].count("\n")


def test_uncertain_equivalence_is_refused():
    for source in [
        "def f():\n yield 1\n",
        "@decorate\ndef f():\n return 1\n",
        "import inspect\ndef f():\n return 1\n",
    ]:
        assert semantic_twin(source)["status"] == "NOT_SUPPORTED"
