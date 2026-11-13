"""Bounded call/def-use impact, tournament evidence and operational suggestion policy."""

import ast
from collections import Counter, deque
import difflib
from .repair import trusted


def blast_radius(report, candidate):
    function = next(
        (f.name for f in report.functions if f.span.start_line <= candidate.line <= f.span.end_line), None
    )
    edges = report.structure.get("graph", {}).get("edges", [])
    calls = [e for e in edges if e["kind"] == "CALLS" and e.get("resolved")]
    visited, queue, traversed = set(), deque([f"fn:{function}"] if function else []), []
    while queue and len(visited) < 32:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for edge in calls:
            if edge["target"] == node:
                traversed.append(edge)
                queue.append(edge["source"])
    affected = sorted(n.removeprefix("fn:") for n in visited)
    dependent = [t.id for t in report.tests if t.function in affected]
    unknown = [
        e
        for e in edges
        if e["kind"] == "CALLS" and not e.get("resolved") and e["source"].removeprefix("fn:") in affected
    ]
    defuse = [
        e
        for e in edges
        if e["kind"] == "DEF_USE"
        and any(f":{candidate.line}:" in str(e.get(k)) for k in ("source", "target"))
    ]
    regression_ids = {c.get("test_id") for c in candidate.checks if c.get("regression")}
    caller_regressions = [
        t.id
        for t in report.tests
        if t.id in regression_ids and t.function in affected and t.function != function
    ]
    return {
        "edited_function": function,
        "affected_functions": affected,
        "call_edges": traversed,
        "def_use_edges": defuse,
        "dependent_test_ids": dependent,
        "unresolved_edges": unknown,
        "caller_regression_ids": caller_regressions,
        "bounded_nodes": len(visited),
        "limit": 32,
        "scope": "Reverse static calls + lexical def-use; all available suites still run",
    }


def ast_footprint(original, patched):
    try:
        a = [
            type(n).__name__ + ":" + ast.dump(n, include_attributes=False)
            for n in ast.walk(ast.parse(original))
        ]
        b = [
            type(n).__name__ + ":" + ast.dump(n, include_attributes=False)
            for n in ast.walk(ast.parse(patched))
        ]
        return sum(
            max(j - i, end - start)
            for tag, i, j, start, end in difflib.SequenceMatcher(None, a, b).get_opcodes()
            if tag != "equal"
        )
    except SyntaxError:
        return None


def enrich_tournament(report):
    rows, impacts, policies = [], {}, {}
    for candidate in report.candidates:
        impact = blast_radius(report, candidate)
        impacts[candidate.id] = impact
        candidate.context["blast_radius"] = impact
        matrix = list(zip(report.tests, report.original_results, candidate.results))
        fail_to_pass = sum(
            trusted(t) and a.status in {"FAIL", "ERROR"} and b.status == "PASS" for t, a, b in matrix
        )
        pass_to_pass = sum(trusted(t) and a.status == b.status == "PASS" for t, a, b in matrix)
        regressions = [c for c in candidate.checks if c.get("regression")]
        syntax_gate = next(
            (c for c in candidate.checks if c.get("gate") == "syntax_security_applicability"), None
        )
        admissible = candidate.verdict in {"VALIDATED_ON_TESTS", "VALIDATED_RUNTIME_FAULT_ONLY"}
        ast_edits = ast_footprint(report.source, candidate.source)
        rank = [
            0 if admissible else 1,
            0 if candidate.verdict == "VALIDATED_ON_TESTS" else 1,
            candidate.changed_lines,
            ast_edits or 0,
            len(impact["affected_functions"]),
        ]
        gates = [
            {
                "gate": "syntax/security",
                "status": "REJECTED" if syntax_gate else "PASSED",
                "reason": syntax_gate.get("reason")
                if syntax_gate
                else "Syntax, signatures, imports and edit budget checked",
            },
            {
                "gate": "regression",
                "status": "REJECTED" if regressions else "PASSED" if candidate.results else "NOT_RUN",
                "test_ids": [r["test_id"] for r in regressions],
            },
            {
                "gate": "oracle",
                "status": candidate.verdict,
                "fail_to_pass": fail_to_pass,
                "pass_to_pass": pass_to_pass,
            },
            {
                "gate": "runtime",
                "status": candidate.performance["status"],
                "reason": candidate.performance.get("reason"),
            },
        ]
        reasons = []
        if not admissible:
            band = "DO_NOT_RECOMMEND"
            reasons.append("No validated admissible repair, or a safety/regression/unresolved gate remains")
        else:
            strong = any(trusted(t) and t.tier in {"A", "B"} for t in report.tests)
            novel = report.intelligence.get("novelty", {}).get("abstain", True)
            if (
                strong
                and not novel
                and not impact["unresolved_edges"]
                and candidate.changed_lines <= 4
                and len(impact["affected_functions"]) <= 2
            ):
                band = "AUTO_SUGGEST"
                reasons.append(
                    "Small recorded-test validated edit with resolved static context and familiar model features"
                )
            else:
                band = "REVIEW_REQUIRED"
                if not strong:
                    reasons.append("Runtime-fault-only evidence does not establish output semantics")
                if novel:
                    reasons.append("Heuristic novelty or model disagreement calls for review")
                if impact["unresolved_edges"]:
                    reasons.append("Static call graph contains unresolved calls")
                if candidate.changed_lines > 4 or len(impact["affected_functions"]) > 2:
                    reasons.append("Larger edit or caller impact")
        policies[candidate.id] = {
            "band": band,
            "reasons": reasons,
            "automatic_application": False,
            "signals": {
                "validated": admissible,
                "changed_lines": candidate.changed_lines,
                "affected_functions": len(impact["affected_functions"]),
                "graph_unknown": bool(impact["unresolved_edges"]),
                "fail_to_pass": fail_to_pass,
            },
        }
        rows.append(
            {
                "candidate_id": candidate.id,
                "verdict": candidate.verdict,
                "admissible": admissible,
                "rank_key": rank,
                "ast_edits": ast_edits,
                "fail_to_pass": fail_to_pass,
                "pass_to_pass": pass_to_pass,
                "gates": gates,
                "regression_ids": [c["test_id"] for c in regressions],
            }
        )
    rows.sort(key=lambda r: (r["rank_key"], r["candidate_id"]))
    report.intelligence["tournament"] = {
        "status": "RANKED",
        "candidates": rows,
        "winner_id": next((r["candidate_id"] for r in rows if r["admissible"]), None),
        "policy": "Safety/regression gates → trusted correctness → changed lines → AST footprint → caller radius. Inconclusive runtime cannot break ties.",
    }
    report.intelligence["blast_radius"] = {
        "status": "COMPUTED",
        "candidates": impacts,
        "caller_regressions": sum(len(i["caller_regression_ids"]) for i in impacts.values()),
        "all_available_tests_run": True,
    }
    report.intelligence["risk_budget"] = {
        "status": "ASSESSED",
        "policy_version": "1.0",
        "candidates": policies,
        "distribution": dict(Counter(p["band"] for p in policies.values())),
        "reason": "Operational review bands, never an automatic code commit or a probability of safety",
    }
