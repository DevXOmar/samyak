"""Reproducible live Phase 2 circuit; every result is a queued API/runner computation."""

import json
from pathlib import Path
import httpx
from scripts.demo import wait

ROOT = Path(__file__).resolve().parents[1]


def main():
    observations = []
    dest = ROOT / "var"
    dest.mkdir(exist_ok=True)
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        capability = client.get("/v1/capabilities")
        capability.raise_for_status()
        if capability.json()["runner"]["status"] != "AVAILABLE" or capability.json()["worker"] != "READY":
            raise SystemExit("EXECUTION_UNAVAILABLE: start Docker, make runner and make dev")

        def record(label, response):
            response.raise_for_status()
            report = wait(client, response.json())
            snapshot = {
                "label": label,
                "job_id": report["job_id"],
                "parent_id": report["parent_id"],
                "verdict": report["verdict"],
                "source_hash": report["source_hash"],
                "model_id": report["model"].get("model_id"),
                "runner_digest": report["runner"].get("digest"),
                "experiment_status": {
                    k: v.get("status") for k, v in report["intelligence"].items() if isinstance(v, dict)
                },
            }
            observations.append(snapshot)
            (dest / f"phase2-{label}.zip").write_bytes(
                client.get(f"/v1/analyses/{report['job_id']}/bundle").content
            )
            print(json.dumps(snapshot), flush=True)
            return report

        def investigate(base, action, **extra):
            return record(
                action,
                client.post(f"/v1/analyses/{base['job_id']}/investigate", json={"action": action, **extra}),
            )

        cases = {}
        for name in ["binary_search", "average", "caller_regression", "unfamiliar"]:
            source = client.get(f"/v1/fixtures/{name}")
            source.raise_for_status()
            cases[name] = record(name, client.post("/v1/analyses", json=source.json()))
        assert cases["binary_search"]["verdict"] == "VALIDATED_ON_TESTS"
        assert cases["average"]["verdict"] == "INCONCLUSIVE_NO_OUTPUT_ORACLE"
        assert cases["unfamiliar"]["verdict"] == "INCONCLUSIVE_NO_OUTPUT_ORACLE"
        assert cases["unfamiliar"]["intelligence"]["novelty"]["abstain"]
        trap = cases["caller_regression"]
        assert trap["intelligence"]["blast_radius"]["caller_regressions"] > 0
        assert any(c["verdict"] == "REJECTED_REGRESSION" for c in trap["candidates"])
        witness = investigate(cases["binary_search"], "witness")
        assert witness["intelligence"]["witness"]["status"] == "REPRODUCED"
        replay = investigate(witness, "replay", test_id=witness["intelligence"]["witness"]["test"]["id"])
        assert replay["intelligence"]["replay"]["status"] == "MATCH"
        comparison = investigate(cases["binary_search"], "precedents")
        assert (
            comparison["intelligence"]["precedents"]["comparison"]["status"] == "MEASURED_ON_THIS_SUBMISSION"
        )
        twin = investigate(cases["binary_search"], "twin")
        assert twin["intelligence"]["twin"]["status"] == "MEASURED"
        ledger = investigate(cases["binary_search"], "ledger")
        assert ledger["intelligence"]["ledger"]["verification"]["status"] == "REPLAY_VERIFIED"
        average = cases["average"]
        exact = record(
            "exact-oracle",
            client.post(
                f"/v1/analyses/{average['job_id']}/contracts/confirm",
                json={
                    "function": "average",
                    "args": [[]],
                    "expected": 0,
                    "reviewer": "authored-phase2-demo-contract",
                },
            ),
        )
        assert exact["verdict"] == "VALIDATED_ON_TESTS"
        sorting = record(
            "explicit-sorting-contract",
            client.post(
                "/v1/analyses",
                json={
                    "source": "def normalize(nums):\n    return nums\n",
                    "property_contracts": {"normalize": "sorted_multiset"},
                },
            ),
        )
        shield = investigate(sorting, "metamorphic")
        assert shield["intelligence"]["metamorphic"]["violations"] > 0
    (dest / "phase2-demo-results.json").write_text(json.dumps(observations, indent=2))
    print(f"Verified {len(observations)} real jobs; evidence bundles in {dest}")


if __name__ == "__main__":
    main()
