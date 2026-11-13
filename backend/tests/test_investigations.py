import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from samyak.api import app
from samyak.fixtures import fixture
from samyak.store import Store
from samyak.worker import process_one
from samyak.runner import DockerRunner


@pytest.fixture
def client(tmp_path, monkeypatch):
    if not DockerRunner().available():
        pytest.skip("Docker integration requires the fixed runner")
    monkeypatch.setenv("SAMYAK_DATA", str(tmp_path))
    return TestClient(app)


def complete(client, response):
    assert response.status_code == 202, response.text
    assert process_one(Store())
    job = client.get("/v1/analyses/" + response.json()["id"]).json()
    assert job["status"] == "COMPLETED", job
    return client.get("/v1/analyses/" + job["id"] + "/report").json()


def submit(client, name):
    return complete(client, client.post("/v1/analyses", json=fixture(name)))


def action(client, report, name, **extra):
    return complete(
        client, client.post(f"/v1/analyses/{report['job_id']}/investigate", json={"action": name, **extra})
    )


def test_actual_witness_replay_and_immutable_contract_decision(client):
    original = submit(client, "average")
    witness = action(client, original, "witness")
    proof = witness["intelligence"]["witness"]
    assert proof["status"] == "REPRODUCED" and proof["minimal_args"] == [[]]
    assert proof["repeatable"] and proof["result"]["status"] == "ERROR"
    assert proof["domain"] == "UNCONFIRMED"
    replay = action(client, witness, "replay", test_id=original["tests"][0]["id"])
    assert replay["intelligence"]["replay"]["status"] == "MATCH"
    decision = complete(
        client,
        client.post(
            f"/v1/analyses/{replay['job_id']}/contracts/decision",
            json={"test_id": original["tests"][0]["id"], "expected": 0, "reviewer": "judge"},
        ),
    )
    assert decision["verdict"] == "INCONCLUSIVE_NO_OUTPUT_ORACLE"
    assert decision["intelligence"]["contract_decisions"][0]["decision"] == "REJECT_EXPECTATION"
    assert not any(t["tier"] == "A" for t in decision["tests"])
    assert client.get(f"/v1/analyses/{original['job_id']}/report").json() == original


def test_semantic_witness_uses_an_independently_trusted_case(client):
    original = submit(client, "binary_search")
    report = action(client, original, "witness")
    proof = report["intelligence"]["witness"]
    assert proof["status"] == "REPRODUCED" and proof["test"]["tier"] == "A"
    assert proof["result"]["status"] == "FAIL"
    assert proof["minimal_args"] == [[7], 7]
    first = client.get(f"/v1/analyses/{report['job_id']}/bundle").content
    assert first == client.get(f"/v1/analyses/{report['job_id']}/bundle").content
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert any(p.startswith("licenses/") for p in archive.namelist())


def test_retrieval_ablation_and_full_ledger_replay(client):
    base = submit(client, "binary_search")
    report = action(client, base, "precedents")
    comparison = report["intelligence"]["precedents"]["comparison"]
    assert comparison["status"] == "MEASURED_ON_THIS_SUBMISSION"
    assert comparison["distinct_executed_candidates"] > 0
    assert comparison["arms"]["with_retrieval"]["validated_candidates"] > 0
    assert comparison["arms"]["without_retrieval"]["validated_candidates"] > 0
    verified = action(client, report, "ledger")
    proof = verified["intelligence"]["ledger"]["verification"]
    assert proof["status"] == "REPLAY_VERIFIED"
    assert all(r["match"] for r in proof["replays"])


def test_twin_runs_real_analysis_and_repair(client):
    base = submit(client, "binary_search")
    twin = action(client, base, "twin")["intelligence"]["twin"]
    assert twin["status"] == "MEASURED"
    assert twin["risk_delta"] == 0
    assert twin["twin_verdict"] == "VALIDATED_ON_TESTS"
    assert twin["execution_results"] and twin["candidate_evidence"]
    assert twin["source"] != base["source"]


def test_sorting_shield_discovers_actual_property_violation(client):
    response = client.post("/v1/analyses", json={"source": "def normalize(nums):\n    return nums\n"})
    base = complete(client, response)
    unsupported = action(client, base, "metamorphic")
    assert unsupported["intelligence"]["metamorphic"]["status"] == "NOT_SUPPORTED"
    declared = complete(
        client,
        client.post(
            f"/v1/analyses/{base['job_id']}/contracts/property",
            json={"function": "normalize", "reviewer": "judge"},
        ),
    )
    measured = action(client, declared, "metamorphic")["intelligence"]["metamorphic"]
    assert measured["status"] == "MEASURED" and measured["violations"] > 0
    assert any(r["relation"] == "permutation_and_multiset" and r["violated"] for r in measured["relations"])
    assert any(r["relation"] == "idempotence" for r in measured["relations"])
    assert all(r["test"]["tier"] == "B" for r in measured["relations"])
