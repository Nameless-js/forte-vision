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
        run([py, "-m", "pip", "install", "torch==2.6.0", "torchvision==0.21.0"])
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
        run([py, "-m", "pip", "install", "-r", str(req)])
    run([py, "-m", "pip", "install", "-e", f"{ROOT}[dev]", "--no-deps"])
    run([py, str(ROOT / "scripts" / "build_labels.py")])
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
    t_test([])
    t_eval(["--out", str(ROOT / "reports" / "final")])
    t_robustness(["--out", str(ROOT / "reports" / "final" / "robustness")])
    t_timing(["--out", str(ROOT / "reports" / "final" / "timing")])
    t_offline_check(["--out", str(ROOT / "reports" / "final" / "offline")])
    t_api_test(["--out", str(ROOT / "reports" / "final" / "api_test")])
    run([venv_python(), str(ROOT / "scripts" / "validate_reports.py"), str(ROOT / "reports" / "final")])
    print("\nVERIFY: all steps passed")


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
