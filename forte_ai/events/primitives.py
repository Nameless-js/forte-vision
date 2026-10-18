"""Per-frame primitives derived from perception + calibration (Layer B, part 1).

Every primitive is a plain fact about one sampled frame, expressed with roles (cashier / client / collector)
and relative geometry (distances in fractions of the frame diagonal). Rules (rules.py) are temporal
conditions over sequences of these facts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np

from ..perception.detector import Detection, FrameDetections
from ..perception.pipeline import PerceptionResult
from ..perception.pose import FramePoses, L_ELBOW, L_WRIST, R_ELBOW, R_WRIST
from ..perception.roles import Calibration, _dist_point_box, _iou


@dataclass
class FrameState:
    k: int  # index into pr.frames
    t: float
    cashier_present: bool
    cashier_box: Optional[tuple]
    cashier_in_zone: bool
    cashier_hands: list[tuple[float, float]]  # wrists (det px)
    cashier_elbows: list[tuple[float, float]]
    cashier_pose_ok: bool
    client_ids: list[int]  # client tracks present in this frame
    client_at_window: list[int]  # client tracks within the counter band
    client_hands: dict[int, list[tuple[float, float]]]
    client_hand_over_counter: list[int]  # client tracks with a wrist on the cashier side of the line
    non_cashier_in_zone: list[int]  # any non-cashier track whose body point is inside the cashier zone
    collector_ids: list[int]
    cash: list[Detection]
    cash_near_cashier_hand: bool
    cash_near_client_hand: bool
    cash_on_counter: bool  # cash box centre within the counter band
    cash_on_cashier_side: bool  # cash visible on the cashier side (desk) away from hands
    cash_near_storage: bool
    phone_near_cashier_hand: bool
    phone_near_cashier_body: bool
    bag: list[Detection]
    bag_near_collector: bool
    bag_near_cashier_hand: bool
    document_near_hands: bool  # a document / id card near any hand around the counter
    id_card_visible: bool
    counting_machine_active: bool  # a cashier hand near the counting machine with cash near it
    n_people: int
    cup_near_cashier_hand: bool = False  # cup / bottle / food package in the cashier's hand
    cashier_strong: bool = False  # the cashier box is backed by a solid person detection (not through glass)
    person_in_zone_any: bool = False  # ANY solidly-detected person body is inside the cashier zone
    n_people_strong: int = 0  # VALID people (pose-backed or very solid detection) anywhere in the frame
    track_ages: dict = field(default_factory=dict)  # track id -> seconds since the track first appeared
    det_scores: dict = field(default_factory=dict)  # track id -> matched person-detection score this frame
    valid_tracks: list = field(default_factory=list)  # track ids that look like real humans this frame
    valid_bodies: list = field(default_factory=list)  # their body points


def _hands(fp: FramePoses, tid: int, thr: float) -> tuple[list, list, bool]:
    for p in fp.poses:
        if p.track_id == tid:
            w = [tuple(map(float, p.kpts[i])) for i in (L_WRIST, R_WRIST) if p.scores[i] >= thr]
            e = [tuple(map(float, p.kpts[i])) for i in (L_ELBOW, R_ELBOW) if p.scores[i] >= thr]
            return w, e, bool(w)
    return [], [], False


def _hand_fallback(box: tuple) -> list[tuple[float, float]]:
    """If no wrist keypoints are available use the two lower corners of the box as a crude hand proxy."""
    x1, y1, x2, y2 = box
    return [(x1 + 0.25 * (x2 - x1), y1 + 0.6 * (y2 - y1)), (x1 + 0.75 * (x2 - x1), y1 + 0.6 * (y2 - y1))]


def _near(points: Iterable[tuple], dets: Iterable[Detection], radius: float) -> bool:
    for p in points:
        for d in dets:
            if _dist_point_box(p, d.xyxy) <= radius:
                return True
    return False


def _own_phones(phones: list[Detection], c_hands: list, k_hands: list, cal: Calibration) -> list[Detection]:
    """Phone-like boxes that belong to the CASHIER: centre not on the client side of the counter and closer to
    a cashier wrist than to any client wrist (a client's wallet/phone during a handover is not the cashier's)."""
    out = []
    for d in phones:
        c = ((d.xyxy[0] + d.xyxy[2]) / 2.0, (d.xyxy[1] + d.xyxy[3]) / 2.0)
        if cal.window_anchor is not None and cal.signed_dist_to_counter(c) < 0:
            continue
        dc = min((math.hypot(c[0] - h[0], c[1] - h[1]) for h in c_hands), default=1e9)
        dk = min((math.hypot(c[0] - h[0], c[1] - h[1]) for h in k_hands), default=1e9)
        if dc <= dk:
            out.append(d)
    return out


def _cups(fd: FrameDetections, min_score: float) -> list[Detection]:
    """Cup/bottle/food detections that are confident and not just a re-labeled banknote stack or document."""
    others = fd.by_class("cash") + fd.by_class("document") + fd.by_class("id_card")
    out = []
    for d in fd.by_class("cup"):
        if d.score < min_score:
            continue
        if any(_iou(d.xyxy, o.xyxy) > 0.2 for o in others):
            continue
        out.append(d)
    return out


def build_frame_states(pr: PerceptionResult, cal: Calibration, cfg: dict) -> list[FrameState]:
    diag = cal.diag
    kthr = float(cfg.get("kpt_threshold", 0.3))
    hand_r = float(cfg.get("hand_radius_frac", 0.06)) * diag
    phone_r = float(cfg.get("phone_radius_frac", 0.045)) * diag
    phone_score = float(cfg.get("phone_min_score", 0.45))
    cup_score = float(cfg.get("cup_min_score", 0.55))
    strong_score = float(cfg.get("person_strong_score", 0.5))
    body_r = float(cfg.get("body_radius_frac", 0.10)) * diag
    band = float(cfg.get("counter_margin_frac", 0.06)) * diag
    storage_r = float(cfg.get("storage_radius_frac", 0.10)) * diag
    machine_r = float(cfg.get("machine_radius_frac", 0.08)) * diag
    cashier = cal.cashier_track
    clients = set(cal.client_tracks)
    collectors = set(cal.collector_tracks)
    states: list[FrameState] = []
    for k, (fd, fp, assigned) in enumerate(zip(pr.frames, pr.poses, pr.per_frame_tracks)):
        cbox = assigned.get(cashier) if cashier is not None else None
        c_present = cbox is not None
        person_dets = fd.by_class("person")

        def det_score_of(box) -> float:
            best = 0.0
            for d in person_dets:
                if _iou(box, d.xyxy) >= 0.5:
                    best = max(best, d.score)
            return best

        # ---- per-track validity: a REAL person is pose-backed (several solid body keypoints) or has a very
        # confident detection. Chairs, jackets on chairs, reflections and figures behind the glass wall all
        # produce person boxes around 0.4-0.6 with no coherent pose — the main source of phantom events.
        pose_kpts: dict[int, int] = {}
        for p in fp.poses:
            if p.track_id is not None:
                pose_kpts[p.track_id] = int((p.scores[5:11] >= kthr).sum())  # shoulders, elbows, wrists
        pose_kpts_ok = {tid: n >= 3 for tid, n in pose_kpts.items()}
        det_scores: dict[int, float] = {}
        ages: dict[int, float] = {}
        valid_tracks: list[int] = []
        valid_bodies: list[tuple[float, float]] = []
        any_in_zone = False
        n_room = 0  # people that count as "someone is in the room" (blocks departures)
        for _tid, _box in assigned.items():
            sc = det_score_of(_box)
            det_scores[_tid] = sc
            st0 = pr.tracks.get(_tid)
            ages[_tid] = (fd.t - st0.first_t) if st0 is not None else 0.0
            kp = pose_kpts.get(_tid, 0)
            is_valid = kp >= 3 or sc >= float(cfg.get("person_solid_score", 0.65))
            # room occupancy needs more than a reflection / through-glass figure: a reasonably confident
            # detection on top of the pose (people seen through the glass wall score ~0.35-0.5)
            if (kp >= 3 and sc >= float(cfg.get("room_min_det", 0.55))) or sc >= float(cfg.get("person_solid_score", 0.65)):
                n_room += 1
            _bp = ((_box[0] + _box[2]) / 2, _box[1] + 0.6 * (_box[3] - _box[1]))
            if is_valid:
                valid_tracks.append(_tid)
                valid_bodies.append(_bp)
                if cal.in_cashier_zone(_bp):
                    any_in_zone = True
        n_strong = n_room
        c_strong = c_present and (cashier in valid_tracks)
        c_in_zone = False
        c_hands: list = []
        c_elbows: list = []
        c_pose_ok = False
        if c_present:
            bp = ((cbox[0] + cbox[2]) / 2, cbox[1] + 0.6 * (cbox[3] - cbox[1]))
            c_in_zone = cal.in_cashier_zone(bp)
            c_hands, c_elbows, c_pose_ok = _hands(fp, cashier, kthr)
            if not c_hands:
                c_hands = _hand_fallback(cbox)
        client_ids, at_window, over_counter, in_zone_non_cashier, coll_ids = [], [], [], [], []
        client_hands: dict[int, list] = {}
        intrusion_depth = 0.25 * max(cal.cashier_client_dist, 0.15 * diag)
        for tid, box in assigned.items():
            if tid == cashier:
                continue
            bp = ((box[0] + box[2]) / 2, box[1] + 0.6 * (box[3] - box[1]))
            # intrusion is body-based and guarded: the cashier must be visible in the same frame (otherwise
            # "the intruder" is usually the cashier herself after a track-id switch), the box must not be a
            # duplicate detection of the cashier (IoU), and the body must be clearly PAST the midline toward
            # the cashier seat or inside the seat radius — leaning over the desk from the client side is normal.
            if (
                c_present
                and _iou(box, cbox) < 0.3
                and fd.t >= float(cfg.get("intrusion_warmup_s", 3.0))
                and ages.get(tid, 0.0) >= float(cfg.get("intrusion_track_age_s", 2.0))
                and pose_kpts.get(tid, 0) >= 6
                and det_scores.get(tid, 0.0) >= float(cfg.get("intrusion_min_det", 0.60))
                and cashier in valid_tracks
            ):
                sd = cal.signed_dist_to_counter(bp)
                if sd > intrusion_depth or cal.dist_to_cashier(bp) <= 1.0 * cal.zone_radius:
                    in_zone_non_cashier.append(tid)
            if tid in collectors:
                coll_ids.append(tid)
            if tid in clients or tid in collectors:
                client_ids.append(tid)
                sd = cal.signed_dist_to_counter(bp)
                if cal.window_anchor is not None:
                    # "at the window" = within reach of the visitor seat (the anchor), not anywhere on the
                    # client side — people behind the glass wall are on the client side too
                    reach_r = float(cfg.get("window_reach_frac", 0.15)) * diag
                    at_w = math.hypot(bp[0] - cal.window_anchor[0], bp[1] - cal.window_anchor[1]) <= reach_r
                else:
                    at_w = abs(sd) <= band * 2.5 or (sd < 0 and -sd <= 0.25 * diag)
                if at_w:
                    at_window.append(tid)
                hs, _, ok = _hands(fp, tid, kthr)
                if not hs:
                    hs = _hand_fallback(box)
                client_hands[tid] = hs
                # a client's wrist clearly on the cashier side, or extended well ahead of the client's own torso
                k_body = cal.signed_dist_to_counter(bp)
                reach = float(cfg.get("reach_frac", 0.10)) * diag
                if ok and any(cal.signed_dist_to_counter(h) > band * 0.5 or (cal.signed_dist_to_counter(h) - k_body) >= reach for h in hs):
                    over_counter.append(tid)
        cash = fd.by_class("cash")
        phones = [d for d in fd.by_class("phone") if d.score >= phone_score]
        # a "phone" box adjacent to / inside a static landmark (laptop screen corner, counting-machine
        # display) is a known false positive of the open-vocabulary detector
        landmarks = fd.by_class("laptop") + fd.by_class("counting_machine") + fd.by_class("storage")
        phones = [p for p in phones if not any(_iou(p.xyxy, lm.xyxy) > 0.05 or _dist_point_box(((p.xyxy[0] + p.xyxy[2]) / 2, (p.xyxy[1] + p.xyxy[3]) / 2), lm.xyxy) < 0.015 * diag for lm in landmarks)]
        bags = fd.by_class("bag")
        docs = fd.by_class("document") + fd.by_class("id_card")
        all_client_hands = [h for hs in client_hands.values() for h in hs]
        cash_on_counter = any(abs(cal.signed_dist_to_counter(((d.xyxy[0] + d.xyxy[2]) / 2, (d.xyxy[1] + d.xyxy[3]) / 2))) <= band for d in cash)
        cash_cashier_side = any(cal.signed_dist_to_counter(((d.xyxy[0] + d.xyxy[2]) / 2, (d.xyxy[1] + d.xyxy[3]) / 2)) > band for d in cash)
        storage_pt = cal.storage_point
        machine_pt = cal.counting_machine_point
        cash_near_storage = bool(storage_pt) and any(_dist_point_box(storage_pt, d.xyxy) <= storage_r for d in cash)
        machine_active = bool(machine_pt) and c_present and any(math.hypot(h[0] - machine_pt[0], h[1] - machine_pt[1]) <= machine_r for h in c_hands)
        states.append(
            FrameState(
                k=k,
                t=fd.t,
                cashier_present=c_present,
                cashier_box=cbox,
                cashier_in_zone=c_in_zone,
                cashier_hands=c_hands,
                cashier_elbows=c_elbows,
                cashier_pose_ok=c_pose_ok,
                client_ids=client_ids,
                client_at_window=at_window,
                client_hands=client_hands,
                client_hand_over_counter=over_counter,
                non_cashier_in_zone=in_zone_non_cashier,
                collector_ids=coll_ids,
                cash=cash,
                cash_near_cashier_hand=c_present and _near(c_hands, cash, hand_r),
                cash_near_client_hand=_near(all_client_hands, cash, hand_r),
                cash_on_counter=cash_on_counter,
                cash_on_cashier_side=cash_cashier_side,
                cash_near_storage=cash_near_storage,
                phone_near_cashier_hand=c_present and c_pose_ok and _near(c_hands, _own_phones(phones, c_hands, all_client_hands, cal), phone_r),
                phone_near_cashier_body=c_present and any(_iou(cbox, p.xyxy) > 0 or _dist_point_box(((p.xyxy[0] + p.xyxy[2]) / 2, (p.xyxy[1] + p.xyxy[3]) / 2), cbox) <= body_r * 0.5 for p in phones),
                bag=bags,
                bag_near_collector=any(_near(client_hands.get(t, []), bags, hand_r * 1.5) for t in coll_ids),
                bag_near_cashier_hand=c_present and _near(c_hands, bags, hand_r * 1.5),
                document_near_hands=_near(c_hands + all_client_hands, docs, hand_r),
                id_card_visible=bool(fd.by_class("id_card")),
                counting_machine_active=machine_active,
                n_people=len(assigned),
                cup_near_cashier_hand=c_present and c_pose_ok and _near(c_hands, _cups(fd, cup_score), phone_r),
                cashier_strong=c_strong,
                person_in_zone_any=any_in_zone,
                n_people_strong=n_strong,
                track_ages=ages,
                det_scores=det_scores,
                valid_tracks=valid_tracks,
                valid_bodies=valid_bodies,
            )
        )
    return states


# ---------------------------------------------------------------- temporal helpers
@dataclass
class Segment:
    start: float
    end: float
    k_start: int
    k_end: int
    value: float = 1.0
    facts: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end - self.start


def runs(flags: list[bool], times: list[float], min_duration: float = 0.0, max_gap_frames: int = 1) -> list[Segment]:
    """Contiguous runs of True (allowing gaps of up to max_gap_frames False frames)."""
    segs: list[Segment] = []
    start = None
    gap = 0
    last_true = -1
    for i, f in enumerate(flags):
        if f:
            if start is None:
                start = i
            last_true = i
            gap = 0
        elif start is not None:
            gap += 1
            if gap > max_gap_frames:
                if times[last_true] - times[start] >= min_duration:
                    segs.append(Segment(times[start], times[last_true], start, last_true))
                start, gap = None, 0
    if start is not None and times[last_true] - times[start] >= min_duration:
        segs.append(Segment(times[start], times[last_true], start, last_true))
    return segs


def hand_motion_energy(states: list[FrameState], window_frames: int) -> np.ndarray:
    """Per-frame mean wrist (or elbow) speed of the cashier over a sliding window (det px per frame)."""
    n = len(states)
    speed = np.zeros(n, dtype=np.float32)
    prev = None
    for i, s in enumerate(states):
        pts = s.cashier_hands if s.cashier_pose_ok else s.cashier_elbows
        if s.cashier_present and pts and prev is not None and len(prev) == len(pts):
            speed[i] = float(np.mean([math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pts, prev)]))
        prev = pts if (s.cashier_present and pts) else None
    if window_frames > 1:
        kernel = np.ones(window_frames, dtype=np.float32) / window_frames
        speed = np.convolve(speed, kernel, mode="same")
    return speed


def periodicity(signal: np.ndarray, fps: float, fmin: float = 0.8, fmax: float = 4.0) -> float:
    """Share of spectral energy in the hand-counting band (0.8–4 Hz) — 0..1."""
    x = np.asarray(signal, dtype=np.float32)
    if len(x) < 8:
        return 0.0
    x = x - x.mean()
    if np.allclose(x, 0):
        return 0.0
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), d=1.0 / fps)
    band = (freqs >= fmin) & (freqs <= fmax)
    tot = spec[1:].sum()
    return float(spec[band].sum() / tot) if tot > 0 else 0.0
