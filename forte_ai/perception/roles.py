"""Roles and zones without pixel coordinates (Layer A, step 5).

Everything is expressed relative to the frame diagonal and to the people/objects in the video, so the same
code works for a different camera angle, a horizontally flipped or rotated video:

- cashier  = the track that is present the most, moves the least, appears from the start, sits closest to the
             workplace objects (counting machine / safe / drawer / laptop) and handles cash most often;
- cashier zone = convex hull of the cashier's body positions, dilated;
- counter line = the line separating the cashier's positions from the positions of the other people
             (perpendicular bisector of the two position clusters, refined by a linear separator);
- client   = another track that comes within reach of the counter line (its "window" side);
- collector = a non-cashier track that co-occurs with a `bag` detection.

The calibration is computed from the first `calibration_seconds` and then refined on the whole video
(the per-video result is stored in the output JSON for debugging).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .detector import FrameDetections
from .pose import FramePoses, L_WRIST, R_WRIST
from .tracker import TrackState

WORKPLACE_CLASSES = ("counting_machine", "storage", "laptop")


@dataclass
class Calibration:
    frame_w: int
    frame_h: int
    diag: float
    cashier_track: Optional[int]
    cashier_score: float
    track_scores: dict[int, dict]  # per-track cue values
    cashier_center: tuple[float, float]  # median body center of the cashier (det pixels)
    cashier_hull: list[tuple[float, float]]  # dilated convex hull of cashier positions
    counter_point: tuple[float, float]  # a point on the counter line
    counter_normal: tuple[float, float]  # unit normal pointing to the cashier side
    counter_confidence: float
    client_tracks: list[int]
    collector_tracks: list[int]
    other_tracks: list[int]
    workplace_objects: dict[str, tuple[float, float]]  # median centers of static objects
    storage_point: Optional[tuple[float, float]]  # safe / drawer location if seen
    counting_machine_point: Optional[tuple[float, float]]
    method: str = "presence+static+early+objects+cash"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "frame_w": self.frame_w,
            "frame_h": self.frame_h,
            "cashier_track": self.cashier_track,
            "cashier_score": round(self.cashier_score, 3),
            "cashier_center_norm": [round(self.cashier_center[0] / self.frame_w, 3), round(self.cashier_center[1] / self.frame_h, 3)],
            "cashier_hull_norm": [[round(x / self.frame_w, 3), round(y / self.frame_h, 3)] for x, y in self.cashier_hull],
            "counter_point_norm": [round(self.counter_point[0] / self.frame_w, 3), round(self.counter_point[1] / self.frame_h, 3)],
            "counter_normal": [round(self.counter_normal[0], 3), round(self.counter_normal[1], 3)],
            "counter_confidence": round(self.counter_confidence, 3),
            "client_tracks": self.client_tracks,
            "collector_tracks": self.collector_tracks,
            "other_tracks": self.other_tracks,
            "workplace_objects_norm": {k: [round(v[0] / self.frame_w, 3), round(v[1] / self.frame_h, 3)] for k, v in self.workplace_objects.items()},
            "storage_point_norm": None if self.storage_point is None else [round(self.storage_point[0] / self.frame_w, 3), round(self.storage_point[1] / self.frame_h, 3)],
            "counting_machine_point_norm": None if self.counting_machine_point is None else [round(self.counting_machine_point[0] / self.frame_w, 3), round(self.counting_machine_point[1] / self.frame_h, 3)],
            "track_scores": {str(k): {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in self.track_scores.items()},
            "method": self.method,
            "notes": self.notes,
        }
        return d

    # ---- geometry helpers ----
    def signed_dist_to_counter(self, p) -> float:
        """> 0 on the cashier side, < 0 on the client side (in det pixels)."""
        return float((p[0] - self.counter_point[0]) * self.counter_normal[0] + (p[1] - self.counter_point[1]) * self.counter_normal[1])

    def in_cashier_zone(self, p) -> bool:
        """Inside the (dilated) hull of the cashier's body positions AND on the cashier's side of the counter."""
        return self.signed_dist_to_counter(p) > 0 and _point_in_polygon(p, self.cashier_hull)


# ---------------------------------------------------------------- geometry
def _convex_hull(points: np.ndarray) -> np.ndarray:
    pts = np.unique(points, axis=0)
    if len(pts) < 3:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.asarray(lower[:-1] + upper[:-1])


def _dilate_polygon(poly: np.ndarray, amount: float) -> np.ndarray:
    if len(poly) == 0:
        return poly
    c = poly.mean(axis=0)
    out = []
    for p in poly:
        v = p - c
        n = np.linalg.norm(v)
        out.append(p + (v / n * amount if n > 1e-6 else np.array([amount, 0.0])))
    return np.asarray(out)


def _point_in_polygon(p, poly) -> bool:
    if poly is None or len(poly) < 3:
        return False
    x, y = p
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _center(b) -> tuple[float, float]:
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def _body_point(b) -> tuple[float, float]:
    """Torso-ish point: centre of the box, slightly below (more stable than the head for seated people)."""
    return ((b[0] + b[2]) / 2.0, b[1] + 0.6 * (b[3] - b[1]))


# ---------------------------------------------------------------- calibration
def calibrate(frames: list[FrameDetections], poses: list[FramePoses], tracks: dict[int, TrackState], per_frame_tracks: list[dict], cfg: dict, frame_w: int, frame_h: int) -> Calibration:
    diag = math.hypot(frame_w, frame_h)
    n_frames = max(1, len(frames))
    calib_s = float(cfg.get("calibration_seconds", 12.0))
    t0 = frames[0].t if frames else 0.0

    # static workplace objects: median centres of their detections (only classes seen in >= 10 % of frames)
    workplace: dict[str, tuple[float, float]] = {}
    for cls in WORKPLACE_CLASSES:
        cs = [_center(d.xyxy) for f in frames for d in f.by_class(cls)]
        if len(cs) >= max(3, 0.10 * n_frames):
            arr = np.asarray(cs)
            workplace[cls] = (float(np.median(arr[:, 0])), float(np.median(arr[:, 1])))

    # per-track cues
    cash_centers_by_frame = [[_center(d.xyxy) for d in f.by_class("cash")] for f in frames]
    track_scores: dict[int, dict] = {}
    for tid, st in tracks.items():
        if st.n < int(cfg.get("min_track_frames", 5)):
            continue
        pts = np.asarray([_body_point(b) for b in st.boxes])
        presence = st.n / n_frames
        disp = float(np.sqrt(((pts - pts.mean(axis=0)) ** 2).sum(axis=1).mean())) / diag
        s_static = max(0.0, 1.0 - disp / 0.08)  # 8 % of the diagonal of wander -> 0
        s_early = 1.0 if st.first_t - t0 <= min(calib_s, 3.0) else max(0.0, 1.0 - (st.first_t - t0) / calib_s)
        med = (float(np.median(pts[:, 0])), float(np.median(pts[:, 1])))
        if workplace:
            dists = [math.hypot(med[0] - p[0], med[1] - p[1]) / diag for p in workplace.values()]
            s_obj = max(0.0, 1.0 - min(dists) / 0.35)
        else:
            s_obj = 0.5
        # cash handling: share of cash detections whose centre is closest to this track's box
        mine, total = 0, 0
        for k, cs in enumerate(cash_centers_by_frame):
            if not cs or k >= len(per_frame_tracks):
                continue
            boxes = per_frame_tracks[k]
            if tid not in boxes:
                continue
            for c in cs:
                total += 1
                dmin, best = 1e9, None
                for ot, ob in boxes.items():
                    d = _dist_point_box(c, ob)
                    if d < dmin:
                        dmin, best = d, ot
                if best == tid:
                    mine += 1
        s_cash = (mine / total) if total >= 5 else 0.5
        score = 0.30 * presence + 0.20 * s_static + 0.15 * s_early + 0.20 * s_obj + 0.15 * s_cash
        track_scores[tid] = {"presence": presence, "static": s_static, "early": s_early, "objects": s_obj, "cash": s_cash, "score": score, "n": st.n, "median": [med[0], med[1]]}

    if not track_scores:
        return Calibration(frame_w, frame_h, diag, None, 0.0, {}, (frame_w / 2, frame_h / 2), [], (frame_w / 2, frame_h / 2), (0.0, 1.0), 0.0, [], [], [], workplace, workplace.get("storage"), workplace.get("counting_machine"), notes=["no tracks"])

    cashier = max(track_scores, key=lambda k: track_scores[k]["score"])
    cs = track_scores[cashier]
    st = tracks[cashier]
    cpts = np.asarray([_body_point(b) for b in st.boxes])
    c_center = (float(np.median(cpts[:, 0])), float(np.median(cpts[:, 1])))
    # zone: hull of the cashier's torso points (box centre + a point at 60 % height), dilated by a body-sized
    # margin. Full boxes are NOT used: an outstretched arm or the chair would swallow the client's seat.
    body_pts = []
    for b in st.boxes:
        cx = (b[0] + b[2]) / 2.0
        body_pts.extend([(cx, b[1] + 0.35 * (b[3] - b[1])), (cx, b[1] + 0.6 * (b[3] - b[1])), (cx, b[1] + 0.8 * (b[3] - b[1]))])
    hull = _convex_hull(np.asarray(body_pts))
    med_w = float(np.median([b[2] - b[0] for b in st.boxes])) if st.boxes else 0.1 * diag
    hull = _dilate_polygon(hull, max(0.5 * med_w, float(cfg.get("cashier_zone_dilate_frac", 0.12)) * diag))

    # counter line: between the cashier cluster and the positions of the people who come within reach of the
    # cashier ("window candidates"); far-away people (e.g. seen through a glass wall) are ignored
    others = [t for t in track_scores if t != cashier]
    reach = float(cfg.get("client_max_dist_frac", 0.40)) * diag
    candidates: list[int] = []
    opts = []
    for t in others:
        near = [p for p in (_body_point(b) for b in tracks[t].boxes) if math.hypot(p[0] - c_center[0], p[1] - c_center[1]) <= reach]
        if len(near) >= max(3, 0.1 * tracks[t].n):
            candidates.append(t)
            opts.extend(near)
    if opts:
        o = np.asarray(opts)
        o_center = (float(np.median(o[:, 0])), float(np.median(o[:, 1])))
        v = np.array([c_center[0] - o_center[0], c_center[1] - o_center[1]])
        nv = np.linalg.norm(v)
        normal = (v / nv) if nv > 1e-6 else np.array([0.0, 1.0])
        # refine: place the line at the midpoint between the closest cashier point and closest other point along the normal
        proj_c = (cpts - np.array(c_center)) @ normal
        proj_o = (o - np.array(c_center)) @ normal
        edge_c = float(np.percentile(proj_c, 10))  # cashier's near edge
        edge_o = float(np.percentile(proj_o, 90))  # others' near edge (negative side)
        mid = (edge_c + edge_o) / 2.0
        point = (c_center[0] + normal[0] * mid, c_center[1] + normal[1] * mid)
        sep = (edge_c - edge_o) / diag
        counter_conf = float(min(1.0, max(0.0, 0.5 + sep / 0.1)))
        counter_normal = (float(normal[0]), float(normal[1]))
    else:
        # no other people: line perpendicular to the cashier->storage direction, just in front of the cashier
        sp = workplace.get("counting_machine") or workplace.get("storage")
        normal = np.array([0.0, 1.0])
        if sp is not None:
            v = np.array([c_center[0] - sp[0], c_center[1] - sp[1]])
            if np.linalg.norm(v) > 1e-6:
                normal = v / np.linalg.norm(v)
        point = (c_center[0] - normal[0] * 0.12 * diag, c_center[1] - normal[1] * 0.12 * diag)
        counter_conf = 0.2
        counter_normal = (float(normal[0]), float(normal[1]))

    # clients / collectors / others: a window candidate must actually come close to the counter line
    bag_iou = float(cfg.get("collector_bag_iou", 0.05))
    client_band = float(cfg.get("client_band_frac", 0.15)) * diag
    clients, collectors, rest = [], [], []
    for t in others:
        if t not in candidates:
            rest.append(t)
            continue
        pts_t = [_body_point(b) for b in tracks[t].boxes]
        dmin = min(abs((p[0] - point[0]) * counter_normal[0] + (p[1] - point[1]) * counter_normal[1]) for p in pts_t)
        n_close = sum(1 for p in pts_t if abs((p[0] - point[0]) * counter_normal[0] + (p[1] - point[1]) * counter_normal[1]) <= client_band)
        if dmin > client_band or n_close < max(3, 0.1 * len(pts_t)):
            rest.append(t)
            continue
        with_bag = 0
        for k, fi in enumerate(tracks[t].frame_indices):
            fr = _frame_by_index(frames, fi)
            if fr is None:
                continue
            tb = tracks[t].boxes[k]
            for d in fr.by_class("bag"):
                if _iou(tb, d.xyxy) >= bag_iou:
                    with_bag += 1
                    break
        if with_bag >= max(3, 0.15 * tracks[t].n):
            collectors.append(t)
        else:
            clients.append(t)

    storage = workplace.get("storage")
    notes = []
    if cs["presence"] < float(cfg.get("cashier_min_presence", 0.5)):
        notes.append(f"cashier presence {cs['presence']:.2f} below {cfg.get('cashier_min_presence', 0.5)}")
    if len(track_scores) >= 2:
        second = sorted((v["score"] for v in track_scores.values()), reverse=True)[1]
        if cs["score"] - second < 0.05:
            notes.append(f"cashier margin small: {cs['score']:.3f} vs {second:.3f}")
    return Calibration(
        frame_w, frame_h, diag, cashier, cs["score"], track_scores, c_center, [tuple(map(float, p)) for p in hull], point, counter_normal, counter_conf,
        clients, collectors, rest, workplace, storage, workplace.get("counting_machine"), notes=notes
    )


def _frame_by_index(frames: list[FrameDetections], fi: int) -> Optional[FrameDetections]:
    # frames are in increasing index order; binary search
    lo, hi = 0, len(frames) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        v = frames[mid].frame_index
        if v == fi:
            return frames[mid]
        if v < fi:
            lo = mid + 1
        else:
            hi = mid - 1
    return None


def _dist_point_box(p, b) -> float:
    dx = max(b[0] - p[0], 0.0, p[0] - b[2])
    dy = max(b[1] - p[1], 0.0, p[1] - b[3])
    return math.hypot(dx, dy)


def _iou(a, b) -> float:
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def hands_of(fp: FramePoses, track_id: int, thr: float = 0.3) -> list[tuple[float, float]]:
    for p in fp.poses:
        if p.track_id == track_id:
            return [tuple(map(float, p.kpts[i])) for i in (L_WRIST, R_WRIST) if p.scores[i] >= thr]
    return []
