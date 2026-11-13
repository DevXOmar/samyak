import shutil
import pytest
from samyak.runner import DockerRunner
from samyak.contracts import TestCase


def test_fail_closed(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    result = DockerRunner().run("def f(): return 1", [TestCase(function="f", id="x")])
    assert result[0].status == "EXECUTION_UNAVAILABLE"


def test_containment_command_has_no_mounts_or_secrets():
    command = DockerRunner().command("samyak-test")
    for flag in [
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=32",
        "--user=10001:10001",
        "--memory=256m",
    ]:
        assert flag in command
    assert not any("docker.sock" in arg for arg in command)
    assert "-v" not in command and "--mount" not in command


@pytest.fixture
def runner():
    runner = DockerRunner()
    if not runner.available():
        pytest.skip("Docker runner unavailable: containment integration requires make runner")
    return runner


def test_actual_containment(runner, monkeypatch):
    monkeypatch.setenv("SAMYAK_TEST_SECRET", "host-secret-must-not-enter-container")
    # Bypass application allowlist deliberately to test the actual container boundary.
    source = """def containment():
    import os, socket
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
    return checks
"""
    result = runner.run(source, [TestCase(id="containment", function="containment")])[0]
    assert result.status == "PASS"
    assert all(result.output.values())


def test_timeout_and_output_limit_do_not_pass(runner):
    result = runner.run("def hang():\n while True: pass\n", [TestCase(id="hang", function="hang")])[0]
    assert result.status in {"TIMEOUT", "SANDBOX_ERROR"}
    result = runner.run('def large():\n return "x" * 100000\n', [TestCase(id="large", function="large")])[0]
    assert result.status in {"OUTPUT_LIMIT", "SANDBOX_ERROR"}


def test_actual_counterexample_delta_reduction_never_enlarges_witness(runner):
    from samyak.inference import shrink_fault

    source = "def fail_when_long(nums):\n    if len(nums) >= 2:\n        return 1 / 0\n    return 0\n"
    case = TestCase(id="long", function="fail_when_long", args=[[9, 8, 7, 6, 5]])
    original = runner.run(source, [case])[0]
    assert original.status == "ERROR"
    proof = shrink_fault(source, [case], [original], runner)
    assert len(proof["minimal_args"][0]) == 2
    assert proof["input_weight_after"] < proof["input_weight_before"]
    assert proof["observation"]["status"] == "ERROR" and proof["attempts"] <= 10
