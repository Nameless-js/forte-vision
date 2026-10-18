"""Exercise React/Vite -> integrated web API -> actual local ML engine, without mocks."""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import requests
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from forte_ai.labels import read_labels_csv
    from forte_ai.schema import validate_result
    out = ROOT / "reports" / "integration"
    out.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(32)
    env = dict(os.environ, API_KEY=key, DATABASE_BACKEND="sqlite", DATA_DIRECTORY=str(out / "runtime"), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    log = (out / "service.log").open("w", encoding="utf-8")
    process = subprocess.Popen([sys.executable,str(ROOT / "scripts" / "start_app.py"),"--api-port","8013","--port","5174"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    base = "http://127.0.0.1:5174"
    report = {"ok":False, "steps":[]}
    def check(name, condition):
        report["steps"].append({"name":name, "ok":bool(condition)})
        print(("PASS " if condition else "FAIL ") + name, flush=True)
        if not condition:
            raise AssertionError(name)
    try:
        for _ in range(120):
            try:
                health = requests.get(base + "/api/health",timeout=2)
                if health.ok and health.json().get("model") == "forte_ai":
                    break
            except requests.RequestException:
                pass
            if process.poll() is not None:
                raise RuntimeError("app startup failed; see reports/integration/service.log")
            time.sleep(.5)
        else:
            raise TimeoutError("frontend/API did not become ready")
        check("frontend HTML served", requests.get(base,timeout=10).status_code == 200)
        check("Vite proxy authenticates without a browser API key", health.json().get("database_connected"))
        check("direct API still requires jury key", requests.get("http://127.0.0.1:8013/api/v1/jobs",timeout=10).status_code == 401)
        row = next(r for r in read_labels_csv(ROOT / "data" / "labels.csv") if r.video_id == 4)
        started = time.monotonic()
        with (ROOT / row.path).open("rb") as video:
            response = requests.post(base + "/api/v1/analyze",files={"file":(Path(row.path).name,video,"video/quicktime")},timeout=60)
        check("video uploaded through frontend proxy", response.status_code == 202)
        job_id = response.json()["job_id"]
        progress_seen = False
        while time.monotonic() - started < 290:
            response = requests.get(base + "/api/v1/jobs/" + job_id,timeout=10)
            response.raise_for_status()
            result = response.json()
            progress_seen |= result.get("status") == "processing"
            if result.get("status") in ("done", "failed"):
                break
            time.sleep(.5)
        check("real inference completed", result.get("status") == "done")
        check("processing lifecycle visible", progress_seen)
        check("engine result schema and JPEG evidence valid", not validate_result(result))
        check("real engine positive result", result.get("engine_version") is not None and result["verdict"] == "violation" and not result.get("demo"))
        check("citation fields mapped for React", all(v.get("rule",{}).get("title") and v["rule"].get("section") for v in result["violations"]))
        check("upload cleaned up", not list((out / "runtime").glob("*.mov")))
        history = requests.get(base + "/api/v1/jobs",timeout=10).json()
        check("analysis persisted in history", any(r["job_id"] == job_id for r in history["jobs"]))
        results = out / "results"
        results.mkdir(exist_ok=True)
        (results / "job.json").write_text(json.dumps(result,ensure_ascii=False),encoding="utf-8")
        report.update(ok=True, video_id=4, elapsed_s=round(time.monotonic()-started,1), verdict=result["verdict"], violations=len(result["violations"]))
    finally:
        if process.poll() is None:
            process.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        log.close()
        (out / "report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0 if report["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
