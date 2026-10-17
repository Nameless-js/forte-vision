"""`make offline-check` (gate 7): run a full analysis with HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 and a
socket guard that raises on ANY outbound connection attempt, then audit the processing-path code for network
calls and face-recognition dependencies.

Usage: python scripts/offline_check.py [--video public/X-1.mov] [--out reports/offline]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

ATTEMPTS: list[str] = []
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_create_connection = socket.create_connection


def _blocked(*args, **kwargs):
    target = args[1] if len(args) > 1 else kwargs.get("address")
    ATTEMPTS.append(repr(target))
    raise OSError(f"network blocked by offline_check: {target!r}")


def install_guard() -> None:
    socket.socket.connect = _blocked  # type: ignore[assignment]
    socket.socket.connect_ex = _blocked  # type: ignore[assignment]
    socket.create_connection = lambda *a, **k: _blocked(None, a[0] if a else k.get("address"))  # type: ignore[assignment]


NET_PATTERNS = [r"\brequests\.", r"\burllib\.request", r"\bhttpx\b", r"\baiohttp\b", r"\bsocket\.", r"\burlopen\(", r"openai", r"anthropic", r"google\.generativeai", r"boto3", r"azure"]
FACE_PATTERNS = [r"face_recognition", r"insightface", r"deepface", r"facenet", r"arcface", r"retinaface", r"dlib", r"mediapipe\.solutions\.face"]


def audit() -> dict:
    hits_net, hits_face = [], []
    for p in sorted((ROOT / "forte_ai").rglob("*.py")):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(txt.splitlines(), 1):
            s = line.strip()
            if s.startswith("#"):
                continue
            for pat in NET_PATTERNS:
                if re.search(pat, line):
                    hits_net.append(f"{p.relative_to(ROOT)}:{i}: {s[:100]}")
            for pat in FACE_PATTERNS:
                if re.search(pat, line, re.I):
                    hits_face.append(f"{p.relative_to(ROOT)}:{i}: {s[:100]}")
    # dependencies
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8", errors="ignore").lower() if (ROOT / "requirements.txt").exists() else ""
    face_deps = [d for d in ("face-recognition", "insightface", "deepface", "facenet", "dlib", "retinaface") if d in req]
    return {"network_calls_in_processing_path": hits_net, "face_patterns": hits_face, "face_dependencies": face_deps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(ROOT / "public" / "X-1.mov"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "offline"))
    ap.add_argument("--profile", default=None)
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {"env": {k: os.environ.get(k) for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")}, "audit": audit()}
    install_guard()
    from forte_ai.analyzer import Analyzer
    from forte_ai.schema import validate_result

    t0 = time.time()
    try:
        an = Analyzer(profile=a.profile)
        res = an.analyze(a.video, use_cache=not a.no_cache)
        probs = validate_result(res)
        report["run"] = {"ok": not probs, "verdict": res["verdict"], "n_violations": len(res["violations"]), "elapsed_s": round(time.time() - t0, 1), "schema_problems": probs, "vlm_calls": res.get("vlm", {}).get("calls")}
    except Exception as e:  # noqa: BLE001
        report["run"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    report["network_attempts"] = ATTEMPTS
    report["ok"] = bool(report["run"].get("ok")) and not ATTEMPTS and not report["audit"]["network_calls_in_processing_path"] and not report["audit"]["face_dependencies"]
    (out / "offline_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print("OFFLINE CHECK", "PASSED" if report["ok"] else "FAILED")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
