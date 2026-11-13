import ast
import difflib
import json
import os
import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider
import httpx
from .contracts import Candidate
from .ml import edit_priors
from .store import digest

OPERATORS = [
    "COMPARISON_LT_TO_LTE",
    "COMPARISON_LTE_TO_LT",
    "COMPARISON_GT_TO_GTE",
    "CHANGE_BOOLEAN_OPERATOR",
    "ADD_GUARD",
    "REPLACE_RETURN",
    "INDEX_SHIFT",
]
SAFE_IMPORTS = {
    "math",
    "typing",
    "collections",
    "itertools",
    "functools",
    "statistics",
    "bisect",
    "heapq",
    "re",
    "string",
    "decimal",
    "fractions",
}
FORBIDDEN = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "breakpoint",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
    "exit",
    "quit",
}


def safety(source, allow_input=False):
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        return "REJECTED_SYNTAX", str(exc)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(n.name.split(".")[0] not in SAFE_IMPORTS for n in node.names):
            return "REJECTED_SECURITY", "Import outside the fixed standard-library allowlist"
        if isinstance(node, ast.ImportFrom) and (
            node.level or (node.module or "").split(".")[0] not in SAFE_IMPORTS | {"__future__"}
        ):
            return "REJECTED_SECURITY", "Import outside the fixed standard-library allowlist"
        if isinstance(node, ast.Name) and (
            (node.id in FORBIDDEN and not (allow_input and node.id == "input"))
            or node.id.startswith("__")
            and node.id not in {"__name__"}
        ):
            return "REJECTED_SECURITY", f"Restricted name: {node.id}"
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return "REJECTED_SECURITY", "Dunder introspection is unsupported"
    return None, None


def make_candidate(original, patched, operator, line, prior, context):
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(True), patched.splitlines(True), fromfile="original.py", tofile="patched.py"
        )
    )
    changed = sum(
        text.startswith(("+", "-")) and not text.startswith(("+++", "---")) for text in diff.splitlines()
    )
    return Candidate(
        id=digest(patched)[:20],
        source_hash=digest(patched),
        source=patched,
        diff=diff,
        operator=operator,
        line=line,
        prior=prior,
        context=context,
        changed_lines=changed,
    )


