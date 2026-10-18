"""Video decoding and frame sampling (Layer A, step 1).

Uses PyAV (bundled FFmpeg libraries; no system ffmpeg needed). Frames are sampled at a target rate
while keeping the original frame index and presentation timestamp. Nothing here depends on torch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from .errors import AnalysisError


@dataclass
class VideoInfo:
    path: str
    duration_s: float
    fps: float
    width: int
    height: int
    codec: str
    nb_frames: int
    rotation: int  # degrees from the display matrix / metadata, 0 if none
    content_md5: str


@dataclass
class Frame:
    index: int  # index of the decoded frame in the stream (0-based)
    t: float  # presentation time in seconds
    image: np.ndarray  # HxWx3 uint8 BGR (OpenCV convention)


def file_md5(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _rotation_of(stream) -> int:
    rot = 0
    try:
        md = dict(stream.metadata or {})
        if md.get("rotate"):
            rot = int(float(md["rotate"]))
    except Exception:
        pass
    try:  # PyAV >= 14 exposes side data with a display matrix
        for sd in getattr(stream, "side_data", []) or []:
            if "Display" in str(type(sd)) or "displaymatrix" in str(sd).lower():
                r = getattr(sd, "rotation", None)
                if r is not None:
                    rot = int(round(float(r)))
    except Exception:
        pass
    return rot % 360


_PROBE_CACHE: dict[tuple, "VideoInfo"] = {}


def probe(path: str | Path) -> VideoInfo:
    """Container metadata + content md5, cached per (path, size, mtime) — evidence/VLM frame grabs call
    this repeatedly and re-hashing a 30 MB file each time is pure waste."""
    p = Path(path)
    if not p.exists():
        raise AnalysisError(f"video not found: {p}")
    st = p.stat()
    key = (str(p.resolve()), st.st_size, st.st_mtime_ns)
    hit = _PROBE_CACHE.get(key)
    if hit is not None:
        return hit
    info = _probe_uncached(p)
    if len(_PROBE_CACHE) > 64:
        _PROBE_CACHE.clear()
    _PROBE_CACHE[key] = info
    return info


def _probe_uncached(p: Path) -> VideoInfo:
    import av

    try:
        with av.open(str(p)) as c:
            if not c.streams.video:
                raise AnalysisError(f"no video stream in {p}")
            vs = c.streams.video[0]
            fps = float(vs.average_rate or vs.guessed_rate or 0.0)
            if c.duration:
                dur = float(c.duration / av.time_base)
            elif vs.duration and vs.time_base:
                dur = float(vs.duration * vs.time_base)
            else:
                dur = 0.0
            return VideoInfo(
                path=str(p),
                duration_s=dur,
                fps=fps,
                width=vs.codec_context.width,
                height=vs.codec_context.height,
                codec=vs.codec_context.name,
                nb_frames=int(vs.frames or 0),
                rotation=_rotation_of(vs),
                content_md5=file_md5(p),
            )
    except AnalysisError:
        raise
    except Exception as e:  # pragma: no cover - depends on the container
        raise AnalysisError(f"cannot open video {p}: {e}") from e


def iter_frames(
    path: str | Path,
    sample_fps: float = 5.0,
    max_side: Optional[int] = None,
    start_s: float = 0.0,
    end_s: Optional[float] = None,
    apply_rotation: bool = True,
) -> Iterator[Frame]:
    """Decode sequentially and yield frames at ~sample_fps (nearest decoded frame to each sample time).

    Frames are yielded in BGR uint8. `max_side` downsizes so that max(h, w) <= max_side.
    """
    import av
    import cv2

    info = probe(path)
    step = 1.0 / float(sample_fps) if sample_fps and sample_fps > 0 else 0.0
    next_t = float(start_s)
    rot = info.rotation if apply_rotation else 0
    with av.open(str(path)) as c:
        vs = c.streams.video[0]
        vs.thread_type = "AUTO"
        tb = vs.time_base or Fraction(1, 90000)
        idx = -1
        for packet in c.demux(vs):
            for frame in packet.decode():
                idx += 1
                if frame.pts is None:
                    t = idx / (info.fps or 30.0)
                else:
                    t = float(frame.pts * tb)
                if t + 1e-6 < next_t:
                    continue
                if end_s is not None and t > end_s + 1e-6:
                    return
                img = frame.to_ndarray(format="bgr24")
                if rot:
                    if rot == 90:
                        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    elif rot == 180:
                        img = cv2.rotate(img, cv2.ROTATE_180)
                    elif rot == 270:
                        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                if max_side and max(img.shape[:2]) > max_side:
                    s = max_side / max(img.shape[:2])
                    img = cv2.resize(img, (int(round(img.shape[1] * s)), int(round(img.shape[0] * s))), interpolation=cv2.INTER_AREA)
                yield Frame(index=idx, t=t, image=img)
                if step <= 0:
                    continue
                # advance to the next sample time strictly after this frame
                while next_t <= t + 1e-6:
                    next_t += step


def frame_at(path: str | Path, t: float, max_side: Optional[int] = None) -> Optional[Frame]:
    """Return the decoded frame nearest to time t (seeks to a keyframe, then decodes forward)."""
    import av
    import cv2

    info = probe(path)
    best: Optional[Frame] = None
    with av.open(str(path)) as c:
        vs = c.streams.video[0]
        # no frame-threading here: threaded decoding combined with seek() deadlocked intermittently
        # (observed once during a full evaluation run); single-threaded decode of <=1 s is fast enough
        tb = vs.time_base or Fraction(1, 90000)
        seek_t = max(0.0, t - 1.0)
        try:
            c.seek(int(seek_t / tb), stream=vs, backward=True, any_frame=False)
        except Exception:
            pass
        for frame in c.decode(vs):
            ft = float(frame.pts * tb) if frame.pts is not None else 0.0
            if best is None or abs(ft - t) < abs(best.t - t):
                img = frame.to_ndarray(format="bgr24")
                if info.rotation == 90:
                    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif info.rotation == 180:
                    img = cv2.rotate(img, cv2.ROTATE_180)
                elif info.rotation == 270:
                    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                if max_side and max(img.shape[:2]) > max_side:
                    s = max_side / max(img.shape[:2])
                    img = cv2.resize(img, (int(round(img.shape[1] * s)), int(round(img.shape[0] * s))), interpolation=cv2.INTER_AREA)
                best = Frame(index=-1, t=ft, image=img)
            if ft > t + 0.05:
                break
    return best


def encode_jpeg_base64(image_bgr: np.ndarray, quality: int = 85, max_width: int = 1280) -> str:
    """JPEG-encode a BGR frame (resized to max_width) and return base64 without a data-URI prefix."""
    import base64

    import cv2

    img = image_bgr
    if img.shape[1] > max_width:
        s = max_width / img.shape[1]
        img = cv2.resize(img, (max_width, int(round(img.shape[0] * s))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise AnalysisError("JPEG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")
