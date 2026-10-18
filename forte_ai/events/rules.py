"""Layer B rules: small temporal conditions over frame primitives -> candidates with exact timecodes.

Rule set M2, derived from the frame review of all 42 training videos (analysis/review/, analysis/taxonomy.json).
Violation families observed in the data:
  R1a cashier leaves while a client is at the window           -> cashier_left_during_service
  R1b cashier walks out, room left empty, workplace not secured -> workplace_left_unsecured / cash_left_unattended
  R2  cash lies on the cashier's side with nobody at it         -> cash_left_unattended
  R3  phone in the cashier's hand                               -> phone_at_workplace
  R3b cup/bottle/food in the cashier's hand                     -> personal_items_at_workplace
  R4  another person deep in the cashier's zone while she works -> unauthorized_in_cash_zone
  R10 a person enters an EMPTY cash workplace and settles there -> unauthorized_in_cash_zone
  R5  cash issued to the client with no counting shortly before -> issue_without_count
  R6  cash accepted and not counted while the client is present -> accept_without_count
  R7  cash handover with no ID/document shown before            -> no_id_check (conservative)
  R8  collector bag taken with no inspection/document           -> collection_bag_unchecked
  R9  second client while the first operation's cash is out     -> two_clients_cash_mixed

Timecode policy (documented in VIOLATION_TYPES.md):
  * action violation  -> t_event = first sampled frame where the condition becomes true;
  * omission          -> t_event = the moment of the action that should have been preceded by the skipped
    step (the handover without counting; the client walking away with the cash never counted; the storing
    without counting).
All thresholds come from configs/*.yaml (section `rules`); distances are fractions of the frame diagonal,
sides are relative to the per-video calibration. No pixel constants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ..perception.roles import Calibration
from ..report import Candidate
from .primitives import FrameState, Segment, hand_motion_energy, periodicity, runs


@dataclass
class Episode:
    """A service episode: a client (or collector) is at the window."""

    start: float
    end: float
    k_start: int
    k_end: int
    client_ids: set = field(default_factory=set)
    is_collector: bool = False


@dataclass
class Handover:
    t: float
    k: int
    direction: str  # cashier_to_client | client_to_cashier | unknown
    evidence: str
    strength: float  # 0..1


@dataclass
class EventSummary:
    episodes: list[Episode]
    handovers: list[Handover]
    counting: list[Segment]
    cashier_absent: list[Segment]
    phone: list[Segment]
    cup: list[Segment]
    intrusion: list[Segment]
    cash_visible: list[Segment]
    id_shown: list[Segment]
    bag_handling: list[Segment]
    storage_dwell: list[Segment]
    room_empty: list[Segment]
    departures: list[float]
    empty_start: bool
    hand_speed: np.ndarray

    def to_dict(self) -> dict:
        seg = lambda ss: [[round(s.start, 2), round(s.end, 2)] for s in ss]  # noqa: E731
        return {
            "episodes": [[round(e.start, 2), round(e.end, 2), sorted(e.client_ids), e.is_collector] for e in self.episodes],
            "handovers": [[round(h.t, 2), h.direction, h.evidence, round(h.strength, 2)] for h in self.handovers],
            "counting": seg(self.counting),
            "cashier_absent": seg(self.cashier_absent),
            "phone": seg(self.phone),
            "cup": seg(self.cup),
            "intrusion": seg(self.intrusion),
            "cash_visible": seg(self.cash_visible),
            "id_shown": seg(self.id_shown),
            "bag_handling": seg(self.bag_handling),
            "storage_dwell": seg(self.storage_dwell),
            "room_empty": seg(self.room_empty),
            "departures": [round(t, 2) for t in self.departures],
            "empty_start": self.empty_start,
        }


# ---------------------------------------------------------------------- helpers
def _smooth(flags: list[bool], k: int) -> list[bool]:
    """Majority vote in a window of k frames (odd)."""
    if k <= 1:
        return list(flags)
    a = np.asarray(flags, dtype=np.float32)
    kernel = np.ones(k, dtype=np.float32) / k
    s = np.convolve(a, kernel, mode="same")
    return [bool(v >= 0.5) for v in s]


def _overlaps(a0: float, a1: float, b0: float, b1: float) -> bool:
    return a0 <= b1 and b0 <= a1


def _any_in(segs: list[Segment], t0: float, t1: float, min_dur: float = 0.0) -> Optional[Segment]:
    for s in segs:
        if _overlaps(s.start, s.end, t0, t1) and s.duration >= min_dur:
            return s
    return None


def _cum_in(segs: list[Segment], t0: float, t1: float) -> float:
    """Cumulative overlap duration of segments with [t0, t1]."""
    total = 0.0
    for s in segs:
        total += max(0.0, min(s.end, t1) - max(s.start, t0))
    return total


# ---------------------------------------------------------------------- event extraction
def extract_events(states: list[FrameState], cal: Calibration, cfg: dict, fps: float, duration: float) -> EventSummary:
    times = [s.t for s in states]
    n = len(states)
    diag = cal.diag
    gap = max(1, int(round(float(cfg.get("gap_tolerance_s", 1.0)) * fps)))
    smooth_k = int(cfg.get("smooth_frames", 3)) | 1

    # ---- episodes: someone (client/collector) at the window
    present = _smooth([bool(s.client_at_window) for s in states], smooth_k)
    episodes: list[Episode] = []
    for seg in runs(present, times, min_duration=float(cfg.get("episode_min_s", 2.0)), max_gap_frames=gap * 2):
        ids: set = set()
        coll = False
        for k in range(seg.k_start, seg.k_end + 1):
            ids.update(states[k].client_at_window)
            if states[k].collector_ids:
                coll = True
        episodes.append(Episode(seg.start, seg.end, seg.k_start, seg.k_end, ids, coll))

    # ---- cashier absent from own zone / room empty. "Absent" = no SOLIDLY-detected person body in the zone:
    # this survives track-id switches (the person is still seen under another id) and the cashier remaining
    # tracked through the glass wall after leaving (weak, low-score detections).
    absent = _smooth([not s.person_in_zone_any for s in states], smooth_k)
    cashier_absent = runs(absent, times, min_duration=float(cfg.get("left_zone_min_s", 1.5)), max_gap_frames=gap)
    room_empty = runs(_smooth([s.n_people_strong == 0 for s in states], smooth_k), times, min_duration=0.6, max_gap_frames=gap)

    # ---- phone / cup in the cashier's hand
    phone = runs(_smooth([s.phone_near_cashier_hand for s in states], smooth_k), times, min_duration=float(cfg.get("phone_min_s", 2.0)), max_gap_frames=gap)
    cup = runs(_smooth([getattr(s, "cup_near_cashier_hand", False) for s in states], smooth_k), times, min_duration=float(cfg.get("cup_min_s", 2.0)), max_gap_frames=gap)

    # ---- non-cashier body deep in the cashier zone (hand reaches are handovers, not intrusions)
    intr_flags = [bool(s.non_cashier_in_zone) for s in states]
    intrusion = runs(_smooth(intr_flags, smooth_k), times, min_duration=float(cfg.get("intrusion_min_s", 1.5)), max_gap_frames=gap)

    # ---- cash visible, id/document shown near hands, bag handling, hands at the safe
    cash_visible = runs(_smooth([bool(s.cash) for s in states], smooth_k), times, min_duration=0.0, max_gap_frames=gap)
    id_shown = runs(_smooth([s.document_near_hands or s.id_card_visible for s in states], smooth_k), times, min_duration=float(cfg.get("id_min_s", 0.6)), max_gap_frames=gap)
    bag_handling = runs(_smooth([s.bag_near_cashier_hand or s.bag_near_collector for s in states], smooth_k), times, min_duration=0.4, max_gap_frames=gap)
    # hands at the safe while the BODY has moved toward it (seated hand-waving near an adjacent safe is not
    # a securing routine; clean videos 25/27 show the cashier standing at the safe to store valuables)
    storage_r = float(cfg.get("storage_dwell_radius_frac", 0.09)) * diag
    sps = list(cal.storage_points) or ([cal.storage_point] if cal.storage_point else [])
    sd_flags = []
    for s in states:
        ok = False
        if sps and s.cashier_present and s.cashier_box is not None:
            b = s.cashier_box
            body = ((b[0] + b[2]) / 2.0, b[1] + 0.5 * (b[3] - b[1]))
            moved = cal.dist_to_cashier(body) > 0.5 * cal.zone_radius
            pts = list(s.cashier_hands) + [body]
            ok = moved and any(math.hypot(p[0] - sp[0], p[1] - sp[1]) <= storage_r for p in pts for sp in sps)
        sd_flags.append(ok)
    storage_dwell = runs(_smooth(sd_flags, smooth_k), times, min_duration=0.6, max_gap_frames=gap)

    # ---- counting: machine use (sustained) OR periodic hand motion with cash at the hands
    speed = hand_motion_energy(states, window_frames=1) * fps / diag  # fraction of diagonal per second
    win = max(4, int(round(float(cfg.get("counting_window_frames_s", 2.0)) * fps)))
    s_min = float(cfg.get("counting_hand_speed_frac_s", 0.03))
    p_min = float(cfg.get("counting_periodicity_min", 0.30))
    cash_frac_min = float(cfg.get("counting_cash_fraction", 0.25))
    machine_runs = runs(
        _smooth([s.counting_machine_active for s in states], smooth_k), times, min_duration=float(cfg.get("counting_machine_min_s", 1.2)), max_gap_frames=gap
    )
    # cash detections are sporadic -> dilate the cash-near-hand signal ±2 s before using it as evidence
    cash_near = np.asarray([s.cash_near_cashier_hand for s in states], dtype=bool)
    dil = max(1, int(round(2.0 * fps)))
    cash_dil = np.zeros(n, dtype=bool)
    for i in np.flatnonzero(cash_near):
        cash_dil[max(0, i - dil) : min(n, i + dil + 1)] = True
    in_machine = [False] * n
    for seg in machine_runs:
        # a machine run only counts as counting if cash is actually seen around it (±3 s): standing next to
        # the machine while packing a bag is not a count
        a3 = max(0, seg.k_start - int(round(3.0 * fps)))
        b3 = min(n, seg.k_end + 1 + int(round(3.0 * fps)))
        if not cash_dil[a3:b3].any():
            continue
        for k in range(seg.k_start, seg.k_end + 1):
            in_machine[k] = True
    count_flags = []
    for i in range(n):
        a, b = max(0, i - win // 2), min(n, i + win // 2 + 1)
        seg = speed[a:b]
        s = states[i]
        cash_frac = float(cash_dil[a:b].mean())
        periodic = float(np.mean(seg)) >= s_min and periodicity(seg, fps) >= p_min
        count_flags.append(in_machine[i] or (periodic and s.cashier_present and cash_frac >= cash_frac_min))
    counting = runs(_smooth(count_flags, smooth_k), times, min_duration=float(cfg.get("counting_min_duration_s", 1.5)), max_gap_frames=gap)

    # ---- departures: the cashier goes absent and the room empties (and stays empty)
    empty_after = float(cfg.get("empty_room_after_s", 2.5))
    departures: list[float] = []
    # A departure may include a long linger AT THE DOOR before stepping out, so the room-empty condition is
    # "somewhere inside/right after the absence the room stays empty" rather than a fraction of the absence.
    for seg in cashier_absent:
        window = [s for s in states if seg.start <= s.t <= min(seg.end + 2.0, duration)]
        if not window:
            continue
        empty_flags = [s.n_people_strong == 0 for s in window]
        wtimes = [s.t for s in window]
        till_end = seg.end >= duration - 1.0
        empty_runs = runs(empty_flags, wtimes, min_duration=0.0, max_gap_frames=1)
        if till_end:
            emptied = any(r.duration >= 1.2 or r.end >= duration - 1.5 for r in empty_runs)
        else:
            # mid-video "departures" are usually occlusions (the cashier crouching behind furniture):
            # demand a long truly-empty stretch AND that she was last seen WALKING AWAY from the seat,
            # not vanishing in place at the desk
            emptied = any(r.duration >= max(8.0, empty_after) for r in empty_runs)
            if emptied:
                last_pos = None
                for s in states:
                    if s.t < seg.start and s.valid_bodies:
                        for tid, b in zip(s.valid_tracks, s.valid_bodies):
                            if tid == (cal.cashier_track if cal.cashier_track is not None else tid):
                                last_pos = b
                if last_pos is not None and cal.dist_to_cashier(last_pos) < 1.3 * cal.zone_radius:
                    emptied = False
        if emptied:
            departures.append(seg.start)

    # ---- empty start: nobody at the workplace during the first seconds
    empty_start_s = float(cfg.get("empty_start_s", 2.5))
    near_r = float(cfg.get("workplace_near_frac", 0.16)) * diag
    anchors = [a for a in ([cal.counting_machine_point] + list(cal.storage_points) + [cal.workplace_objects.get("laptop")]) if a is not None]
    if not anchors:
        anchors = [cal.cashier_center]

    def at_workplace(s: FrameState) -> bool:
        return any(math.hypot(p[0] - a[0], p[1] - a[1]) <= near_r for p in s.valid_bodies for a in anchors)

    # empty start: nobody AT THE OPERATOR SEAT in the first seconds (people may be visible through the
    # glass or walking in). Object-anchor radii fail here: the room is heavily compressed in projection,
    # so the door can be as close to the counting machine as the seat is. The seat itself separates best.
    seat_r = max(1.2 * cal.zone_radius, 0.09 * diag)

    def at_seat(s: FrameState) -> bool:
        return any(math.hypot(p[0] - cal.cashier_center[0], p[1] - cal.cashier_center[1]) <= seat_r for p in s.valid_bodies)

    # Empty start = the very first frames contain NO solid person anywhere in the room, and the track
    # that later works at the desk only appears afterwards. In the training clips a cashier who is on duty
    # is always detected from frame 0; seat-based tests fail because an entrant reaches "its own seat"
    # within 2 s. People behind the glass wall never reach the room-occupancy detection level.
    head0 = [s for s in states if s.t <= float(cfg.get("empty_start_probe_s", 0.4))]
    st_c = None
    if cal.cashier_track is not None:
        from_tracks = getattr(cal, "track_first_t", {}) or {}
        st_c = from_tracks.get(cal.cashier_track)
    first_c = st_c if st_c is not None else next((s.t for s in states if s.cashier_present), 0.0)
    empty_start = bool(head0) and all(s.n_people_strong == 0 for s in head0) and first_c >= float(cfg.get("empty_start_min_first_s", 0.6))

    handovers = _detect_handovers(states, cal, cfg, fps)
    return EventSummary(
        episodes, handovers, counting, cashier_absent, phone, cup, intrusion, cash_visible, id_shown, bag_handling,
        storage_dwell, room_empty, departures, empty_start, speed
    )


def _detect_handovers(states: list[FrameState], cal: Calibration, cfg: dict, fps: float) -> list[Handover]:
    """A handover is an active REACH across the counter: the cashier extends a wrist well ahead of the torso
    toward the client side (or across the line), or a client does the same toward the cashier side."""
    diag = cal.diag
    band = float(cfg.get("reach_band_frac", 0.08)) * diag
    meet = float(cfg.get("hands_meet_frac", 0.05)) * diag
    reach = float(cfg.get("reach_frac", 0.10)) * diag
    times = [s.t for s in states]
    n = len(states)

    def body_sd(box):
        return cal.signed_dist_to_counter(((box[0] + box[2]) / 2.0, box[1] + 0.6 * (box[3] - box[1])))

    eq = [a for a in ([cal.counting_machine_point] + list(cal.storage_points)) if a is not None]
    eq_r = float(cfg.get("equipment_hand_radius_frac", 0.06)) * diag
    eq_box_r = float(cfg.get("equipment_box_radius_frac", 0.05)) * diag
    eq_boxes = [b for k, b in (cal.workplace_boxes or {}).items() if k in ("counting_machine", "storage")]

    def at_equipment(h) -> bool:
        if any(math.hypot(h[0] - a[0], h[1] - a[1]) <= eq_r for a in eq):
            return True
        for b in eq_boxes:
            dx = max(b[0] - h[0], 0.0, h[0] - b[2])
            dy = max(b[1] - h[1], 0.0, h[1] - b[3])
            if math.hypot(dx, dy) <= eq_box_r:
                return True
        return False

    reach_c, reach_k, meets, cash_any = [], [], [], []
    for s in states:
        rc = rk = mt = False
        if s.cashier_present and s.cashier_hands and s.client_ids and s.cashier_pose_ok:
            c_body = body_sd(s.cashier_box)
            for ch in s.cashier_hands:
                if at_equipment(ch):
                    continue  # reaching to the counting machine / safe is an equipment operation, not a handover
                sd = cal.signed_dist_to_counter(ch)
                if sd < -0.5 * band or ((c_body - sd) >= reach and sd <= 0.5 * band):
                    rc = True
            for hs in s.client_hands.values():
                for kh in hs:
                    if any(math.hypot(ch[0] - kh[0], ch[1] - kh[1]) <= meet for ch in s.cashier_hands):
                        mt = True
        if s.client_hand_over_counter:
            rk = True
        reach_c.append(rc)
        reach_k.append(rk)
        meets.append(mt)
        cash_any.append(bool(s.cash_near_cashier_hand or s.cash_near_client_hand or s.cash_on_counter))
    flags = [a or b for a, b in zip(reach_c, reach_k)]
    gap = max(1, int(round(0.6 * fps)))
    out: list[Handover] = []
    w1 = int(round(1.0 * fps))
    for seg in runs(flags, times, min_duration=float(cfg.get("handover_min_s", 0.4)), max_gap_frames=gap):
        ks = range(seg.k_start, seg.k_end + 1)
        n_c = sum(1 for k in ks if reach_c[k])
        n_k = sum(1 for k in ks if reach_k[k])
        party = "cashier_reach" if n_c >= n_k else "client_reach"
        lo, hi = max(0, seg.k_start - w1), min(n - 1, seg.k_end + w1)
        with_cash = any(cash_any[k] for k in range(lo, hi + 1))
        met = any(meets[k] for k in ks)
        before = states[max(0, seg.k_start - int(3 * fps)) : seg.k_start]
        after = states[seg.k_end + 1 : min(n, seg.k_end + 1 + int(3 * fps))]
        c_before = sum(1 for s in before if s.cash_near_cashier_hand)
        k_before = sum(1 for s in before if s.cash_near_client_hand)
        c_after = sum(1 for s in after if s.cash_near_cashier_hand)
        k_after = sum(1 for s in after if s.cash_near_client_hand)
        if c_before > k_before and k_after >= c_after and (c_before + k_after) > 0:
            direction = "cashier_to_client"
        elif k_before > c_before and c_after >= k_after and (k_before + c_after) > 0:
            direction = "client_to_cashier"
        elif with_cash and party == "cashier_reach" and c_before >= k_before:
            direction = "cashier_to_client"
        elif with_cash and party == "client_reach" and k_before >= c_before:
            direction = "client_to_cashier"
        else:
            direction = "unknown"
        strength = min(1.0, 0.45 + (0.3 if with_cash else 0.0) + (0.15 if met else 0.0) + min(0.1, 0.05 * seg.duration))
        evidence = party + ("+meet" if met else "") + ("+cash" if with_cash else "")
        out.append(Handover(seg.start, seg.k_start, direction, evidence, strength))
    return out


def _disengage_time(states: list[FrameState], cal: Calibration, t_absent: float, cfg: dict) -> float:
    """Last moment before `t_absent` at which the cashier was still ENGAGED with the workplace (seated within
    half the zone radius of the seat, or a wrist at the counting machine / a storage unit / the laptop). The
    labels anchor departures on this "detached and oriented to leave" moment, not on the door crossing."""
    diag = cal.diag
    eq = [a for a in ([cal.counting_machine_point] + list(cal.storage_points) + [cal.workplace_objects.get("laptop")]) if a is not None]
    r_hand = float(cfg.get("engage_hand_radius_frac", 0.07)) * diag
    seat_r = 0.5 * cal.zone_radius
    lookback = float(cfg.get("disengage_lookback_s", 10.0))
    last = None
    for st in states:
        if st.t >= t_absent:
            break
        if st.t < t_absent - lookback or not st.cashier_present or st.cashier_box is None:
            continue
        b = st.cashier_box
        body = ((b[0] + b[2]) / 2.0, b[1] + 0.6 * (b[3] - b[1]))
        seated = cal.dist_to_cashier(body) <= seat_r
        hands_at_eq = st.cashier_pose_ok and any(math.hypot(h[0] - a[0], h[1] - a[1]) <= r_hand for h in st.cashier_hands for a in eq)
        if seated or hands_at_eq:
            last = st.t
    return last if last is not None else t_absent


# ---------------------------------------------------------------------- rules
def run_rules(states: list[FrameState], cal: Calibration, cfg: dict, fps: float, duration: float) -> tuple[list[Candidate], EventSummary]:
    ev = extract_events(states, cal, cfg, fps, duration)
    cands: list[Candidate] = []
    base = cfg.get("base_confidence", {}) or {}
    diag = cal.diag
    dt = states[1].t - states[0].t if len(states) > 1 else 1.0 / max(fps, 1.0)

    def episode_at(t: float) -> Optional[Episode]:
        for e in ev.episodes:
            if e.start - 1.0 <= t <= e.end + 1.0:
                return e
        return None

    # ---------------- R10: entry into an unattended cash workplace ----------------
    if ev.empty_start:
        near_r = float(cfg.get("workplace_near_frac", 0.16)) * diag
        anchors = [a for a in ([cal.counting_machine_point] + list(cal.storage_points) + [cal.workplace_objects.get("laptop")]) if a is not None] or [cal.cashier_center]
        # the entrant is "at the cash equipment": within r of the counting machine, a storage unit or the laptop
        eq = [a for a in ([cal.counting_machine_point] + list(cal.storage_points) + [cal.workplace_objects.get("laptop")]) if a is not None]
        r_eq = float(cfg.get("entry_equipment_radius_frac", 0.10)) * diag
        flags = [any(math.hypot(p[0] - a[0], p[1] - a[1]) <= r_eq for p in s.valid_bodies for a in eq) for s in states]
        segs = runs(_smooth(flags, 3), [s.t for s in states], min_duration=float(cfg.get("entry_min_s", 1.5)), max_gap_frames=max(1, int(fps)))
        if segs:
            first = segs[0]
            # t_event: the entrant, already >= 2 s inside, first comes close to a storage unit (safe) or the
            # counting machine — the moment the access to cash equipment becomes visible
            t_in = next((st_.t for st_ in states if st_.valid_bodies), first.start)
            r_close = float(cfg.get("entry_access_radius_frac", 0.07)) * diag
            close_eq = [a for a in ([cal.counting_machine_point] + list(cal.storage_points)) if a is not None]
            t_access = next(
                (
                    st_.t
                    for st_ in states
                    if st_.t >= t_in + float(cfg.get("entry_min_inside_s", 2.0))
                    and any(math.hypot(p[0] - a[0], p[1] - a[1]) <= r_close for p in st_.valid_bodies for a in close_eq)
                ),
                None,
            )
            if t_access is not None:
                first = type(first)(t_access, max(t_access, first.end), first.k_start, first.k_end)
            conf = float(base.get("entry_unattended", 0.8)) + min(0.15, 0.02 * sum(s.duration for s in segs))
            cands.append(
                Candidate(
                    "unauthorized_in_cash_zone",
                    first.start,
                    (first.start, segs[-1].end),
                    min(0.95, conf),
                    [
                        f"рабочее место пустовало в начале видео (первые {cfg.get('empty_start_s', 2.5)} с)",
                        f"вошедший находится у кассового оборудования {first.start:.1f}–{first.end:.1f} с",
                    ],
                    rule_id="R10",
                    vlm_window=(0.0, min(duration, first.start + 5.0)),
                    vlm_choice=(
                        "Сначала у кассового стола никого нет; затем входит человек и располагается у кассового оборудования (счётной машины, сейфа) или садится за кассовый стол, а кассира на рабочем месте нет.",
                        "Кассир с самого начала находится на своём рабочем месте и работает; посторонние к кассовому оборудованию не подходят.",
                    ),
                )
            )

    # ---------------- R1a / R1b: the cashier leaves ----------------
    established_s = float(cfg.get("service_established_s", 2.0))
    securing_min = float(cfg.get("securing_min_s", 5.0))
    lookback = float(cfg.get("securing_lookback_s", 18.0))
    for seg in ev.cashier_absent:
        if ev.empty_start:
            break  # the "cashier" of an empty-start video is the entrant; R10 covers it
        pre_all = [s for s in states if s.t < seg.start and s.cashier_present and s.cashier_in_zone]
        if len(pre_all) * dt < max(3.0, 0.15 * seg.start):
            continue  # the cashier was barely ever there before -> unreliable identity
        during = [s for s in states if seg.start <= s.t <= seg.end]
        if not during:
            continue
        ep = episode_at(seg.start)
        client_during = sum(1 for s in during if s.client_at_window) >= 0.5 * len(during)
        if ep is not None and seg.start >= ep.start + 0.5 and client_during:
            pre = [s for s in states if ep.start <= s.t < seg.start and s.cashier_present and s.cashier_in_zone]
            if len(pre) * dt >= established_s:
                conf = float(base.get("cashier_left_during_service", 0.8)) + min(0.15, 0.03 * seg.duration)
                cands.append(
                    Candidate(
                        "cashier_left_during_service", seg.start, (seg.start, seg.end), min(0.95, conf),
                        [f"кассир вне рабочей зоны {seg.start:.1f}–{seg.end:.1f} с", f"клиент у окна {ep.start:.1f}–{ep.end:.1f} с"],
                        rule_id="R1a",
                    )
                )
            continue
        # R1b: departure with the room left empty
        if seg.start not in ev.departures:
            continue
        secured = _cum_in(ev.storage_dwell, seg.start - lookback, min(seg.end, seg.start + 8.0))
        after_end = min(duration, seg.start + 6.0)
        # cash OR a cash bag left out ON THE DESK counts as valuables left unattended; sporadic low-score
        # detections (papers, reflections) must not turn a clean departure into "cash left"
        def _on_desk(d):
            c = ((d.xyxy[0] + d.xyxy[2]) / 2.0, (d.xyxy[1] + d.xyxy[3]) / 2.0)
            return cal.dist_to_cashier(c) <= 1.6 * cal.zone_radius
        n_cash_after = sum(
            1
            for s in states
            if seg.start <= s.t <= after_end
            and (any(d.score >= 0.40 and _on_desk(d) for d in s.cash) or any(d.score >= 0.50 and _on_desk(d) for d in s.bag))
        )
        cash_after = n_cash_after >= 3
        facts = [f"кассир выходит из помещения на {seg.start:.1f} с; помещение остаётся пустым до {seg.end:.1f} с"]
        if cash_after:
            type_id = "cash_left_unattended"
            conf = float(base.get("cash_left_unattended_depart", 0.9))
            facts.append("на столе остаются наличные")
        else:
            # The securing routine is a continuum (storing items vs touching the lock vs just reaching):
            # confidence slides with the measured hands-at-safe time, and the VLM sees the pre-departure
            # window to judge whether valuables were stored and the workplace shut down.
            type_id = "workplace_left_unsecured"
            hi = float(base.get("workplace_left_unsecured", 0.78))
            lo = float(base.get("workplace_left_secured", 0.45))
            k = max(0.0, min(1.0, (secured - 2.0) / 6.0))
            conf = hi - (hi - lo) * k
            facts.append(f"работа у сейфа перед уходом ≈{secured:.1f} с")
        dep_needs_support = (not cash_after) and k >= 0.5
        t_dep = _disengage_time(states, cal, seg.start, cfg)
        if t_dep < seg.start - 0.2:
            facts.append(f"последний контакт с рабочим местом на {t_dep:.1f} с, затем уход")
        if cash_after:
            dep_needs_support = False
        cands.append(
            Candidate(
                type_id, t_dep, (max(0.0, t_dep - 10.0), min(duration, seg.start + 3.0)), conf, facts, rule_id="R1b", needs_support=dep_needs_support,
                vlm_window=(max(0.0, t_dep - 8.0), min(duration, seg.start + 3.0)),
                vlm_question=(
                    "Кассир уходит из кассового помещения. По кадрам ПЕРЕД уходом: убрала ли она ценности/предметы "
                    "в сейф и закрыла ли его, выключен/закрыт ли ноутбук, пуст ли стол? Если рабочее место осталось "
                    "'живым' (открытый ноутбук, предметы, открытый сейф) — cashier_left: yes; если всё убрано и "
                    "закрыто перед уходом — cashier_left: no."
                ),
                vlm_expect=("cashier_left", {"yes"}, {"no"}),
            )
        )

    # ---------------- R1c: the room empties for good, but zone absence never formed ----------------
    # (degenerate seat/zone geometry in some solo clips; the trailing emptiness is still unambiguous)
    if not ev.empty_start and not any(c.rule_id == "R1b" for c in cands):
        tail_empty = [r for r in ev.room_empty if r.end >= duration - 1.2 and r.duration >= 1.5 and r.start > 3.0]
        if tail_empty:
            te = tail_empty[0]
            seen_before = [s.t for s in states if s.t < te.start and s.valid_bodies]
            if seen_before and te.start - seen_before[-1] <= 6.0:
                t_event = max(0.0, min(te.start, seen_before[-1] + 0.4) - 1.0)
                t_event = min(t_event, _disengage_time(states, cal, t_event, cfg))
                secured = _cum_in(ev.storage_dwell, t_event - lookback, te.start)
                hi = float(base.get("workplace_left_unsecured", 0.78))
                lo = float(base.get("workplace_left_secured", 0.45))
                k = max(0.0, min(1.0, (secured - 2.0) / 6.0))
                cands.append(
                    Candidate(
                        "workplace_left_unsecured", t_event, (max(0.0, t_event - 10.0), min(duration, te.start + 2.0)),
                        hi - (hi - lo) * k - 0.06,
                        [f"помещение пустеет с {te.start:.1f} с до конца видео; работа у сейфа перед этим ≈{secured:.1f} с"],
                        rule_id="R1c",
                        vlm_window=(max(0.0, t_event - 10.0), min(duration, te.start + 2.0)),
                        vlm_question=(
                            "Уходит ли кассир из помещения, оставляя рабочее место без присмотра? Убрала ли она перед "
                            "уходом предметы в сейф, закрыт ли ноутбук, пуст ли стол? Если место осталось 'живым' — "
                            "cashier_left: yes; если всё убрано и закрыто — cashier_left: no."
                        ),
                        vlm_expect=("cashier_left", {"yes"}, {"no"}),
                    )
                )

    # ---------------- R2: cash left unattended (cashier away or hands far) ----------------
    unatt_s = float(cfg.get("unattended_cash_s", 4.0))
    far = float(cfg.get("unattended_hand_dist_frac", 0.12)) * diag
    min_score = float(cfg.get("unattended_min_cash_score", 0.35))
    flags = []
    for s in states:
        good_cash = [c for c in s.cash if c.score >= min_score]
        if not good_cash or not (s.cash_on_cashier_side or s.cash_on_counter):
            flags.append(False)
            continue
        if not s.cashier_present or not s.cashier_in_zone:
            flags.append(True)
            continue
        hands = s.cashier_hands
        d = min((min(math.hypot(h[0] - (c.xyxy[0] + c.xyxy[2]) / 2, h[1] - (c.xyxy[1] + c.xyxy[3]) / 2) for h in hands) for c in good_cash), default=0.0) if hands else 0.0
        flags.append(bool(hands) and d > far)
    for seg in runs(_smooth(flags, 3), [s.t for s in states], min_duration=unatt_s, max_gap_frames=max(1, int(fps))):
        conf = float(base.get("cash_left_unattended", 0.6)) + min(0.25, 0.03 * (seg.duration - unatt_s))
        cands.append(Candidate("cash_left_unattended", seg.start, (seg.start, seg.end), min(0.95, conf), [f"наличные видны без рук кассира рядом {seg.start:.1f}–{seg.end:.1f} с"], rule_id="R2"))

    # ---------------- R3 / R3b: phone, personal items ----------------
    for seg in ev.phone:
        conf = float(base.get("phone_at_workplace", 0.55)) + min(0.2, 0.05 * seg.duration)
        cands.append(Candidate("phone_at_workplace", seg.start, (seg.start, seg.end), min(0.9, conf), [f"предмет, похожий на телефон, у руки кассира {seg.start:.1f}–{seg.end:.1f} с"], rule_id="R3"))
    for seg in ev.cup:
        conf = float(base.get("personal_items_at_workplace", 0.65)) + min(0.2, 0.05 * seg.duration)
        cands.append(Candidate("personal_items_at_workplace", seg.start, (seg.start, seg.end), min(0.9, conf), [f"стакан/бутылка/еда у руки кассира {seg.start:.1f}–{seg.end:.1f} с"], rule_id="R3b"))

    # ---------------- R4: another person deep in the cashier zone ----------------
    for seg in ev.intrusion:
        conf = float(base.get("unauthorized_in_cash_zone", 0.65)) + min(0.25, 0.08 * seg.duration)
        cands.append(Candidate("unauthorized_in_cash_zone", seg.start, (seg.start, seg.end), min(0.95, conf), [f"посторонний в зоне кассира {seg.start:.1f}–{seg.end:.1f} с"], rule_id="R4"))

    # ---------------- R5: issue without counting ----------------
    cw = float(cfg.get("counting_window_s", 15.0))
    for h in ev.handovers:
        if h.direction == "cashier_to_client" and "+cash" in h.evidence:
            cnt = _any_in(ev.counting, h.t - cw, h.t)
            if cnt is None:
                conf = float(base.get("issue_without_count", 0.5)) + 0.25 * h.strength
                cands.append(Candidate("issue_without_count", h.t, (max(0.0, h.t - cw), h.t + 2.0), min(0.9, conf), [f"передача наличных кассир→клиент на {h.t:.1f} с ({h.evidence})", f"пересчёт за предыдущие {cw:.0f} с не зафиксирован"], rule_id="R5"))
            elif cnt.end < h.t - 5.0:
                # some hand motion looked like counting, but it ended long before the issue — let the VLM
                # decide whether the notes were actually counted right before being handed over
                conf = float(base.get("issue_without_count_weak", 0.42))
                cands.append(
                    Candidate(
                        "issue_without_count", h.t, (max(0.0, h.t - 10.0), h.t + 2.0), conf,
                        [f"передача наличных кассир→клиент на {h.t:.1f} с", f"возможный пересчёт закончился на {cnt.end:.1f} с (за {h.t - cnt.end:.0f} с до выдачи)"],
                        rule_id="R5w", needs_support=True,
                        vlm_question="Пересчитывал ли кассир купюры (перебирал по одной или на счётной машине) непосредственно перед передачей их клиенту?",
                        vlm_expect=("counted_money", {"no"}, {"yes"}),
                    )
                )

    # ---------------- R6: cash acquired during an episode, no counting while the counter-party is present --
    for ep in ev.episodes:
        acq: Optional[float] = None
        how = ""
        for h in ev.handovers:
            if h.direction == "client_to_cashier" and ep.start - 1.0 <= h.t <= ep.end + 1.0 and "+cash" in h.evidence:
                acq, how = h.t, f"приём наличных на {h.t:.1f} с"
                break
        if acq is None and ep.is_collector:
            seg = _any_in(ev.cash_visible, ep.start, ep.end + 5.0, min_dur=0.4)
            if seg is not None:
                acq, how = seg.start, f"наличные появляются у кассира на {seg.start:.1f} с (инкассация)"
        if acq is None:
            continue
        t_party_gone = ep.end
        cnt = _any_in(ev.counting, acq - 1.0, t_party_gone + 1.0)
        if cnt is not None:
            # a count that begins only when the counter-party is already walking away is the violation
            # pattern of video 34 ("приём без пересчёта в присутствии клиента")
            remaining = t_party_gone - cnt.start
            if cnt.start > acq + 3.0 and remaining < 2.5 and t_party_gone < duration - 1.5:
                conf = float(base.get("accept_count_late", 0.62))
                cands.append(
                    Candidate(
                        "accept_without_count", max(cnt.start, acq + 1.0), (acq, min(duration, cnt.start + 4.0)), conf,
                        [how, f"пересчёт начат на {cnt.start:.1f} с, когда {'инкассатор' if ep.is_collector else 'клиент'} уже уходил (у окна до {t_party_gone:.1f} с)"],
                        rule_id="R6b", needs_support=True,
                        vlm_question="Пересчитывал ли кассир принятые наличные, ПОКА клиент ещё находился у стола, или начал пересчёт только после того, как клиент отвернулся/ушёл?",
                        vlm_expect=("counted_money", {"no"}, {"yes"}),
                    )
                )
            continue
        # t_event: storing moment if seen (cash near storage, or a safe visit while cash is around),
        # else the moment the counter-party walks away, else shortly after the acquisition
        t_store = None
        for s in states:
            if acq + 0.5 < s.t <= min(duration, acq + 30.0) and s.cash_near_storage:
                t_store = s.t
                break
        if t_store is None:
            cash_runs = [cv for cv in ev.cash_visible if cv.end > acq]
            for d in ev.storage_dwell:
                if d.start > acq and any(cv.start - 3.0 <= d.start <= cv.end + 3.0 for cv in cash_runs):
                    t_store = d.start
                    break
        if t_store is not None and t_store <= t_party_gone + 8.0:
            t_event = t_store
        elif t_party_gone < duration - 1.5:
            t_event = t_party_gone
        else:
            t_event = min(duration - 0.5, acq + 2.0)
        conf = float(base.get("accept_without_count", 0.6)) + (0.1 if ep.is_collector else 0.0)
        cands.append(
            Candidate(
                "accept_without_count", t_event, (acq, min(duration, t_event + 2.0)), min(0.9, conf),
                [how, f"пересчёт в присутствии {'инкассатора' if ep.is_collector else 'клиента'} (до {t_party_gone:.1f} с) не зафиксирован"],
                rule_id="R6",
            )
        )

    # ---------------- R7: cash handover without an ID shown before (conservative) ----------------
    idw = float(cfg.get("id_check_window_s", 20.0))
    for h in ev.handovers:
        ep = episode_at(h.t)
        if ep is None:
            continue  # no client episode -> no ID requirement applies
        # cash evidence: at the handover itself, or cash seen during the episode (cash detections are sparse)
        if "+cash" not in h.evidence and _any_in(ev.cash_visible, ep.start, ep.end) is None:
            continue
        t0 = min(ep.start, h.t - idw)
        if _any_in(ev.id_shown, t0, h.t) is None:
            conf = float(base.get("no_id_check", 0.4)) + 0.05 * h.strength
            cands.append(Candidate("no_id_check", h.t, (max(0.0, t0), h.t + 1.0), min(0.75, conf), [f"передача наличных на {h.t:.1f} с без предъявления документа с начала обслуживания"], rule_id="R7"))

    # ---------------- R8: collector bag without inspection / document ----------------
    # Fires on bag handling during collector episodes, and (fallback) on sustained bag handling during any
    # episode when the collector classification failed — the discriminator is the missing document exchange.
    bw = float(cfg.get("bag_check_window_s", 15.0))
    bag_eps = [e for e in ev.episodes if e.is_collector]  # no collector -> the cashier handles a bag herself (normal)
    for ep in bag_eps:
        bags = [b for b in ev.bag_handling if _overlaps(b.start, b.end, ep.start - 2.0, ep.end + 2.0)]
        if not bags:
            continue
        first = bags[0]
        inspected = sum(b.duration for b in bags) >= float(cfg.get("bag_inspect_min_s", 3.0))
        doc = _any_in(ev.id_shown, first.start - bw, first.end + bw)
        if doc is not None:
            continue
        if not inspected:
            conf = float(base.get("collection_bag_unchecked", 0.55)) + (0.05 if ep.is_collector else 0.0)
        else:
            # the bag was handled at length, but no accompanying document was seen anywhere around the
            # handover — geometry cannot tell inspection from transfer, the VLM decides
            conf = float(base.get("collection_bag_no_doc", 0.48))
        cands.append(
            Candidate(
                "collection_bag_unchecked", first.start, (max(0.0, first.start - 2.0), first.end + 2.0), conf,
                [f"сумка инкассатора у рук {first.start:.1f}–{first.end:.1f} с; сопроводительный документ не зафиксирован"],
                rule_id="R8", needs_support=True,
                vlm_question="Передаётся ли инкассаторская сумка? Осматривал ли кассир сумку и пломбу и работал ли с сопроводительным документом (бумагой) при передаче? Если документа и осмотра не видно — bag_checked: no.",
                vlm_expect=("bag_checked", {"no"}, {"yes", "no_bag"}),
            )
        )
        break

    # ---------------- R9: second client / cash of two clients ----------------
    # Variant A: two visitors at the window simultaneously while the operation is live.
    # The two bodies must be clearly separated — duplicate boxes of one person do not count.
    def two_separated(s: FrameState) -> bool:
        ids = sorted(set(s.client_at_window))
        if len(ids) < 2 or not s.cashier_present:
            return False
        pts = []
        for tid in ids:
            hs = s.client_hands.get(tid)
            if hs:
                pts.append((sum(h[0] for h in hs) / len(hs), sum(h[1] for h in hs) / len(hs)))
        if len(pts) < 2:
            return False
        dmax = max(math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(pts) for b in pts[i + 1 :])
        return dmax >= 0.10 * diag

    flags = [two_separated(s) for s in states]
    cash_flags = [bool(s.cash) or s.cash_on_counter for s in states]
    for seg in runs(_smooth(flags, 3), [s.t for s in states], min_duration=float(cfg.get("two_clients_min_s", 4.0)), max_gap_frames=max(1, int(fps))):
        with_cash = any(cash_flags[k] for k in range(seg.k_start, seg.k_end + 1))
        conf = (0.7 if with_cash else float(base.get("two_clients_no_cash", 0.55))) + min(0.15, 0.04 * seg.duration)
        facts = [f"два посетителя у окна одновременно {seg.start:.1f}–{seg.end:.1f} с" + (", наличные на столе" if with_cash else "")]
        cands.append(
            Candidate(
                "two_clients_cash_mixed", seg.start, (seg.start, seg.end), min(0.9, conf), facts, rule_id="R9a",
                vlm_question="Находятся ли у стола кассира ДВА посетителя одновременно (не считая кассира), пока идёт операция? Если второй человек лишь проходит мимо или это отражение в стекле — unauthorized_person: no; если их действительно двое у стола — unauthorized_person: yes.",
                vlm_expect=("unauthorized_person", {"yes"}, {"no"}),
            )
        )
    # Variant B: a new episode begins while the previous operation's cash is still out (not stored)
    for i, ep in enumerate(ev.episodes):
        if i == 0:
            continue
        prev = ev.episodes[i - 1]
        stored_between = any(prev.end <= s.t <= ep.start and s.cash_near_storage for s in states)
        window = [s for s in states if ep.start - 2.0 <= s.t <= ep.start + 3.0]
        cash_out = sum(1 for s in window if s.cash_on_cashier_side or s.cash_on_counter) >= max(2, 0.25 * len(window))
        if cash_out and not stored_between:
            conf = float(base.get("two_clients_prev_cash", 0.7))
            cands.append(
                Candidate(
                    "two_clients_cash_mixed", ep.start, (max(0.0, ep.start - 2.0), ep.start + 3.0), conf,
                    [f"новый посетитель с {ep.start:.1f} с, при этом наличные предыдущей операции не убраны"],
                    rule_id="R9b",
                )
            )

    # ---------------- R9c: visitor change while the previous operation's cash is still out ----------------
    # A NEW visitor track arrives at the window (coming from afar, i.e. through the door — not an id switch
    # at the seat) shortly after the previous visitor was there, and cash is still visible on the cashier's
    # side with no storing in between.
    if cal.window_anchor is not None:
        reach_r = float(cfg.get("window_reach_frac", 0.15)) * diag
        first_at: dict = {}
        last_at: dict = {}
        first_pos: dict = {}
        for st in states:
            for tid in st.client_at_window:
                first_at.setdefault(tid, st.t)
                last_at[tid] = st.t
        for st in states:
            for tid, b in zip(st.valid_tracks, st.valid_bodies):
                first_pos.setdefault(tid, b)
        for t2_id, t2 in sorted(first_at.items(), key=lambda kv: kv[1]):
            if t2 < 5.0:
                continue
            # the previous visitor must have LEFT the window shortly before (a real hand-over of the window has
            # a gap of >= 0.6 s; a tracker id switch re-creates the track without a gap)
            prev = [
                t1 for t1, a1 in first_at.items()
                if t1 != t2_id and a1 < t2 - 3.0 and 0.6 <= t2 - last_at.get(t1, -99.0) <= 8.0
            ]
            if not prev:
                continue
            stored = any(t2 - 8.0 <= st.t <= t2 and st.cash_near_storage for st in states)
            near = [st for st in states if t2 - 8.0 <= st.t <= t2 + 6.0]
            desk_r = 0.6 * cal.cashier_client_dist + 0.05 * diag

            def on_desk(d) -> bool:
                c = ((d.xyxy[0] + d.xyxy[2]) / 2.0, (d.xyxy[1] + d.xyxy[3]) / 2.0)
                return math.hypot(c[0] - cal.counter_point[0], c[1] - cal.counter_point[1]) <= desk_r

            cash_out = sum(1 for st in near if any(on_desk(d) for d in st.cash)) >= 3
            if cash_out and not stored:
                cands.append(
                    Candidate(
                        "two_clients_cash_mixed", t2, (max(0.0, t2 - 4.0), min(duration, t2 + 6.0)), float(base.get("two_clients_visitor_change", 0.62)),
                        [f"новый посетитель подходит на {t2:.1f} с, предыдущий был у окна до {max(last_at[t] for t in prev):.1f} с", "наличные предыдущей операции остаются на столе"],
                        rule_id="R9c",
                        vlm_window=(max(0.0, t2 - 4.0), min(duration, t2 + 6.0)),
                        vlm_choice=(
                            "Подходит новый посетитель, а деньги предыдущей операции всё ещё лежат на столе кассира.",
                            "Деньги предыдущей операции убраны до того, как подходит следующий посетитель.",
                        ),
                    )
                )
                break

    # ---------------- R11: note separated after a machine count and merged back (VLM-arbitrated) ----------
    # Pattern of video 44: the counting machine leaves a note in the hopper; the cashier holds it apart and
    # slips it back into the counted pack without re-checking. Pure geometry cannot separate this from the
    # correct handling (odd note kept aside — clean twins 43/45), so the rule emits a LOW-confidence
    # candidate that only crosses the verdict threshold if the local VLM supports it.
    if bool(cfg.get("suspect_note_rule", True)):
        machs = runs(_smooth([st.counting_machine_active for st in states], 3), [st.t for st in states], min_duration=float(cfg.get("counting_machine_min_s", 1.2)), max_gap_frames=max(1, int(fps)))
        for m in machs:
            w0, w1 = m.end, min(duration, m.end + 10.0)
            handling = _cum_in(ev.cash_visible, w0, w1)
            ep = episode_at((w0 + w1) / 2)
            if handling >= 1.5 and ep is None:
                conf = float(base.get("suspect_note_mishandled", 0.40))
                cands.append(
                    Candidate(
                        "suspect_note_mishandled", round(w0 + 1.0, 1), (w0, w1), conf,
                        [f"работа счётной машины до {m.end:.1f} с, затем ручная работа с купюрами {handling:.1f} с"],
                        rule_id="R11", needs_support=True,
                        vlm_question=(
                            "После выгрузки купюр из счётной машины: отделял ли кассир отдельную купюру от пачки, "
                            "и если да — вернул ли он её обратно в пересчитанную пачку (нарушение) или отложил "
                            "отдельно на стол (норма)? Если купюра не отделялась — counted_money: yes."
                        ),
                        vlm_expect=("counted_money", {"no"}, {"yes"}),
                    )
                )
                break  # one candidate per video is enough for this subtle pattern

    # ---------------- R12: safe opened, cashier walks away without closing (VLM-arbitrated) ---------------
    # Pattern of video 20: cash taken out of the safe, the cashier walks to the desk leaving the door open.
    if bool(cfg.get("open_safe_rule", True)) and ev.storage_dwell:
        for i, dwell in enumerate(ev.storage_dwell):
            if dwell.duration < 1.2:
                continue
            # cash appears at the cashier's hands / desk shortly after the dwell
            cash_after = _any_in(ev.cash_visible, dwell.end - 1.0, dwell.end + 6.0)
            # no return to the safe afterwards (closing would be another dwell)
            returned = any(d.start > dwell.end + 1.0 and d.duration >= 0.8 for d in ev.storage_dwell[i + 1 :])
            sp = cal.storage_point
            sr = float(cfg.get("storage_dwell_radius_frac", 0.09)) * diag
            moved_away = sp is None or any(
                dwell.end < s.t <= dwell.end + 3.0 and s.cashier_present and s.cashier_box is not None
                and math.hypot((s.cashier_box[0] + s.cashier_box[2]) / 2 - sp[0], s.cashier_box[1] + 0.6 * (s.cashier_box[3] - s.cashier_box[1]) - sp[1]) > 1.6 * sr
                for s in states
            )
            counting_after = any(abs(c.start - dwell.end) <= 2.0 for c in ev.counting)
            if (cash_after is not None or counting_after) and not returned and moved_away:
                conf = float(base.get("open_safe", 0.42))
                cands.append(
                    Candidate(
                        "cash_left_unattended", round(dwell.end, 1), (dwell.start, min(duration, dwell.end + 6.0)), conf,
                        [f"работа у сейфа {dwell.start:.1f}–{dwell.end:.1f} с, затем кассир отходит с наличными; возврата к сейфу не зафиксировано"],
                        rule_id="R12", needs_support=True,
                        vlm_question="Осталась ли дверца сейфа (металлического шкафа) открытой после того, как кассир отошёл от него? Ответь в поле safe_open.",
                        vlm_expect=("safe_open", {"yes"}, {"no"}),
                        vlm_window=(max(0.0, dwell.start - 1.0), min(duration, dwell.end + 6.0)),
                        vlm_choice=(
                            "Кассир достаёт что-то из сейфа и отходит, оставив дверцу сейфа открытой.",
                            "Кассир закрывает дверцу сейфа, прежде чем отойти от него.",
                        ),
                    )
                )
                break

    return merge_candidates(cands, float(cfg.get("merge_events_within_s", 3.0))), ev


def merge_candidates(cands: list[Candidate], within_s: float) -> list[Candidate]:
    out: list[Candidate] = []
    for c in sorted(cands, key=lambda c: (c.type_id, c.t_event)):
        if out and out[-1].type_id == c.type_id and abs(out[-1].t_event - c.t_event) <= within_s:
            if c.confidence > out[-1].confidence:
                out[-1] = c
            continue
        out.append(c)
    return sorted(out, key=lambda c: c.t_event)


def select_violations(cands: list[Candidate], threshold: float, per_type: Optional[dict] = None, max_n: int = 6) -> list[Candidate]:
    per_type = per_type or {}
    keep = [c for c in cands if getattr(c, "eligible", True) and c.confidence >= float(per_type.get(c.type_id, threshold))]
    keep.sort(key=lambda c: -c.confidence)
    return sorted(keep[:max_n], key=lambda c: c.t_event)
