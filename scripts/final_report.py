"""Assemble the measured sections of FINAL_REPORT.md from the artifacts under reports/final/.

Every number in the generated tables is read from a file produced by `scripts/run.py verify` (or the
individual targets) — nothing is typed by hand. The narrative sections of FINAL_REPORT.md live in
docs/final_report_narrative.md and are concatenated after the generated block.

Usage: python scripts/final_report.py [--final reports/final] [--out FINAL_REPORT.md]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GATES = [
    ("1. Detection", "LOVO recall 22/22, FP on clean ≤ 1 (catch-all adds ≤ 1)"),
    ("2. Localization", "≥ 80 % within ±2 s, ≥ 95 % within ±5 s; 1–3 valid JPEGs, one within ±1 s"),
    ("3. Classification", "type_id + rule card on every violation; LOVO type accuracy ≥ 80 %"),
    ("4. Grounding", "every citation in kb/rule_cards.json, quotes verbatim (tests), SOURCES.md honest"),
    ("5. Robustness", "verdict agreement ≥ 90 %, timecode within ±3 s ≥ 80 %, roles on flips/rotations"),
    ("6. Time", "≤ 240 s on the longest video; watchdog returns before 300 s"),
    ("7. Offline & local", "HF offline + socket guard run succeeds; audit: no outbound calls, no face models"),
    ("8. Contract", "api-test passes; CLI == package API"),
    ("9. Reproducibility", "fresh clone → README steps → setup/test/eval succeed; Docker build + api-test"),
    ("10. Docs", "all documents exist and are current; FINAL_REPORT has metrics, hardware, per-video, failures, commands"),
]


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def pct(x):
    return "-" if x is None else f"{100 * x:.0f} %"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", default=str(ROOT / "reports" / "final"))
    ap.add_argument("--out", default=str(ROOT / "FINAL_REPORT.md"))
    a = ap.parse_args()
    fd = Path(a.final)
    m = load(fd / "metrics.json") or {}
    rob = load(fd / "robustness" / "summary.json") or {}
    tim = load(fd / "timing" / "timing.json") or {}
    off = load(fd / "offline" / "offline_report.json") or {}
    api = load(fd / "api_test" / "api_test_report.json") or {}
    lines = ["# FINAL REPORT — forte_ai", "", f"Generated from `{fd.relative_to(ROOT).as_posix()}` by `scripts/final_report.py`.", ""]
    lines += [f"Hardware: {m.get('hardware', '-')}; profile `{m.get('profile', '-')}`; VLM {'on' if m.get('vlm_enabled') else 'off'}.", ""]

    def row(name, d):
        if not d:
            return f"| {name} | - | - | - | - | - | - |"
        loc = d.get("localization", {})
        n_v = d.get("n_violation", d.get("tp", 0) + d.get("fn", 0))
        return (
            f"| {name} | {d.get('tp')}/{n_v} | {d.get('fp')} | {d.get('accuracy', 0):.3f} | "
            f"{pct(loc.get('within_1s'))} / {pct(loc.get('within_2s'))} / {pct(loc.get('within_3s'))} / {pct(loc.get('within_5s'))} | "
            f"{loc.get('median_dt', '-')} | {pct(d.get('classification_accuracy'))} |"
        )

    lines += ["## Detection, localization, classification", "", "| setting | recall | FP clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |", "|---|---|---|---|---|---|---|"]
    lines.append(row(f"train, config threshold {m.get('config_threshold')}", m.get("train_config_threshold")))
    lines.append(row(f"train, fitted threshold {m.get('fitted_threshold')}", m.get("train_fitted_threshold")))
    lines.append(row("**leave-one-video-out**", m.get("lovo")))
    lines.append("")
    t = m.get("timing", {})
    lines += ["## Time", "", f"Evaluation run: mean {t.get('mean_s', 0):.1f} s / video, max {t.get('max_s', 0):.1f} s (cached perception)."]
    if tim:
        lines += ["", "| video | duration s | wall s (cold) | within 240 s |", "|---|---|---|---|"]
        for v in tim.get("videos", []):
            lines.append(f"| {v['video_id']} | {v['duration_s']} | {v['wall_s']} | {'yes' if v['within_240'] else 'NO'} |")
        wd = tim.get("watchdog") or {}
        if wd:
            lines.append(f"\nWatchdog (VLM slowed by 25 s per call): wall {wd.get('wall_s')} s, VLM calls {wd.get('vlm_calls')}, skipped by deadline {wd.get('skipped_deadline')}, returned before 300 s: {wd.get('returned_before_300')}.")
    lines.append("")
    if rob:
        lines += ["## Robustness", "", f"Runs: {rob.get('n_runs')}; verdict agreement {pct(rob.get('verdict_agreement'))}; violation timecode within ±{rob.get('tol_s')} s {pct(rob.get('timecode_within_tol'))}; cashier role found {pct(rob.get('role_ok'))}.", "", "| variant | verdict agreement | timecode ±3 s | role ok |", "|---|---|---|---|"]
        for k, v in (rob.get("per_variant") or {}).items():
            lines.append(f"| {k} | {pct(v.get('verdict_agreement'))} | {pct(v.get('timecode_within_tol'))} | {pct(v.get('role_ok'))} |")
        lines.append("")
    lines += ["## Offline & contract", "", f"Offline run: {'PASSED' if off.get('ok') else 'FAILED / not run'}; network attempts: {len(off.get('network_attempts', [])) if off else '-'}; audit hits: {len((off.get('audit') or {}).get('network_calls_in_processing_path', [])) if off else '-'}; face dependencies: {(off.get('audit') or {}).get('face_dependencies', '-') if off else '-'}.", f"API test: {'PASSED' if api.get('ok') else 'FAILED / not run'} ({', '.join(s['name'] + (' ✓' if s['ok'] else ' ✗') for s in api.get('steps', []))}).", ""]
    rows = []
    pv = fd / "per_video.csv"
    if pv.exists():
        import csv

        with open(pv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        lines += ["## Per-video (LOVO)", "", "| id | label | t_label | team type | pred | t_pred | Δt | pred type | ok |", "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['video_id']} | {r['label']} | {r['t_label'] or '-'} | {r['team_type'] or '-'} | {r['pred_lovo']} | {r['t_pred_lovo'] or '-'} | {r['dt_lovo'] or '-'} | {r['pred_type_lovo'] or '-'} | {r['type_ok_lovo'] or '-'} |")
        lines.append("")
    narrative = ROOT / "docs" / "final_report_narrative.md"
    if narrative.exists():
        lines += [narrative.read_text(encoding="utf-8")]
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
