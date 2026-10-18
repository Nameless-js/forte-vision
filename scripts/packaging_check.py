"""Build a wheel, then exercise its resources outside the source checkout, without installing dependencies."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    out = ROOT / "reports" / "final" / "packaging"
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir", str(out), str(ROOT)], check=True)
    wheels = sorted(out.glob("forte_ai-*.whl"), key=lambda p: p.stat().st_mtime)
    wheel = wheels[-1]
    extracted = Path(tempfile.mkdtemp(prefix="forte-wheel-"))
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(extracted)
        names = archive.namelist()
    code = r'''import sys, pathlib, json
sys.path.insert(0, sys.argv[1])
import forte_ai
from forte_ai.config import Config
from forte_ai.kb import KnowledgeBase
from forte_ai.schema import validate_result
from forte_ai.supervisor import SupervisedAnalyzer
assert pathlib.Path(forte_ai.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[1]).resolve())
assert Config.load(profile="cpu").get("device") == "cpu"
assert not KnowledgeBase().verify_all()
assert not validate_result({"job_id":"wheel", "status":"done", "verdict":"no_violation", "violations":[]})
print(json.dumps({"package_path":forte_ai.__file__, "cards":len(KnowledgeBase().cards), "ok":True}))
'''
    result = subprocess.run([sys.executable, "-I", "-c", code, str(extracted)], cwd=extracted, text=True, capture_output=True)
    report = {"ok": result.returncode == 0, "wheel": wheel.name, "resource_files": [n for n in names if n.endswith((".json", ".yaml"))], "stdout": result.stdout, "stderr": result.stderr, "scope": "wheel resource/import isolation using existing dependencies; not a fresh dependency installation or Docker build"}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
