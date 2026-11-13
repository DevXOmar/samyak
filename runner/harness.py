import json
import os
import signal
import subprocess
import sys
import tempfile
import time

request = json.loads(sys.stdin.read(262144))
open("/work/submission.py", "w").write(request["source"])
results = []
for test in request["tests"]:
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        child = subprocess.Popen(
            [sys.executable, "-I", "/app/script_case.py" if test.get("mode") == "SCRIPT" else "/app/case.py"],
            stdin=subprocess.PIPE,
            stdout=out,
            stderr=err,
            env={"PATH": "/usr/local/bin:/usr/bin", "PYTHONHASHSEED": "0"},
            start_new_session=True,
        )
        started = time.perf_counter()
        try:
            child.communicate(json.dumps(test).encode(), timeout=3)
            if child.returncode == -signal.SIGXCPU:
                value = {"status": "TIMEOUT", "error": "1 second per-case CPU budget exceeded"}
            elif out.tell() > 65536 or err.tell() > 65536:
                value = {"status": "OUTPUT_LIMIT", "error": "Output limit exceeded"}
            else:
                out.seek(0)
                value = json.loads(out.read())
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            value = {"status": "TIMEOUT", "error": "3 second per-case wall limit"}
        except (ValueError, OSError):
            value = {"status": "SANDBOX_ERROR", "error": "Case process terminated or invalid output"}
        value.setdefault("exit_code", child.returncode)
        value.setdefault("duration_ms", (time.perf_counter() - started) * 1000)
        value["test_id"] = test["id"]
        results.append(value)
print(json.dumps(results, allow_nan=False))
