"""Person tracking with a ByteTrack-style tracker (forte_ai.perception.bytetrack).
Track ids exist only inside one video; no re-identification, no faces."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .bytetrack import ByteTrack
from .detector import FrameDetections


@dataclass
class TrackState:
    track_id: int
    first_t: float
    last_t: float
    n: int = 0
    boxes: list[tuple[float, float, float, float]] = field(default_factory=list)
    times: list[float] = field(default_factory=list)
    frame_indices: list[int] = field(default_factory=list)

    def centers(self) -> np.ndarray:
        b = np.asarray(self.boxes, dtype=np.float32).reshape(-1, 4)
        return np.stack([(b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2], axis=1)


class PersonTracker:
    """Call update(fd) per sampled frame; returns {track_id: xyxy} for confirmed person tracks."""

    def __init__(self, cfg: dict, sample_fps: float):
        self.cfg = cfg
        self.bt = ByteTrack(
            track_activation_threshold=float(cfg.get("track_activation_threshold", 0.3)),
            lost_track_buffer=int(cfg.get("lost_track_buffer", 25)),
            minimum_matching_threshold=float(cfg.get("minimum_matching_threshold", 0.8)),
            minimum_consecutive_frames=int(cfg.get("minimum_consecutive_frames", 2)),
            frame_rate=max(1, int(round(sample_fps))),
        )
        self.tracks: dict[int, TrackState] = {}

    def update(self, fd: FrameDetections) -> dict[int, tuple[float, float, float, float]]:
        persons = fd.by_class("person")
        if persons:
            xyxy = np.asarray([d.xyxy for d in persons], dtype=np.float32)
            conf = np.asarray([d.score for d in persons], dtype=np.float32)
        else:
            xyxy = np.zeros((0, 4), np.float32)
            conf = np.zeros((0,), np.float32)
        out: dict[int, tuple[float, float, float, float]] = {}
        for tid, box in self.bt.update(xyxy, conf):
            b = tuple(float(x) for x in box)
            st = self.tracks.get(tid)
            if st is None:
                st = TrackState(tid, fd.t, fd.t)
                self.tracks[tid] = st
            st.last_t = fd.t
            st.n += 1
            st.boxes.append(b)
            st.times.append(fd.t)
            st.frame_indices.append(fd.frame_index)
            out[tid] = b
        return out

    def finished(self, min_frames: int = 1) -> dict[int, TrackState]:
        return {k: v for k, v in self.tracks.items() if v.n >= min_frames}
