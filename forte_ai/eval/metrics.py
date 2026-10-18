"""Pure metric functions over per-video candidate lists (no models here; unit-testable)."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

LOCALIZATION_TOLERANCES = (1.0, 2.0, 3.0, 5.0)


@dataclass
class PerVideo:
    video_id: int
    label: str  # violation | no_violation
    t_label: Optional[float]
    group: str  # LOVO group (content md5)
    candidates: list[dict]  # {type_id, t_event, confidence, source}
    team_type: Optional[str] = None  # team-assigned type for the labeled event
    elapsed_s: float = 0.0
    stage_timings: dict = field(default_factory=dict)


def select_by_threshold(cands: list[dict], thr: float, per_type: Optional[dict] = None, max_n: int = 6) -> list[dict]:
    per_type = per_type or {}
    keep = [c for c in cands if c.get("eligible", True) and float(c["confidence"]) >= float(per_type.get(c["type_id"], thr))]
    keep.sort(key=lambda c: -float(c["confidence"]))
    return sorted(keep[:max_n], key=lambda c: c["t_event"])


def video_outcome(pv: PerVideo, thr: float, per_type: Optional[dict] = None, max_n: int = 6) -> dict:
    chosen = select_by_threshold(pv.candidates, thr, per_type, max_n)
    pred = "violation" if chosen else "no_violation"
    out = {"video_id": pv.video_id, "label": pv.label, "t_label": pv.t_label, "pred": pred, "n_pred": len(chosen), "t_pred": None, "dt": None, "pred_type": None, "team_type": pv.team_type, "type_ok": None, "pred_events": [(c["type_id"], round(c["t_event"], 2), round(float(c["confidence"]), 3)) for c in chosen]}
    if pv.label == "violation" and chosen and pv.t_label is not None:
        best = min(chosen, key=lambda c: abs(c["t_event"] - pv.t_label))
        out["t_pred"] = round(best["t_event"], 2)
        out["dt"] = round(abs(best["t_event"] - pv.t_label), 2)
        out["pred_type"] = best["type_id"]
        if pv.team_type:
            out["type_ok"] = best["type_id"] == pv.team_type
    return out


def compute_metrics(pvs: list[PerVideo], thr: float, per_type: Optional[dict] = None, max_n: int = 6, loc_tol_for_recall: Optional[float] = None) -> dict:
    """Video-level + localization + classification metrics for a fixed threshold."""
    rows = [video_outcome(pv, thr, per_type, max_n) for pv in pvs]
    viol = [r for r in rows if r["label"] == "violation"]
    clean = [r for r in rows if r["label"] == "no_violation"]
    tp = sum(1 for r in viol if r["pred"] == "violation")
    fn = len(viol) - tp
    fp = sum(1 for r in clean if r["pred"] == "violation")
    tn = len(clean) - fp
    dts = [r["dt"] for r in viol if r["dt"] is not None]
    loc = {f"within_{int(t)}s": (sum(1 for d in dts if d <= t) / len(dts) if dts else 0.0) for t in LOCALIZATION_TOLERANCES}
    loc["median_dt"] = statistics.median(dts) if dts else None
    loc["n"] = len(dts)
    typed = [r for r in viol if r["type_ok"] is not None]
    cls_acc = (sum(1 for r in typed if r["type_ok"]) / len(typed)) if typed else None
    out = {
        "threshold": thr,
        "n_videos": len(rows),
        "n_violation": len(viol),
        "n_clean": len(clean),
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "accuracy": (tp + tn) / len(rows) if rows else 0.0,
        "recall_violation": tp / len(viol) if viol else 0.0,
        "fp_rate_clean": fp / len(clean) if clean else 0.0,
        "localization": loc,
        "classification_accuracy": cls_acc,
        "classification_n": len(typed),
        "rows": rows,
    }
    if loc_tol_for_recall is not None:
        out["recall_within_tol"] = (sum(1 for d in dts if d <= loc_tol_for_recall) / len(viol)) if viol else 0.0
    return out


def fit_threshold(pvs: list[PerVideo], grid: Optional[list[float]] = None, max_n: int = 6, loc_tol: float = 5.0) -> float:
    """Objective: recall on violation videos (events within loc_tol of the label) first, then fewest FPs.
    Among equally good thresholds the median one is returned (middle of the feasible interval), which
    leaves margin both for unseen violations with lower confidence and for unseen false positives."""
    grid = grid or [round(0.05 * i, 2) for i in range(1, 20)]
    scored = []
    for thr in grid:
        m = compute_metrics(pvs, thr, None, max_n, loc_tol_for_recall=loc_tol)
        scored.append(((m["recall_within_tol"], m["recall_violation"], -m["fp"]), thr))
    best_key = max(k for k, _ in scored)
    optimal = sorted(thr for k, thr in scored if k == best_key)
    return optimal[len(optimal) // 2]


def lovo_evaluate(pvs: list[PerVideo], max_n: int = 6, loc_tol: float = 5.0) -> dict:
    """Leave-one-video-out: for every content group, fit the threshold on the other groups and apply it to the
    held-out videos. Returns per-video rows (with the fold threshold) and aggregate metrics."""
    groups = sorted({pv.group for pv in pvs})
    rows = []
    fold_thr = {}
    for g in groups:
        train = [pv for pv in pvs if pv.group != g]
        held = [pv for pv in pvs if pv.group == g]
        thr = fit_threshold(train, max_n=max_n, loc_tol=loc_tol)
        fold_thr[g] = thr
        for pv in held:
            r = video_outcome(pv, thr, None, max_n)
            r["fold_threshold"] = thr
            rows.append(r)
    # aggregate exactly like compute_metrics but from precomputed rows
    viol = [r for r in rows if r["label"] == "violation"]
    clean = [r for r in rows if r["label"] == "no_violation"]
    tp = sum(1 for r in viol if r["pred"] == "violation")
    fp = sum(1 for r in clean if r["pred"] == "violation")
    dts = [r["dt"] for r in viol if r["dt"] is not None]
    loc = {f"within_{int(t)}s": (sum(1 for d in dts if d <= t) / len(dts) if dts else 0.0) for t in LOCALIZATION_TOLERANCES}
    loc["median_dt"] = statistics.median(dts) if dts else None
    loc["n"] = len(dts)
    typed = [r for r in viol if r["type_ok"] is not None]
    return {
        "n_folds": len(groups),
        "fold_thresholds": fold_thr,
        "tp": tp,
        "fn": len(viol) - tp,
        "fp": fp,
        "tn": len(clean) - fp,
        "accuracy": (tp + len(clean) - fp) / len(rows) if rows else 0.0,
        "recall_violation": tp / len(viol) if viol else 0.0,
        "fp_rate_clean": fp / len(clean) if clean else 0.0,
        "localization": loc,
        "classification_accuracy": (sum(1 for r in typed if r["type_ok"]) / len(typed)) if typed else None,
        "classification_n": len(typed),
        "rows": sorted(rows, key=lambda r: r["video_id"]),
    }


def confusion_by_type(rows: list[dict]) -> dict:
    """team_type -> {pred_type: count} for detected violation videos."""
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        if r["label"] != "violation" or not r.get("team_type"):
            continue
        out.setdefault(r["team_type"], {})
        key = r["pred_type"] or "(missed)"
        out[r["team_type"]][key] = out[r["team_type"]].get(key, 0) + 1
    return out
