import io
import json
import zipfile
import pytest
from fastapi.testclient import TestClient
from samyak.api import app
from samyak.contracts import AnalysisRequest
from samyak.fixtures import fixture
from samyak.runner import DockerRunner
from samyak.store import Store
from samyak.worker import process_one


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAMYAK_DATA", str(tmp_path))
    return TestClient(app)


def require_runner():
    if not DockerRunner().available():
        pytest.skip("Isolated integration requires make runner")


def run(client, request):
    response = client.post("/v1/analyses", json=request)
    assert response.status_code == 202, response.text
    ident = response.json()["id"]
    assert process_one(Store())
    job = client.get(f"/v1/analyses/{ident}").json()
    assert job["status"] == "COMPLETED", job
    return client.get(f"/v1/analyses/{ident}/report").json()


def test_binary_repair_real_pipeline_and_bundle(client):
    require_runner()
    report = run(client, fixture("binary_search"))
    assert report["overall_risk"] is not None
    assert report["verdict"] == "VALIDATED_ON_TESTS"
    assert any(
        c["verdict"] == "VALIDATED_ON_TESTS" and "while left <= right" in c["source"]
        for c in report["candidates"]
    )
    assert len(report["outputs"]) == 8
    assert any(r["signals"]["ochiai"] is not None for r in report["localization"])
    bundle = client.get(f"/v1/analyses/{report['job_id']}/bundle")
    archive = zipfile.ZipFile(io.BytesIO(bundle.content))
    assert json.loads(archive.read("repair_manifest.json"))["source_hash"] == report["source_hash"]
    assert archive.read("original.py").decode() == report["source"]


def test_wrong_local_patch_rejected_by_caller(client):
    require_runner()
    report = run(client, fixture("caller_regression"))
    assert report["verdict"] == "VALIDATED_ON_TESTS"
    harmful = next(c for c in report["candidates"] if c["operator"] == "REPLACE_RETURN")
    assert harmful["verdict"] == "REJECTED_REGRESSION"
    assert any(check["regression"] for check in harmful["checks"])
    impact = report["intelligence"]["blast_radius"]["candidates"][harmful["id"]]
    assert "contains" in impact["affected_functions"] and impact["caller_regression_ids"]
    assert report["intelligence"]["risk_budget"]["candidates"][harmful["id"]]["band"] == "DO_NOT_RECOMMEND"
    assert report["intelligence"]["tournament"]["winner_id"]


def test_unknown_domain_then_exact_confirmation_is_new_revision(client):
    require_runner()
    report = run(client, fixture("average"))
    assert report["verdict"] == "INCONCLUSIVE_NO_OUTPUT_ORACLE"
    assert any(r["status"] == "ERROR" and r["repeatable"] for r in report["original_results"])
    assert all(c["verdict"] != "VALIDATED_ON_TESTS" for c in report["candidates"])
    confirmation = client.post(
        f"/v1/analyses/{report['job_id']}/contracts/confirm",
        json={"function": "average", "args": [[]], "expected": 0, "reviewer": "test-user"},
    )
    assert confirmation.status_code == 202
    assert process_one(Store())
    new = client.get(f"/v1/analyses/{confirmation.json()['id']}/report").json()
    assert new["parent_id"] == report["job_id"]
    assert new["verdict"] == "VALIDATED_ON_TESTS"
    assert new["test_revision"] != report["test_revision"]
    assert client.get(f"/v1/analyses/{report['job_id']}/report").json() == report


def test_unavailable_runner_and_invalid_source_report(client, monkeypatch):
    monkeypatch.setattr(DockerRunner, "available", lambda _: False)
    report = run(client, fixture("average"))
    assert report["verdict"] == "EXECUTION_UNAVAILABLE"
    assert all(r["status"] == "EXECUTION_UNAVAILABLE" for r in report["original_results"])
    invalid = run(client, AnalysisRequest(source="def :").model_dump())
    assert invalid["verdict"] == "REJECTED_SYNTAX"
    assert invalid["outputs"]["M2_DEFECT_PREDICTION"]["value"] is None


