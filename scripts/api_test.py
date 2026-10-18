"""`make api-test`: start the reference server + worker, exercise the contract, validate the JSON.

Checks: 401 without key / with a wrong key; POST returns job_id; GET goes processing -> done; the result
validates against forte_ai/result_schema.json; verdict/violations semantics; upload deleted afterwards.
Usage: python scripts/api_test.py [--video public/X-1.mov] [--port 8011] [--out reports/api_test] [--no-vlm]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.schema import validate_result  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(ROOT / "public" / "X-1.mov"))
    ap.add_argument("--port", type=int, default=8011)
    ap.add_argument("--out", default=str(ROOT / "reports" / "api_test"))
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--no-vlm", action="store_true")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--base-url", default=None, help="test an already running server (e.g. a Docker container) instead of starting one")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    key = "test-key-" + os.urandom(4).hex()
    env = dict(os.environ, FORTE_API_KEY=key, PYTHONUTF8="1", FORTE_DB_PATH=str(out / "jobs.sqlite3"), FORTE_UPLOAD_DIR=str(out / "uploads"))
    if a.no_vlm:
        env["FORTE_CONFIG"] = str(out / "no_vlm.yaml")
        (out / "no_vlm.yaml").write_text("vlm:\n  enabled: false\n", encoding="utf-8")
    if a.profile:
        env["FORTE_PROFILE"] = a.profile
    py = sys.executable
    procs = []
    base = a.base_url or f"http://127.0.0.1:{a.port}"
    if a.base_url:
        key = os.environ.get("FORTE_API_KEY", key)
    report = {"steps": [], "ok": False}

    def step(name, ok, detail=""):
        report["steps"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:500]})
        print(f"[{'OK' if ok else 'FAIL'}] {name} {detail}", flush=True)
        return ok

    try:
        if not a.base_url:
            (out / "jobs.sqlite3").unlink(missing_ok=True)
            procs.append(subprocess.Popen([py, "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", str(a.port), "--log-level", "warning"], cwd=str(ROOT), env=env))
            procs.append(subprocess.Popen([py, "-m", "server.worker", "--poll", "0.5", "--max-jobs", "1"], cwd=str(ROOT), env=env))
            for _ in range(120):
                try:
                    if requests.get(f"{base}/health", timeout=2).status_code == 200:
                        break
                except Exception:
                    time.sleep(0.5)
            else:
                step("server up", False, "health endpoint not reachable")
                return 1
            step("server up", True, base)
        ok = True
        r = requests.post(f"{base}/api/v1/analyze", files={"file": ("x.mov", b"abc")}, timeout=30)
        ok &= step("401 without key", r.status_code == 401, r.status_code)
        r = requests.post(f"{base}/api/v1/analyze", files={"file": ("x.mov", b"abc")}, headers={"X-API-Key": "wrong"}, timeout=30)
        ok &= step("401 with wrong key", r.status_code == 401, r.status_code)
        r = requests.get(f"{base}/api/v1/jobs/doesnotexist", headers={"X-API-Key": key}, timeout=30)
        ok &= step("404 unknown job", r.status_code == 404, r.status_code)
        with open(a.video, "rb") as f:
            t0 = time.time()
            r = requests.post(f"{base}/api/v1/analyze", files={"file": (Path(a.video).name, f, "video/quicktime")}, headers={"X-API-Key": key}, timeout=300)
        ok &= step("POST analyze -> job_id", r.status_code == 200 and "job_id" in r.json(), f"{r.status_code} {r.text[:120]}")
        job_id = r.json().get("job_id")
        seen_processing = False
        final = None
        while time.time() - t0 < a.timeout:
            r = requests.get(f"{base}/api/v1/jobs/{job_id}", headers={"X-API-Key": key}, timeout=30)
            j = r.json()
            if j.get("status") == "processing":
                seen_processing = True
            if j.get("status") in ("done", "failed"):
                final = j
                break
            time.sleep(2)
        elapsed = time.time() - t0
        ok &= step("job lifecycle processing -> done", final is not None and final.get("status") == "done" and seen_processing, f"status={final.get('status') if final else None} elapsed={elapsed:.0f}s")
        if final and final.get("status") == "done":
            probs = validate_result(final)
            ok &= step("JSON schema + semantics", not probs, "; ".join(probs)[:300])
            ok &= step("verdict present", final.get("verdict") in ("violation", "no_violation"), final.get("verdict"))
            ok &= step("within 5 min", elapsed <= 300, f"{elapsed:.0f}s")
            slim = {k: v for k, v in final.items() if k != "violations"}
            slim["violations"] = [{k: (v if k != "evidence_frames" else [{"timestamp_sec": e["timestamp_sec"], "image_base64_len": len(e["image_base64"])} for e in v]) for k, v in viol.items()} for viol in final["violations"]]
            (out / "job_result_slim.json").write_text(json.dumps(slim, ensure_ascii=False, indent=1), encoding="utf-8")
            (out / "job_result_full.json").write_text(json.dumps(final, ensure_ascii=False), encoding="utf-8")
        if not a.base_url:
            time.sleep(1.0)
            leftovers = list((out / "uploads").glob("*")) if (out / "uploads").exists() else []
            ok &= step("upload deleted after processing", not leftovers, [p.name for p in leftovers])
        report["ok"] = bool(ok)
        report["elapsed_s"] = elapsed
        report["job_id"] = job_id
        return 0 if ok else 2
    finally:
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=20)
            except Exception:
                p.kill()
        (out / "api_test_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print("API TEST", "PASSED" if report["ok"] else "FAILED", "->", out / "api_test_report.json")


if __name__ == "__main__":
    raise SystemExit(main())
