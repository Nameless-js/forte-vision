"""Continue the measured checks with a user-specified deadline and explicit partial robustness coverage."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--until-utc", required=True)
    args = ap.parse_args()
    deadline = datetime.fromisoformat(args.until_utc)
    if deadline.tzinfo is None:
        raise ValueError("deadline needs an explicit UTC offset")
    out = ROOT / "reports" / "final"
    path = out / "verification.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    proof = json.loads((out / "deadline_continuation.json").read_text(encoding="utf-8"))
    if not proof.get("prior_stages_source_match") or proof.get("prior_source_sha256") != state.get("source_sha256"):
        raise ValueError("missing source-integrity proof for prior checks")
    state["inherited_source_sha256"] = state["source_sha256"]
    digest = hashlib.sha256()
    for folder in ("forte_ai", "server", "scripts", "tests", "configs"):
        for source in sorted((ROOT / folder).rglob("*")):
            if source.suffix in (".py", ".yaml"):
                digest.update(source.relative_to(ROOT).as_posix().encode())
                digest.update(source.read_bytes())
    state["source_sha256"] = digest.hexdigest()
    state["deadline_utc"] = args.until_utc
    state["coverage_policy"] = "variant-first perception, cached-only scoring; partial coverage explicitly reported"
    state["ok"] = False
    py = sys.executable
    script = lambda name: str(ROOT / "scripts" / name)
    stages = [
        ("tests", [py, "-m", "pytest", "-q", "--junitxml", str(out / "tests.xml")]),
        ("robustness-perception", [py, script("robustness.py"), "--perception-only", "--variant-first", "--until-utc", (deadline - timedelta(minutes=50)).isoformat(), "--out", str(out / "robustness")]),
        ("robustness", [py, script("robustness.py"), "--cached-only", "--variant-first", "--until-utc", (deadline - timedelta(minutes=20)).isoformat(), "--out", str(out / "robustness")]),
        ("schema", [py, script("validate_reports.py"), str(out)]),
        ("packaging", [py, script("packaging_check.py")]),
        ("quality-gates", [py, script("final_report.py"), "--check"]),
    ]
    environment = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    for name, command in stages:
        state["steps"] = [s for s in state["steps"] if s["name"] != name]
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"DEADLINE VERIFY STAGE: {name}", flush=True)
        start = time.monotonic()
        code = subprocess.run(command, cwd=ROOT, env=environment).returncode
        state["steps"].append({"name": name, "exit_code": code, "elapsed_s": round(time.monotonic() - start, 1)})
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    state["ok"] = all(s["exit_code"] == 0 for s in state["steps"])
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return 0 if state["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
