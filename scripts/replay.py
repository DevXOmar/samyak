import json
from pathlib import Path
import sys
from samyak.contracts import TestCase
from samyak.runner import DockerRunner
from samyak.store import digest

root = Path(sys.argv[1])
manifest = json.loads((root / "repair_manifest.json").read_text())
for name, expected in manifest["files"].items():
    assert digest((root / name).read_bytes()) == expected, f"Artifact integrity mismatch: {name}"
runner = DockerRunner()
if not runner.available() or runner.manifest["digest"] != manifest["runner"]["digest"]:
    raise SystemExit("EXECUTION_UNAVAILABLE: exact runner image is required")
tests = [TestCase.model_validate(t) for t in json.loads((root / "tests.json").read_text())]
report = json.loads((root / "report.json").read_text())
if report.get("script_result"):
    request = json.loads((root / "request.json").read_text())
    stdin = request.get("analysis", {}).get("stdin", "")
    observed = runner.run(
        (root / "original.py").read_text(),
        [TestCase(id="script", function="__script__", mode="SCRIPT", stdin=stdin)],
    )[0]
    old_script = report["script_result"]
    fields = ["status", "stdout", "stderr", "error", "exit_code", "fault_lines", "lines"]
    same = all(getattr(observed, k) == old_script.get(k) for k in fields)
    print("script", "MATCH" if same else "MISMATCH")
    if not same:
        raise SystemExit(1)
for source_path, old in [(root / "original.py", report["original_results"])] + [
    (root / "patches" / (c["id"] + ".py"), c["results"]) for c in report["candidates"] if c["results"]
]:
    results = runner.run(source_path.read_text(), tests)
    same = [(r.status, r.output, r.error) for r in results] == [
        (r["status"], r["output"], r["error"]) for r in old
    ]
    print(source_path.name, "MATCH" if same else "MISMATCH")
    if not same:
        raise SystemExit(1)
