"""Reference API (ТЗ §10): POST /api/v1/analyze (multipart `file`) -> {job_id}; GET /api/v1/jobs/{job_id}.

Run:  uvicorn server.app:app --host 0.0.0.0 --port 8000      (plus `python -m server.worker` in another process)
Auth: header X-API-Key must equal env FORTE_API_KEY (401 otherwise).
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from . import db

app = FastAPI(title="forte_ai reference API", version="0.1.0")
MAX_UPLOAD_MB = float(os.environ.get("FORTE_MAX_UPLOAD_MB", "500"))


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("FORTE_API_KEY", "")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/v1/analyze", dependencies=[Depends(require_key)])
async def analyze(file: UploadFile = File(...)) -> dict:
    name = Path(file.filename or "video.mov").name
    if not name.lower().endswith((".mov", ".mp4")):
        raise HTTPException(status_code=400, detail="expected a .mov file in field 'file'")
    job_id = uuid.uuid4().hex[:8]
    db.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = db.UPLOAD_DIR / f"{job_id}{Path(name).suffix.lower()}"
    size = 0
    with open(dest, "wb") as f:
        while True:
            chunk = await file.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_MB * 1e6:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="file too large")
            f.write(chunk)
    con = db.connect()
    try:
        db.create_job(con, job_id, name, str(dest))
    finally:
        con.close()
    return {"job_id": job_id, "status": "processing"}


@app.get("/api/v1/jobs/{job_id}", dependencies=[Depends(require_key)])
def job_status(job_id: str):
    con = db.connect()
    try:
        j = db.get_job(con, job_id)
    finally:
        con.close()
    if j is None:
        raise HTTPException(status_code=404, detail="job not found")
    status = "processing" if j["status"] in ("queued", "processing") else j["status"]
    body = {"job_id": job_id, "status": status, "progress": round(float(j["progress"] or 0.0), 3), "stage": j["stage"] or ""}
    if status == "done" and j["result"]:
        res = dict(j["result"])
        res["job_id"] = job_id
        res["status"] = "done"
        body.update(res)
    elif status == "failed":
        body["error"] = j["error"] or "analysis failed"
        body["verdict"] = None
        body["violations"] = []
    return JSONResponse(body)
