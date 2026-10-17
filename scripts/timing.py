"""`make timing`: end-to-end and per-stage timing on the 3 longest videos, cold cache, plus the watchdog test
(simulated slow VLM must still return a result before 300 s).

Usage: python scripts/timing.py [--out reports/timing] [--n 3] [--profile gpu-small] [--skip-watchdog]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.labels import read_labels_csv  # noqa: E402
from forte_ai.video import probe  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "timing"))
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--skip-watchdog", action="store_true")
    ap.add_argument("--deadline", type=float, default=240)
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [r for r in read_labels_csv(ROOT / "data" / "labels.csv") if r.path]
    durs = {r.video_id: probe(ROOT / r.path).duration_s for r in rows}
    # de-duplicate identical content
    seen, longest = set(), []
    for r in sorted(rows, key=lambda r: -durs[r.video_id]):
        if r.content_md5 in seen:
            continue
        seen.add(r.content_md5)
        longest.append(r)
        if len(longest) >= a.n:
            break

    from forte_ai.analyzer import Analyzer

    an = Analyzer(profile=a.profile)
    an.warmup()
    report = {"profile": an.cfg.profile, "deadline_s": a.deadline, "videos": [], "watchdog": None}
    for r in longest:
        t0 = time.time()
        res = an.analyze(ROOT / r.path, deadline_sec=a.deadline, use_cache=False)  # cold: no perception cache
        wall = time.time() - t0
        entry = {"video_id": r.video_id, "duration_s": round(durs[r.video_id], 1), "wall_s": round(wall, 1), "stage_timings": res["stage_timings"], "vlm": {k: v for k, v in res.get("vlm", {}).items() if k in ("calls", "cached", "skipped_deadline")}, "within_240": wall <= 240}
        report["videos"].append(entry)
        print(json.dumps(entry), flush=True)
    report["max_wall_s"] = max(v["wall_s"] for v in report["videos"]) if report["videos"] else None
    report["gate_time_le_240"] = all(v["within_240"] for v in report["videos"])

    if not a.skip_watchdog and an.vlm is not None:
        # Watchdog: make every VLM call artificially slow and prove the result still arrives before 300 s.
        import forte_ai.vlm.verifier as V

        real_generate = V.VLMVerifier._generate

        def slow_generate(self, frames, prompt):
            time.sleep(25.0)
            return real_generate(self, frames, prompt)

        V.VLMVerifier._generate = slow_generate
        try:
            an.vlm.cache_dir = out / "vlm_cache_watchdog"  # do not reuse cached answers
            an.vlm.cache_dir.mkdir(parents=True, exist_ok=True)
            r = longest[0]
            t0 = time.time()
            res = an.analyze(ROOT / r.path, deadline_sec=a.deadline, use_cache=True)
            wall = time.time() - t0
            report["watchdog"] = {"video_id": r.video_id, "wall_s": round(wall, 1), "vlm_calls": res["vlm"]["calls"], "skipped_deadline": res["vlm"]["skipped_deadline"], "returned_before_300": wall < 300, "verdict": res["verdict"]}
            print("watchdog:", json.dumps(report["watchdog"]), flush=True)
        finally:
            V.VLMVerifier._generate = real_generate
    (out / "timing.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out / "timing.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
