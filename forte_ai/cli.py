"""Command-line interface.

  python -m forte_ai analyze <video.mov> --out result.json [--evidence-dir dir] [--profile auto|gpu-large|gpu-small|cpu]
  python -m forte_ai batch <dir> --out results/
  python -m forte_ai eval --labels data/labels.csv --videos public/ --out reports/
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
import time
from pathlib import Path


def _write_result(result: dict, out: Path, evidence_dir: Path | None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if evidence_dir:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        for i, v in enumerate(result.get("violations", [])):
            for j, f in enumerate(v["evidence_frames"]):
                p = evidence_dir / f"{out.stem}_v{i + 1}_f{j + 1}_{f['timestamp_sec']:.1f}s.jpg"
                p.write_bytes(base64.b64decode(f["image_base64"]))
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


def _progress_printer(fraction: float, msg: str) -> None:
    sys.stderr.write(f"\r[{fraction * 100:5.1f}%] {msg:<60}")
    sys.stderr.flush()
    if fraction >= 1.0:
        sys.stderr.write("\n")


def cmd_analyze(a) -> int:
    from .analyzer import Analyzer
    from .schema import validate_result

    overrides = {}
    if a.no_vlm:
        overrides = {"vlm": {"enabled": False}}
    an = Analyzer(device=a.device, config=(a.config or (overrides or None)), profile=a.profile)
    if overrides and a.config:
        an.cfg.set("vlm.enabled", False)
    t0 = time.time()
    res = an.analyze(a.video, on_progress=_progress_printer if not a.quiet else None, deadline_sec=a.deadline, use_cache=not a.no_cache, collect_all=a.collect_all)
    problems = validate_result(res)
    _write_result(res, Path(a.out), Path(a.evidence_dir) if a.evidence_dir else None)
    n = len(res["violations"])
    print(f"{Path(a.video).name}: verdict={res['verdict']} violations={n} time={time.time() - t0:.1f}s -> {a.out}")
    for v in res["violations"]:
        print(f"  - {v['timecode_sec']:7.2f}s  {v['type_id']:<32} conf={v['confidence']:.2f}  {v['type']}")
    if problems:
        print("SCHEMA PROBLEMS:", *problems, sep="\n  ")
        return 3
    return 0


def cmd_batch(a) -> int:
    from .analyzer import Analyzer

    an = Analyzer(device=a.device, config=a.config, profile=a.profile)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    vids = sorted(p for p in Path(a.dir).iterdir() if p.suffix.lower() in (".mov", ".mp4"))
    rows = []
    for p in vids:
        t0 = time.time()
        try:
            res = an.analyze(p, deadline_sec=a.deadline, use_cache=not a.no_cache)
            _write_result(res, out / f"{p.stem}.json", (out / "evidence") if a.evidence else None)
            rows.append((p.name, res["verdict"], len(res["violations"]), round(time.time() - t0, 1)))
        except Exception as e:  # noqa: BLE001
            rows.append((p.name, f"ERROR {e}", 0, round(time.time() - t0, 1)))
        print(rows[-1], flush=True)
    (out / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


def cmd_eval(a) -> int:
    from scripts_bridge import run_eval  # type: ignore

    return run_eval(a)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="forte_ai", description="Fully local cash-desk violation detector")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--profile", default=None, help="auto|gpu-large|gpu-small|cpu")
        p.add_argument("--config", default=None, help="YAML config overriding configs/default.yaml")
        p.add_argument("--device", default="auto")
        p.add_argument("--deadline", type=float, default=None, help="seconds (default from config: 240)")
        p.add_argument("--no-cache", action="store_true")
        p.add_argument("--no-vlm", action="store_true")
        p.add_argument("-v", "--verbose", action="store_true")

    p = sub.add_parser("analyze", help="analyze one video")
    p.add_argument("video")
    p.add_argument("--out", required=True)
    p.add_argument("--evidence-dir", default=None)
    p.add_argument("--collect-all", action="store_true", help="also store all candidates (debug/eval)")
    p.add_argument("--quiet", action="store_true")
    common(p)
    p.set_defaults(fn=cmd_analyze)

    p = sub.add_parser("batch", help="analyze every video in a directory")
    p.add_argument("dir")
    p.add_argument("--out", required=True)
    p.add_argument("--evidence", action="store_true")
    common(p)
    p.set_defaults(fn=cmd_batch)

    p = sub.add_parser("eval", help="evaluate on the labeled set (delegates to scripts/eval.py)")
    p.add_argument("--labels", default="data/labels.csv")
    p.add_argument("--videos", default="public")
    p.add_argument("--out", default="reports")
    common(p)
    p.set_defaults(fn=None)

    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if getattr(a, "verbose", False) else logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if a.cmd == "eval":
        import runpy

        sys.argv = ["scripts/eval.py", "--labels", a.labels, "--videos", a.videos, "--out", a.out] + (["--profile", a.profile] if a.profile else []) + (["--no-vlm"] if a.no_vlm else [])
        root = Path(__file__).resolve().parents[1]
        runpy.run_path(str(root / "scripts" / "eval.py"), run_name="__main__")
        return 0
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
