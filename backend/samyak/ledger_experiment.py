from .ledger import build_bundle, verify_bundle
from .store import Store
from .investigations import signature
from .contracts import Report


def verify_ledger(report, payload, runner, stage):
    base = Store().read(payload["base_report_hash"])
    digest = base["runner"].get("digest")
    if not digest or digest != runner.manifest["digest"]:
        report.intelligence["ledger"]["verification"] = {
            "status": "NOT_SUPPORTED",
            "reason": "Exact recorded runner image is required; current digest differs",
        }
        return
    request = {k: v for k, v in payload.items() if k not in {"investigation", "base_report_hash"}}
    blob = build_bundle(base, request, Store().events(base["job_id"]))
    integrity = verify_bundle(blob)
    original = Report.model_validate(base)
    suites = [("original", original.source, original.original_results)] + [
        (c.id, c.source, c.results) for c in original.candidates if c.results
    ]
    checks = []
    for label, source, recorded in suites:
        stage("execution", f"Ledger replay: {label} in the exact recorded image")
        observed = runner.run(source, original.tests)
        checks.append(
            {
                "revision": label,
                "match": len(observed) == len(recorded)
                and all(signature(a) == signature(b) for a, b in zip(observed, recorded)),
                "observed": [r.model_dump() for r in observed],
            }
        )
    report.intelligence["ledger"]["verification"] = {
        "status": "REPLAY_VERIFIED"
        if integrity["status"] == "INTEGRITY_VERIFIED" and all(c["match"] for c in checks)
        else "REPLAY_MISMATCH",
        "integrity": integrity,
        "replays": checks,
        "source_job_id": base["job_id"],
        "timing_equality_required": False,
    }
