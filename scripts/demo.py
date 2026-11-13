"""Real source demos against the running API/worker. No canned report loading."""

import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]


def wait(client, job):
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        status = client.get(f"/v1/analyses/{job['id']}").json()
        if status["status"] == "FAILED":
            raise RuntimeError(status["error"])
        if status["status"] == "COMPLETED":
            return client.get(f"/v1/analyses/{job['id']}/report").json()
        time.sleep(0.3)
    raise RuntimeError("Demo worker deadline exceeded")


def main():
    results = []
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        for fixture in ["binary_search", "average", "caller_regression"]:
            source = client.get(f"/v1/fixtures/{fixture}").json()
            response = client.post("/v1/analyses", json=source)
            response.raise_for_status()
            start = time.perf_counter()
            report = wait(client, response.json())
            if report["runner"]["status"] != "AVAILABLE":
                raise SystemExit("EXECUTION_UNAVAILABLE: run make runner with Docker running")
            if fixture == "average":
                assert report["verdict"] == "INCONCLUSIVE_NO_OUTPUT_ORACLE", report["verdict"]
            else:
                assert report["verdict"] == "VALIDATED_ON_TESTS", report["verdict"]
            if fixture == "caller_regression":
                assert any(c["verdict"] == "REJECTED_REGRESSION" for c in report["candidates"])
            result = {
                "fixture": fixture,
                "job_id": report["job_id"],
                "verdict": report["verdict"],
                "seconds": round(time.perf_counter() - start, 3),
                "source_hash": report["source_hash"],
                "candidate_verdicts": [c["verdict"] for c in report["candidates"]],
            }
            results.append(result)
            print(json.dumps(result), flush=True)
            (ROOT / "var" / f"demo-{fixture}.zip").write_bytes(
                client.get(f"/v1/analyses/{report['job_id']}/bundle").content
            )
        original = next(r for r in results if r["fixture"] == "average")
        # The demo is an explicitly authored product contract, not a guessed mathematical identity.
        confirmation = client.post(
            f"/v1/analyses/{original['job_id']}/contracts/confirm",
            json={"function": "average", "args": [[]], "expected": 0, "reviewer": "authored-demo-contract"},
        )
        confirmation.raise_for_status()
        report = wait(client, confirmation.json())
        assert report["verdict"] == "VALIDATED_ON_TESTS"
        results.append(
            {
                "fixture": "average-confirmed-empty-returns-zero",
                "job_id": report["job_id"],
                "verdict": report["verdict"],
                "parent_id": report["parent_id"],
            }
        )
        print(json.dumps(results[-1]), flush=True)
    (ROOT / "var/demo-results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
