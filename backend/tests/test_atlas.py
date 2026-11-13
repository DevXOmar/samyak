from samyak.atlas import syntax_tree


def test_ast_artifact_is_bounded_and_source_mapped():
    graph = syntax_tree("def f(x):\n    return x + 1\n", limit=8)
    assert len(graph["nodes"]) <= 8
    assert any(n["ast_type"] == "Return" and n["start_line"] == 2 for n in graph["nodes"])
    assert all(e["source"] in {n["id"] for n in graph["nodes"]} for e in graph["edges"])
    assert any(e["kind"] == "body" for e in graph["edges"])


def test_large_artifact_reports_exact_omissions_without_touching_features():
    source = "\n".join(f"def f{i}(x):\n    return x + {i}" for i in range(100))
    complete = syntax_tree(source)
    bounded = syntax_tree(source, limit=25)
    assert not complete["truncated"]
    assert bounded["omitted_nodes"] == len(complete["nodes"]) - 25
