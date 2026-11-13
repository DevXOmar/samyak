import io
import json
import zipfile
from samyak.ledger import build_bundle, verify_bundle


def test_deterministic_archive_and_detected_tampering():
    report = {
        "contract_version": "1.1",
        "job_id": "j",
        "parent_id": None,
        "source": "def f(): return 1\n",
        "source_hash": "source",
        "tests": [],
        "test_revision": "t",
        "model": {},
        "runner": {},
        "candidates": [],
        "precedents": [],
        "intelligence": {},
    }
    first = build_bundle(report, {"analysis": {}}, [])
    assert first == build_bundle(report, {"analysis": {}}, [])
    assert verify_bundle(first)["status"] == "INTEGRITY_VERIFIED"
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(first)) as old, zipfile.ZipFile(output, "w") as new:
        for name in old.namelist():
            new.writestr(name, b"tampered" if name == "original.py" else old.read(name))
    assert verify_bundle(output.getvalue())["status"] == "INTEGRITY_MISMATCH"
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert "index_id" in json.loads(archive.read("repair_manifest.json"))
