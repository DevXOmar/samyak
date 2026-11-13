from samyak.atlas import syntax_tree


def test_ast_artifact_is_bounded_and_source_mapped():
    graph = syntax_tree("def f(x):\n    return x + 1\n", limit=8)
    assert len(graph["nodes"]) <= 8
    assert any(n["ast_type"] == "Return" and n["start_line"] == 2 for n in graph["nodes"])
    assert all(e["source"] in {n["id"] for n in graph["nodes"]} for e in graph["edges"])
    assert any(e["kind"] == "body" for e in graph["edges"])
