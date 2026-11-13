"""Local supervisor: API and one durable worker are separate OS processes."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    env = os.environ.copy()
    # Basic .env values only; no shell evaluation. Existing environment wins.
    path = ROOT / ".env"
    if path.exists():
        for raw in path.read_text().splitlines():
            if "=" in raw and not raw.lstrip().startswith("#"):
                key, value = raw.split("=", 1)
                env.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    env["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + str(ROOT)
    env["PATH"] = str(ROOT / ".venv/bin") + os.pathsep + env.get("PATH", "")
    children = [
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "samyak.api:app", "--host", "127.0.0.1", "--port", "8000"],
            env=env,
        ),
        subprocess.Popen([sys.executable, "-m", "samyak.worker"], env=env),
        subprocess.Popen(["npm", "run", "dev"], cwd=ROOT / "frontend", env=env),
    ]

    def stop(*_):
        for child in children:
            child.terminate()
        for child in children:
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print("SAMYAK: http://127.0.0.1:3000 · API http://127.0.0.1:8000/docs", flush=True)
    while all(child.poll() is None for child in children):
        time.sleep(0.5)
    stop()


if __name__ == "__main__":
    main()
