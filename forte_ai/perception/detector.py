"""Open-vocabulary object detection with Grounding DINO (Apache-2.0) through `transformers`.

Engine classes: person, cash, bag, document, id_card, phone, cash_drawer, counting_machine.
Each engine class maps to one or more text prompts (configs/default.yaml -> perception.detector.prompts);
detections are mapped back to the engine class and filtered by per-class thresholds.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

log = logging.getLogger(__name__)

ENGINE_CLASSES = ("person", "cash", "bag", "document", "id_card", "phone", "storage", "counting_machine", "laptop", "cup")
SMALL_OBJECT_CLASSES = ("cash", "bag", "document", "id_card", "phone", "cup")


@dataclass
class Detection:
    cls: str
    score: float
    xyxy: tuple[float, float, float, float]  # pixels in the frame given to the detector
    label_text: str = ""


@dataclass
class FrameDetections:
    frame_index: int
    t: float
    width: int
    height: int
    dets: list[Detection] = field(default_factory=list)

    def by_class(self, cls: str) -> list[Detection]:
        return [d for d in self.dets if d.cls == cls]

    def to_record(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "t": self.t,
            "width": self.width,
            "height": self.height,
            "dets": [[d.cls, round(d.score, 4), *[round(float(x), 1) for x in d.xyxy], d.label_text] for d in self.dets],
        }

    @staticmethod
    def from_record(r: dict) -> "FrameDetections":
        fd = FrameDetections(r["frame_index"], r["t"], r["width"], r["height"])
        for cls, score, x1, y1, x2, y2, lab in r["dets"]:
            fd.dets.append(Detection(cls, float(score), (x1, y1, x2, y2), lab))
        return fd


def _nms_per_class(dets: list[Detection], iou_thr: float = 0.6) -> list[Detection]:
    out: list[Detection] = []
    for cls in sorted({d.cls for d in dets}):
        cand = sorted([d for d in dets if d.cls == cls], key=lambda d: -d.score)
        kept: list[Detection] = []
        for d in cand:
            ok = True
            for k in kept:
                if _iou(d.xyxy, k.xyxy) > iou_thr:
                    ok = False
                    break
            if ok:
                kept.append(d)
        out.extend(kept)
    return out


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


def _containment(inner, outer) -> float:
    """Share of `inner` box area that lies inside `outer`."""
    iw = max(0.0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    ih = max(0.0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    a = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return (iw * ih / a) if a > 0 else 0.0


def _cross_class_suppression(dets: list[Detection], landmark_classes: Sequence[str], iou_thr: float) -> list[Detection]:
    """Resolve competing labels for the same object.

    * persons never compete with anything;
    * a small object (cash/bag/document/id_card/phone) mostly inside a static landmark (counting machine,
      storage unit, laptop) is dropped — the open-vocabulary detector labels the counting machine as "bag"
      and the laptop as "document" otherwise;
    * among the remaining overlapping boxes of different classes the higher score wins.
    """
    landmarks = [d for d in dets if d.cls in landmark_classes]
    keep: list[Detection] = []
    for d in dets:
        if d.cls == "person" or d.cls in landmark_classes:
            keep.append(d)
            continue
        if any(_containment(d.xyxy, lm.xyxy) >= 0.7 for lm in landmarks):
            continue
        keep.append(d)
    # pairwise competition among small objects
    small = sorted([d for d in keep if d.cls in SMALL_OBJECT_CLASSES], key=lambda d: -d.score)
    chosen: list[Detection] = []
    for d in small:
        if any(c.cls != d.cls and _iou(d.xyxy, c.xyxy) >= iou_thr for c in chosen):
            continue
        chosen.append(d)
    others = [d for d in keep if d.cls not in SMALL_OBJECT_CLASSES]
    # landmarks competing with each other (e.g. storage vs counting machine on the same box): higher score wins
    lm_sorted = sorted([d for d in others if d.cls in landmark_classes], key=lambda d: -d.score)
    lm_chosen: list[Detection] = []
    for d in lm_sorted:
        if any(c.cls != d.cls and _iou(d.xyxy, c.xyxy) >= iou_thr for c in lm_chosen):
            continue
        lm_chosen.append(d)
    persons = [d for d in others if d.cls == "person"]
    return persons + lm_chosen + chosen


class GroundingDinoDetector:
    """Zero-shot detector. Loads once; call `detect(frames_bgr)` with a list of HxWx3 uint8 arrays."""

    def __init__(self, cfg: dict, device: str = "cuda"):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.cfg = cfg
        self.model_id = cfg.get("model_id", "IDEA-Research/grounding-dino-tiny")
        self.device = device if (device == "cpu" or torch.cuda.is_available()) else "cpu"
        self.fp16 = bool(cfg.get("fp16", True)) and self.device != "cpu"
        self.box_threshold = float(cfg.get("box_threshold", 0.3))
        self.text_threshold = float(cfg.get("text_threshold", 0.25))
        self.class_thresholds = dict(cfg.get("class_thresholds", {}) or {})
        self.min_box_area_frac = float(cfg.get("min_box_area_frac", 0.0003))
        self.max_boxes_per_class = int(cfg.get("max_boxes_per_class", 8))
        self.landmark_classes = tuple(cfg.get("landmark_classes", ("counting_machine", "storage", "laptop")))
        self.class_max_area_frac = dict(cfg.get("class_max_area_frac", {}) or {})
        self.cross_class_iou = float(cfg.get("cross_class_iou", 0.5))
        self.batch_size = int(cfg.get("batch_size", 2))
        prompts = cfg.get("prompts") or {c: [c.replace("_", " ")] for c in ENGINE_CLASSES}
        self.prompt_to_class: dict[str, str] = {}
        phrases: list[str] = []
        for cls, plist in prompts.items():
            for p in plist:
                p = p.strip().lower()
                self.prompt_to_class[p] = cls
                phrases.append(p)
        self.phrases = phrases
        # Grounding DINO expects lower-case phrases separated by " . " and ending with "."
        self.text = " . ".join(phrases) + " ."
        t0 = time.time()
        from ..models_util import resolve_model_path

        path = resolve_model_path(self.model_id)
        self.processor = AutoProcessor.from_pretrained(path)
        short = int(cfg.get("input_short_side", 480))
        if short > 0:  # the default processor upsamples to 800 px — far too slow for a 464-px source
            self.processor.image_processor.size = {"shortest_edge": short, "longest_edge": int(short * 1333 / 800)}
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(path)
        self.model.to(self.device).eval()
        # fp16 is applied with autocast at inference time (model.half() breaks the text branch)
        self.load_time = time.time() - t0
        log.info("GroundingDINO %s loaded on %s in %.1fs (fp16=%s)", self.model_id, self.device, self.load_time, self.fp16)

    def _map_label(self, label_text: str) -> Optional[str]:
        lt = label_text.strip().lower()
        if lt in self.prompt_to_class:
            return self.prompt_to_class[lt]
        # the model may return a sub-phrase or a merged phrase; pick the longest prompt contained in it
        best, best_len = None, 0
        for p, cls in self.prompt_to_class.items():
            if p in lt and len(p) > best_len:
                best, best_len = cls, len(p)
        if best is None:
            for p, cls in self.prompt_to_class.items():
                if lt and lt in p and len(lt) >= 3:
                    return cls
        return best

    @staticmethod
    def _to_rgb_pil(frames_bgr: Sequence[np.ndarray]):
        from PIL import Image

        return [Image.fromarray(f[:, :, ::-1]) for f in frames_bgr]

    def detect(self, frames_bgr: Sequence[np.ndarray], frame_indices: Sequence[int], times: Sequence[float]) -> list[FrameDetections]:
        import torch

        out: list[FrameDetections] = []
        for s in range(0, len(frames_bgr), self.batch_size):
            chunk = list(frames_bgr[s : s + self.batch_size])
            images = self._to_rgb_pil(chunk)
            inputs = self.processor(images=images, text=[self.text] * len(images), return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.inference_mode():
                if self.fp16:
                    with torch.autocast("cuda", dtype=torch.float16):
                        outputs = self.model(**inputs)
                    outputs.logits = outputs.logits.float()
                    outputs.pred_boxes = outputs.pred_boxes.float()
                else:
                    outputs = self.model(**inputs)
            sizes = [(im.height, im.width) for im in images]
            results = self._post_process(outputs, inputs["input_ids"], sizes)
            for j, res in enumerate(results):
                h, w = sizes[j]
                fd = FrameDetections(int(frame_indices[s + j]), float(times[s + j]), w, h)
                labels = res.get("text_labels", res.get("labels"))
                for score, box, lab in zip(res["scores"].tolist(), res["boxes"].tolist(), labels):
                    lab_text = lab if isinstance(lab, str) else str(lab)
                    cls = self._map_label(lab_text)
                    if cls is None:
                        continue
                    thr = float(self.class_thresholds.get(cls, self.box_threshold))
                    if score < thr:
                        continue
                    x1, y1, x2, y2 = box
                    x1, y1 = max(0.0, x1), max(0.0, y1)
                    x2, y2 = min(float(w), x2), min(float(h), y2)
                    area = (x2 - x1) * (y2 - y1)
                    if area < self.min_box_area_frac * w * h:
                        continue
                    if cls in self.class_max_area_frac and area > float(self.class_max_area_frac[cls]) * w * h:
                        continue
                    fd.dets.append(Detection(cls, float(score), (x1, y1, x2, y2), lab_text))
                fd.dets = _nms_per_class(fd.dets)
                fd.dets = _cross_class_suppression(fd.dets, self.landmark_classes, self.cross_class_iou)
                # cap per class
                capped: list[Detection] = []
                for cls in sorted({d.cls for d in fd.dets}):
                    capped.extend(sorted(fd.by_class(cls), key=lambda d: -d.score)[: self.max_boxes_per_class])
                fd.dets = capped
                out.append(fd)
        return out

    def _post_process(self, outputs, input_ids, sizes):
        pp = self.processor.post_process_grounded_object_detection
        try:  # transformers >= 4.51
            return pp(outputs, input_ids, threshold=min(self.box_threshold, min(self.class_thresholds.values(), default=1.0)), text_threshold=self.text_threshold, target_sizes=sizes)
        except TypeError:  # older signature
            return pp(outputs, input_ids, box_threshold=self.box_threshold, text_threshold=self.text_threshold, target_sizes=sizes)

    def unload(self) -> None:
        import torch

        self.model = None
        self.processor = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def draw_detections(frame_bgr: np.ndarray, fd: FrameDetections, scale: float = 1.0) -> np.ndarray:
    """Annotate a frame with boxes and labels (for QA sheets and evidence frames)."""
    import cv2

    colors = {
        "person": (0, 200, 0),
        "cash": (0, 215, 255),
        "bag": (200, 0, 200),
        "document": (255, 255, 255),
        "id_card": (255, 128, 0),
        "phone": (0, 0, 255),
        "storage": (128, 128, 255),
        "counting_machine": (255, 0, 128),
        "laptop": (160, 160, 160),
    }
    out = frame_bgr.copy()
    for d in fd.dets:
        x1, y1, x2, y2 = [int(round(v * scale)) for v in d.xyxy]
        c = colors.get(d.cls, (200, 200, 200))
        cv2.rectangle(out, (x1, y1), (x2, y2), c, 2)
        cv2.putText(out, f"{d.cls} {d.score:.2f}", (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1, cv2.LINE_AA)
    return out
