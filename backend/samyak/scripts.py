"""Side-effect-free module facts and orchestration of isolated script observations."""

import ast
from .contracts import Execution, Finding, Span, TestCase
from .structure import span
from .repair import safety
from .runner import DockerRunner


def module_facts(source):
    tree = ast.parse(source)
    nodes, edges, findings, calls, statements = [], [], [], [], []
    known = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    class ModuleVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            pass

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef
        visit_Import = visit_FunctionDef
        visit_ImportFrom = visit_FunctionDef

    class Collector(ModuleVisitor):
        def generic_visit(self, node):
            if isinstance(node, ast.stmt):
                statements.append(node)
            super().generic_visit(node)

    visitor = Collector()
    visitor.visit(tree)
    ids = {id(n): f"stmt:<module>:{n.lineno}:{n.col_offset}" for n in statements}
    for n in statements:
        nodes.append(
            {"id": ids[id(n)], "kind": "Statement", "ast_type": type(n).__name__, **span(n).model_dump()}
        )
        edges.append({"source": "module", "target": ids[id(n)], "kind": "CONTAINS"})

    def block(body, successor=None, loop=None):
        next_id = successor
        for n in reversed(body):
            nid = ids.get(id(n))
            if not nid:
                continue
            if isinstance(n, ast.If):
                for branch, kind in [(n.body, "TRUE_BRANCH"), (n.orelse, "FALSE_BRANCH")]:
                    dest = block(branch, next_id, loop)
                    if dest:
                        edges.append({"source": nid, "target": dest, "kind": kind})
            elif isinstance(n, (ast.While, ast.For)):
                dest = block(n.body, nid, (nid, next_id))
                if dest:
                    edges.append({"source": nid, "target": dest, "kind": "TRUE_BRANCH"})
                dest = block(n.orelse, next_id, loop)
                if dest:
                    edges.append({"source": nid, "target": dest, "kind": "FALSE_BRANCH"})
            elif isinstance(n, ast.Break) and loop and loop[1]:
                edges.append({"source": nid, "target": loop[1], "kind": "CONTROL_NEXT"})
            elif isinstance(n, ast.Continue) and loop:
                edges.append({"source": nid, "target": loop[0], "kind": "CONTROL_NEXT"})
            elif not isinstance(n, ast.Raise):
                if next_id:
                    edges.append({"source": nid, "target": next_id, "kind": "CONTROL_NEXT"})
                for field in ("body", "finalbody"):
                    if getattr(n, field, None):
                        block(getattr(n, field), next_id, loop)
                for handler in getattr(n, "handlers", []):
                    block(handler.body, next_id, loop)
            next_id = nid
        return next_id

    block(tree.body)

    def finding(rule, node, text, strength, family="OTHER"):
        findings.append(
            Finding(
                id=f"module:{rule}:{node.lineno}:{node.col_offset}",
                rule_id=rule,
                function="<module>",
                span=span(node),
                explanation=text,
                strength=strength,
                family=family,
                qualification="Static hypothesis; reachability and script input contract are unconfirmed",
            )
        )

    class Operations(ModuleVisitor):
        def visit_BinOp(self, node):
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and not (
                isinstance(node.right, ast.Constant)
                and isinstance(node.right.value, (int, float))
                and node.right.value != 0
            ):
                finding("DIV_ZERO", node, "Module divisor may be zero", 0.85, "ARITHMETIC_OPERATOR")
            if any(isinstance(o, ast.Constant) and o.value is None for o in (node.left, node.right)):
                finding("NONE_OPERATION", node, "None participates in arithmetic", 0.65, "GUARD_REMOVAL")
            self.generic_visit(node)

        def visit_Subscript(self, node):
            finding(
                "INDEX_BOUNDARY",
                node,
                "Module index requires bounds and a non-empty collection",
                0.5,
                "INDEX_OFFSET",
            )
            self.generic_visit(node)

        def visit_Compare(self, node):
            if any(ast.dump(node.left) == ast.dump(other) for other in node.comparators):
                finding(
                    "BAD_CONDITION",
                    node,
                    "Self-comparison may encode a mistaken condition (NaN is an exception)",
                    0.7,
                    "CONDITION_NEGATION",
                )
            self.generic_visit(node)

        def visit_Call(self, node):
            target = ast.unparse(node.func)
            cid = f"call:<module>:{node.lineno}:{node.col_offset}"
            nodes.append(
                {
                    "id": cid,
                    "kind": "Call",
                    "target": target,
                    "resolved": target in known,
                    **span(node).model_dump(),
                }
            )
            edges.append(
                {
                    "source": "module",
                    "target": f"fn:{target}" if target in known else cid,
                    "kind": "CALLS",
                    "resolved": target in known,
                    "line": node.lineno,
                }
            )
            calls.append({"line": node.lineno, "target": target, "resolved": target in known})
            if target in {"eval", "exec", "compile", "os.system", "subprocess.run", "subprocess.Popen"}:
                finding(
                    "UNSAFE_EVAL_EXEC", node, f"Potential unsafe sink: {target}; execution is blocked", 1.0
                )
            if target in {"pickle.loads", "pickle.load", "marshal.loads", "yaml.load"}:
                finding("DANGEROUS_DESERIALIZATION", node, f"Unsafe deserialization sink: {target}", 1.0)
            if target in {"min", "max"}:
                finding(
                    "EMPTY_COLLECTION",
                    node,
                    "Empty iterable needs a domain or explicit handling",
                    0.55,
                    "GUARD_REMOVAL",
                )
            if target == "range" and any(isinstance(a, ast.BinOp) for a in node.args):
                finding(
                    "LOOP_OFF_BY_ONE",
                    node,
                    "Arithmetic range endpoint may skip or exceed a boundary",
                    0.45,
                    "BOUNDARY_COMPARISON",
                )
            self.generic_visit(node)

    Operations().visit(tree)
    # Lexical, flow-insensitive def-use approximation, never evidence of execution.
    definitions = {}
    for stmt in statements:

        class Names(ModuleVisitor):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load) and node.id in definitions:
                    edges.append(
                        {
                            "source": definitions[node.id],
                            "target": ids[id(stmt)],
                            "kind": "DEF_USE",
                            "variable": node.id,
                            "approximation": "lexical",
                        }
                    )
                elif isinstance(node.ctx, ast.Store):
                    definitions[node.id] = ids[id(stmt)]

            def generic_visit(self, node):
                if isinstance(node, ast.stmt) and node is not stmt:
                    return
                super().generic_visit(node)

        Names().visit(stmt)
    return {
        "statement_count": len(statements),
        "nodes": nodes,
        "edges": edges,
        "calls": calls,
        "qualification": "Bounded static CFG and lexical def-use; coverage alone records observed lines",
    }, findings


