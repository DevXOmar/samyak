"""Script acceptance uses the production API, worker and restricted Docker image."""

import json
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from samyak.api import app
from samyak.contracts import AnalysisRequest
from samyak.ml import ModelService
from samyak.runner import DockerRunner
from samyak.scripts import module_facts, execute_script
from samyak.store import Store, digest
from samyak.worker import process_one


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAMYAK_DATA", str(tmp_path))
    return TestClient(app)


def submit(client, source, **kwargs):
    job = client.post("/v1/analyses", json={"source": source, **kwargs})
    assert job.status_code == 202, job.text
    ident = job.json()["id"]
    assert process_one(Store())
    assert client.get(f"/v1/analyses/{ident}").json()["status"] == "COMPLETED"
    report = client.get(f"/v1/analyses/{ident}/report").json()
    assert "event: done" in client.get(f"/v1/analyses/{ident}/events").text
    return report


@pytest.fixture
def isolated():
    if not DockerRunner().available():
        pytest.skip("Script execution requires the restricted Docker image: make runner")


@pytest.mark.parametrize(
    "source,stdin,stdout",
    [
        ('print("hello")', "", "hello\n"),
        ("for i in range(3):\n    print(i)", "", "0\n1\n2\n"),
        ('print("Hello, " + input("Name: "))', "Samyak\n", "Name: Hello, Samyak\n"),
        ('if __name__ == "__main__":\n    print("main")', "", "main\n"),
        (
            'import math\ndef greeting():\n    print(math.sqrt(4))\nif __name__ == "__main__":\n    greeting()',
            "",
            "2.0\n",
        ),
    ],
)
def test_script_output_and_main_guard(client, isolated, source, stdin, stdout):
    report = submit(client, source, mode="SCRIPT", stdin=stdin)
    result = report["script_result"]
    assert report["verdict"] == result["status"] == "EXECUTED_SUCCESSFULLY"
    assert result["stdout"] == stdout and result["stderr"] == "" and result["exit_code"] == 0
    assert result["duration_ms"] >= 0 and result["lines"]
    assert not report["candidates"]
    assert report["outputs"]["M7_VALIDATION"]["status"] == "NOT_APPLICABLE"
    if not report["functions"]:
        assert report["overall_risk"] is None
        assert report["model"]["applicability"] == "NOT_APPLICABLE_SCRIPT_ONLY"
        assert report["outputs"]["M2_DEFECT_PREDICTION"]["status"] == "NOT_APPLICABLE"
    if source.startswith("import"):
        assert 1 not in result["lines"] and 2 not in result["lines"]
    archive = zipfile.ZipFile(io.BytesIO(client.get(f"/v1/analyses/{report['job_id']}/bundle").content))
    assert json.loads(archive.read("request.json"))["analysis"]["stdin"] == stdin
    assert json.loads(archive.read("report.json"))["script_result"] == result


@pytest.mark.parametrize(
    "source,error,line",
    [
        ('helloworld("Print")', "NameError", 1),
        ("x = 0\nprint(1 / x)", "ZeroDivisionError", 2),
        ('printf("hello")', "NameError", 1),
    ],
)
def test_analyze_without_functions_observes_fault_without_oracle(client, isolated, source, error, line):
    report = submit(client, source)
    result = report["script_result"]
    assert result["status"] == "ERROR" and result["exit_code"] == 1
    assert error in result["error"] and error in result["traceback"]
    assert result["fault_lines"] == [line]
    assert any(
        f["span"]["start_line"] == line and f["evidence"] == "OBSERVED_RUNTIME_FAULT"
        for f in report["findings"]
    )
    assert report["intelligence"]["execution"]["domain"] == "UNCONFIRMED"
    assert not report["candidates"] and not report["verdict"].startswith("VALIDATED")
    if "printf" in source:
        assert any("C library function" in text for text in report["limitations"])


def test_script_timeout_and_output_bounds(isolated):
    result, _ = execute_script('print("started")\nwhile True: pass', "")
    assert result.status == "TIMEOUT" and result.duration_ms > 0
    assert result.stdout == "started\n"
    result, _ = execute_script('print("a" * 20000)', "")
    assert result.status == "OUTPUT_LIMIT"


