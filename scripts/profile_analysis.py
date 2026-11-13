"""Real isolated fixture profiling; no submitted source is executed on the host."""

import argparse
import json
import os
import time
from pathlib import Path
from samyak.fixtures import fixture
from samyak.runner import DockerRunner
from samyak.store import Store, digest
from samyak.worker import process_one


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    args = parser.parse_args()
    root = Path("var/performance") / args.label
    os.environ["SAMYAK_DATA"] = str(root.resolve())
    store = Store()
    original_run, original_available = DockerRunner.run, DockerRunner.available
    counters = {}

    def run(self, source, tests):
        counters["suite_calls"] += bool(tests)
        counters["executed_cases_requested"] += len(tests)
        return original_run(self, source, tests)

    def available(self):
        counters["availability_calls"] += 1
        return original_available(self)

    import subprocess

    popen = subprocess.Popen

    def launch(command, *a, **kw):
        if command[:2] == ["docker", "run"]:
            counters["docker_invocations"] += 1
        if command[:3] == ["docker", "image", "inspect"]:
            counters["image_inspections"] += 1
        return popen(command, *a, **kw)

    DockerRunner.run, DockerRunner.available, subprocess.Popen = run, available, launch
    observations = []
    for name in ["binary_search", "caller_regression", "ledger_reconciler"]:
        counters = dict.fromkeys(
            [
                "suite_calls",
                "executed_cases_requested",
                "availability_calls",
                "docker_invocations",
                "image_inspections",
            ],
            0,
        )
        request = fixture(name)
        started = time.perf_counter()
        job = store.submit({"analysis": request})
        assert process_one(store)
        report = store.report(job.id)
        if report is None:
            raise RuntimeError(store.job(job.id).error)
        events = store.events(job.id)
        from datetime import datetime

        stages = [
            {
                "stage": a["stage"],
                "seconds": (
                    datetime.fromisoformat(b["timestamp"]) - datetime.fromisoformat(a["timestamp"])
                ).total_seconds(),
            }
            for a, b in zip(events, events[1:])
        ]
        row = {
            "fixture": name,
            "job_id": job.id,
            "wall_seconds": time.perf_counter() - started,
            **counters,
            "stages": stages,
            "source_hash": report["source_hash"],
            "request_hash": digest(json.dumps(request, sort_keys=True)),
            "test_revision": report["test_revision"],
            "model_id": report["model"].get("model_id"),
            "runner_digest": report["runner"].get("digest"),
            "verdict": report["verdict"],
            "candidate_verdicts": {c["id"]: c["verdict"] for c in report["candidates"]},
            "observations": [
                (r["test_id"], r["status"], r["output"], r["error"]) for r in report["original_results"]
            ],
        }
        observations.append(row)
        (root / "measurements.json").write_text(json.dumps(observations, indent=2))
        print(
            json.dumps({k: v for k, v in row.items() if k not in {"observations", "candidate_verdicts"}}),
            flush=True,
        )


if __name__ == "__main__":
    main()
