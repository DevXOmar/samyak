import json
import os
import shutil
import subprocess
import tempfile
import time
from uuid import uuid4
from .contracts import Execution


class DockerRunner:
    """Host orchestrator only. No submitted code executes in this interpreter."""

    def __init__(self):
        self.image = os.getenv("SAMYAK_RUNNER_IMAGE", "samyak-runner:phase1")
        # Docker Desktop's containerd store can list short tags but require canonical inspect names.
        if "/" not in self.image and not self.image.startswith("sha256:"):
            self.image = "docker.io/library/" + self.image
        self.manifest = {
            "status": "EXECUTION_UNAVAILABLE",
            "isolation": "Docker-only development-grade",
            "image": self.image,
            "digest": None,
            "network": "none",
            "user": "10001:10001",
        }

    def available(self):
        if not shutil.which("docker"):
            return False
        try:
            p = subprocess.run(
                ["docker", "image", "inspect", self.image, "--format", "{{.Id}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if p.returncode == 0 and p.stdout.strip().startswith("sha256:"):
                self.manifest.update(status="AVAILABLE", digest=p.stdout.strip())
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass
        return False

    def command(self, name):
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--network=none",
            "--read-only",
            "--user=10001:10001",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--cpus=1",
            "--memory=256m",
            "--memory-swap=256m",
            "--pids-limit=32",
            "--ulimit",
            "nofile=64:64",
            "--ulimit",
            "fsize=1048576:1048576",
            "--tmpfs",
            "/work:rw,noexec,nosuid,size=16m,uid=10001,gid=10001,mode=700",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=8m,uid=10001,gid=10001,mode=700",
            "--env",
            "PYTHONHASHSEED=0",
            "-i",
            self.manifest.get("digest") or self.image,
        ]

    def run(self, source, tests):
        if not tests:
            return []
        if not self.available():
            return [
                Execution(
                    test_id=t.id,
                    status="EXECUTION_UNAVAILABLE",
                    error="Pinned runner image or Docker daemon unavailable",
                )
                for t in tests
            ]
        name = "samyak-" + uuid4().hex
        # Expected outputs stay outside the untrusted container.
        payload = json.dumps(
            {
                "source": source,
                "tests": [
                    {"id": t.id, "function": t.function, "args": t.args, "kwargs": t.kwargs} for t in tests
                ],
            }
        ).encode()
        deadline = time.monotonic() + min(150, 10 + 4 * len(tests))
        try:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                proc = subprocess.Popen(
                    self.command(name), stdin=subprocess.PIPE, stdout=output, stderr=errors
                )
                proc.stdin.write(payload)
                proc.stdin.close()
                exceeded = False
                while proc.poll() is None:
                    if (
                        time.monotonic() > deadline
                        or os.fstat(output.fileno()).st_size > 1048576
                        or os.fstat(errors.fileno()).st_size > 1048576
                    ):
                        exceeded = True
                        subprocess.run(["docker", "kill", name], capture_output=True, timeout=10)
                        proc.kill()
                        break
                    time.sleep(0.05)
                proc.wait(timeout=10)
                if exceeded:
                    raise RuntimeError("Suite time/output limit exceeded")
                output.seek(0)
                values = json.loads(output.read(1048576))
                if len(values) != len(tests):
                    raise ValueError("Incomplete execution ledger")
                results = []
                for t, value in zip(tests, values):
                    allowed = {k: v for k, v in value.items() if k in Execution.model_fields}
                    allowed["test_id"] = t.id
                    r = Execution.model_validate(allowed)
                    if r.status == "OK":
                        r.status = "PASS" if passes(t, r.output) else "FAIL"
                        if r.repeatable is False:
                            r.status = "FLAKY"
                    elif r.status not in {
                        "ERROR",
                        "TIMEOUT",
                        "SANDBOX_ERROR",
                        "UNSUPPORTED_OUTPUT",
                        "OUTPUT_LIMIT",
                    }:
                        r.status = "SANDBOX_ERROR"
                    results.append(r)
                return results
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            return [Execution(test_id=t.id, status="SANDBOX_ERROR", error=str(exc)[:300]) for t in tests]
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)


def passes(test, output):
    if test.has_expected:
        return type(output) is type(test.expected) and output == test.expected
    if test.property == "sorted_multiset":
        try:
            return isinstance(output, list) and output == sorted(test.args[0])
        except (TypeError, IndexError):
            return False
    return True
