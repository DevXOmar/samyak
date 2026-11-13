import ast
import itertools
import json
from hypothesis import given, settings, strategies as st, find, errors
from .contracts import TestCase
from .store import digest

SEED = 20261113


def strategy(kind):
    if kind == "list[int]":
        return st.lists(st.integers(-5, 5), max_size=5)
    if kind == "str":
        return st.text(alphabet="ab 01", max_size=5)
    if kind == "dict":
        return st.dictionaries(st.text(alphabet="ab", max_size=2), st.integers(-2, 2), max_size=3)
    if kind == "optional[int]":
        return st.one_of(st.none(), st.integers(-5, 5))
    if kind == "float":
        return st.floats(-5, 5, allow_nan=False, allow_infinity=False)
    return st.integers(-5, 5)


POOLS = {
    "list[int]": [[], [0], [1], [-1, 0, 1], [1, 1], [2, 1]],
    "str": ["", "a", " ", "0"],
    "dict": [{}, {"a": 1}],
    "optional[int]": [None, 0, 1, -1],
    "float": [0.0, 1.0, -1.0],
    "int": [0, 1, -1, 2],
}


def identify(test):
    test.id = digest(json.dumps(test.model_dump(exclude={"id"}), sort_keys=True))[:20]
    return test


def infer(source, supplied=(), property_contracts=None):
    tree = ast.parse(source)
    tests = [identify(t.model_copy(deep=True)) for t in supplied]
    info = []
    property_contracts = property_contracts or {}
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)][:6]:
        if fn.name in property_contracts and (
            len(fn.args.args) != 1
            or fn.args.posonlyargs
            or fn.args.vararg
            or fn.args.kwarg
            or fn.args.kwonlyargs
        ):
            info.append(
                {
                    "function": fn.name,
                    "unsupported": "NOT_SUPPORTED: sorting contracts require one positional finite list[int] parameter",
                }
            )
            continue
        if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or len(fn.args.args) > 4:
            info.append(
                {"function": fn.name, "unsupported": "Only up to four positional parameters supported"}
            )
            continue
        params, kinds, pools = [], [], []
        calls = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name
        ]
        for index, arg in enumerate(fn.args.args):
            annotation = ast.unparse(arg.annotation) if arg.annotation else ""
            kind, evidence = "int", "AST_OPERATIONS_NUMERIC_FALLBACK"
            if annotation:
                kind = (
                    "list[int]"
                    if "list" in annotation or "List" in annotation
                    else "str"
                    if "str" in annotation
                    else "float"
                    if "float" in annotation
                    else "optional[int]"
                    if "None" in annotation
                    else "int"
                )
                evidence = "ANNOTATION"
            literals = []
            for call in calls:
                if len(call.args) > index:
                    try:
                        literals.append(ast.literal_eval(call.args[index]))
                    except (ValueError, TypeError):
                        pass
            if not annotation and literals:
                value = literals[0]
                kind = (
                    "list[int]"
                    if isinstance(value, list)
                    else "str"
                    if isinstance(value, str)
                    else "dict"
                    if isinstance(value, dict)
                    else "int"
                )
                evidence = "STATIC_CALL_SITE"
            if not annotation and not literals:
                for node in ast.walk(fn):
                    if (
                        isinstance(node, ast.Subscript)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == arg.arg
                    ):
                        kind, evidence = "list[int]", "AST_SUBSCRIPT"
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id in {"len", "sum", "min", "max", "sorted"}
                        and any(isinstance(a, ast.Name) and a.id == arg.arg for a in node.args)
                    ):
                        kind, evidence = "list[int]", "AST_SIZED_ITERABLE"
                    if (
                        isinstance(node, ast.For)
                        and isinstance(node.iter, ast.Name)
                        and node.iter.id == arg.arg
                    ):
                        kind, evidence = "list[int]", "AST_ITERABLE"
                    if (
                        isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == arg.arg
                    ):
                        if node.attr in {"split", "strip", "lower", "upper"}:
                            kind, evidence = "str", "AST_STRING_OPERATION"
                        if node.attr == "get":
                            kind, evidence = "dict", "AST_MAPPING_OPERATION"
            if fn.name in property_contracts and len(fn.args.args) == 1:
                kind, evidence = "list[int]", "EXPLICIT_PROPERTY_CONTRACT"
            params.append(
                {
                    "name": arg.arg,
                    "candidate_type": kind,
                    "evidence_source": evidence,
                    "domain": "UNCONFIRMED",
                    "reason": "Type evidence does not establish valid values or semantic preconditions",
                    "strategy": str(strategy(kind)),
                }
            )
            kinds.append(kind)
            pools.append(literals + POOLS[kind])
        info.append({"function": fn.name, "parameters": params, "trial_status": "PENDING_SANDBOX"})
        combos = list(itertools.islice(itertools.product(*pools), 7)) if pools else [()]
        # Include aligned boundaries as well as Cartesian cases under a fixed budget.
        combos += [tuple(pool[i % len(pool)] for pool in pools) for i in range(3)] if pools else []
        examples = []

        @settings(max_examples=4, derandomize=True, database=None, deadline=None)
        @given(st.tuples(*(strategy(k) for k in kinds)))
        def collect(args):
            examples.append(args)

        collect()
        combos += examples
        for args in combos:
            prop = property_contracts.get(fn.name)
            t = TestCase(
                function=fn.name,
                args=list(args),
                property=prop,
                tier="B" if prop else "C",
                domain="CONFIRMED" if prop else "UNCONFIRMED",
                origin="EXPLICIT_PROPERTY_CONTRACT" if prop else "HYPOTHESIS_BOUNDARY",
                reason="User declares sorting contract: ascending output preserving input multiplicities"
                if prop
                else "Candidate boundary/negative/edge input; domain unconfirmed",
                strategy="tuples(" + ", ".join(str(strategy(k)) for k in kinds) + ")",
            )
            tests.append(identify(t))
    # Exact literal assertions supplied in the source become authored, tuple-scoped A oracles.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assert)
            and isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.Eq)
        ):
            call = node.test.left
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                try:
                    args = [ast.literal_eval(a) for a in call.args]
                    expected = ast.literal_eval(node.test.comparators[0])
                    tests.append(
                        identify(
                            TestCase(
                                function=call.func.id,
                                args=args,
                                expected=expected,
                                has_expected=True,
                                tier="A",
                                domain="CONFIRMED",
                                origin="USER_SOURCE_ASSERT",
                                reason=f"Authored source assertion at line {node.lineno}",
                            )
                        )
                    )
                except (ValueError, TypeError):
                    pass
    unique = {}
    for t in tests:
        unique[t.id] = t
    return info, list(unique.values())[:64]


