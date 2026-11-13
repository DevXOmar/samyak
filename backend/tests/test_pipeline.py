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