def candidates(source, structure, findings, tests, original_results, precedents):
    wrapper = MetadataWrapper(cst.parse_module(source))
    positions = wrapper.resolve(PositionProvider)
    priors = edit_priors(precedents, OPERATORS)
    fn_names = [n.name for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)]
    context = {
        "functions": fn_names,
        "surrounding_functions": [
            {"name": f.name, "source": ast.get_source_segment(source, f)}
            for f in ast.walk(ast.parse(source))
            if isinstance(f, ast.FunctionDef)
        ],
        "callers": [e for e in structure["graph"]["edges"] if e["kind"] == "CALLS"],
        "def_use": [e for e in structure["graph"]["edges"] if e["kind"] == "DEF_USE"][:100],
        "witnesses": [r.model_dump() for r in original_results if r.status in {"FAIL", "ERROR"}][:8],
        "test_revision": digest(json.dumps([t.model_dump() for t in tests], sort_keys=True)),
        "precedent_ids": [p["id"] for p in precedents],
        "assumptions": "Candidates are hypotheses. Only frozen A/B/I in-contract tests can validate them.",
    }
    edits = []

    class Collect(cst.CSTVisitor):
        def visit_ComparisonTarget(self, node):
            pos = positions[node]
            relevant = any(
                f.rule_id in {"LOOP_OFF_BY_ONE", "BAD_CONDITION", "INDEX_BOUNDARY"}
                and f.span.start_line <= pos.start.line <= f.span.end_line
                for f in findings
            )
            swaps = {
                cst.LessThan: (cst.LessThanEqual, "COMPARISON_LT_TO_LTE"),
                cst.LessThanEqual: (cst.LessThan, "COMPARISON_LTE_TO_LT"),
                cst.GreaterThan: (cst.GreaterThanEqual, "COMPARISON_GT_TO_GTE"),
                cst.Equal: (cst.NotEqual, "CHANGE_BOOLEAN_OPERATOR"),
                cst.NotEqual: (cst.Equal, "CHANGE_BOOLEAN_OPERATOR"),
            }
            if relevant and type(node.operator) in swaps:
                op, name = swaps[type(node.operator)]
                edits.append((node, node.with_changes(operator=op()), name, pos.start.line))

        def visit_Return(self, node):
            if isinstance(node.value, cst.Name) and node.value.value == "None":
                edits.append(
                    (
                        node,
                        node.with_changes(value=cst.UnaryOperation(cst.Minus(), cst.Integer("1"))),
                        "REPLACE_RETURN",
                        positions[node].start.line,
                    )
                )

        def visit_FunctionDef(self, node):
            matching = [
                f
                for f in findings
                if f.function == node.name.value and f.rule_id in {"DIV_ZERO", "EMPTY_COLLECTION"}
            ]
            if matching and isinstance(node.body, cst.IndentedBlock) and node.params.params:
                fn_ast = next(
                    (
                        f
                        for f in ast.walk(ast.parse(source))
                        if isinstance(f, ast.FunctionDef) and f.name == node.name.value
                    ),
                    None,
                )
                parameter_names = {p.name.value for p in node.params.params}
                guards = set()
                if fn_ast:
                    for operation in ast.walk(fn_ast):
                        if isinstance(operation, ast.BinOp) and isinstance(
                            operation.op, (ast.Div, ast.FloorDiv, ast.Mod)
                        ):
                            divisor = operation.right
                            if isinstance(divisor, ast.Name) and divisor.id in parameter_names:
                                guards.add(f"{divisor.id} == 0")
                            if (
                                isinstance(divisor, ast.Call)
                                and isinstance(divisor.func, ast.Name)
                                and divisor.func.id == "len"
                                and len(divisor.args) == 1
                                and isinstance(divisor.args[0], ast.Name)
                                and divisor.args[0].id in parameter_names
                            ):
                                guards.add(f"not {divisor.args[0].id}")
                if not guards and any(f.rule_id == "EMPTY_COLLECTION" for f in matching):
                    guards.add(f"not {node.params.params[0].name.value}")
                for condition in sorted(guards)[:2]:
                    for result in ("0", "None"):
                        guard = cst.parse_statement(f"if {condition}:\n    return {result}\n")
                        edits.append(
                            (
                                node,
                                node.with_changes(body=node.body.with_changes(body=(guard, *node.body.body))),
                                "ADD_GUARD",
                                positions[node].start.line,
                            )
                        )

    wrapper.module.visit(Collect())
    output = []
    for target, replacement, operator, line in edits:

        class Edit(cst.CSTTransformer):
            def on_leave(self, original_node, updated_node):
                return replacement if original_node is target else updated_node

        patched = wrapper.module.visit(Edit()).code
        if patched != source:
            output.append(make_candidate(source, patched, operator, line, priors.get(operator, 0), context))
    # Fixed bounded pool, ranked by historical operator prior and then patch footprint.
    output = sorted({c.id: c for c in output}.values(), key=lambda c: (-c.prior, c.changed_lines, c.line))[:6]
    return output, context


def llm_candidates(source, context, findings, tests, precedents):
    base, model, key = (
        os.getenv("SAMYAK_LLM_BASE_URL"),
        os.getenv("SAMYAK_LLM_MODEL"),
        os.getenv("SAMYAK_LLM_API_KEY"),
    )
    if not base or not model or not key:
        return [], "DISABLED_NO_CONFIGURATION"
    prompt = {
        "source": source,
        "context": context,
        "findings": [f.model_dump() for f in findings],
        "tests": [t.model_dump() for t in tests],
        "historical_analogies_not_oracles": precedents,
        "instruction": "Return JSON object with candidates array containing at most two objects with complete source. Minimal local edits only. Preserve API/imports. Analogies are not specifications. Do not invent output oracles.",
    }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                base.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + key},
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": json.dumps(prompt)}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 3500,
                },
            )
            response.raise_for_status()
            if len(response.content) > 100000:
                return [], "RESPONSE_TOO_LARGE"
            payload = json.loads(response.json()["choices"][0]["message"]["content"])
            result = []
            for item in payload.get("candidates", [])[:2]:
                patched = item["source"]
                if isinstance(patched, str) and len(patched) <= 60000:
                    result.append(make_candidate(source, patched, "LLM_CONTEXTUAL", 1, 0, context))
            return result, "GENERATED"
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        return [], "UNAVAILABLE_" + type(exc).__name__


