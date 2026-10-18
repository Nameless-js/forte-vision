"""Rules on synthetic event streams (no models): each rule must fire on its pattern and stay silent on the
corresponding normal action. Geometry: 464x848 frame, counter line horizontal at y=430, cashier below it."""

import math

import numpy as np
import pytest

from forte_ai.events.primitives import FrameState, runs
from forte_ai.events.rules import merge_candidates, run_rules, select_violations
from forte_ai.perception.detector import Detection
from forte_ai.perception.roles import Calibration

W, H = 464, 848
FPS = 5.0
CFG = {
    "intrusion_warmup_s": 3.0,
    "counting_window_s": 15.0,
    "counting_min_duration_s": 1.5,
    "counting_hand_speed_frac_s": 0.03,
    "counting_periodicity_min": 0.30,
    "unattended_cash_s": 4.0,
    "left_zone_min_s": 1.5,
    "phone_min_s": 1.0,
    "intrusion_min_s": 0.6,
    "episode_min_s": 2.0,
    "id_check_window_s": 20.0,
    "bag_check_window_s": 15.0,
    "merge_events_within_s": 3.0,
    "counter_margin_frac": 0.06,
    "reach_frac": 0.10,
    "handover_min_s": 0.4,
    "base_confidence": {},
}


def make_cal() -> Calibration:
    diag = math.hypot(W, H)
    hull = [(120.0, 470.0), (340.0, 470.0), (340.0, 760.0), (120.0, 760.0)]
    return Calibration(W, H, diag, 1, 0.9, {}, (230.0, 600.0), hull, (230.0, 430.0), (0.0, 1.0), 1.0, [2], [], [], {"counting_machine": (80.0, 500.0), "laptop": (260.0, 560.0)}, (400.0, 520.0), (80.0, 500.0), storage_points=[(400.0, 520.0)], zone_radius=110.0)


def state(k, t, cashier=True, in_zone=True, hands=None, client=True, client_hands=None, cash=None, cash_c=False, cash_k=False, phone=False, intrusion=False, over=False, cash_side=False, pose_ok=True):
    hands = hands if hands is not None else [(200.0, 520.0), (260.0, 520.0)]
    return FrameState(
        k=k,
        t=t,
        cashier_present=cashier,
        cashier_box=(170.0, 440.0, 290.0, 760.0) if cashier else None,
        cashier_in_zone=in_zone if cashier else False,
        cashier_hands=hands if cashier else [],
        cashier_elbows=[],
        cashier_pose_ok=pose_ok and cashier,
        client_ids=[2] if client else [],
        client_at_window=[2] if client else [],
        client_hands={2: client_hands or [(200.0, 380.0), (260.0, 380.0)]} if client else {},
        client_hand_over_counter=[2] if over else [],
        non_cashier_in_zone=[2] if intrusion else [],
        collector_ids=[],
        cash=cash or [],
        cash_near_cashier_hand=cash_c,
        cash_near_client_hand=cash_k,
        cash_on_counter=False,
        cash_on_cashier_side=cash_side,
        cash_near_storage=False,
        phone_near_cashier_hand=phone,
        phone_near_cashier_body=phone,
        bag=[],
        bag_near_collector=False,
        bag_near_cashier_hand=False,
        document_near_hands=False,
        id_card_visible=False,
        counting_machine_active=False,
        n_people=(1 if cashier else 0) + (1 if client else 0),
        cashier_strong=cashier,
        person_in_zone_any=bool(cashier and in_zone) or intrusion,
        n_people_strong=(1 if cashier else 0) + (1 if client else 0),
        valid_tracks=([1] if cashier else []) + ([2] if client else []),
        valid_bodies=([(230.0, 632.0)] if cashier else []) + ([(260.0, 330.0)] if client else []),
    )


def stream(n_s: float, fn):
    out = []
    for k in range(int(n_s * FPS)):
        t = k / FPS
        out.append(fn(k, t))
    return out


def _types(cands):
    return {c.type_id for c in cands}


def test_runs_helper():
    flags = [False, True, True, False, True, True, True, False, False, False, True]
    times = [i * 0.2 for i in range(len(flags))]
    segs = runs(flags, times, min_duration=0.0, max_gap_frames=1)
    assert [(s.k_start, s.k_end) for s in segs] == [(1, 6), (10, 10)]


def test_cashier_left_during_service_fires_only_with_client():
    # client present whole time; cashier leaves 10..14 s
    cal = make_cal()
    st = stream(20, lambda k, t: state(k, t, cashier=not (10 <= t < 14)))
    cands, ev = run_rules(st, cal, CFG, FPS, 20.0)
    left = [c for c in cands if c.type_id == "cashier_left_during_service"]
    assert len(left) == 1 and abs(left[0].t_event - 10.0) <= 0.21
    # same absence without any client -> no candidate
    st2 = stream(20, lambda k, t: state(k, t, cashier=not (10 <= t < 14), client=False))
    cands2, _ = run_rules(st2, cal, CFG, FPS, 20.0)
    assert "cashier_left_during_service" not in _types(cands2)


