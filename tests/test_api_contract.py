"""API contract (ТЗ §10) without models: FastAPI TestClient + a simulated worker writing to the SQLite queue.

Covers: 401 without / with a wrong key (and when the server key is unset), 400 for a non-.mov upload,
POST -> {job_id, status=processing}, GET 404 for unknown ids, queued -> processing, done -> ТЗ result keys
verbatim with job_id/status overridden, failed -> status failed + error, progress exposure.
"""

import importlib
import json

import numpy as np
import pytest

from forte_ai.schema import validate_result
from forte_ai.video import encode_jpeg_base64

KEY = "test-secret-key"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FORTE_API_KEY", KEY)
    import server.db as db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "jobs.sqlite3")
    monkeypatch.setattr(db, "UPLOAD_DIR", tmp_path / "uploads")
    import server.app as app_mod

    importlib.reload(app_mod)  # rebind module-level references to the patched db
    from fastapi.testclient import TestClient

    return TestClient(app_mod.app), db


def _valid_result(job_id: str) -> dict:
    img = np.zeros((40, 60, 3), np.uint8)
    b64 = encode_jpeg_base64(img)
    return {
        "job_id": job_id,
        "status": "done",
        "verdict": "violation",
        "violations": [
            {
                "type": "Выдача наличных без пересчёта в присутствии клиента",
                "timecode_sec": 12.4,
                "description": "На 12,4 с кассир передаёт клиенту наличные без видимого пересчёта.",
                "evidence_frames": [{"timestamp_sec": 12.4, "image_base64": b64}],
                "type_id": "issue_without_count",
            }
        ],
    }


def test_auth_required(client):
    c, _ = client
    r = c.post("/api/v1/analyze", files={"file": ("a.mov", b"x")})
    assert r.status_code == 401
    r = c.post("/api/v1/analyze", files={"file": ("a.mov", b"x")}, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401
    r = c.get("/api/v1/jobs/abc")
    assert r.status_code == 401


def test_unset_server_key_rejects_everything(client, monkeypatch):
    c, _ = client
    monkeypatch.delenv("FORTE_API_KEY", raising=False)
    r = c.post("/api/v1/analyze", files={"file": ("a.mov", b"x")}, headers={"X-API-Key": ""})
    assert r.status_code == 401


def test_rejects_non_mov(client):
    c, _ = client
    r = c.post("/api/v1/analyze", files={"file": ("a.txt", b"x")}, headers={"X-API-Key": KEY})
    assert r.status_code == 400


def test_unknown_job_404(client):
    c, _ = client
    r = c.get("/api/v1/jobs/doesnotexist", headers={"X-API-Key": KEY})
    assert r.status_code == 404


def test_lifecycle_done(client):
    c, db = client
    r = c.post("/api/v1/analyze", files={"file": ("video_017.mov", b"\x00" * 1024, "video/quicktime")}, headers={"X-API-Key": KEY})
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"job_id", "status"} and body["status"] == "processing"
    jid = body["job_id"]
    # queued is reported as processing
    r = c.get(f"/api/v1/jobs/{jid}", headers={"X-API-Key": KEY})
    assert r.json()["status"] == "processing"
    # the worker claims the job and reports progress
    con = db.connect()
    job = db.claim_next(con)
    assert job["job_id"] == jid
    db.set_progress(con, jid, 0.42, "Анализ кадров")
    con.close()
    r = c.get(f"/api/v1/jobs/{jid}", headers={"X-API-Key": KEY})
    j = r.json()
    assert j["status"] == "processing" and abs(j["progress"] - 0.42) < 1e-6 and j["stage"] == "Анализ кадров"
    # the worker finishes with a result carrying a DIFFERENT job id: the API must expose its own
    con = db.connect()
    db.finish_job(con, jid, _valid_result("other-id"))
    con.close()
    r = c.get(f"/api/v1/jobs/{jid}", headers={"X-API-Key": KEY})
    j = r.json()
    assert j["status"] == "done" and j["job_id"] == jid
    for k in ("job_id", "status", "verdict", "violations"):
        assert k in j
    assert validate_result(j) == []


def test_lifecycle_failed(client):
    c, db = client
    r = c.post("/api/v1/analyze", files={"file": ("x.mov", b"\x00" * 10)}, headers={"X-API-Key": KEY})
    jid = r.json()["job_id"]
    con = db.connect()
    db.claim_next(con)
    db.fail_job(con, jid, "AnalysisError: cannot decode")
    con.close()
    j = c.get(f"/api/v1/jobs/{jid}", headers={"X-API-Key": KEY}).json()
    assert j["status"] == "failed" and "cannot decode" in j["error"] and j["violations"] == []


def test_claim_is_exclusive(client):
    c, db = client
    ids = [c.post("/api/v1/analyze", files={"file": (f"{i}.mov", b"\x00")}, headers={"X-API-Key": KEY}).json()["job_id"] for i in range(3)]
    con = db.connect()
    claimed = [db.claim_next(con)["job_id"] for _ in range(3)]
    assert db.claim_next(con) is None
    con.close()
    assert sorted(claimed) == sorted(ids)  # every job claimed exactly once
