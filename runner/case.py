"""Runs only inside the restricted container; outputs observations, never verdicts."""

import contextlib
import io
import json
import resource
import statistics
import sys
import time
import traceback
import coverage

resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CPU, (1, 2))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
request = json.loads(sys.stdin.read(131072))
trace = coverage.Coverage(data_file=None, branch=True, include=["/work/submission.py"])
namespace = {"__name__": "submission", "__file__": "/work/submission.py"}
result = {"status": "OK", "output": None, "lines": [], "samples_ms": []}
stdout = io.StringIO()
try:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stdout):
        trace.start()
        exec(compile(open("/work/submission.py").read(), "/work/submission.py", "exec"), namespace)
        fn = namespace[request["function"]]
        output = fn(*request["args"], **request.get("kwargs", {}))
        trace.stop()
        result["output"] = output
        # Fresh JSON inputs per repeat prevent mutation of the workload across calls.
        observations = [json.dumps(output, sort_keys=True, allow_nan=False)]
        for _ in range(7):
            repeat = json.loads(json.dumps(request))
            start = time.perf_counter_ns()
            observed = fn(*repeat["args"], **repeat.get("kwargs", {}))
            result["samples_ms"].append((time.perf_counter_ns() - start) / 1e6)
            observations.append(json.dumps(observed, sort_keys=True, allow_nan=False))
        result["repeatable"] = len(set(observations)) == 1
        result["median_ms"] = statistics.median(result["samples_ms"])
        result["p95_ms"] = sorted(result["samples_ms"])[-1]
except BaseException as exc:
    trace.stop()
    result.update(status="ERROR", error=type(exc).__name__ + ": " + str(exc)[:500], repeatable=None)
    result["fault_lines"] = [
        f.lineno for f in traceback.extract_tb(exc.__traceback__) if f.filename == "/work/submission.py"
    ]
finally:
    result["lines"] = trace.get_data().lines("/work/submission.py") or []
    result["stdout"] = stdout.getvalue()[:2048]
try:
    print(json.dumps(result, allow_nan=False))
except (TypeError, ValueError):
    print(
        json.dumps(
            {"status": "UNSUPPORTED_OUTPUT", "error": "Output must be finite JSON", "lines": result["lines"]}
        )
    )
