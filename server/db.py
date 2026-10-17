"""SQLite job store shared by the API process and the worker process."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

DB_PATH = Path(os.environ.get("FORTE_DB_PATH", Path(__file__).resolve().parent / "jobs.sqlite3"))
UPLOAD_DIR = Path(os.environ.get("FORTE_UPLOAD_DIR", Path(__file__).resolve().parent / "uploads"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,            -- queued | processing | done | failed
  created REAL NOT NULL,
  started REAL,
  finished REAL,
  filename TEXT,
  path TEXT,
  progress REAL DEFAULT 0,
  stage TEXT DEFAULT '',
  result TEXT,                     -- JSON (full result incl. base64 frames)
  error TEXT
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=30, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    con.executescript(SCHEMA)
    return con


def create_job(con: sqlite3.Connection, job_id: str, filename: str, path: str) -> None:
    con.execute("INSERT INTO jobs(job_id,status,created,filename,path) VALUES (?,?,?,?,?)", (job_id, "queued", time.time(), filename, path))


def get_job(con: sqlite3.Connection, job_id: str) -> Optional[dict]:
    cur = con.execute("SELECT job_id,status,created,started,finished,filename,progress,stage,result,error FROM jobs WHERE job_id=?", (job_id,))
    row = cur.fetchone()
    if not row:
        return None
    keys = ["job_id", "status", "created", "started", "finished", "filename", "progress", "stage", "result", "error"]
    d = dict(zip(keys, row))
    d["result"] = json.loads(d["result"]) if d["result"] else None
    return d


def claim_next(con: sqlite3.Connection) -> Optional[dict]:
    """Atomically claim the oldest queued job."""
    con.execute("BEGIN IMMEDIATE")
    try:
        cur = con.execute("SELECT job_id,path,filename FROM jobs WHERE status='queued' ORDER BY created LIMIT 1")
        row = cur.fetchone()
        if not row:
            con.execute("COMMIT")
            return None
        con.execute("UPDATE jobs SET status='processing', started=? WHERE job_id=?", (time.time(), row[0]))
        con.execute("COMMIT")
        return {"job_id": row[0], "path": row[1], "filename": row[2]}
    except Exception:
        con.execute("ROLLBACK")
        raise


def set_progress(con: sqlite3.Connection, job_id: str, progress: float, stage: str) -> None:
    con.execute("UPDATE jobs SET progress=?, stage=? WHERE job_id=?", (float(progress), stage, job_id))


def finish_job(con: sqlite3.Connection, job_id: str, result: dict) -> None:
    con.execute("UPDATE jobs SET status='done', finished=?, progress=1.0, stage='Готово', result=? WHERE job_id=?", (time.time(), json.dumps(result, ensure_ascii=False), job_id))


def fail_job(con: sqlite3.Connection, job_id: str, error: str) -> None:
    con.execute("UPDATE jobs SET status='failed', finished=?, error=? WHERE job_id=?", (time.time(), error[:2000], job_id))


def requeue_stale(con: sqlite3.Connection, max_age_s: float = 900.0) -> int:
    """Jobs stuck in 'processing' (worker crashed) are marked failed after max_age_s."""
    cur = con.execute("UPDATE jobs SET status='failed', error='worker timeout', finished=? WHERE status='processing' AND started < ?", (time.time(), time.time() - max_age_s))
    return cur.rowcount
