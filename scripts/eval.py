"""Evaluation on the labeled set (Section 11): train-fitted and leave-one-video-out metrics.

Usage: python scripts/eval.py [--out reports/iter_001] [--profile gpu-small] [--no-vlm] [--ids 1 2 ...] [--no-cache]
Writes: metrics.json, per_video.csv, README.md, results/<id>.json (full results, gitignored), candidates.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import platform
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.eval.metrics import PerVideo, compute_metrics, confusion_by_type, fit_threshold, lovo_evaluate  # noqa: E402
from forte_ai.labels import read_labels_csv  # noqa: E402
from forte_ai.schema import validate_result  # noqa: E402


def next_iter_dir(reports: Path) -> Path:
    nums = [int(m.group(1)) for p in reports.glob("iter_*") if (m := re.match(r"iter_(\d+)", p.name))]
    return reports / f"iter_{(max(nums) + 1 if nums else 1):03d}"


def load_team_types(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for a in d.get("assignments", []):
        out[int(a["id"])] = a["type_id"]
    return out


def hardware_string() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            return f"{p.name} ({p.total_memory / 1e9:.1f} GB), torch {torch.__version__}, {platform.platform()}"
    except Exception:
        pass
    return platform.platform()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(ROOT / "data" / "labels.csv"))
    ap.add_argument("--videos", default=str(ROOT / "public"))
    ap.add_argument("--out", default=None, help="report dir (default: next reports/iter_XXX)")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--no-vlm", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--ids", nargs="*", type=int)
    ap.add_argument("--taxonomy", default=str(ROOT / "analysis" / "taxonomy.json"))
    ap.add_argument("--deadline", type=float, default=None)
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    from forte_ai.analyzer import Analyzer

    out = Path(a.out) if a.out else next_iter_dir(ROOT / "reports")
    (out / "results").mkdir(parents=True, exist_ok=True)
    rows = [r for r in read_labels_csv(Path(a.labels)) if r.split == "labeled" and r.path]
    if a.ids:
        rows = [r for r in rows if r.video_id in a.ids]
    team = load_team_types(Path(a.taxonomy))
    overrides = {"vlm": {"enabled": False}} if a.no_vlm else None
    an = Analyzer(config=(a.config or overrides), profile=a.profile)
    if a.no_vlm and a.config:
        an.cfg.set("vlm.enabled", False)
        an.vlm = None
    cfg_thr = float(an.cfg.get("verdict.threshold", 0.5))
    max_n = int(an.cfg.get("rules.max_violations_per_video", 6))

    pvs: list[PerVideo] = []
    schema_problems = {}
    t_all = time.time()
    for i, r in enumerate(rows):
        vp = ROOT / r.path
        t0 = time.time()
        try:
            res = an.analyze(vp, deadline_sec=a.deadline, use_cache=not a.no_cache, collect_all=True)
        except Exception as e:  # noqa: BLE001
            print(f"[{i + 1}/{len(rows)}] id {r.video_id}: ERROR {e}", flush=True)
            pvs.append(PerVideo(r.video_id, r.label, r.t_sec, r.content_md5 or str(r.video_id), [], team.get(r.video_id), time.time() - t0, {}))
            continue
        el = time.time() - t0
        probs = validate_result(res)
        if probs:
            schema_problems[r.video_id] = probs
        (out / "results" / f"{r.video_id:02d}.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        cands = res.get("candidates_all", [])
        pvs.append(PerVideo(r.video_id, r.label, r.t_sec, r.content_md5 or str(r.video_id), cands, team.get(r.video_id), el, res.get("stage_timings", {})))
        ev = ", ".join(f"{c['type_id']}@{c['t_event']:.1f}({c['confidence']:.2f})" for c in sorted(cands, key=lambda c: -c["confidence"])[:4])
        print(f"[{i + 1}/{len(rows)}] id {r.video_id:>2} {r.label:<12} t={r.t_sec if r.t_sec is not None else '-':<5} verdict={res['verdict']:<12} {el:5.1f}s  {ev}", flush=True)
    total_wall = time.time() - t_all

    # ---- metrics
    fitted_thr = fit_threshold(pvs, max_n=max_n)
    train_cfg = compute_metrics(pvs, cfg_thr, an.cfg.get("verdict.per_type_thresholds", {}), max_n)
    train_fit = compute_metrics(pvs, fitted_thr, None, max_n)
    lovo = lovo_evaluate(pvs, max_n=max_n)
    times = [pv.elapsed_s for pv in pvs]
    longest = max(pvs, key=lambda pv: pv.elapsed_s) if pvs else None
    stage_sum: dict[str, list[float]] = {}
    for pv in pvs:
        for k, v in pv.stage_timings.items():
            stage_sum.setdefault(k, []).append(float(v))
    metrics = {
        "note": a.note,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware": hardware_string(),
        "profile": an.cfg.profile,
        "vlm_enabled": an.vlm is not None,
        "n_videos": len(pvs),
        "config_threshold": cfg_thr,
        "fitted_threshold": fitted_thr,
        "train_config_threshold": {k: v for k, v in train_cfg.items() if k != "rows"},
        "train_fitted_threshold": {k: v for k, v in train_fit.items() if k != "rows"},
        "lovo": {k: v for k, v in lovo.items() if k != "rows"},
        "type_confusion_train": confusion_by_type(train_cfg["rows"]),
        "type_confusion_lovo": confusion_by_type(lovo["rows"]),
        "timing": {"mean_s": sum(times) / len(times) if times else 0, "max_s": max(times) if times else 0, "max_video": longest.video_id if longest else None, "total_wall_s": total_wall, "stage_mean": {k: sum(v) / len(v) for k, v in stage_sum.items()}, "stage_max": {k: max(v) for k, v in stage_sum.items()}},
        "schema_problems": schema_problems,
        "team_types_available": bool(team),
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "candidates.json").write_text(json.dumps([{"video_id": pv.video_id, "label": pv.label, "t_label": pv.t_label, "group": pv.group, "team_type": pv.team_type, "candidates": pv.candidates} for pv in pvs], ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- per-video table (config threshold, fitted threshold and LOVO verdicts side by side)
    lovo_rows = {r["video_id"]: r for r in lovo["rows"]}
    fit_rows = {r["video_id"]: r for r in train_fit["rows"]}
    with open(out / "per_video.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["video_id", "label", "t_label", "team_type", "pred_cfg", "pred_fit", "pred_lovo", "lovo_thr", "t_pred_lovo", "dt_lovo", "pred_type_lovo", "type_ok_lovo", "elapsed_s", "top_candidates"])
        for r in train_cfg["rows"]:
            vid = r["video_id"]
            lr = lovo_rows[vid]
            pv = next(p for p in pvs if p.video_id == vid)
            top = "; ".join(f"{c['type_id']}@{c['t_event']:.1f}:{c['confidence']:.2f}" for c in sorted(pv.candidates, key=lambda c: -c["confidence"])[:5])
            w.writerow([vid, r["label"], r["t_label"], r["team_type"], r["pred"], fit_rows[vid]["pred"], lr["pred"], lr["fold_threshold"], lr["t_pred"], lr["dt"], lr["pred_type"], lr["type_ok"], round(pv.elapsed_s, 1), top])

    # ---- README
    def fmt(m):
        loc = m["localization"]
        return (
            f"| {m['tp']}/{m['n_violation'] if 'n_violation' in m else m['tp'] + m['fn']} | {m['fp']} | {m['accuracy']:.3f} | "
            f"{loc['within_1s']:.2f} / {loc['within_2s']:.2f} / {loc['within_3s']:.2f} / {loc['within_5s']:.2f} | {loc['median_dt'] if loc['median_dt'] is not None else '-'} | "
            f"{(f'{m[chr(99) + chr(108) + chr(97) + chr(115) + chr(115) + chr(105) + chr(102) + chr(105) + chr(99) + chr(97) + chr(116) + chr(105) + chr(111) + chr(110) + chr(95) + chr(97) + chr(99) + chr(99) + chr(117) + chr(114) + chr(97) + chr(99) + chr(121)]:.2f}' if m.get('classification_accuracy') is not None else '-')} |"
        )

    lines = [
        f"# Evaluation report — {out.name}",
        "",
        f"Created {metrics['created']} on {metrics['hardware']}; profile `{metrics['profile']}`, VLM {'on' if metrics['vlm_enabled'] else 'off'}. {a.note}",
        "",
        f"Videos: {len(pvs)} ({train_cfg['n_violation']} violation / {train_cfg['n_clean']} clean). Config threshold {cfg_thr}; fitted threshold {fitted_thr}; LOVO folds {lovo['n_folds']}.",
        "",
        "| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |",
        "|---|---|---|---|---|---|---|",
        f"| train, config threshold {fmt(train_cfg)}",
        f"| train, fitted threshold {fmt(train_fit)}",
        f"| **LOVO** {fmt(lovo)}",
        "",
        f"Timing: mean {metrics['timing']['mean_s']:.1f} s, max {metrics['timing']['max_s']:.1f} s (video {metrics['timing']['max_video']}); total wall {total_wall:.0f} s.",
        f"Schema problems: {len(schema_problems)} video(s).",
        "",
        "## Per-video (LOVO)",
        "",
        "| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in lovo["rows"]:
        ev = ", ".join(f"{t}@{tt}({c})" for t, tt, c in r["pred_events"][:3])
        lines.append(f"| {r['video_id']} | {r['label']} | {r['t_label'] if r['t_label'] is not None else '-'} | {r['team_type'] or '-'} | {r['pred']} | {r['fold_threshold']} | {r['t_pred'] if r['t_pred'] is not None else '-'} | {r['dt'] if r['dt'] is not None else '-'} | {r['pred_type'] or '-'} | {'' if r['type_ok'] is None else ('yes' if r['type_ok'] else 'no')} | {ev} |")
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:12]))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
