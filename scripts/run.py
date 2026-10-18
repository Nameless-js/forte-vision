"""Cross-platform task runner (replacement for `make` on Windows).

Usage: python scripts/run.py <target> [extra args...]

Targets (mirror the Makefile):
  setup            create .venv (if missing), install the package + dev deps, build data/labels.csv
  download-weights pre-download all model weights into the local HF cache (needs network once)
  test             pytest
  eval             full evaluation on the labeled set -> reports/iter_XXX/ (or --out)
  robustness       augmentation suite -> reports/robustness/
  timing           per-stage timing on the 3 longest videos -> reports/timing/
  api-test         start the reference server, upload a video, poll, validate the schema
  offline-check    run one analysis with HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 and a socket guard
  verify           test + eval + robustness + timing + offline-check + api-test + schema validation of reports/final
  clean-cache      delete data/cache
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"


def venv_python() -> str:
    """Return the interpreter to use: the venv one if it exists, else the current one."""
    if os.environ.get("FORTE_PYTHON"):
        return os.environ["FORTE_PYTHON"]
    cand = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if cand.exists():
        return str(cand)
    return sys.executable


def run(cmd: list[str], env: dict | None = None, check: bool = True, cwd: Path | None = None) -> int:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    full_env = dict(os.environ)
    full_env.setdefault("PYTHONUTF8", "1")
    full_env.setdefault("PYTHONIOENCODING", "utf-8")
    if env:
        full_env.update(env)
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd or ROOT), env=full_env)
    if check and r.returncode != 0:
        print(f"!! command failed with exit code {r.returncode}", file=sys.stderr)
        sys.exit(r.returncode)
    return r.returncode


def t_setup(args: list[str]) -> None:
    base = sys.executable
    if not VENV.exists():
        run([base, "-m", "venv", str(VENV)])
    py = venv_python()
    run([py, "-m", "pip", "install", "--upgrade", "pip"])
    if "--cpu" in args:
        run([py, "-m", "pip", "install", "--index-url", "https://download.pytorch.org/whl/cpu", "torch==2.6.0", "torchvision==0.21.0"])
    else:
        run(
            [
                py,
                "-m",
                "pip",
                "install",
                "--index-url",
                "https://download.pytorch.org/whl/cu124",
                "torch==2.6.0",
                "torchvision==0.21.0",
            ]
        )
    req = ROOT / "requirements.txt"
    if req.exists():
        # The selected torch build must survive installing the development freeze.
        filtered = VENV / "requirements-runtime.txt"
        filtered.write_text("\n".join(line for line in req.read_text(encoding="utf-8").splitlines() if not line.lower().startswith(("torch==", "torchvision=="))) + "\n", encoding="utf-8")
        run([py, "-m", "pip", "install", "-r", str(filtered)])
    run([py, "-m", "pip", "install", "-e", f"{ROOT}[dev]"])
    if (ROOT / "public").is_dir() and (ROOT / "open" / "open_labels.xlsx").is_file():
        run([py, str(ROOT / "scripts" / "build_labels.py")])
    else:
        print("Dataset not supplied: skipping label rebuild. You can analyze your own uploaded videos.", flush=True)
    if (ROOT / "scripts" / "inventory.py").exists() and (ROOT / "public").exists():
        run([py, str(ROOT / "scripts" / "inventory.py")], check=False)


def t_download_weights(args: list[str]) -> None:
    run([venv_python(), str(ROOT / "scripts" / "download_weights.py"), *args])


def t_test(args: list[str]) -> None:
    run([venv_python(), "-m", "pytest", "-q", *args])


def t_eval(args: list[str]) -> None:
    run([venv_python(), str(ROOT / "scripts" / "eval.py"), *args])


def t_robustness(args: list[str]) -> None:
    run([venv_python(), str(ROOT / "scripts" / "robustness.py"), *args])


def t_timing(args: list[str]) -> None:
    run([venv_python(), str(ROOT / "scripts" / "timing.py"), *args])


def t_api_test(args: list[str]) -> None:
    run([venv_python(), str(ROOT / "scripts" / "api_test.py"), *args])


def t_offline_check(args: list[str]) -> None:
    run(
        [venv_python(), str(ROOT / "scripts" / "offline_check.py"), *args],
        env={"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"},
    )


def t_verify(args: list[str]) -> None:
    """Run every check, retain failures, and never equate successful execution with model quality."""
    import hashlib
    import json
    import time
    out = ROOT / "reports" / "final"
    out.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    for folder in ("forte_ai", "server", "scripts", "tests", "configs"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.suffix in (".py", ".yaml"):
                digest.update(path.relative_to(ROOT).as_posix().encode())
                digest.update(path.read_bytes())
    signature = digest.hexdigest()
    progress_path = out / "verification.json"
    previous = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
    previous_steps = {x["name"]: x for x in previous.get("steps", [])} if previous.get("source_sha256") == signature and "--resume" in args else {}
    py = venv_python()
    script = lambda name: str(ROOT / "scripts" / name)
    steps = [
        ("tests", [py, "-m", "pytest", "-q", "--junitxml", str(out / "tests.xml")]),
        ("evaluation", [py, script("eval.py"), "--out", str(out), "--note", "Final implementation verification; default configuration; cached perception"]),
        ("offline", [py, script("offline_check.py"), "--no-cache", "--out", str(out / "offline")]),
        ("api", [py, script("api_test.py"), "--timeout", "300", "--out", str(out / "api_test")]),
        ("equivalence", [py, script("contract_equivalence.py")]),
        ("timing", [py, script("timing.py"), "--out", str(out / "timing")]),
        ("robustness-perception", [py, script("robustness.py"), "--perception-only", "--out", str(out / "robustness")]),
        ("robustness", [py, script("robustness.py"), "--out", str(out / "robustness")]),
        ("schema", [py, script("validate_reports.py"), str(out)]),
        ("packaging", [py, script("packaging_check.py")]),
        ("quality-gates", [py, script("final_report.py"), "--check"]),
    ]
    state = {"source_sha256": signature, "steps": [], "ok": False}
    for name, cmd in steps:
        old = previous_steps.get(name)
        if old and old.get("exit_code") == 0:
            entry = dict(old, resumed=True)
            print(f"RESUME: {name} already passed for this source hash", flush=True)
        else:
            print(f"VERIFY STAGE: {name}", flush=True)
            started = time.monotonic()
            code = run(cmd, check=False)
            entry = {"name": name, "exit_code": code, "elapsed_s": round(time.monotonic() - started, 1)}
        state["steps"].append(entry)
        progress_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    state["ok"] = all(x["exit_code"] == 0 for x in state["steps"])
    progress_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print("VERIFY:", "all gates passed" if state["ok"] else "unmet or unverified gates; see FINAL_REPORT.md")
    if not state["ok"]:
        raise SystemExit(2)


def t_clean_cache(args: list[str]) -> None:
    for d in [ROOT / "data" / "cache"]:
        if d.exists():
            shutil.rmtree(d)
            print("removed", d)


TARGETS = {
    "setup": t_setup,
    "download-weights": t_download_weights,
    "test": t_test,
    "eval": t_eval,
    "robustness": t_robustness,
    "timing": t_timing,
    "api-test": t_api_test,
    "offline-check": t_offline_check,
    "verify": t_verify,
    "clean-cache": t_clean_cache,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in TARGETS:
        print(__doc__)
        print("available targets:", ", ".join(TARGETS))
        return 2
    TARGETS[sys.argv[1]](sys.argv[2:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