def test_script_fail_closed_and_no_host_side_effects(client, monkeypatch):
    monkeypatch.setattr(DockerRunner, "available", lambda _: False)
    report = submit(client, 'print("not on host")')
    assert report["script_result"]["status"] == "EXECUTION_UNAVAILABLE"
    assert report["script_result"]["stdout"] == ""
    assert report["verdict"] == "EXECUTION_UNAVAILABLE"
    for source in ['open("/tmp/no", "w")', 'import os\nos.system("echo no")', 'eval("1")']:
        result, _ = execute_script(source, "")
        assert result.status == "REJECTED_SECURITY"
    with pytest.raises(ValueError):
        AnalysisRequest(source="pass", stdin="x" * 8001)


def test_static_module_graph_rules_never_import_or_execute():
    source = "import math\ndef untouched():\n    return 1 / 0\nx = 0\nif x == x:\n    print(1 / x)\n"
    facts, findings = module_facts(source)
    assert facts["statement_count"] == 3
    assert {f.rule_id for f in findings} == {"BAD_CONDITION", "DIV_ZERO"}
    assert all(f.function == "<module>" and f.evidence == "HYPOTHESIS" for f in findings)
    assert any(e["kind"] == "DEF_USE" and e["variable"] == "x" for e in facts["edges"])
    assert any(e["kind"] == "TRUE_BRANCH" for e in facts["edges"])
    assert not any(n.get("start_line") in {1, 2, 3} for n in facts["nodes"])


def test_script_observation_does_not_change_models_and_rerun_is_immutable(client, isolated):
    before = digest(json.dumps(ModelService().meta, sort_keys=True))
    old = submit(client, "print(input())", stdin="one\n")
    rerun = client.post(f"/v1/analyses/{old['job_id']}/tests", json={})
    assert rerun.status_code == 202
    assert process_one(Store())
    new = client.get(f"/v1/analyses/{rerun.json()['id']}/report").json()
    assert new["parent_id"] == old["job_id"] and new["script_result"]["stdout"] == "one\n"
    assert client.get(f"/v1/analyses/{old['job_id']}/report").json() == old
    assert digest(json.dumps(ModelService().meta, sort_keys=True)) == before


def test_script_container_boundary_matches_function_boundary(isolated, monkeypatch):
    from samyak.contracts import TestCase

    monkeypatch.setenv("SAMYAK_TEST_SECRET", "must-not-enter-container")
    # Deliberately bypass source allowlist to verify the Docker boundary itself.
    source = """import os, socket, json
checks = {"nonroot": os.getuid() == 10001, "secret_absent": "SAMYAK_TEST_SECRET" not in os.environ,
          "socket_absent": not os.path.exists("/var/run/docker.sock")}
try:
    open("/root-write-test", "w").write("no")
    checks["readonly"] = False
except OSError:
    checks["readonly"] = True
try:
    socket.create_connection(("1.1.1.1", 53), timeout=.1)
    checks["network_off"] = False
except OSError:
    checks["network_off"] = True
print(json.dumps(checks))"""
    result = DockerRunner().run(source, [TestCase(id="script", function="__script__", mode="SCRIPT")])[0]
    assert result.status == "EXECUTED_SUCCESSFULLY" and all(json.loads(result.stdout).values())


def test_script_stderr_and_exit_status(isolated):
    from samyak.contracts import TestCase

    # Trusted harness integration probes; public source policy still rejects sys.
    result = DockerRunner().run(
        'import sys\nprint("detail", file=sys.stderr)\nraise SystemExit(3)',
        [TestCase(id="script", function="__script__", mode="SCRIPT")],
    )[0]
    assert result.status == "ERROR" and result.exit_code == 3
    assert result.stderr == "detail\n" and result.fault_lines == [3]
    assert "SystemExit: 3" in result.traceback


def test_analyzed_main_script_keeps_runtime_localization_and_function_models(client, isolated):
    report = submit(client, 'def greet():\n    return 7\nif __name__ == "__main__":\n    missing()')
    assert report["script_result"]["status"] == "ERROR"
    assert report["functions"][0]["risk"] is not None
    assert any(f["id"] == "script-runtime:4" for f in report["findings"])
    assert any(r["line"] == 4 and r["mode"] == "OBSERVED_RUNTIME_FAULT" for r in report["localization"])
    assert not report["verdict"].startswith("VALIDATED")
