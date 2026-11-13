import json
import joblib
import pytest
from samyak.ml import ModelService
from samyak.runner import DockerRunner
from samyak.store import digest, Store
from samyak.contracts import AnalysisRequest
from samyak.worker import process_one


def test_model_reuse_still_checks_hashes_and_invalidates(tmp_path, monkeypatch):
    artifact = tmp_path / "model.joblib"
    manifest = tmp_path / "manifest.json"

    def write(value):
        joblib.dump({"version": value}, artifact)
        manifest.write_text(
            json.dumps({"status": "TRAINED", "artifact_sha256": digest(artifact.read_bytes())})
        )

    write(1)
    original = joblib.load
    calls = []
    monkeypatch.setattr(joblib, "load", lambda path: (calls.append(path), original(path))[1])
    first = ModelService(tmp_path)
    second = ModelService(tmp_path)
    assert first.bundle is second.bundle and len(calls) == 1
    first.meta["status"] = "changed"
    assert second.meta["status"] == "TRAINED"
    write(2)
    third = ModelService(tmp_path)
    assert third.bundle["version"] == 2 and len(calls) == 2
    artifact.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        ModelService(tmp_path)


def test_runner_pins_verified_digest_only_for_its_lifetime(monkeypatch):
    import samyak.runner as module
    from types import SimpleNamespace

    monkeypatch.setattr(module.shutil, "which", lambda _: "/docker")
    calls = []
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *a, **k: (calls.append(a), SimpleNamespace(returncode=0, stdout="sha256:verified"))[1],
    )
    runner = DockerRunner()
    assert runner.available() and runner.available() and len(calls) == 1
    assert "sha256:verified" in runner.command("test")
    assert DockerRunner().available() and len(calls) == 2
    monkeypatch.setattr(module.shutil, "which", lambda _: None)
    assert not runner.available()


def test_initial_analysis_does_not_minimize_and_timings_are_persisted(tmp_path, monkeypatch):
    import samyak.inference as inference

    monkeypatch.setenv("SAMYAK_DATA", str(tmp_path))
    monkeypatch.setattr(DockerRunner, "available", lambda _: False)
    monkeypatch.setattr(
        inference, "shrink_fault", lambda *a, **k: pytest.fail("Initial analysis must not minimize")
    )
    store = Store()
    job = store.submit(
        {
            "analysis": AnalysisRequest(
                source="def average(nums):\n    return sum(nums)/len(nums)"
            ).model_dump()
        }
    )
    assert process_one(store)
    report = store.report(job.id)
    assert report["verdict"] == "EXECUTION_UNAVAILABLE"
    assert "minimal_witness" not in report["structure"]
    assert report["intelligence"]["witness"]["status"] == "NOT_RUN"
    timing = report["intelligence"]["timing"]
    assert timing["wall_seconds"] > 0 and all(s["seconds"] >= 0 for s in timing["stages"])
    assert timing["execution"].get("docker_invocations", 0) == 0


def test_reproduced_fault_defers_probes_until_explicit_action(tmp_path, monkeypatch):
    import samyak.inference as inference
    from samyak.pipeline import run_pipeline
    from samyak.contracts import Execution

    class ObservedRunner:
        manifest = {"status": "AVAILABLE", "digest": "test-only"}

        def available(self):
            return True

        def run(self, source, tests):
            return [
                Execution(
                    test_id=t.id,
                    status="ERROR",
                    error="ZeroDivisionError: division by zero",
                    fault_lines=[2],
                    lines=[2],
                    repeatable=True,
                )
                for t in tests
            ]

    import samyak.pipeline as pipeline

    monkeypatch.setattr(pipeline, "DockerRunner", ObservedRunner)
    monkeypatch.setattr(
        inference, "shrink_fault", lambda *a, **kw: pytest.fail("No eager shrinking permitted")
    )
    report = run_pipeline(
        "test",
        {
            "analysis": AnalysisRequest(
                source="def average(nums):\n    return sum(nums) / len(nums)"
            ).model_dump()
        },
        lambda *a: None,
    )
    assert any(r.status == "ERROR" and r.repeatable for r in report.original_results)
    assert "minimal_witness" not in report.structure and report.intelligence["witness"]["status"] == "NOT_RUN"
