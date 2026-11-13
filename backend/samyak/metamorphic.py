"""Contract-justified sort metamorphic checks; naming alone never enables them."""

from .contracts import TestCase
from .inference import identify


def shield(report, payload, runner, stage):
    contracts = payload["analysis"].get("property_contracts", {})
    if not contracts:
        report.intelligence["metamorphic"] = {
            "status": "NOT_SUPPORTED",
            "reason": "Declare a sorting contract explicitly; no property is inferred from a function name",
        }
        return
    bases = []
    seen = set()
    for test in report.tests:
        if (
            test.function in contracts
            and len(test.args) == 1
            and isinstance(test.args[0], list)
            and all(type(v) is int for v in test.args[0])
        ):
            key = (test.function, str(test.args))
            if key not in seen:
                seen.add(key)
                bases.append(test)
    bases = bases[:8]
    if not bases:
        report.intelligence["metamorphic"] = {
            "status": "NOT_SUPPORTED",
            "reason": "This bounded Shield supports one finite list[int] argument only",
        }
        return
    stage(
        "execution",
        "Metamorphic Shield: executing base lists, reversed permutations and output-as-input idempotence",
    )
    originals = runner.run(report.source, bases)
    transformations = []
    for test, result in zip(bases, originals):
        reverse = identify(
            TestCase(
                function=test.function,
                args=[list(reversed(test.args[0]))],
                tier="B",
                domain="CONFIRMED",
                property="sorted_multiset",
                origin="METAMORPHIC_PERMUTATION",
                reason="Explicit sorting contract: reversing a permutation preserves the sorted multiset",
            )
        )
        transformations.append(("permutation_and_multiset", test.id, reverse))
        if (
            result.status in {"PASS", "FAIL"}
            and isinstance(result.output, list)
            and all(type(v) is int for v in result.output)
        ):
            idem = identify(
                TestCase(
                    function=test.function,
                    args=[result.output],
                    expected=result.output,
                    has_expected=True,
                    tier="B",
                    domain="CONFIRMED",
                    property="sorted_multiset",
                    origin="METAMORPHIC_IDEMPOTENCE",
                    reason="Explicit sorting contract entails f(f(xs)) == f(xs), separately from multiset preservation",
                )
            )
            transformations.append(("idempotence", test.id, idem))
    results = runner.run(report.source, [t for _, _, t in transformations])
    rows = [
        {
            "relation": relation,
            "base_test_id": base,
            "test": test.model_dump(),
            "result": result.model_dump(),
            "violated": result.status in {"FAIL", "ERROR"},
        }
        for (relation, base, test), result in zip(transformations, results)
    ]
    report.intelligence["metamorphic"] = {
        "status": "MEASURED",
        "assumptions": [
            "User explicitly declares ascending sort preserving multiplicities",
            "Single finite list[int] input; pure function behavior",
        ],
        "base_results": [r.model_dump() for r in originals],
        "relations": rows,
        "violations": sum(r["violated"] for r in rows),
        "runner_digest": runner.manifest["digest"],
        "reason": "B-tier checks prove only these declared properties, not arbitrary semantic correctness",
    }
