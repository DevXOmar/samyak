import os
from pathlib import Path
import time
import traceback
from .pipeline import run_pipeline
from .investigations import run_investigation
from .store import Store
from .runner import RUN_METRICS


def process_one(store):
    ident = store.claim()
    if not ident:
        return False
    metrics = {}
    token = RUN_METRICS.set(metrics)
    started = time.perf_counter()
    durations = []
    current_stage = [None, started]
    try:
        job = store.job(ident)
        payload = store.request(ident)

        def stage(s, m):
            now = time.perf_counter()
            if current_stage[0] is not None:
                durations.append({"stage": current_stage[0], "seconds": now - current_stage[1]})
            current_stage[:] = [s, now]
            store.event(ident, s, m)

        if payload.get("investigation"):
            report = run_investigation(ident, payload, store.read(payload["base_report_hash"]), stage)
        else:
            report = run_pipeline(ident, payload, stage, job.parent_id)
        now = time.perf_counter()
        if current_stage[0] is not None:
            durations.append({"stage": current_stage[0], "seconds": now - current_stage[1]})
        report.intelligence["timing"] = {
            "wall_seconds": now - started,
            "stages": durations,
            "execution": metrics,
            "clock": "worker monotonic; queue/store-finalization excluded",
        }
        store.finish(ident, report.model_dump())
    except Exception as exc:
        traceback.print_exc()
        store.finish(ident, error=f"{type(exc).__name__}: {str(exc)[:1000]}")
    finally:
        RUN_METRICS.reset(token)
    return True


def main():
    # Scanner executables are resolved from the same pinned environment as this interpreter.
    import sys

    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    store = Store()
    # OS advisory lock enforces one worker and allows crash recovery without duplicate execution.
    import fcntl

    with (store.root / "worker.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("One worker is already running")
        store.recover()
        while True:
            if not process_one(store):
                time.sleep(0.4)


if __name__ == "__main__":
    main()
