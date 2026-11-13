"""Side-effect-free structural extraction; never imports submitted modules."""

import ast
from collections import Counter
import io
import math
import symtable
import tokenize
import networkx as nx
from .contracts import Finding, FunctionInfo, Span

FEATURES = [
    "lines",
    "parameters",
    "branches",
    "loops",
    "comparisons",
    "calls",
    "subscripts",
    "divisors",
    "returns",
    "nesting",
    "complexity",
    "bool_ops",
    "handlers",
    "none_checks",
]
FAMILY_RULES = {
    "BOUNDARY_COMPARISON": {"LOOP_OFF_BY_ONE", "INDEX_BOUNDARY"},
    "CONDITION_NEGATION": {"BAD_CONDITION"},
    "GUARD_REMOVAL": {"EMPTY_COLLECTION", "DIV_ZERO"},
    "ARITHMETIC_OPERATOR": {"DIV_ZERO"},
    "INDEX_OFFSET": {"INDEX_BOUNDARY"},
    "RETURN_VALUE": {"INCONSISTENT_RETURN"},
}


def span(node):
    return Span(
        start_line=node.lineno,
        end_line=node.end_lineno or node.lineno,
        start_col=node.col_offset,
        end_col=node.end_col_offset or node.col_offset,
    )


def runtime_nodes(node):
    return list(ast.walk(ast.Module(body=node.body, type_ignores=[])))


def numeric(node):
    nodes = runtime_nodes(node)

    def count(types):
        return sum(isinstance(n, types) for n in nodes)

    def depth(n):
        children = list(ast.iter_child_nodes(n))
        return int(isinstance(n, (ast.If, ast.For, ast.While, ast.Try))) + max(
            (depth(c) for c in children), default=0
        )

    return dict(
        zip(
            FEATURES,
            [
                node.end_lineno - node.lineno + 1,
                len(node.args.args),
                count((ast.If, ast.IfExp)),
                count((ast.For, ast.While)),
                count(ast.Compare),
                count(ast.Call),
                count(ast.Subscript),
                sum(
                    isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod))
                    for n in nodes
                ),
                count(ast.Return),
                depth(node),
                1 + count((ast.If, ast.For, ast.While, ast.ExceptHandler)),
                count(ast.BoolOp),
                count(ast.ExceptHandler),
                sum(isinstance(n, ast.Constant) and n.value is None for n in nodes),
            ],
        )
    )


