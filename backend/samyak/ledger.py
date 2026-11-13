"""Canonical, deterministic evidence archives and independent integrity verification."""

import io
import json
from pathlib import Path
import zipfile
from .store import ROOT, digest


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)


def ledger_metadata(report):
    return {
        "status": "RECORDED",
        "source_hash": report.source_hash,
        "test_revision": report.test_revision,
        "model_id": report.model.get("model_id"),
        "index_id": report.intelligence.get("precedents", {}).get("index_id"),
        "runner_digest": report.runner.get("digest"),
        "patch_hashes": {c.id: c.source_hash for c in report.candidates},
        "integrity": "SHA-256 content identity; not authentication or a correctness proof",
        "verification": {
            "status": "NOT_RUN",
            "reason": "Run ledger verification to replay original and candidate observations in the exact image",
        },
    }


def build_bundle(report, request, events):
    files = {
        "report.json": canonical(report),
        "original.py": report["source"],
        "tests.json": canonical(report["tests"]),
        "request.json": canonical(request),
        "events.json": canonical(events),
        "REPLAY.txt": "PYTHONPATH=backend .venv/bin/python scripts/replay.py <extracted-directory>\nExpected runtime image is fixed in repair_manifest.json. Timing equality is not required.\n",
    }
    for candidate in report["candidates"]:
        files[f"patches/{candidate['id']}.py"] = candidate["source"]
        files[f"patches/{candidate['id']}.diff"] = candidate["diff"]
    for precedent in report["precedents"]:
        path = (ROOT / precedent.get("license_path", "data/seeds/THEALGORITHMS_LICENSE.md")).resolve()
        if path.is_relative_to((ROOT / "data/seeds").resolve()) and path.is_file():
            files[f"licenses/{path.name}"] = path.read_text()
    manifest = {
        "contract_version": report["contract_version"],
        "job_id": report["job_id"],
        "parent_id": report.get("parent_id"),
        "source_hash": report["source_hash"],
        "test_revision": report["test_revision"],
        "model_id": report["model"].get("model_id"),
        "index_id": report.get("intelligence", {}).get("precedents", {}).get("index_id"),
        "runner": report["runner"],
        "files": {name: digest(raw) for name, raw in sorted(files.items())},
        "replay": "PYTHONPATH=backend .venv/bin/python scripts/replay.py <extracted-directory>",
    }
    files["repair_manifest.json"] = canonical(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, raw.encode())
    return output.getvalue()


def verify_bundle(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            Path(n).is_absolute() or ".." in Path(n).parts for n in names
        ):
            raise ValueError("Unsafe or duplicate archive path")
        manifest = json.loads(archive.read("repair_manifest.json"))
        if set(names) != set(manifest["files"]) | {"repair_manifest.json"}:
            raise ValueError("Archive manifest coverage mismatch")
        checks = [
            {
                "file": name,
                "hash": digest(archive.read(name)),
                "match": digest(archive.read(name)) == expected,
            }
            for name, expected in manifest["files"].items()
        ]
    return {
        "status": "INTEGRITY_VERIFIED" if all(c["match"] for c in checks) else "INTEGRITY_MISMATCH",
        "archive_sha256": digest(blob),
        "files": checks,
    }
