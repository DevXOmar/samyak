"""Within-job retrieval ablation: two eligible candidate orders, identical frozen suite."""

from .repair import candidates, validate


def compare_precedents(report, payload, runner, stage):
    stage("execution", "Freezing a fresh original baseline for both retrieval arms")
    original = runner.run(report.source, report.tests)
    if any(r.status in {"EXECUTION_UNAVAILABLE", "SANDBOX_ERROR"} for r in original):
        report.intelligence["precedents"]["comparison"] = {
            "status": "EXECUTION_UNAVAILABLE",
            "reason": "Cannot establish an executable baseline",
        }
        return
    cache, arms = {}, {}
    for arm, neighbors in [("without_retrieval", []), ("with_retrieval", report.precedents)]:
        pool, _ = candidates(
            report.source, report.structure, report.findings, report.tests, original, neighbors
        )
        rows = []
        for candidate in pool:
            if candidate.id not in cache:
                stage("validation", f"Retrieval ablation: validating distinct candidate {candidate.id[:8]}")
                cache[candidate.id] = validate(candidate, report.source, report.tests, original, runner)
            evidence = cache[candidate.id]
            rows.append(
                {
                    "candidate_id": candidate.id,
                    "operator": candidate.operator,
                    "prior": candidate.prior,
                    "verdict": evidence.verdict,
                }
            )
        successful = [
            i + 1
            for i, r in enumerate(rows)
            if r["verdict"] in {"VALIDATED_ON_TESTS", "VALIDATED_RUNTIME_FAULT_ONLY"}
        ]
        arms[arm] = {
            "ordered_candidates": rows,
            "first_valid_rank": min(successful) if successful else None,
            "validated_at_1": bool(successful and min(successful) == 1),
            "validated_at_3": bool(successful and min(successful) <= 3),
            "validated_candidates": len(successful),
            "budget": 6,
        }
    report.intelligence["precedents"]["comparison"] = {
        "status": "MEASURED_ON_THIS_SUBMISSION",
        "arms": arms,
        "distinct_executed_candidates": len(cache),
        "suite_hash": report.test_revision,
        "runner_digest": runner.manifest["digest"],
        "reason": "Within-job counterfactual ordering, not a held-out retrieval benchmark. Identical patches share exact-suite execution evidence.",
        "executions": {
            key: {
                "source_hash": value.source_hash,
                "results": [r.model_dump() for r in value.results],
                "checks": value.checks,
            }
            for key, value in cache.items()
        },
    }