def analyze(source):
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    if len(nodes) > 12000:
        raise ValueError("AST node budget exceeded (12000)")
    scopes = symtable.symtable(source, "submission.py", "exec")
    toks = [
        {"type": tokenize.tok_name[t.type], "text": t.string, "start": list(t.start), "end": list(t.end)}
        for t in tokenize.generate_tokens(io.StringIO(source).readline)
    ]
    functions, findings = [], []
    graph = nx.MultiDiGraph()
    graph.add_node("module", kind="Module")
    funcs = [n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    known = {n.name for n in funcs}
    graph.add_nodes_from(
        (f"fn:{f.name}", {"kind": "Function", "name": f.name, **span(f).model_dump()}) for f in funcs
    )

    def finding(
        rule, node, fn, text, strength, family, qualification="Static hypothesis; behavior requires an oracle"
    ):
        findings.append(
            Finding(
                id=f"{rule}:{node.lineno}:{node.col_offset}",
                rule_id=rule,
                function=fn,
                span=span(node),
                explanation=text,
                strength=strength,
                family=family,
                qualification=qualification,
                severity="LOW" if rule == "MUTABLE_DEFAULT" else "MEDIUM",
            )
        )

    for fn in funcs:
        functions.append(
            FunctionInfo(
                name=fn.name, span=span(fn), source=ast.get_source_segment(source, fn), features=numeric(fn)
            )
        )
        graph.add_edge("module", f"fn:{fn.name}", kind="CONTAINS")
        statements = [
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.stmt)
            and n is not fn
            and not (
                isinstance(n, ast.Expr)
                and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)
            )
        ]
        ids = {id(n): f"stmt:{fn.name}:{n.lineno}:{n.col_offset}" for n in statements}
        for n in statements:
            graph.add_node(ids[id(n)], kind="Statement", ast_type=type(n).__name__, **span(n).model_dump())
            graph.add_edge(f"fn:{fn.name}", ids[id(n)], kind="CONTAINS")

        def block(body, successor=None, loop=None):
            next_id = successor
            for n in reversed(body):
                nid = ids.get(id(n))
                if not nid:
                    continue
                if isinstance(n, ast.If):
                    yes = block(n.body, next_id, loop)
                    no = block(n.orelse, next_id, loop)
                    for dest, kind in [(yes, "TRUE_BRANCH"), (no, "FALSE_BRANCH")]:
                        if dest:
                            graph.add_edge(nid, dest, kind=kind)
                elif isinstance(n, (ast.While, ast.For)):
                    body_id = block(n.body, nid, (nid, next_id))
                    if body_id:
                        graph.add_edge(nid, body_id, kind="TRUE_BRANCH")
                    exit_id = block(n.orelse, next_id, loop)
                    if exit_id:
                        graph.add_edge(nid, exit_id, kind="FALSE_BRANCH")
                elif isinstance(n, ast.Break) and loop and loop[1]:
                    graph.add_edge(nid, loop[1], kind="CONTROL_NEXT")
                elif isinstance(n, ast.Continue) and loop:
                    graph.add_edge(nid, loop[0], kind="CONTROL_NEXT")
                elif not isinstance(n, (ast.Return, ast.Raise)) and next_id:
                    graph.add_edge(nid, next_id, kind="CONTROL_NEXT")
                next_id = nid
            return next_id

        block(fn.body)
        definitions = {}
        for n in sorted(statements, key=lambda n: (n.lineno, n.col_offset)):
            nid = ids[id(n)]
            # Flow-insensitive lexical approximation; branch/alias uncertainty is explicit.
            for sub in ast.walk(n):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id in definitions:
                    graph.add_edge(
                        definitions[sub.id], nid, kind="DEF_USE", variable=sub.id, approximation="lexical"
                    )
            for sub in ast.walk(n):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    definitions[sub.id] = nid
        for n in runtime_nodes(fn):
            if isinstance(n, ast.Call):
                target = n.func.id if isinstance(n.func, ast.Name) else ast.unparse(n.func)
                cid = f"call:{fn.name}:{n.lineno}:{n.col_offset}"
                graph.add_node(
                    cid, kind="Call", target=target, resolved=target in known, **span(n).model_dump()
                )
                graph.add_edge(
                    f"fn:{fn.name}",
                    f"fn:{target}" if target in known else cid,
                    kind="CALLS",
                    resolved=target in known,
                    line=n.lineno,
                )
                if target in {"eval", "exec", "compile", "os.system", "subprocess.run", "subprocess.Popen"}:
                    finding(
                        "UNSAFE_EVAL_EXEC",
                        n,
                        fn.name,
                        f"Potential critical unsafe sink: {target}",
                        1.0,
                        "OTHER",
                        "Potential critical; untrusted reachability is not established. Execution is blocked.",
                    )
                if target in {"pickle.loads", "pickle.load", "marshal.loads", "yaml.load"}:
                    finding(
                        "DANGEROUS_DESERIALIZATION",
                        n,
                        fn.name,
                        f"Unsafe deserialization sink: {target}",
                        1.0,
                        "OTHER",
                        "Potential critical; data trust and reachability unconfirmed. Execution is blocked.",
                    )
                if target == "range" and any(isinstance(a, ast.BinOp) for a in n.args):
                    finding(
                        "LOOP_OFF_BY_ONE",
                        n,
                        fn.name,
                        "Arithmetic range endpoint may skip or exceed a boundary",
                        0.45,
                        "BOUNDARY_COMPARISON",
                    )
                if target in {"min", "max"}:
                    finding(
                        "EMPTY_COLLECTION",
                        n,
                        fn.name,
                        "Empty iterable requires a contract or explicit handling",
                        0.55,
                        "GUARD_REMOVAL",
                    )
            if (
                isinstance(n, ast.While)
                and isinstance(n.test, ast.Compare)
                and any(isinstance(o, (ast.Lt, ast.Gt)) for o in n.test.ops)
            ):
                finding(
                    "LOOP_OFF_BY_ONE",
                    n.test,
                    fn.name,
                    "Strict loop comparison may omit the final boundary",
                    0.8,
                    "BOUNDARY_COMPARISON",
                )
            if isinstance(n, ast.Subscript):
                finding(
                    "INDEX_BOUNDARY",
                    n,
                    fn.name,
                    "Index access depends on bounds and collection non-emptiness",
                    0.5,
                    "INDEX_OFFSET",
                )
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                if not (
                    isinstance(n.right, ast.Constant)
                    and isinstance(n.right.value, (int, float))
                    and n.right.value != 0
                ):
                    finding(
                        "DIV_ZERO",
                        n,
                        fn.name,
                        "Divisor may be zero; establish its allowed domain",
                        0.85,
                        "ARITHMETIC_OPERATOR",
                    )
            if isinstance(n, ast.Compare):
                left = ast.dump(n.left)
                if any(ast.dump(r) == left for r in n.comparators):
                    finding(
                        "BAD_CONDITION",
                        n,
                        fn.name,
                        "Self-comparison may encode a mistaken condition (NaN is an exception)",
                        0.7,
                        "CONDITION_NEGATION",
                    )
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                param = next((a for a in fn.args.args if a.arg == n.value.id), None)
                if param and param.annotation and "None" in ast.unparse(param.annotation):
                    finding(
                        "NONE_DEREFERENCE",
                        n,
                        fn.name,
                        "Optional parameter is dereferenced; inspect path guards",
                        0.6,
                        "GUARD_REMOVAL",
                    )
        known_none = {a.arg for a in fn.args.args if a.annotation and "None" in ast.unparse(a.annotation)}
        for assignment in runtime_nodes(fn):
            if (
                isinstance(assignment, ast.Assign)
                and isinstance(assignment.value, ast.Constant)
                and assignment.value.value is None
            ):
                known_none.update(t.id for t in assignment.targets if isinstance(t, ast.Name))
        for operation in runtime_nodes(fn):
            operands = (
                [operation.left, operation.right]
                if isinstance(operation, ast.BinOp)
                else [operation.value]
                if isinstance(operation, ast.Subscript)
                else []
            )
            if any(
                isinstance(o, ast.Constant)
                and o.value is None
                or isinstance(o, ast.Name)
                and o.id in known_none
                for o in operands
            ):
                finding(
                    "NONE_OPERATION",
                    operation,
                    fn.name,
                    "An optional or statically None value participates in an operation; inspect path guards",
                    0.65,
                    "GUARD_REMOVAL",
                )
        returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
        types = {
            "None"
            if n.value is None or isinstance(n.value, ast.Constant) and n.value.value is None
            else type(n.value.value).__name__
            if isinstance(n.value, ast.Constant)
            else type(n.value).__name__
            for n in returns
        }
        if "None" in types and len(types) > 1:
            finding(
                "INCONSISTENT_RETURN",
                fn,
                fn.name,
                "Mixed bare and value returns; callers may rely on sentinel behavior",
                0.55,
                "RETURN_VALUE",
            )
        if returns and not isinstance(fn.body[-1], (ast.Return, ast.Raise)):
            finding(
                "INCONSISTENT_RETURN",
                fn,
                fn.name,
                "Possible implicit None return on an unproven path",
                0.35,
                "RETURN_VALUE",
            )
        for default in fn.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                finding(
                    "MUTABLE_DEFAULT", default, fn.name, "Mutable default persists across calls", 0.7, "OTHER"
                )
    structure = {
        "ast_counts": dict(Counter(type(n).__name__ for n in nodes)),
        "tokens": toks,
        "symbols": [
            {"scope": child.get_name(), "names": list(child.get_identifiers())}
            for child in scopes.get_children()
        ],
        "graph": nx.node_link_data(graph, edges="edges"),
        "limits": [
            "CFG is intraprocedural; exception edges, nested scopes and dynamic dispatch are approximate",
            "DEF_USE is lexical and flow-insensitive; aliasing is unresolved",
        ],
    }
    return structure, functions, findings


