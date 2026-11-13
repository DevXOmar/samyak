"""Queued, immutable investigation actions; all program executions go through DockerRunner."""

import json
from .contracts import TestCase, Report
from .inference import identify, shrink_fault
from .runner import DockerRunner
from .repair import safety

ACTIONS = ["replay", "witness", "precedents", "ledger", "twin", "metamorphic"]


def signature(result):
    return result.status, result.output, result.error


def witnessed_case(report, runner):
    failing = [
        (t, r)
        for t, r in zip(report.tests, report.original_results)
        if r.status in {"FAIL", "ERROR"} and r.repeatable is not False
    ]
    if not failing:
        return {"status": "NOT_SUPPORTED", "reason": "No reproduced failure exists in the recorded suite"}
    # The smallest already-authoritative case needs no guessed expected output.
    failing.sort(key=lambda pair: (len(json.dumps(pair[0].args)), pair[0].id))
    smallest, prior = failing[0]
    largest, _ = max(failing, key=lambda pair: len(json.dumps(pair[0].args)))
    original_replay = runner.run(report.source, [smallest])[0]
    if signature(original_replay) != signature(prior):
        return {
            "status": "INCONCLUSIVE_REPLAY",
            "reason": "Recorded failure did not reproduce under the current runner",
            "result": original_replay.model_dump(),
        }
    if prior.status == "ERROR":
        shrunk = shrink_fault(report.source, [smallest], [original_replay], runner)
        args = shrunk["minimal_args"] if shrunk else smallest.args
        probe = identify(
            TestCase(
                function=smallest.function,
                args=args,
                kwargs=smallest.kwargs,
                tier="C",
                domain="UNCONFIRMED",
                origin="SHRUNK_RUNTIME_OBSERVATION",
                minimized_from=smallest.id,
            )
        )
        replay = runner.run(report.source, [probe])[0]
        replay2 = runner.run(report.source, [probe])[0]
        repeatable = signature(replay) == signature(replay2) and replay.status == "ERROR"
        return {
            "status": "REPRODUCED" if repeatable else "INCONCLUSIVE_REPLAY",
            "original_args": largest.args,
            "minimal_args": args,
            "test": probe.model_dump(),
            "parent_test_id": smallest.id,
            "result": replay.model_dump(),
            "repeatable": repeatable,
            "failure_signature": replay.error,
            "reached_lines": replay.lines,
            "method": shrunk["method"] if shrunk else "recorded witness",
            "domain": "UNCONFIRMED",
            "reason": "Exception shrinking does not establish the new input's contract or expected output",
        }
    largest_result = runner.run(report.source, [largest])[0]
    return {
        "status": "REPRODUCED",
        "original_args": largest.args,
        "minimal_args": smallest.args,
        "test": smallest.model_dump(),
        "parent_test_id": smallest.id,
        "result": original_replay.model_dump(),
        "original_result": largest_result.model_dump(),
        "repeatable": True,
        "failure_signature": "TRUSTED_OUTPUT_MISMATCH",
        "reached_lines": original_replay.lines,
        "domain": smallest.domain,
        "method": "Smallest independently oracle-backed failing case in the frozen suite",
        "reason": "Semantic shrinking beyond exact authored cases is NOT_SUPPORTED without a broader declared reference",
    }


def run_investigation(ident, payload, previous, stage):
    report = Report.model_validate(previous).model_copy(deep=True)
    report.job_id = ident
    report.parent_id = previous["job_id"]
    action = payload["investigation"]["action"]
    runner = DockerRunner()
    blocked, reason = safety(report.source)
    stage("investigation", f"Running {action} against immutable source {report.source_hash[:12]}")
    if blocked or not runner.available():
        report.intelligence[action if action != "witness" else "witness"] = {
            "status": "NOT_SUPPORTED" if blocked else "EXECUTION_UNAVAILABLE",
            "reason": reason or "Docker runner/image unavailable; no host execution fallback",
        }
        return report
    report.runner = runner.manifest
    if action == "replay":
        test = next((t for t in report.tests if t.id == payload["investigation"].get("test_id")), None)
        saved_witness = report.intelligence.get("witness", {})
        if test is None and saved_witness.get("test", {}).get("id") == payload["investigation"].get(
            "test_id"
        ):
            test = TestCase.model_validate(saved_witness["test"])
            old = saved_witness.get("result")
        else:
            old = next(
                (r.model_dump() for r in report.original_results if test and r.test_id == test.id), None
            )
        if test is None or old is None:
            report.intelligence["replay"] = {
                "status": "NOT_SUPPORTED",
                "reason": "Select a recorded test or minimized witness to replay",
            }
        else:
            from .contracts import Execution

            stage("execution", f"Replaying exact {test.function} input in restricted Docker")
            result = runner.run(report.source, [test])[0]
            report.intelligence["replay"] = {
                "status": "MATCH"
                if signature(result) == signature(Execution.model_validate(old))
                else "MISMATCH",
                "test": test.model_dump(),
                "result": result.model_dump(),
                "runner_digest": runner.manifest["digest"],
            }

    elif action == "witness":
        stage("execution", "Reproducing and minimizing actual failures; oracle/domain scope is preserved")
        report.intelligence["witness"] = witnessed_case(report, runner)
    else:
        # Registered extensions below dispatch independently; unsupported eligibility remains explicit.
        from .experiments import run_experiment

        run_experiment(action, report, payload, runner, stage)
    stage("evidence", f"Persisting independent {action} artifact in a new report revision")
    return report