def test_phone_rule_needs_duration():
    cal = make_cal()
    st = stream(10, lambda k, t: state(k, t, phone=(3 <= t < 5)))
    cands, _ = run_rules(st, cal, CFG, FPS, 10.0)
    ph = [c for c in cands if c.type_id == "phone_at_workplace"]
    assert len(ph) == 1 and abs(ph[0].t_event - 3.0) <= 0.41
    st2 = stream(10, lambda k, t: state(k, t, phone=(3 <= t < 3.4)))
    cands2, _ = run_rules(st2, cal, CFG, FPS, 10.0)
    assert "phone_at_workplace" not in _types(cands2)


def test_intrusion_rule():
    cal = make_cal()
    st = stream(10, lambda k, t: state(k, t, intrusion=(4 <= t < 6)))
    cands, _ = run_rules(st, cal, CFG, FPS, 10.0)
    assert "unauthorized_in_cash_zone" in _types(cands)
    assert abs(next(c for c in cands if c.type_id == "unauthorized_in_cash_zone").t_event - 4.0) <= 0.41


def test_unattended_cash_rule():
    cal = make_cal()
    cash = [Detection("cash", 0.5, (300.0, 480.0, 330.0, 500.0))]
    # cash on the desk, cashier gone for 6 s
    st = stream(16, lambda k, t: state(k, t, cashier=not (5 <= t < 11), cash=cash, cash_side=True))
    cands, _ = run_rules(st, cal, CFG, FPS, 16.0)
    un = [c for c in cands if c.type_id == "cash_left_unattended"]
    assert len(un) == 1 and abs(un[0].t_event - 5.0) <= 0.61
    # cashier present with hands on the cash -> nothing
    st2 = stream(16, lambda k, t: state(k, t, cash=cash, cash_side=True, cash_c=True, hands=[(310.0, 490.0), (320.0, 495.0)]))
    cands2, _ = run_rules(st2, cal, CFG, FPS, 16.0)
    assert "cash_left_unattended" not in _types(cands2)


def _reach_hands(t, t0, t1):
    """Cashier wrist extended 130 px toward the client between t0 and t1 (crosses the counter line)."""
    if t0 <= t < t1:
        return [(230.0, 400.0), (260.0, 520.0)]
    return [(200.0, 520.0), (260.0, 520.0)]


def test_issue_without_count_fires_without_counting_and_not_with_counting():
    cal = make_cal()
    cash = [Detection("cash", 0.5, (225.0, 395.0, 240.0, 410.0))]
    # cashier holds cash (cash_c) then reaches to the client at 12 s; no counting motion before
    st = stream(16, lambda k, t: state(k, t, hands=_reach_hands(t, 12.0, 13.0), cash=cash if 10 <= t < 13.5 else [], cash_c=(10 <= t < 12.5), cash_k=(12.4 <= t < 13.5)))
    cands, ev = run_rules(st, cal, CFG, FPS, 16.0)
    assert [h.direction for h in ev.handovers] == ["cashier_to_client"]
    iw = [c for c in cands if c.type_id == "issue_without_count"]
    assert len(iw) == 1 and abs(iw[0].t_event - 12.0) <= 0.21

    # same, but with periodic counting motion of the wrists during 6..10 s -> no candidate
    def hands_counting(t):
        if 6.0 <= t < 10.0:
            a = 25.0 * math.sin(2 * math.pi * 2.0 * t)  # 2 Hz flicking, 25 px amplitude
            return [(200.0 + a, 520.0 + a), (260.0, 520.0)]
        return _reach_hands(t, 12.0, 13.0)

    st2 = stream(16, lambda k, t: state(k, t, hands=hands_counting(t), cash=cash if 5 <= t < 13.5 else [], cash_c=(5 <= t < 12.5), cash_k=(12.4 <= t < 13.5)))
    cands2, ev2 = run_rules(st2, cal, CFG, FPS, 16.0)
    assert ev2.counting, "periodic wrist motion must be detected as counting"
    assert "issue_without_count" not in _types(cands2)


def test_merge_and_select():
    from forte_ai.report import Candidate

    cs = [Candidate("a", 10.0, (9, 11), 0.6), Candidate("a", 11.5, (10, 12), 0.8), Candidate("b", 30.0, (29, 31), 0.3)]
    m = merge_candidates(cs, 3.0)
    assert len(m) == 2 and m[0].confidence == 0.8
    sel = select_violations(m, 0.5)
    assert [c.type_id for c in sel] == ["a"]
    sel2 = select_violations(m, 0.5, {"b": 0.2})
    assert [c.type_id for c in sel2] == ["a", "b"]
