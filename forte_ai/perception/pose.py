"""2-D body pose with RTMPose via rtmlib (Apache-2.0, ONNX Runtime). Only body keypoints; no faces are
identified (the 5 facial keypoints of COCO are used purely for geometry and never for identification)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# COCO-17 keypoint indices
NOSE, L_EYE, R_EYE, L_EAR, R_EAR = 0, 1, 2, 3, 4
L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST = 5, 6, 7, 8, 9, 10
L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE = 11, 12, 13, 14, 15, 16


@dataclass
class PersonPose:
    bbox: tuple[float, float, float, float]
    kpts: np.ndarray  # (17, 2) pixels
    scores: np.ndarray  # (17,)
    track_id: Optional[int] = None

    def wrist(self, side: str, thr: float = 0.3) -> Optional[np.ndarray]:
        i = L_WRIST if side == "left" else R_WRIST
        return self.kpts[i] if self.scores[i] >= thr else None

    def wrists(self, thr: float = 0.3) -> list[np.ndarray]:
        return [self.kpts[i] for i in (L_WRIST, R_WRIST) if self.scores[i] >= thr]

    def to_record(self) -> dict:
        return {
            "bbox": [round(float(v), 1) for v in self.bbox],
            "kpts": np.round(self.kpts, 1).tolist(),
            "scores": np.round(self.scores, 3).tolist(),
            "track_id": self.track_id,
        }

    @staticmethod
    def from_record(r: dict) -> "PersonPose":
        return PersonPose(tuple(r["bbox"]), np.asarray(r["kpts"], np.float32), np.asarray(r["scores"], np.float32), r.get("track_id"))


@dataclass
class FramePoses:
    frame_index: int
    t: float
    poses: list[PersonPose] = field(default_factory=list)

    def to_record(self) -> dict:
        return {"frame_index": self.frame_index, "t": self.t, "poses": [p.to_record() for p in self.poses]}

    @staticmethod
    def from_record(r: dict) -> "FramePoses":
        return FramePoses(r["frame_index"], r["t"], [PersonPose.from_record(p) for p in r["poses"]])


class RTMPoseEstimator:
    """Top-down RTMPose on given person boxes (no internal detector: boxes come from Grounding DINO/tracks)."""

    def __init__(self, cfg: dict, device: str = "cuda"):
        from rtmlib import RTMPose

        self.cfg = cfg
        mode = cfg.get("mode", "lightweight")
        dev = "cuda" if device == "cuda" else "cpu"
        t0 = time.time()
        # Use the Body model zoo of rtmlib: resolve URLs/input sizes through the Body class config
        from rtmlib import Body

        mode_cfg = Body.MODE[mode] if mode in Body.MODE else Body.MODE["lightweight"]
        self.pose = RTMPose(
            mode_cfg["pose"],
            model_input_size=mode_cfg["pose_input_size"],
            to_openpose=False,
            backend="onnxruntime",
            device=dev,
        )
        self.kpt_thr = float(cfg.get("kpt_threshold", 0.3))
        self.load_time = time.time() - t0
        log.info("RTMPose (%s) loaded on %s in %.1fs", mode, dev, self.load_time)

    def estimate(self, frame_bgr: np.ndarray, boxes: list[tuple[float, float, float, float]]) -> list[PersonPose]:
        if not boxes:
            return []
        arr = np.asarray(boxes, dtype=np.float32).reshape(-1, 4)
        kpts, scores = self.pose(frame_bgr, bboxes=arr)
        out = []
        for i, b in enumerate(boxes):
            out.append(PersonPose(tuple(float(v) for v in b), np.asarray(kpts[i], np.float32), np.asarray(scores[i], np.float32)))
        return out


def draw_poses(frame_bgr: np.ndarray, fp: FramePoses, thr: float = 0.3) -> np.ndarray:
    import cv2

    out = frame_bgr.copy()
    skel = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
    for p in fp.poses:
        col = (0, 255, 255) if p.track_id is None else ((37 * p.track_id) % 255, (91 * p.track_id) % 255, 200)
        for a, b in skel:
            if p.scores[a] >= thr and p.scores[b] >= thr:
                cv2.line(out, tuple(int(v) for v in p.kpts[a]), tuple(int(v) for v in p.kpts[b]), col, 2)
        for i in (L_WRIST, R_WRIST):
            if p.scores[i] >= thr:
                cv2.circle(out, tuple(int(v) for v in p.kpts[i]), 5, (0, 0, 255), -1)
        if p.track_id is not None:
            x1, y1 = int(p.bbox[0]), int(p.bbox[1])
            cv2.putText(out, f"id{p.track_id}", (x1, max(12, y1 - 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    return out