def localize(structure, functions, findings, tests=(), results=(), ml=True, family=True):
    failed = [r for r in results if r.status in {"FAIL", "ERROR", "TIMEOUT"}]
    graph = nx.node_link_graph(structure["graph"], edges="edges").to_undirected()
    anchors = [
        n
        for n, attrs in graph.nodes(data=True)
        if attrs.get("start_line") in {line for r in failed for line in r.lines}
    ]
    ranks = []
    for node in structure["graph"]["nodes"]:
        if node["kind"] != "Statement":
            continue
        line = node["start_line"]
        fn = next((f for f in functions if f.span.start_line <= line <= f.span.end_line), None)
        if not fn:
            continue
        matched = [
            f for f in findings if f.span.start_line <= line <= f.span.end_line and f.function == fn.name
        ]
        rule = max((f.strength for f in matched), default=0)
        fc = sum(line in r.lines for r in failed)
        pc = sum(line in r.lines for r in results if r.status == "PASS")
        ochiai = fc / math.sqrt(len(failed) * (fc + pc)) if failed and fc + pc else None
        distances = []
        for anchor in anchors[:64]:
            try:
                distances.append(nx.shortest_path_length(graph, node["id"], anchor))
            except nx.NetworkXNoPath:
                pass
        proximity = 1 / (1 + min(distances)) if distances else 0
        risk = fn.risk if ml and fn.risk is not None else 0
        fam = (
            max((fn.family_distribution.get(f.family, 0) for f in matched), default=0) if ml and family else 0
        )
        signals = {
            "rule": rule,
            "model_risk": risk,
            "family_prior": fam,
            "graph_proximity": proximity,
            "ochiai": ochiai,
        }
        score = 0.4 * rule + 0.2 * risk + 0.15 * fam + 0.1 * proximity + 0.35 * (ochiai or 0)
        ranks.append(
            {
                "line": line,
                "function": fn.name,
                "span": {k: node[k] for k in ("start_line", "end_line", "start_col", "end_col")},
                "score": score,
                "signals": signals,
                "mode": "SPECTRA" if failed else "STATIC_ONLY",
            }
        )
    return sorted(ranks, key=lambda r: (-r["score"], r["line"]))