def shrink_fault(source, tests, results, runner, max_attempts=10):
    """Hypothesis searches/shrinks one reproducible exception, exclusively via Docker."""
    target = next(
        (
            (t, r)
            for t, r in zip(tests, results)
            if r.status == "ERROR" and r.error and not r.error.startswith("TypeError")
        ),
        None,
    )
    if not target:
        return None
    test, observed = target
    # Already minimal common boundaries do not need more containers.
    if test.args in ([[]], [0], [None]):
        return {
            "test_id": test.id,
            "minimal_args": test.args,
            "method": "bounded boundary minimum",
            "replayed": bool(observed.repeatable),
            "domain": test.domain,
            "error": observed.error,
        }
    kinds = [
        "list[int]" if isinstance(a, list) else "str" if isinstance(a, str) else "int" for a in test.args
    ]
    attempts = 0
    cache = {json.dumps(test.args, sort_keys=True): (True, observed)}

    def predicate(args):
        nonlocal attempts
        key = json.dumps(args, sort_keys=True)
        if key in cache:
            return cache[key][0]
        if attempts >= max_attempts:
            cache[key] = (False, None)
            return False
        attempts += 1
        probe = test.model_copy(
            update={
                "args": list(args),
                "has_expected": False,
                "property": None,
                "tier": "C",
                "domain": "UNCONFIRMED",
            }
        )
        result = runner.run(source, [probe])[0]
        matched = bool(
            result.status == "ERROR"
            and result.error
            and result.error.split(":")[0] == observed.error.split(":")[0]
        )
        cache[key] = (matched, result)
        return matched

    def weight(value):
        if isinstance(value, list):
            return 1 + sum(weight(v) for v in value)
        if isinstance(value, (int, float)):
            return 1 + len(str(value)) + int(value != 0)
        return 1 + len(json.dumps(value))

    # Start from the actual failure. Never replace it with a larger generated witness.
    best = json.loads(json.dumps(test.args))
    for index in range(len(best)):
        changed = True
        while changed and attempts < max_attempts:
            changed = False
            value = best[index]
            variants = []
            if isinstance(value, (list, str)) and value:
                middle = max(1, len(value) // 2)
                variants = [value[:middle], value[middle:]]
                variants += [value[:i] + value[i + 1 :] for i in range(min(4, len(value)))]
                if isinstance(value, list) and all(type(v) in {int, float} for v in value):
                    variants.append([0 for _ in value])
            elif isinstance(value, (int, float)):
                variants = [0, 1 if value > 0 else -1]
            for variant in variants:
                candidate = list(best)
                candidate[index] = variant
                if weight(candidate) < weight(best) and predicate(candidate):
                    best, changed = candidate, True
                    break
                if attempts >= max_attempts:
                    break
    reason = None
    if attempts < max_attempts:
        try:
            found = list(
                find(
                    st.tuples(*(strategy(k) for k in kinds)),
                    predicate,
                    settings=settings(
                        max_examples=max_attempts, derandomize=True, database=None, deadline=None
                    ),
                )
            )
            if weight(found) < weight(best):
                best = found
        except errors.HypothesisException as exc:
            reason = type(exc).__name__
    result = cache[json.dumps(best, sort_keys=True)][1]
    return {
        "test_id": test.id,
        "original_args": test.args,
        "minimal_args": best,
        "method": "Bounded delta debugging + Hypothesis.find",
        "attempts": attempts,
        "domain": test.domain if best == test.args else "UNCONFIRMED",
        "observation": result.model_dump(),
        "input_weight_before": weight(test.args),
        "input_weight_after": weight(best),
        "search_limit": max_attempts,
        "search_note": reason,
        "note": "Best reproduced witness within the probe budget, not a global minimum or a transferred output/domain oracle",
    }
