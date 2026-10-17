"""Phase 4 QA: run calibration on every cached video and write analysis/roles_qa.md.

Checks per video: cashier track found, its score and margin, window anchor presence, empty-start mode,
counter confidence. Videos where the roles look unreliable are listed for manual review.
Usage: python scripts/roles_qa.py [--profile gpu-small]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.config import Config  # noqa: E402
from forte_ai.events.primitives import build_frame_states  # noqa: E402
from forte_ai.events.rules import extract_events  # noqa: E402
from forte_ai.labels import read_labels_csv  # noqa: E402
from forte_ai.perception.pipeline import PerceptionEngine  # noqa: E402
from forte_ai.perception.roles import calibrate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="gpu-small")
    a = ap.parse_args()
    cfg = Config.load(profile=a.profile)
    eng = PerceptionEngine(cfg)
    rows = [r for r in read_labels_csv(ROOT / "data" / "labels.csv") if r.path]
    lines = [
        "# Roles & zones QA",
        "",
        "Per-video calibration summary (behaviour-based; see forte_ai/perception/roles.py). `empty_start` means",
        "nobody was at the workplace in the first seconds — там выбранный 'cashier'-трек на самом деле вошедший",
        "посторонний, и правила переключаются в режим R10 (вход в пустой кассовый узел).",
        "",
        "| id | label | cashier T | score | margin | presence | window anchor | counter conf | empty start | notes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    flagged = []
    for r in rows:
        pr = eng.run(ROOT / r.path, use_cache=True)
        cal = calibrate(pr.frames, pr.poses, pr.tracks, pr.per_frame_tracks, cfg.section("roles"), pr.det_width, pr.det_height)
        pc = dict(cfg.section("roles"))
        pc.update(cfg.section("rules"))
        pc["kpt_threshold"] = cfg.get("perception.pose.kpt_threshold", 0.3)
        states = build_frame_states(pr, cal, pc)
        rc = dict(cfg.section("rules"))
        rc.setdefault("counter_margin_frac", cfg.get("roles.counter_margin_frac", 0.06))
        ev = extract_events(states, cal, rc, pr.sample_fps, pr.video["duration_s"])
        scores = sorted((v["score"] for v in cal.track_scores.values()), reverse=True)
        margin = (scores[0] - scores[1]) if len(scores) > 1 else 1.0
        presence = cal.track_scores.get(cal.cashier_track, {}).get("presence", 0.0) if cal.cashier_track else 0.0
        note = "; ".join(cal.notes)
        if cal.cashier_track is None or (presence < 0.4 and not ev.empty_start) or (margin < 0.05 and not ev.empty_start):
            flagged.append(r.video_id)
            note = (note + "; " if note else "") + "FLAGGED"
        lines.append(
            f"| {r.video_id} | {r.label or '-'} | {cal.cashier_track} | {cal.cashier_score:.2f} | {margin:.2f} | {presence:.2f} | "
            f"{'yes' if cal.window_anchor else 'no'} | {cal.counter_confidence:.2f} | {'YES' if ev.empty_start else ''} | {note} |"
        )
        print(lines[-1], flush=True)
    lines += ["", f"Flagged for manual check: {flagged or 'none'}", "", "Flip/rotation invariance of the role logic is covered by tests/test_roles.py; end-to-end invariance is measured by `make robustness` (reports/robustness)."]
    out = ROOT / "analysis" / "roles_qa.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", out, "flagged:", flagged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
