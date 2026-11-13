import hashlib
import json
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4
from .contracts import Job

ROOT = Path(__file__).resolve().parents[2]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    raw = value if isinstance(value, bytes) else value.encode()
    return hashlib.sha256(raw).hexdigest()


class Store:
    def __init__(self, root=None):
        self.root = Path(root or os.getenv("SAMYAK_DATA", ROOT / "var"))
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "artifacts").mkdir(exist_ok=True)
        with self.connect() as db:
            db.executescript("""PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, parent_id TEXT, status TEXT, stage TEXT,
              created_at TEXT, updated_at TEXT, error TEXT, report_hash TEXT,
              request_hash TEXT NOT NULL, lease_pid INTEGER);
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, stage TEXT, message TEXT, timestamp TEXT);
            """)

    def connect(self):
        db = sqlite3.connect(self.root / "jobs.sqlite", timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def artifact(self, value):
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
        key = digest(raw)
        path = self.root / "artifacts" / key
        if not path.exists():
            temp = path.with_suffix(f".{uuid4().hex}.tmp")
            temp.write_bytes(raw)
            os.replace(temp, path)
        return key

    def read(self, key):
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("Invalid artifact digest")
        raw = (self.root / "artifacts" / key).read_bytes()
        if digest(raw) != key:
            raise ValueError("Artifact integrity mismatch")
        return json.loads(raw)

    def submit(self, request, parent=None):
        key, ident, stamp = self.artifact(request), uuid4().hex, now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ident, parent, "QUEUED", "queued", stamp, stamp, None, None, key, None),
            )
        self.event(ident, "queued", "Immutable source and test revision stored")
        return self.job(ident)

    def job(self, ident):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
        if not row:
            raise KeyError(ident)
        return Job.model_validate({k: row[k] for k in Job.model_fields if k in row.keys()})

    def request(self, ident):
        with self.connect() as db:
            row = db.execute("SELECT request_hash FROM jobs WHERE id=?", (ident,)).fetchone()
        return self.read(row[0])

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM jobs WHERE status='QUEUED' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE jobs SET status='RUNNING',lease_pid=?,updated_at=? WHERE id=?",
                (os.getpid(), now(), row["id"]),
            )
        return row["id"]

    def recover(self):
        # Single worker supported. A crashed process leaves an auditable event before retry.
        with self.connect() as db:
            rows = db.execute("SELECT id,lease_pid FROM jobs WHERE status='RUNNING'").fetchall()
            for row in rows:
                try:
                    os.kill(row["lease_pid"], 0)
                except ProcessLookupError:
                    db.execute("UPDATE jobs SET status='QUEUED',stage='recovered' WHERE id=?", (row["id"],))

    def event(self, ident, stage, message):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(job_id,stage,message,timestamp) VALUES (?,?,?,?)",
                (ident, stage, message, now()),
            )
            db.execute("UPDATE jobs SET stage=?,updated_at=? WHERE id=?", (stage, now(), ident))

    def events(self, ident, after=0):
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM events WHERE job_id=? AND id>? ORDER BY id", (ident, after)
                )
            ]

    def finish(self, ident, report=None, error=None):
        key = self.artifact(report) if report else None
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET status=?,report_hash=?,error=?,updated_at=? WHERE id=?",
                ("FAILED" if error else "COMPLETED", key, error, now(), ident),
            )
        self.event(ident, "failed" if error else "completed", error or "Evidence report persisted")

    def report(self, ident):
        job = self.job(ident)
        return self.read(job.report_hash) if job.report_hash else None
