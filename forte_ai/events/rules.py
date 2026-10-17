"""Layer B rules: small temporal conditions over frame primitives -> candidates with exact timecodes.

Timecode policy (documented in VIOLATION_TYPES.md):
  * action violation  -> t_event = first sampled frame where the condition becomes true;
  * omission          -> t_event = the action that should have been preceded by the skipped step
                         (the handover without counting / without an ID check, the storing without counting).
All thresholds come from configs/*.yaml (section `rules`). Nothing here uses pixel coordinates directly:
distances are fractions of the frame diagonal, sides are relative to the calibrated counter line.
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
    intrusion: list[Segment]
    cash_visible: list[Segment]
    id_shown: list[Segment]
    bag_handling: list[Segment]
    hand_speed: np.ndarray

    def to_dict(self) -> dict:
        seg = lambda ss: [[round(s.start, 2), round(s.end, 2)] for s in ss]  # noqa: E731
        return {
            "episodes": [[round(e.start, 2), round(e.end, 2), sorted(e.client_ids), e.is_collector] for e in self.episodes],
            "handovers": [[round(h.t, 2), h.direction, h.evidence, round(h.strength, 2)] for h in self.handovers],
            "counting": seg(self.counting),
            "cashier_absent": seg(self.cashier_absent),
            "phone": seg(self.phone),
            "intrusion": seg(self.intrusion),
            "cash_visible": seg(self.cash_visible),
            "id_shown": seg(self.id_shown),
            "bag_handling": seg(self.bag_handling),
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


# ---------------------------------------------------------------------- event extraction
def extract_events(states: list[FrameState], cal: Calibration, cfg: dict, fps: float) -> EventSummary:
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

    # ---- cashier absent from own zone
    absent = _smooth([not (s.cashier_present and s.cashier_in_zone) for s in states], smooth_k)
    cashier_absent = runs(absent, times, min_duration=float(cfg.get("left_zone_min_s", 1.5)), max_gap_frames=gap)

    # ---- phone in the cashier's hand
    phone = runs(_smooth([s.phone_near_cashier_hand for s in states], smooth_k), times, min_duration=float(cfg.get("phone_min_s", 1.0)), max_gap_frames=gap)

    # ---- non-cashier inside the cashier zone / hand deep over the counter
    intr_flags = [bool(s.non_cashier_in_zone) or bool(s.client_hand_over_counter) for s in states]
    intrusion = runs(_smooth(intr_flags, smooth_k), times, min_duration=float(cfg.get("intrusion_min_s", 0.6)), max_gap_frames=gap)

    # ---- cash visible (anywhere), id/document shown near hands, bag handling
    cash_visible = runs(_smooth([bool(s.cash) for s in states], smooth_k), times, min_duration=0.0, max_gap_frames=gap)
    id_shown = runs(_smooth([s.document_near_hands or s.id_card_visible for s in states], smooth_k), times, min_duration=float(cfg.get("id_min_s", 0.6)), max_gap_frames=gap)
    bag_handling = runs(_smooth([s.bag_near_cashier_hand or s.bag_near_collector for s in states], smooth_k), times, min_duration=0.4, max_gap_frames=gap)

    # ---- counting: periodic hand motion of the cashier over the desk (or counting machine use)
    speed = hand_motion_energy(states, window_frames=1) * fps / diag  # fraction of diagonal per second
    win = max(4, int(round(float(cfg.get("counting_window_frames_s", 2.0)) * fps)))
    s_min = float(cfg.get("counting_hand_speed_frac_s", 0.03))
    p_min = float(cfg.get("counting_periodicity_min", 0.30))
    count_flags = []
    for i in range(n):
        a, b = max(0, i - win // 2), min(n, i + win // 2 + 1)
        seg = speed[a:b]
        s = states[i]
        hands_over_desk = s.cashier_present and bool(s.cashier_hands) and all(cal.signed_dist_to_counter(h) > -0.5 * float(cfg.get("counter_margin_frac", 0.06)) * diag for h in s.cashier_hands)
        periodic = float(np.mean(seg)) >= s_min and periodicity(seg, fps) >= p_min
        count_flags.append(bool(s.counting_machine_active) or (periodic and hands_over_desk and True))
    counting = runs(_smooth(count_flags, smooth_k), times, min_duration=float(cfg.get("counting_min_duration_s", 1.5)), max_gap_frames=gap)

    # ---- handovers: reach events across the counter line
    handovers = _detect_handovers(states, cal, cfg, fps)
    return EventSummary(episodes, handovers, counting, cashier_absent, phone, intrusion, cash_visible, id_shown, bag_handling, speed)


def _detect_handovers(states: list[FrameState], cal: Calibration, cfg: dict, fps: float) -> list[Handover]:
    """A handover is an active REACH across the counter: the cashier extends a wrist well ahead of the torso
    toward the client side (or across the line), or a client does the same toward the cashier side. Wrists
    meeting near the line and cash seen near the hands (within ±1 s) only add evidence — two people seated
    across a desk keep their hands close all the time, so proximity alone is not an event."""
    diag = cal.diag
    band = float(cfg.get("reach_band_frac", 0.08)) * diag
    meet = float(cfg.get("hands_meet_frac", 0.05)) * diag
    reach = float(cfg.get("reach_frac", 0.10)) * diag
    times = [s.t for s in states]
    n = len(states)

    def body_sd(box):
        return cal.signed_dist_to_counter(((box[0] + box[2]) / 2.0, box[1] + 0.6 * (box[3] - box[1])))

    reach_c, reach_k, meets, cash_any = [], [], [], []
    for s in states:
        rc = rk = mt = False
        if s.cashier_present and s.cashier_hands and s.client_ids and s.cashier_pose_ok:
            c_body = body_sd(s.cashier_box)
            for ch in s.cashier_hands:
                sd = cal.signed_dist_to_counter(ch)
                # a reach = wrist crosses the counter line, or wrist is extended far ahead of the torso
                # AND is close to / past the line (normal seated hands stay well on the cashier side)
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
        # direction from cash possession before/after the reach (3 s windows)
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


# ---------------------------------------------------------------------- rules
def run_rules(states: list[FrameState], cal: Calibration, cfg: dict, fps: float, duration: float) -> tuple[list[Candidate], EventSummary]:
    ev = extract_events(states, cal, cfg, fps)
    cands: list[Candidate] = []
    base = cfg.get("base_confidence", {}) or {}
    diag = cal.diag

    def episode_at(t: float) -> Optional[Episode]:
        for e in ev.episodes:
            if e.start - 1.0 <= t <= e.end + 1.0:
                return e
        return None

    # 1. cashier left the workplace during service (action)
    for seg in ev.cashier_absent:
        ep = episode_at(seg.start) or episode_at(seg.end)
        if ep is None:
            continue
        if seg.start < ep.start + 0.5 and seg.end < ep.start + 1.0:
            continue  # absent before the client arrived
        conf = float(base.get("cashier_left_during_service", 0.75)) + min(0.2, 0.04 * seg.duration)
        cands.append(
            Candidate(
                "cashier_left_during_service",
                seg.start,
                (seg.start, seg.end),
                min(0.98, conf),
                [f"кассир вне рабочей зоны {seg.start:.1f}–{seg.end:.1f} с ({seg.duration:.1f} с)", f"клиент у окна {ep.start:.1f}–{ep.end:.1f} с"],
                rule_id="R1",
            )
        )

    # 2. cash left unattended: cash visible on the cashier side with the cashier away or hands far from it (action)
    unatt_s = float(cfg.get("unattended_cash_s", 4.0))
    far = float(cfg.get("unattended_hand_dist_frac", 0.12)) * diag
    flags = []
    for s in states:
        if not s.cash_on_cashier_side and not s.cash_on_counter:
            flags.append(False)
            continue
        if not s.cashier_present or not s.cashier_in_zone:
            flags.append(True)
            continue
        # cashier present: cash far from every hand
        hands = s.cashier_hands
        d = min((min(math.hypot(h[0] - (c.xyxy[0] + c.xyxy[2]) / 2, h[1] - (c.xyxy[1] + c.xyxy[3]) / 2) for h in hands) for c in s.cash), default=0.0) if hands else 0.0
        flags.append(bool(hands) and d > far)
    for seg in runs(_smooth(flags, 3), [s.t for s in states], min_duration=unatt_s, max_gap_frames=max(1, int(fps))):
        conf = float(base.get("cash_left_unattended", 0.55)) + min(0.25, 0.03 * (seg.duration - unatt_s))
        cands.append(Candidate("cash_left_unattended", seg.start, (seg.start, seg.end), min(0.95, conf), [f"наличные видны без рук кассира рядом {seg.start:.1f}–{seg.end:.1f} с"], rule_id="R2"))

    # 3. phone in the cashier's hand (action)
    for seg in ev.phone:
        conf = float(base.get("phone_at_workplace", 0.6)) + min(0.25, 0.08 * seg.duration)
        cands.append(Candidate("phone_at_workplace", seg.start, (seg.start, seg.end), min(0.95, conf), [f"телефон у руки кассира {seg.start:.1f}–{seg.end:.1f} с"], rule_id="R3"))

    # 4. unauthorized person / hand in the cashier zone (action)
    for seg in ev.intrusion:
        conf = float(base.get("unauthorized_in_cash_zone", 0.6)) + min(0.3, 0.1 * seg.duration)
        cands.append(Candidate("unauthorized_in_cash_zone", seg.start, (seg.start, seg.end), min(0.95, conf), [f"посторонний/рука клиента в зоне кассира {seg.start:.1f}–{seg.end:.1f} с"], rule_id="R4"))

    # 5/6. handovers without counting (omission): t_event = the handover
    cw = float(cfg.get("counting_window_s", 15.0))
    for h in ev.handovers:
        if h.direction == "cashier_to_client" or (h.direction == "unknown" and "+cash" in h.evidence):
            cnt = _any_in(ev.counting, h.t - cw, h.t)
            if cnt is None:
                conf = float(base.get("issue_without_count", 0.5)) + 0.25 * h.strength
                cands.append(Candidate("issue_without_count", h.t, (max(0.0, h.t - cw), h.t + 2.0), min(0.95, conf), [f"передача наличных кассир→клиент на {h.t:.1f} с ({h.evidence})", f"пересчёт за предыдущие {cw:.0f} с не зафиксирован"], rule_id="R5"))
        if h.direction == "client_to_cashier":
            # storing (cash near storage or cash disappears) after the handover without counting in between
            t_store = None
            for s in states:
                if s.t > h.t + 0.5 and s.t <= h.t + 25.0 and (s.cash_near_storage or (not s.cash and s.t > h.t + 3.0)):
                    t_store = s.t
                    break
            t_end = t_store if t_store is not None else min(duration, h.t + 15.0)
            if _any_in(ev.counting, h.t, t_end) is None:
                conf = float(base.get("accept_without_count", 0.5)) + 0.2 * h.strength
                cands.append(Candidate("accept_without_count", t_end, (h.t, t_end), min(0.9, conf), [f"приём наличных клиент→кассир на {h.t:.1f} с", f"пересчёт до {t_end:.1f} с не зафиксирован"], rule_id="R6"))

    # 7. handover without an ID shown before it (omission) — conservative, needs a cash handover
    idw = float(cfg.get("id_check_window_s", 20.0))
    for h in ev.handovers:
        if "+cash" not in h.evidence:
            continue
        ep = episode_at(h.t)
        t0 = ep.start if ep else h.t - idw
        if _any_in(ev.id_shown, min(t0, h.t - idw), h.t) is None:
            conf = float(base.get("no_id_check", 0.35)) + 0.1 * h.strength
            cands.append(Candidate("no_id_check", h.t, (max(0.0, h.t - idw), h.t + 1.0), min(0.8, conf), [f"передача наличных на {h.t:.1f} с без предъявления документа в предшествующие {idw:.0f} с"], rule_id="R7"))

    # 8. collection bag handed over without inspection / document (omission)
    bw = float(cfg.get("bag_check_window_s", 15.0))
    for ep in [e for e in ev.episodes if e.is_collector]:
        bags = [b for b in ev.bag_handling if _overlaps(b.start, b.end, ep.start, ep.end)]
        if not bags:
            continue
        first = bags[0]
        inspected = sum(b.duration for b in bags) >= float(cfg.get("bag_inspect_min_s", 3.0))
        doc = _any_in(ev.id_shown, first.start - bw, first.end + bw)
        if not inspected and doc is None:
            conf = float(base.get("collection_bag_unchecked", 0.5))
            cands.append(Candidate("collection_bag_unchecked", first.start, (first.start, first.end), conf, [f"сумка инкассатора у рук {first.start:.1f}–{first.end:.1f} с без осмотра/документа"], rule_id="R8"))

    # 9. two clients at the window with cash on the desk (action)
    flags = [len(set(s.client_at_window)) >= 2 and (bool(s.cash) or s.cash_on_counter) for s in states]
    for seg in runs(_smooth(flags, 3), [s.t for s in states], min_duration=float(cfg.get("two_clients_min_s", 1.5)), max_gap_frames=max(1, int(fps))):
        conf = float(base.get("two_clients_cash_mixed", 0.55)) + min(0.2, 0.05 * seg.duration)
        cands.append(Candidate("two_clients_cash_mixed", seg.start, (seg.start, seg.end), min(0.9, conf), [f"два клиента у окна и наличные на столе {seg.start:.1f}–{seg.end:.1f} с"], rule_id="R9"))

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
    keep = [c for c in cands if c.confidence >= float(per_type.get(c.type_id, threshold))]
    keep.sort(key=lambda c: -c.confidence)
    return sorted(keep[:max_n], key=lambda c: c.t_event)
