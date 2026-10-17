"""A compact ByteTrack-style multi-object tracker (Zhang et al., 2022; original code MIT).

Two-stage association: high-score detections are matched first (IoU + Hungarian), then low-score detections
are matched to the remaining tracks; unmatched tracks are kept alive for `lost_track_buffer` frames.
State per track: constant-velocity Kalman filter on (cx, cy, w, h). Deterministic, no learned re-id.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)), dtype=np.float32)
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    union = area_a[:, None] + area_b[None, :] - inter
    return (inter / np.maximum(union, 1e-6)).astype(np.float32)


class _Kalman:
    """Constant-velocity Kalman filter on (cx, cy, w, h, vx, vy, vw, vh)."""

    def __init__(self, box: np.ndarray):
        cx, cy, w, h = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, box[2] - box[0], box[3] - box[1]
        self.x = np.array([cx, cy, w, h, 0, 0, 0, 0], dtype=np.float64)
        self.P = np.diag([10, 10, 10, 10, 100, 100, 100, 100]).astype(np.float64)
        self.F = np.eye(8)
        self.F[:4, 4:] = np.eye(4)
        self.H = np.zeros((4, 8))
        self.H[:4, :4] = np.eye(4)
        self.Q = np.diag([1, 1, 1, 1, 0.5, 0.5, 0.1, 0.1]).astype(np.float64)
        self.R = np.diag([4, 4, 4, 4]).astype(np.float64)

    def predict(self) -> None:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, box: np.ndarray) -> None:
        z = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2, box[2] - box[0], box[3] - box[1]], dtype=np.float64)
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(8) - K @ self.H) @ self.P

    def box(self) -> np.ndarray:
        cx, cy, w, h = self.x[:4]
        w, h = max(w, 1.0), max(h, 1.0)
        return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], dtype=np.float32)


@dataclass
class _Track:
    track_id: int
    kf: _Kalman
    score: float
    hits: int = 1
    age_lost: int = 0
    confirmed: bool = False
    last_box: np.ndarray = field(default_factory=lambda: np.zeros(4, np.float32))


class ByteTrack:
    def __init__(self, track_activation_threshold: float = 0.3, lost_track_buffer: int = 25, minimum_matching_threshold: float = 0.8, minimum_consecutive_frames: int = 2, frame_rate: int = 5):
        self.high_thr = float(track_activation_threshold)
        self.low_thr = 0.1
        self.max_lost = int(lost_track_buffer)
        self.iou_thr = 1.0 - float(minimum_matching_threshold)  # supervision semantics: 0.8 -> iou >= 0.2
        self.iou_thr = max(self.iou_thr, 0.15)
        self.min_hits = int(minimum_consecutive_frames)
        self.tracks: list[_Track] = []
        self._next_id = 1

    def _match(self, tracks: list[_Track], dets: np.ndarray, thr: float) -> tuple[list[tuple[int, int]], list[int], list[int]]:
        if not tracks or len(dets) == 0:
            return [], list(range(len(tracks))), list(range(len(dets)))
        tb = np.stack([t.kf.box() for t in tracks])
        iou = iou_matrix(tb, dets[:, :4])
        rows, cols = linear_sum_assignment(-iou)
        matches, ut, ud = [], set(range(len(tracks))), set(range(len(dets)))
        for r, c in zip(rows, cols):
            if iou[r, c] >= thr:
                matches.append((r, c))
                ut.discard(r)
                ud.discard(c)
        return matches, sorted(ut), sorted(ud)

    def update(self, boxes: np.ndarray, scores: np.ndarray) -> list[tuple[int, np.ndarray]]:
        """boxes (N,4) xyxy, scores (N,). Returns [(track_id, box)] for confirmed tracks seen in this frame."""
        boxes = np.asarray(boxes, dtype=np.float32).reshape(-1, 4)
        scores = np.asarray(scores, dtype=np.float32).reshape(-1)
        for t in self.tracks:
            t.kf.predict()
        high = np.where(scores >= self.high_thr)[0]
        low = np.where((scores < self.high_thr) & (scores >= self.low_thr))[0]
        active = [t for t in self.tracks]
        out: list[tuple[int, np.ndarray]] = []
        # stage 1: high-score detections vs all tracks
        m1, ut1, ud1 = self._match(active, boxes[high], self.iou_thr)
        matched_tracks: set[int] = set()
        for r, c in m1:
            t = active[r]
            d = boxes[high[c]]
            t.kf.update(d)
            t.score = float(scores[high[c]])
            t.hits += 1
            t.age_lost = 0
            t.last_box = d
            matched_tracks.add(id(t))
        # stage 2: low-score detections vs unmatched tracks (only tracks that were tracked, i.e. not lost long)
        rem = [active[i] for i in ut1 if active[i].age_lost == 0]
        m2, _, _ = self._match(rem, boxes[low], max(0.3, self.iou_thr))
        for r, c in m2:
            t = rem[r]
            d = boxes[low[c]]
            t.kf.update(d)
            t.score = float(scores[low[c]])
            t.hits += 1
            t.age_lost = 0
            t.last_box = d
            matched_tracks.add(id(t))
        # unmatched tracks age
        for t in self.tracks:
            if id(t) not in matched_tracks:
                t.age_lost += 1
        self.tracks = [t for t in self.tracks if t.age_lost <= self.max_lost]
        # new tracks from unmatched high-score detections
        for c in ud1:
            d = boxes[high[c]]
            self.tracks.append(_Track(self._next_id, _Kalman(d), float(scores[high[c]]), last_box=d))
            self._next_id += 1
        for t in self.tracks:
            if t.age_lost == 0 and id(t) in matched_tracks or (t.age_lost == 0 and t.hits >= self.min_hits):
                if t.hits >= self.min_hits:
                    t.confirmed = True
                    out.append((t.track_id, t.last_box.copy()))
        # also report brand-new tracks once they reach min_hits (handled above); single-hit tracks are not reported
        return out
