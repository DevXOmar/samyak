"""Executed only inside the same restricted Linux container as function cases."""

import ast
import contextlib
import io
import json
import resource
import signal
import sys
import time
import traceback
import coverage

resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
resource.setrlimit(resource.RLIMIT_CPU, (1, 2))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
request = json.loads(sys.stdin.read(131072))


class OutputLimitExceeded(RuntimeError):
    pass


class CpuLimitExceeded(TimeoutError):
    pass


class BoundedText(io.StringIO):
    def write(self, text):
        if self.tell() + len(text) > 16000:
            raise OutputLimitExceeded("Script output limit exceeded")
        return super().write(text)


def cpu_timeout(*_):
    raise CpuLimitExceeded("1 second per-case CPU budget exceeded")


signal.signal(signal.SIGXCPU, cpu_timeout)
stdout, stderr = BoundedText(), BoundedText()
trace = coverage.Coverage(data_file=None, branch=True, include=["/work/submission.py"])
result = dict(status="EXECUTED_SUCCESSFULLY", exit_code=0, fault_lines=[], lines=[])
started = time.perf_counter()
try:
    sys.stdin = io.StringIO(request.get("stdin", ""))
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        trace.start()
        exec(
            compile(open("/work/submission.py").read(), "/work/submission.py", "exec"),
            {"__name__": "__main__", "__file__": "/work/submission.py"},
        )
except SystemExit as exc:
    result["exit_code"] = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
    result["status"] = "EXECUTED_SUCCESSFULLY" if result["exit_code"] == 0 else "ERROR"
    if result["exit_code"] != 0:
        result.update(error="SystemExit: " + str(exc.code)[:500], traceback=traceback.format_exc()[-8000:])
        result["fault_lines"] = [
            f.lineno for f in traceback.extract_tb(exc.__traceback__) if f.filename == "/work/submission.py"
        ]
except BaseException as exc:
    result.update(
        status="TIMEOUT"
        if isinstance(exc, CpuLimitExceeded)
        else "OUTPUT_LIMIT"
        if isinstance(exc, OutputLimitExceeded)
        else "ERROR",
        exit_code=1,
        error=type(exc).__name__ + ": " + str(exc)[:500],
        traceback=traceback.format_exc()[-8000:],
    )
    result["fault_lines"] = [
        f.lineno for f in traceback.extract_tb(exc.__traceback__) if f.filename == "/work/submission.py"
    ]
finally:
    trace.stop()
    result.update(
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
        lines=trace.get_data().lines("/work/submission.py") or [],
        duration_ms=(time.perf_counter() - started) * 1000,
    )
# Definition/import lines are structural facts, not observed executable statements.
excluded = {
    n.lineno
    for n in ast.walk(ast.parse(open("/work/submission.py").read()))
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom))
}
result["lines"] = sorted(set(result["lines"]) - excluded)
print(json.dumps(result, allow_nan=False))
