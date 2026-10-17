"""Result assembly: ТЗ §10 JSON (+ engine extras), evidence frames (clean + annotated), Russian descriptions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .kb import KnowledgeBase, RuleCard
from .video import encode_jpeg_base64, frame_at


@dataclass
class Candidate:
    """A rule/VLM candidate violation (Layer B/C output) before reporting."""

    type_id: str
    t_event: float
    t_window: tuple[float, float]
    confidence: float
    facts: list[str] = field(default_factory=list)
    rule_id: str = ""
    description_ru: str = ""  # optional VLM-written "what is visible"
    vlm: Optional[dict] = None
    annotate: dict = field(default_factory=dict)  # drawing hints: boxes {label: xyxy (det px)}, scale
    source: str = "rules"  # rules | vlm_catch_all

    def key(self) -> tuple:
        return (self.type_id, round(self.t_event, 1))


def fmt_sec_ru(t: float) -> str:
    """Russian decimal comma, one decimal: 44.2 -> '44,2'."""
    return f"{t:.1f}".replace(".", ",")


def description_ru(card: RuleCard, cand: Candidate, doc_short: str) -> str:
    """Template description: observable facts first, then why it may be a violation, then the clause."""
    t = fmt_sec_ru(cand.t_event)
    facts = "; ".join(f for f in cand.facts if f) if cand.facts else ""
    if cand.description_ru:
        seen = cand.description_ru.strip().rstrip(".")
    else:
        seen = f"На {t} с: {card.observed_as_ru.rstrip('.')}"
    parts = [seen + "."]
    if facts:
        parts.append(f"Зафиксированные признаки: {facts}.")
    why = f"Это может указывать на нарушение «{card.name_ru}» ({doc_short}, {card.clause})."
    parts.append(why)
    if card.mapping_note_ru:
        parts.append(card.mapping_note_ru)
    parts.append("Вывод требует проверки человеком; система описывает только наблюдаемые на видео действия.")
    return " ".join(parts)


def _draw_annotations(img: np.ndarray, ann: dict, scale: float) -> np.ndarray:
    out = img.copy()
    colors = {"cashier": (0, 200, 0), "client": (255, 160, 0), "collector": (200, 0, 200), "cash": (0, 215, 255), "phone": (0, 0, 255), "bag": (200, 0, 200), "document": (255, 255, 255), "zone": (0, 200, 0), "counter": (255, 255, 0), "hand": (0, 0, 255)}
    s = 1.0 / scale if scale else 1.0
    for label, geom in ann.get("boxes", {}).items():
        x1, y1, x2, y2 = [int(round(v * s)) for v in geom]
        c = colors.get(label.split("#")[0], (200, 200, 200))
        cv2.rectangle(out, (x1, y1), (x2, y2), c, 2)
        cv2.putText(out, label, (x1, max(14, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1, cv2.LINE_AA)
    for pt in ann.get("points", []):
        x, y = [int(round(v * s)) for v in pt[:2]]
        cv2.circle(out, (x, y), 6, colors["hand"], -1)
    poly = ann.get("zone")
    if poly and len(poly) >= 3:
        pts = np.asarray([[int(round(x * s)), int(round(y * s))] for x, y in poly], np.int32).reshape(-1, 1, 2)
        cv2.polylines(out, [pts], True, colors["zone"], 1)
    line = ann.get("counter")
    if line:
        (x1, y1), (x2, y2) = line
        cv2.line(out, (int(x1 * s), int(y1 * s)), (int(x2 * s), int(y2 * s)), colors["counter"], 1)
    arrow = ann.get("arrow")
    if arrow:
        (x1, y1), (x2, y2) = arrow
        cv2.arrowedLine(out, (int(x1 * s), int(y1 * s)), (int(x2 * s), int(y2 * s)), (0, 0, 255), 2, tipLength=0.2)
    text = ann.get("text")
    if text:
        cv2.rectangle(out, (0, out.shape[0] - 26), (min(out.shape[1], 12 * len(text) + 10), out.shape[0]), (0, 0, 0), -1)
        cv2.putText(out, text, (5, out.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def evidence_frames(video_path: str | Path, cand: Candidate, n_frames: int = 3, quality: int = 85, max_width: int = 1280, scale: float = 1.0) -> list[dict]:
    """1–3 frames: clean at t_event, annotated at t_event, clean at t_event+1 s (clamped to the video)."""
    out = []
    f0 = frame_at(video_path, cand.t_event)
    if f0 is None:
        return out
    out.append({"timestamp_sec": round(float(f0.t), 2), "image_base64": encode_jpeg_base64(f0.image, quality, max_width), "kind": "clean"})
    if n_frames >= 2:
        ann = _draw_annotations(f0.image, cand.annotate or {"text": f"t={cand.t_event:.1f}s {cand.type_id}"}, scale)
        out.append({"timestamp_sec": round(float(f0.t), 2), "image_base64": encode_jpeg_base64(ann, quality, max_width), "kind": "annotated"})
    if n_frames >= 3:
        f1 = frame_at(video_path, cand.t_event + 1.0)
        if f1 is not None and abs(f1.t - f0.t) > 0.2:
            out.append({"timestamp_sec": round(float(f1.t), 2), "image_base64": encode_jpeg_base64(f1.image, quality, max_width), "kind": "clean"})
    return out[:3]


def build_result(video_path: str | Path, candidates: list[Candidate], kb: KnowledgeBase, cfg: dict, extras: dict, job_id: Optional[str] = None, scale: float = 1.0) -> dict:
    """Assemble the final result dict (ТЗ keys verbatim + engine extras)."""
    docs = kb.meta.get("documents", {})
    violations = []
    for cand in sorted(candidates, key=lambda c: c.t_event):
        card = kb.get(cand.type_id)
        doc_short = docs.get(card.doc_id, {}).get("short_ru", card.document)
        frames = evidence_frames(
            video_path, cand, int(cfg.get("evidence_frames", 3)), int(cfg.get("evidence_jpeg_quality", 85)), int(cfg.get("evidence_max_width", 1280)), scale
        )
        if not frames:
            continue
        violations.append(
            {
                "type": card.name_ru,
                "timecode_sec": round(float(cand.t_event), 2),
                "description": description_ru(card, cand, doc_short),
                "evidence_frames": [{"timestamp_sec": f["timestamp_sec"], "image_base64": f["image_base64"]} for f in frames],
                "type_id": cand.type_id,
                "confidence": round(float(cand.confidence), 3),
                "rule": card.as_rule_dict(),
                "facts": list(cand.facts),
                "t_window": [round(cand.t_window[0], 2), round(cand.t_window[1], 2)],
                "source": cand.source,
                "vlm": cand.vlm,
            }
        )
    result = {
        "job_id": job_id or uuid.uuid4().hex[:8],
        "status": "done",
        "verdict": "violation" if violations else "no_violation",
        "violations": violations,
    }
    result.update(extras)
    return result
