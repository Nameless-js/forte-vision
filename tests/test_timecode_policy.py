"""Timecode policy (VIOLATION_TYPES.md): action violations -> first frame the condition is true; omission
violations -> the moment of the action that should have been preceded by the skipped step."""

import math

from forte_ai.events.rules import run_rules
from forte_ai.perception.detector import Detection

from tests.test_rules import CFG, FPS, make_cal, state, stream


def _first(cands, type_id):
    xs = [c for c in cands if c.type_id == type_id]
    assert xs, f"no {type_id} candidate"
    return min(xs, key=lambda c: c.t_event)


def test_action_violation_timecode_is_first_true_frame():
    cal = make_cal()
    # cashier leaves at exactly 9.4 s while the client sits at the window
    st = stream(18, lambda k, t: state(k, t, cashier=not (9.4 <= t < 14.0)))
    cands, _ = run_rules(st, cal, CFG, FPS, 18.0)
    c = _first(cands, "cashier_left_during_service")
    assert abs(c.t_event - 9.4) <= 0.21  # within one 5 fps sample of the first absent frame


def test_phone_timecode_is_onset():
    cal = make_cal()
    st = stream(12, lambda k, t: state(k, t, phone=(6.2 <= t < 9.0)))
    cands, _ = run_rules(st, cal, CFG, FPS, 12.0)
    assert abs(_first(cands, "phone_at_workplace").t_event - 6.2) <= 0.41


def test_omission_timecode_is_the_handover_not_the_missing_count():
    cal = make_cal()
    cash = [Detection("cash", 0.5, (225.0, 395.0, 240.0, 410.0))]

    def hands(t):
        return [(230.0, 400.0), (260.0, 520.0)] if 12.0 <= t < 13.0 else [(200.0, 520.0), (260.0, 520.0)]

    st = stream(16, lambda k, t: state(k, t, hands=hands(t), cash=cash if 10 <= t < 13.5 else [], cash_c=(10 <= t < 12.5), cash_k=(12.4 <= t < 13.5)))
    cands, ev = run_rules(st, cal, CFG, FPS, 16.0)
    c = _first(cands, "issue_without_count")
    # the event is anchored on the handover (first reach frame), and the window covers the look-back
    assert abs(c.t_event - 12.0) <= 0.21
    assert c.t_window[0] <= 12.0 - 10.0 + 1e-6 or c.t_window[0] == 0.0
    assert any("пересчёт" in f for f in c.facts)


def test_departure_timecode_is_first_absent_frame():
    cal = make_cal()
    # solo cashier works, then walks out at 8.0 s; the room stays empty until the end
    st = stream(16, lambda k, t: state(k, t, cashier=t < 8.0, client=False))
    cands, ev = run_rules(st, cal, CFG, FPS, 16.0)
    deps = [c for c in cands if c.type_id in ("workplace_left_unsecured", "cash_left_unattended")]
    assert deps, "departure must produce a candidate"
    assert abs(min(c.t_event for c in deps) - 8.0) <= 0.41
