"""Layer A runner: decode -> sample -> detect -> track persons -> pose on tracked persons, with caching.

Frames are processed in streaming batches so that decoded images never accumulate in memory; evidence frames
are re-decoded later by time (forte_ai.video.frame_at).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..config import Config
from ..errors import AnalysisError
from ..video import VideoInfo, iter_frames, probe
from .cache import PerceptionCache, config_hash
from .detector import FrameDetections
from .pose import FramePoses, PersonPose
from .tracker import PersonTracker, TrackState

log = logging.getLogger(__name__)

ProgressCb = Optional[Callable[[float, str], None]]


@dataclass
class PerceptionResult:
    video: dict
    sample_fps: float
    det_width: int
    det_height: int
    scale: float  # det pixels = original pixels * scale
    frames: list[FrameDetections] = field(default_factory=list)
    poses: list[FramePoses] = field(default_factory=list)
    tracks: dict[int, TrackState] = field(default_factory=dict)
    per_frame_tracks: list[dict[int, tuple]] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    from_cache: bool = False

    # ---- serialization ----
    def to_record(self) -> dict:
        return {
            "video": self.video,
            "sample_fps": self.sample_fps,
            "det_width": self.det_width,
            "det_height": self.det_height,
            "scale": self.scale,
            "frames": [f.to_record() for f in self.frames],
            "poses": [p.to_record() for p in self.poses],
            "tracks": {
                str(k): {"track_id": v.track_id, "first_t": v.first_t, "last_t": v.last_t, "n": v.n, "boxes": v.boxes, "times": v.times, "frame_indices": v.frame_indices}
                for k, v in self.tracks.items()
            },
            "per_frame_tracks": [{str(k): list(b) for k, b in d.items()} for d in self.per_frame_tracks],
            "timings": self.timings,
        }

    @staticmethod
    def from_record(r: dict) -> "PerceptionResult":
        pr = PerceptionResult(r["video"], r["sample_fps"], r["det_width"], r["det_height"], r["scale"])
        pr.frames = [FrameDetections.from_record(x) for x in r["frames"]]
        pr.poses = [FramePoses.from_record(x) for x in r["poses"]]
        for k, v in r["tracks"].items():
            st = TrackState(v["track_id"], v["first_t"], v["last_t"], v["n"])
            st.boxes = [tuple(b) for b in v["boxes"]]
            st.times = list(v["times"])
            st.frame_indices = list(v["frame_indices"])
            pr.tracks[int(k)] = st
        pr.per_frame_tracks = [{int(k): tuple(b) for k, b in d.items()} for d in r["per_frame_tracks"]]
        pr.timings = dict(r.get("timings", {}))
        pr.from_cache = True
        return pr


class PerceptionEngine:
    """Owns the perception models (loaded once) and runs them on videos."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.device = cfg.get("device", "cuda")
        self.detector = None
        self.pose = None
        self.load_timings: dict[str, float] = {}
        self.cache = PerceptionCache(
            Path(cfg.get("cache.dir", "data/cache")), bool(cfg.get("cache.enabled", True)), str(cfg.get("cache.pipeline_version", "p1"))
        )

    # ---- lazy model loading ----
    def ensure_models(self) -> None:
        if self.detector is None:
            from .detector import GroundingDinoDetector

            t0 = time.time()
            self.detector = GroundingDinoDetector(self.cfg.section("perception").get("detector", {}), self.device)
            self.load_timings["detector"] = time.time() - t0
        if self.pose is None and self.cfg.get("perception.pose.backend", "rtmlib") == "rtmlib":
            from .pose import RTMPoseEstimator

            t0 = time.time()
            self.pose = RTMPoseEstimator(self.cfg.section("perception").get("pose", {}), self.device)
            self.load_timings["pose"] = time.time() - t0

    def unload(self) -> None:
        if self.detector is not None:
            self.detector.unload()
            self.detector = None
        self.pose = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def _cfg_hash(self) -> str:
        return config_hash({"video": self.cfg.section("video"), "perception": self.cfg.section("perception")})

    # ---- main entry ----
    def run(self, video_path: str | Path, on_progress: ProgressCb = None, use_cache: bool = True, info: Optional[VideoInfo] = None) -> PerceptionResult:
        t_all = time.time()
        info = info or probe(video_path)
        ch = self._cfg_hash()
        if use_cache:
            rec = self.cache.load(info.content_md5, ch)
            if rec is not None:
                pr = PerceptionResult.from_record(rec)
                pr.timings = dict(pr.timings, cache_hit=1.0)
                if on_progress:
                    on_progress(1.0, "Перцепция загружена из кэша")
                return pr
        self.ensure_models()
        sample_fps = float(self.cfg.get("video.sample_fps", 5.0))
        max_side = int(self.cfg.get("video.max_side", 960))
        det_cfg = self.cfg.section("perception").get("detector", {})
        every_n = max(1, int(det_cfg.get("detect_every_n", 1)))
        batch = max(1, int(det_cfg.get("batch_size", 2)))
        tr_cfg = dict(self.cfg.section("perception").get("tracker", {}))
        tr_cfg.setdefault("min_track_frames", self.cfg.get("roles.min_track_frames", 5))
        tracker = PersonTracker(tr_cfg, sample_fps)
        pose_every = max(1, int(self.cfg.get("perception.pose.every_n", 1)))

        scale = 1.0
        if max_side and max(info.width, info.height) > max_side:
            scale = max_side / max(info.width, info.height)
        det_w, det_h = int(round(info.width * scale)), int(round(info.height * scale))
        pr = PerceptionResult(video=info.__dict__.copy(), sample_fps=sample_fps, det_width=det_w, det_height=det_h, scale=scale)
        timings = {"decode": 0.0, "detect": 0.0, "track": 0.0, "pose": 0.0}
        duration = max(info.duration_s, 1e-3)

        buf_imgs: list[np.ndarray] = []
        buf_idx: list[int] = []
        buf_t: list[float] = []
        n_sampled = 0
        last_fd: Optional[FrameDetections] = None

        def flush():
            nonlocal buf_imgs, buf_idx, buf_t, last_fd
            if not buf_imgs:
                return
            t0 = time.time()
            # detector runs on every_n-th frame; in-between frames reuse the previous detections
            det_imgs, det_pos = [], []
            for j, idx in enumerate(buf_idx):
                if (n_sampled - len(buf_idx) + j) % every_n == 0 or last_fd is None:
                    det_imgs.append(buf_imgs[j])
                    det_pos.append(j)
            fds = self.detector.detect(det_imgs, [buf_idx[j] for j in det_pos], [buf_t[j] for j in det_pos]) if det_imgs else []
            timings["detect"] += time.time() - t0
            fd_by_pos = dict(zip(det_pos, fds))
            for j in range(len(buf_idx)):
                if j in fd_by_pos:
                    fd = fd_by_pos[j]
                    last_fd = fd
                else:
                    fd = FrameDetections(buf_idx[j], buf_t[j], last_fd.width, last_fd.height, list(last_fd.dets))
                t1 = time.time()
                assigned = tracker.update(fd)
                timings["track"] += time.time() - t1
                pr.frames.append(fd)
                pr.per_frame_tracks.append(assigned)
                fp = FramePoses(fd.frame_index, fd.t)
                if self.pose is not None and assigned and (len(pr.frames) - 1) % pose_every == 0:
                    t2 = time.time()
                    tids = list(assigned.keys())
                    poses = self.pose.estimate(buf_imgs[j], [assigned[t] for t in tids])
                    for tid, p in zip(tids, poses):
                        p.track_id = tid
                    fp.poses = poses
                    timings["pose"] += time.time() - t2
                pr.poses.append(fp)
            buf_imgs, buf_idx, buf_t = [], [], []

        t_dec = time.time()
        for fr in iter_frames(video_path, sample_fps=sample_fps, max_side=max_side):
            timings["decode"] += time.time() - t_dec
            buf_imgs.append(fr.image)
            buf_idx.append(fr.index)
            buf_t.append(fr.t)
            n_sampled += 1
            if len(buf_imgs) >= batch:
                flush()
                if on_progress:
                    on_progress(min(0.99, fr.t / duration), f"Анализ кадров: {fr.t:.0f} с из {duration:.0f} с")
            t_dec = time.time()
        timings["decode"] += time.time() - t_dec
        flush()
        pr.tracks = tracker.finished(int(tr_cfg.get("min_track_frames", 1)))
        timings["total"] = time.time() - t_all
        timings["n_sampled"] = float(n_sampled)
        pr.timings = timings
        if not pr.frames:
            raise AnalysisError("no frames decoded")
        if use_cache:
            self.cache.save(info.content_md5, ch, pr.to_record())
        if on_progress:
            on_progress(1.0, "Перцепция завершена")
        return pr