def execute_script(source, stdin):
    blocked, reason = safety(source, allow_input=True)
    runner = DockerRunner()
    if blocked:
        return Execution(test_id="script", status=blocked, error=reason), runner.manifest
    result = runner.run(source, [TestCase(id="script", function="__script__", mode="SCRIPT", stdin=stdin)])[0]
    return result, runner.manifest


def annotate_execution(report, module_findings):
    """Keep module hypotheses and exact runtime observations separate from ML/oracles."""
    result = report.script_result
    fault_lines = list(dict.fromkeys(result.fault_lines)) if result else []
    ranks = []
    for line in fault_lines:
        owner = next(
            (f.name for f in report.functions if f.span.start_line <= line <= f.span.end_line), "<module>"
        )
        text = report.source.splitlines()[line - 1] if line <= len(report.source.splitlines()) else ""
        report.findings.append(
            Finding(
                id=f"script-runtime:{line}",
                rule_id="RUNTIME_EXCEPTION",
                function=owner,
                span=Span(start_line=line, end_line=line, start_col=0, end_col=len(text.encode())),
                explanation=result.error or result.status,
                evidence="OBSERVED_RUNTIME_FAULT",
                strength=1.0,
                family="OTHER",
                qualification="Observed for this exact stdin. Input domain is unconfirmed; no correctness claim.",
            )
        )
        ranks.append(
            {
                "line": line,
                "function": owner,
                "score": 1.0,
                "signals": {"runtime_fault": 1.0, "model_risk": None},
                "mode": "OBSERVED_RUNTIME_FAULT",
            }
        )
    ranks.extend(
        {
            "line": f.span.start_line,
            "function": "<module>",
            "score": f.strength,
            "signals": {"rule_strength": f.strength, "model_risk": None},
            "mode": "STATIC_HYPOTHESIS",
        }
        for f in module_findings
        if f.span.start_line not in fault_lines
    )
    return ranks