def compatible(original, patched):
    """Bound candidate edits and preserve top-level function signatures and imports."""
    try:
        a, b = ast.parse(original), ast.parse(patched)
    except SyntaxError as exc:
        return "REJECTED_SYNTAX", str(exc)

    def signatures(tree):
        return [
            (n.name, ast.dump(n.args))
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

    def imports(tree):
        return [ast.dump(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]

    if signatures(a) != signatures(b) or imports(a) != imports(b):
        return "REJECTED_SECURITY", "Candidate changed public signatures or imports"
    changes = list(difflib.SequenceMatcher(None, original.splitlines(), patched.splitlines()).get_opcodes())
    if sum(max(j - i, end - k) for tag, i, j, k, end in changes if tag != "equal") > 20:
        return "REJECTED_SECURITY", "Candidate exceeds 20-line edit budget"
    return safety(patched)


def trusted(test):
    return test.domain == "CONFIRMED" and (test.tier in {"A", "B"} or test.tier == "I")


def verdict(tests, originals, patched):
    pairs = list(zip(tests, originals, patched))
    if any(r.status == "EXECUTION_UNAVAILABLE" for r in originals + patched):
        return "EXECUTION_UNAVAILABLE"
    if any(r.status in {"SANDBOX_ERROR", "OUTPUT_LIMIT", "UNSUPPORTED_OUTPUT"} for r in originals + patched):
        return "SANDBOX_ERROR"
    if any(r.status == "FLAKY" for r in originals + patched):
        return "FLAKY"
    # Preserve operationally passing confirmed-domain generated trials as well as authoritative tests.
    regressions = [
        (t, a, b)
        for t, a, b in pairs
        if t.domain == "CONFIRMED" and a.status == "PASS" and b.status != "PASS"
    ]
    if regressions:
        return "REJECTED_REGRESSION"
    if any(r.status == "TIMEOUT" for r in originals + patched):
        return "INCONCLUSIVE_TIMEOUT"
    hard = [(t, a, b) for t, a, b in pairs if trusted(t)]
    fixed = [(t, a, b) for t, a, b in hard if a.status in {"FAIL", "ERROR"} and b.status == "PASS"]
    unresolved = [(t, a, b) for t, a, b in hard if b.status != "PASS"]
    if fixed and not unresolved:
        return (
            "VALIDATED_ON_TESTS"
            if any(t.tier in {"A", "B"} for t, _, _ in fixed)
            else "VALIDATED_RUNTIME_FAULT_ONLY"
        )
    if unresolved:
        return "UNRESOLVED"
    if not hard:
        return "INCONCLUSIVE_NO_OUTPUT_ORACLE"
    return "UNVERIFIED_SUGGESTION"


def performance(tests, original, patched):
    workloads = []
    for test, a, b in zip(tests, original, patched):
        if (
            test.domain == "CONFIRMED"
            and a.status == b.status == "PASS"
            and a.output == b.output
            and a.repeatable
            and b.repeatable
        ):
            if a.median_ms is not None and b.median_ms is not None:
                workloads.append(
                    {
                        "test_id": test.id,
                        "n": min(len(a.samples_ms), len(b.samples_ms)),
                        "original_median_ms": a.median_ms,
                        "patched_median_ms": b.median_ms,
                        "original_p95_ms": a.p95_ms,
                        "patched_p95_ms": b.p95_ms,
                        "delta_ms": b.median_ms - a.median_ms,
                    }
                )
    # Microsecond functions cannot support a robust speedup claim with seven samples.
    return {
        "status": "PERFORMANCE_INCONCLUSIVE",
        "workloads": workloads,
        "reason": "Bounded seven-sample runs in separate containers; noise/order effects not controlled enough for a speedup claim",
        "startup_excluded": True,
        "warmup_calls": 1,
    }


def validate(candidate, source, tests, originals, runner):
    rejected, reason = compatible(source, candidate.source)
    if rejected:
        candidate.verdict = rejected
        candidate.checks.append(
            {"gate": "syntax_security_applicability", "status": rejected, "reason": reason}
        )
        return candidate
    candidate.results = runner.run(candidate.source, tests)
    # Replay trusted failures and changed outcomes; differing signatures are never accepted.
    replay_ids = [
        i
        for i, (t, a, b) in enumerate(zip(tests, originals, candidate.results))
        if trusted(t) and (a.status != "PASS" or b.status != a.status)
    ]
    if replay_ids and runner.manifest["status"] == "AVAILABLE":
        replays = runner.run(candidate.source, [tests[i] for i in replay_ids])
        for index, replay in zip(replay_ids, replays):
            current = candidate.results[index]
            if (current.status, current.output, current.error) != (
                replay.status,
                replay.output,
                replay.error,
            ):
                current.status = "FLAKY"
    candidate.verdict = verdict(tests, originals, candidate.results)
    candidate.performance = performance(tests, originals, candidate.results)
    for t, a, b in zip(tests, originals, candidate.results):
        candidate.checks.append(
            {
                "test_id": t.id,
                "tier": t.tier,
                "domain": t.domain,
                "original": a.status,
                "patched": b.status,
                "gate": "HARD" if trusted(t) else "OBSERVATION",
                "regression": t.domain == "CONFIRMED" and a.status == "PASS" and b.status != "PASS",
            }
        )
    return candidate
