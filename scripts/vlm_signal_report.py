"""Measure how informative the local VLM answers are, per candidate type (Layer C calibration aid).

For every candidate in reports/<iter>/candidates.json that carries a VLM answer, the candidate is marked
POSITIVE if it lies in a violation video within ±tol s of the labeled time, NEGATIVE if it is in a clean video
(candidates far from the label in violation videos are ignored: they may be real secondary events).
The report tabulates answer distributions per (engine type, answer key) and a simple separability score, so
that only VLM signals that actually discriminate are used to move confidences.

Usage: python scripts/vlm_signal_report.py reports/iter_013 [--tol 5]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

KEYS = ["counted_money", "id_shown", "cashier_left", "phone_visible", "unauthorized_person", "bag_checked", "safe_open", "cash_handover"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report_dir")
    ap.add_argument("--tol", type=float, default=5.0)
    a = ap.parse_args()
    d = Path(a.report_dir)
    items = json.loads((d / "candidates.json").read_text(encoding="utf-8"))
    table: dict[tuple[str, str], dict[str, Counter]] = defaultdict(lambda: {"pos": Counter(), "neg": Counter()})
    verdicts: dict[str, dict[str, Counter]] = defaultdict(lambda: {"pos": Counter(), "neg": Counter()})
    n_with = 0
    for it in items:
        for c in it["candidates"]:
            v = c.get("vlm") or {}
            ans = v.get("answer")
            if not ans:
                continue
            n_with += 1
            et = c.get("type_id_engine", c["type_id"])
            if it["label"] == "violation":
                if it["t_label"] is None or abs(c["t_event"] - it["t_label"]) > a.tol:
                    continue
                side = "pos"
            else:
                side = "neg"
            verdicts[et][side][v.get("verdict", "?")] += 1
            for k in KEYS:
                table[(et, k)][side][str(ans.get(k, "?"))] += 1
    lines = [f"# VLM signal report — {d.name}", "", f"candidates with a VLM answer: {n_with}; POS = within ±{a.tol:g} s of the label in a violation video, NEG = any candidate in a clean video.", ""]
    lines += ["## Verdicts (reject / support / neutral) per engine type", "", "| type | POS verdicts | NEG verdicts |", "|---|---|---|"]
    for et, sides in sorted(verdicts.items()):
        lines.append(f"| {et} | {dict(sides['pos'])} | {dict(sides['neg'])} |")
    lines += ["", "## Answer distributions (only keys whose answers differ between POS and NEG)", "", "| type | key | POS | NEG | separability |", "|---|---|---|---|---|"]
    for (et, k), sides in sorted(table.items()):
        pos, neg = sides["pos"], sides["neg"]
        npos, nneg = sum(pos.values()), sum(neg.values())
        if npos == 0 or nneg == 0:
            continue
        vals = set(pos) | set(neg)
        # total-variation distance between the two answer distributions (0 = identical, 1 = disjoint)
        tv = 0.5 * sum(abs(pos[v] / npos - neg[v] / nneg) for v in vals)
        if tv < 0.15:
            continue
        lines.append(f"| {et} | {k} | {dict(pos)} | {dict(neg)} | {tv:.2f} |")
    # ---- choice mode: p_violation per type, POS vs NEG, with a rank AUC
    pv: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"pos": [], "neg": []})
    for it in items:
        for c in it["candidates"]:
            v = c.get("vlm") or {}
            if v.get("mode") != "choice" or v.get("p_violation") is None:
                continue
            et = c.get("type_id_engine", c["type_id"])
            if it["label"] == "violation":
                if it["t_label"] is None or abs(c["t_event"] - it["t_label"]) > a.tol:
                    continue
                pv[et]["pos"].append(float(v["p_violation"]))
            else:
                pv[et]["neg"].append(float(v["p_violation"]))
    if pv:
        lines += ["", "## Choice mode: p_violation (POS vs NEG)", "", "| type | n POS | mean POS | n NEG | mean NEG | AUC |", "|---|---|---|---|---|---|"]
        allp, alln = [], []
        for et, s in sorted(pv.items()):
            p, n = s["pos"], s["neg"]
            allp += p
            alln += n
            auc = "-"
            if p and n:
                wins = sum((1.0 if x > y else 0.5 if x == y else 0.0) for x in p for y in n)
                auc = f"{wins / (len(p) * len(n)):.2f}"
            lines.append(f"| {et} | {len(p)} | {sum(p) / len(p) if p else float('nan'):.2f} | {len(n)} | {sum(n) / len(n) if n else float('nan'):.2f} | {auc} |")
        if allp and alln:
            wins = sum((1.0 if x > y else 0.5 if x == y else 0.0) for x in allp for y in alln)
            lines.append(f"| **all** | {len(allp)} | {sum(allp) / len(allp):.2f} | {len(alln)} | {sum(alln) / len(alln):.2f} | {wins / (len(allp) * len(alln)):.2f} |")
    out = d / "vlm_signal.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