def test_queue_sse_and_unknown_job(client, monkeypatch):
    monkeypatch.setattr(DockerRunner, "available", lambda _: False)
    report = run(client, fixture("average"))
    stream = client.get(f"/v1/analyses/{report['job_id']}/events")
    assert "event: stage" in stream.text and "event: done" in stream.text
    assert "Parsing AST" in stream.text
    assert client.get("/v1/analyses/missing").status_code == 404


def test_exact_domain_confirmation_validates_only_runtime_fault(client):
    require_runner()
    report = run(client, fixture("average"))
    crashing = next(t for t in report["tests"] if t["args"] == [[]])
    response = client.post(
        f"/v1/analyses/{report['job_id']}/contracts/domain",
        json={"test_ids": [crashing["id"]], "reviewer": "domain-reviewer"},
    )
    assert response.status_code == 202
    assert process_one(Store())
    result = client.get(f"/v1/analyses/{response.json()['id']}/report").json()
    assert result["verdict"] == "VALIDATED_RUNTIME_FAULT_ONLY"
    assert not any(t["tier"] == "A" for t in result["tests"])
    accepted = next(t for t in result["tests"] if t["domain"] == "CONFIRMED")
    assert accepted["reviewer"] == "domain-reviewer" and accepted["confirmed_at"]


def test_capabilities_and_persisted_timeline(client, monkeypatch):
    monkeypatch.setattr(DockerRunner, "available", lambda _: False)
    readiness = client.get("/v1/capabilities").json()
    assert readiness["worker"] == "OFFLINE"
    assert readiness["runner"]["status"] == "EXECUTION_UNAVAILABLE"
    report = run(client, fixture("average"))
    events = client.get(f"/v1/analyses/{report['job_id']}/timeline").json()
    assert events and all(e["timestamp"] and e["job_id"] == report["job_id"] for e in events)
    assert events[-1]["stage"] == "completed"


def test_showcase_fixtures_are_safe_twin_eligible_and_oracles_match_intent():
    from samyak.repair import safety
    from samyak.twins import semantic_twin

    for name, failing in [("inventory_planner", 0), ("ledger_reconciler", 2)]:
        request = AnalysisRequest.model_validate(fixture(name))
        assert safety(request.source) == (None, None)
        assert semantic_twin(request.source)["status"] == "ELIGIBLE"
        namespace = {"__name__": "fixture"}
        exec(compile(request.source, name, "exec"), namespace)
        observed = [namespace[t.function](*t.args) for t in request.tests]
        mismatches = [
            t
            for t, out in zip(request.tests, observed)
            if not (type(out) is type(t.expected) and out == t.expected)
        ]
        assert len(mismatches) == failing, name
        assert all(t.function == "count_settled_by" for t in mismatches)


def test_correct_inventory_planner_admits_no_repair(client):
    require_runner()
    report = run(client, fixture("inventory_planner"))
    authored = {t["id"] for t in report["tests"] if t["tier"] == "A"}
    assert all(r["status"] == "PASS" for r in report["original_results"] if r["test_id"] in authored)
    assert report["script_result"]["status"] == "EXECUTED_SUCCESSFULLY"
    assert not any(c["verdict"].startswith("VALIDATED") for c in report["candidates"])
    harmful = next(c for c in report["candidates"] if c["operator"] == "REPLACE_RETURN")
    assert harmful["verdict"] == "REJECTED_REGRESSION"


def test_buggy_ledger_validates_boundary_fix_and_rejects_caller_trap(client):
    require_runner()
    report = run(client, fixture("ledger_reconciler"))
    assert report["verdict"] == "VALIDATED_ON_TESTS"
    assert any(
        c["verdict"] == "VALIDATED_ON_TESTS" and "timestamps[i] <= cutoff" in c["source"]
        for c in report["candidates"]
    )
    trap = next(c for c in report["candidates"] if c["operator"] == "REPLACE_RETURN")
    assert trap["verdict"] == "REJECTED_REGRESSION"
    impact = report["intelligence"]["blast_radius"]["candidates"][trap["id"]]
    assert "is_known_account" in impact["affected_functions"] and impact["caller_regression_ids"]
    assert report["script_result"]["status"] == "ERROR"
    assert "minimal_witness" not in report["structure"]
    assert report["intelligence"]["witness"]["status"] == "NOT_RUN"
