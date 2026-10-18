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
    window_anchor: Optional[tuple[float, float]] = None  # median seated position of the nearest client
    cashier_client_dist: float = 0.0  # ||cashier_center - window_anchor|| (det px)
    zone_radius: float = 0.0  # radius of the cashier zone around cashier_center (det px)
    storage_points: list = field(default_factory=list)  # all storage-unit cluster centres
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
            "window_anchor_norm": None if self.window_anchor is None else [round(self.window_anchor[0] / self.frame_w, 3), round(self.window_anchor[1] / self.frame_h, 3)],
            "cashier_client_dist_frac": round(self.cashier_client_dist / self.diag, 3) if self.diag else 0.0,
            "zone_radius_frac": round(self.zone_radius / self.diag, 3) if self.diag else 0.0,
            "storage_points_norm": [[round(p[0] / self.frame_w, 3), round(p[1] / self.frame_h, 3)] for p in self.storage_points],
            "method": self.method,
            "notes": self.notes,
        }
        return d

    # ---- geometry helpers ----
    def signed_dist_to_counter(self, p) -> float:
        """> 0 on the cashier side, < 0 on the client side (in det pixels)."""
        return float((p[0] - self.counter_point[0]) * self.counter_normal[0] + (p[1] - self.counter_point[1]) * self.counter_normal[1])

    def in_cashier_zone(self, p) -> bool:
        """Within the zone radius of the cashier's seat, or at a workplace anchor (safe / counting machine).

        Radius-based instead of hull/half-plane: it does not depend on the counter-line estimate, so a noisy
        client-cluster direction cannot make the cashier 'leave' their own zone.
        """
        if math.hypot(p[0] - self.cashier_center[0], p[1] - self.cashier_center[1]) <= self.zone_radius:
            return True
        anchors = list(self.storage_points) + ([self.counting_machine_point] if self.counting_machine_point else [])
        for anchor in anchors:
            if anchor is not None and math.hypot(p[0] - anchor[0], p[1] - anchor[1]) <= 0.7 * self.zone_radius:
                return True
        return False

    def dist_to_cashier(self, p) -> float:
        return math.hypot(p[0] - self.cashier_center[0], p[1] - self.cashier_center[1])


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

    # static workplace objects: CLUSTERED centres of their detections (a scene can contain two storage
    # units — e.g. the safe and a drawer pedestal — and mixing them into one median lands between them)
    workplace: dict[str, tuple[float, float]] = {}
    workplace_clusters: dict[str, list[tuple[float, float]]] = {}
    for cls in WORKPLACE_CLASSES:
        cs = [_center(d.xyxy) for f in frames for d in f.by_class(cls)]
        if len(cs) < max(3, 0.10 * n_frames):
            continue
        clusters: list[list[tuple[float, float]]] = []
        for p in cs:
            for cl in clusters:
                m = np.median(np.asarray(cl), axis=0)
                if math.hypot(p[0] - m[0], p[1] - m[1]) <= 0.10 * diag:
                    cl.append(p)
                    break
            else:
                clusters.append([p])
        clusters = [cl for cl in clusters if len(cl) >= max(3, 0.05 * n_frames)]
        if not clusters:
            continue
        meds = [tuple(np.median(np.asarray(cl), axis=0).tolist()) for cl in sorted(clusters, key=len, reverse=True)]
        workplace_clusters[cls] = meds
        workplace[cls] = meds[0]

    # per-track cues
    cash_centers_by_frame = [[_center(d.xyxy) for d in f.by_class("cash")] for f in frames]
    person_dets_by_index = {f.frame_index: [(d.xyxy, d.score) for d in f.by_class("person")] for f in frames}

    def track_det_score(st: TrackState) -> float:
        """Median matched person-detection score of a track — reflections in the glass stay low."""
        idxs = st.frame_indices
        step = max(1, len(idxs) // 40)
        scores = []
        for k in range(0, len(idxs), step):
            best = 0.0
            for box, sc in person_dets_by_index.get(idxs[k], []):
                if _iou(st.boxes[k], box) >= 0.5:
                    best = max(best, sc)
            scores.append(best)
        scores.sort()
        return scores[len(scores) // 2] if scores else 0.0

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
        det = track_det_score(st)
        score = (0.30 * presence + 0.20 * s_static + 0.15 * s_early + 0.20 * s_obj + 0.15 * s_cash) * (0.6 + 0.4 * min(1.0, det / 0.65))
        track_scores[tid] = {"presence": presence, "static": s_static, "early": s_early, "objects": s_obj, "cash": s_cash, "det": det, "score": score, "n": st.n, "median": [med[0], med[1]]}

    if not track_scores:
        return Calibration(frame_w, frame_h, diag, None, 0.0, {}, (frame_w / 2, frame_h / 2), [], (frame_w / 2, frame_h / 2), (0.0, 1.0), 0.0, [], [], [], workplace, workplace.get("storage"), workplace.get("counting_machine"), zone_radius=0.1 * diag, notes=["no tracks"])

    cashier = max(track_scores, key=lambda k: track_scores[k]["score"])
    cs = track_scores[cashier]
    st = tracks[cashier]
    cpts = np.asarray([_body_point(b) for b in st.boxes])
    # The SEAT is the FIRST sustained stationary dwell of the cashier track, not the whole-track median:
    # the staged clips always open with the cashier at the workplace, while later she may stand at the door
    # for half the clip, which would drag a global median (and the zone) away from the desk. The room is so
    # compressed in projection that anchor-radius filtering cannot separate seat from door.
    c_center = (float(np.median(cpts[:, 0])), float(np.median(cpts[:, 1])))
    still_r = float(cfg.get("seat_still_radius_frac", 0.025)) * diag
    seat_min_s = float(cfg.get("seat_min_still_s", 3.0))
    if len(st.times) >= 5:
        i = 0
        n_pts = len(cpts)
        while i < n_pts:
            j = i
            anchor = cpts[i]
            while j + 1 < n_pts:
                nxt = cpts[j + 1]
                seg = cpts[i : j + 2]
                med = np.median(seg, axis=0)
                if math.hypot(nxt[0] - med[0], nxt[1] - med[1]) > still_r * 2.5:
                    break
                j += 1
            if st.times[j] - st.times[i] >= seat_min_s:
                seg = cpts[i : j + 1]
                c_center = (float(np.median(seg[:, 0])), float(np.median(seg[:, 1])))
                break
            i = j + 1
    # zone: hull of the cashier's torso points (box centre + a point at 60 % height), dilated by a body-sized
    # margin. Full boxes are NOT used: an outstretched arm or the chair would swallow the client's seat.
    body_pts = []
    for b in st.boxes:
        cx = (b[0] + b[2]) / 2.0
        body_pts.extend([(cx, b[1] + 0.35 * (b[3] - b[1])), (cx, b[1] + 0.6 * (b[3] - b[1])), (cx, b[1] + 0.8 * (b[3] - b[1]))])
    hull = _convex_hull(np.asarray(body_pts))
    med_w = float(np.median([b[2] - b[0] for b in st.boxes])) if st.boxes else 0.1 * diag
    hull = _dilate_polygon(hull, max(0.5 * med_w, float(cfg.get("cashier_zone_dilate_frac", 0.12)) * diag))

    # ---- window anchor: the median SEATED position of the main sustained visitor -------------------
    # For every other track collect its positions while within reach of the cashier; a window candidate must
    # hold a stable position there (seated at the desk), which excludes people walking past or seen through
    # the glass wall; it must also sit CLEARLY AWAY from the cashier's own seat — residual duplicate tracks
    # of the cashier otherwise collapse the counter line onto her. The candidate with the most seated frames
    # becomes the window anchor; the counter line is the perpendicular bisector between the seats.
    others = [t for t in track_scores if t != cashier]
    reach = float(cfg.get("client_max_dist_frac", 0.40)) * diag
    sit_r = float(cfg.get("client_sit_radius_frac", 0.05)) * diag
    min_sep = max(float(cfg.get("anchor_min_sep_frac", 0.10)) * diag, 1.0 * med_w)
    candidates: list[int] = []
    cand_medians: dict[int, tuple[float, float]] = {}
    cand_near: dict[int, int] = {}
    min_det = float(cfg.get("client_min_det_score", 0.52))
    for t in others:
        if track_scores[t].get("det", 0.0) < min_det:
            continue  # reflections in the glass / people behind it never reach solid detection scores
        near = [p for p in (_body_point(b) for b in tracks[t].boxes) if math.hypot(p[0] - c_center[0], p[1] - c_center[1]) <= reach]
        if len(near) < max(3, 0.1 * tracks[t].n):
            continue
        arr = np.asarray(near)
        med = (float(np.median(arr[:, 0])), float(np.median(arr[:, 1])))
        if math.hypot(med[0] - c_center[0], med[1] - c_center[1]) < min_sep:
            continue  # sits on top of the cashier -> a duplicate/fragment of her own track
        stable = sum(1 for p in near if math.hypot(p[0] - med[0], p[1] - med[1]) <= sit_r)
        if stable < max(3, 0.3 * len(near)):
            continue  # never settles near the cashier -> passer-by / background person
        candidates.append(t)
        cand_medians[t] = med
        cand_near[t] = stable
    if candidates:
        # the main visitor = the one seated at the window the longest
        anchor_t = max(candidates, key=lambda t: (cand_near[t], -math.hypot(cand_medians[t][0] - c_center[0], cand_medians[t][1] - c_center[1])))
        window_anchor = cand_medians[anchor_t]
        v = np.array([c_center[0] - window_anchor[0], c_center[1] - window_anchor[1]])
        dist_cc = float(np.linalg.norm(v))
        normal = (v / dist_cc) if dist_cc > 1e-6 else np.array([0.0, 1.0])
        point = ((c_center[0] + window_anchor[0]) / 2.0, (c_center[1] + window_anchor[1]) / 2.0)
        counter_conf = float(min(1.0, dist_cc / (0.15 * diag)))
        counter_normal = (float(normal[0]), float(normal[1]))
    else:
        # no visitors: line perpendicular to the cashier->storage direction, just in front of the cashier
        window_anchor = None
        dist_cc = 0.30 * diag
        sp = workplace.get("counting_machine") or workplace.get("storage")
        normal = np.array([0.0, 1.0])
        if sp is not None:
            v = np.array([c_center[0] - sp[0], c_center[1] - sp[1]])
            if np.linalg.norm(v) > 1e-6:
                normal = v / np.linalg.norm(v)
        point = (c_center[0] - normal[0] * 0.15 * diag, c_center[1] - normal[1] * 0.15 * diag)
        counter_conf = 0.2
        counter_normal = (float(normal[0]), float(normal[1]))
    # cashier zone radius: between the seat and the midline, at least a body width; with no visitor at all
    # the fallback dist_cc is fictitious, so the zone shrinks to a body-scaled radius (early absence anchor)
    if window_anchor is not None:
        zone_radius = max(0.45 * dist_cc, 0.6 * med_w, float(cfg.get("zone_min_radius_frac", 0.08)) * diag)
    else:
        zone_radius = max(0.7 * med_w, float(cfg.get("zone_min_radius_frac", 0.08)) * diag)

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
            bw = tb[2] - tb[0]
            for d in fr.by_class("bag"):
                if _iou(tb, d.xyxy) >= bag_iou or _dist_point_box(_center(d.xyxy), tb) <= 0.75 * bw:
                    with_bag += 1
                    break
        # a collector arrives WITH the bag: either the bag co-occurs with the track often, or bag
        # detections start within a couple of seconds of the track's appearance
        bag_times = [f.t for f in frames if f.by_class("bag")]
        bag_at_arrival = bool(bag_times) and any(abs(bt - tracks[t].first_t) <= 2.5 for bt in bag_times[:10])
        if with_bag >= max(3, 0.15 * tracks[t].n) or (bag_at_arrival and with_bag >= 2):
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
    # storage anchor used for dwell/securing: the storage cluster nearest to the cashier seat
    storage_pts = workplace_clusters.get("storage", [])
    storage_near = min(storage_pts, key=lambda p: math.hypot(p[0] - c_center[0], p[1] - c_center[1])) if storage_pts else storage
    return Calibration(
        frame_w, frame_h, diag, cashier, cs["score"], track_scores, c_center, [tuple(map(float, p)) for p in hull], point, counter_normal, counter_conf,
        clients, collectors, rest, workplace, storage_near, workplace.get("counting_machine"),
        window_anchor=window_anchor, cashier_client_dist=dist_cc, zone_radius=zone_radius,
        storage_points=storage_pts or ([storage] if storage else []), notes=notes
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
