from forte_ai.eval.metrics import PerVideo, compute_metrics, fit_threshold, lovo_evaluate, select_by_threshold


def _pv(vid, label, t_label, cands, group=None, team_type=None):
    return PerVideo(vid, label, t_label, group or f"g{vid}", cands, team_type)


def test_select_by_threshold_respects_per_type_and_max():
    cands = [{"type_id": "a", "t_event": 5, "confidence": 0.6}, {"type_id": "b", "t_event": 9, "confidence": 0.4}]
    assert [c["type_id"] for c in select_by_threshold(cands, 0.5)] == ["a"]
    assert [c["type_id"] for c in select_by_threshold(cands, 0.5, {"b": 0.3})] == ["a", "b"]
    assert len(select_by_threshold(cands, 0.1, max_n=1)) == 1


def test_compute_metrics_basic():
    pvs = [
        _pv(1, "violation", 10.0, [{"type_id": "x", "t_event": 11.0, "confidence": 0.9}], team_type="x"),
        _pv(2, "violation", 20.0, [{"type_id": "y", "t_event": 40.0, "confidence": 0.9}], team_type="x"),
        _pv(3, "violation", 5.0, [], team_type="x"),
        _pv(4, "no_violation", None, [{"type_id": "x", "t_event": 3.0, "confidence": 0.3}]),
        _pv(5, "no_violation", None, [{"type_id": "x", "t_event": 3.0, "confidence": 0.8}]),
    ]
    m = compute_metrics(pvs, 0.5)
    assert m["tp"] == 2 and m["fn"] == 1 and m["fp"] == 1 and m["tn"] == 1
    assert abs(m["recall_violation"] - 2 / 3) < 1e-9
    assert m["localization"]["within_2s"] == 0.5 and m["localization"]["within_5s"] == 0.5
    assert m["classification_accuracy"] == 0.5


def test_fit_threshold_prefers_recall_then_fewer_fps():
    pvs = [
        _pv(1, "violation", 10.0, [{"type_id": "x", "t_event": 10.5, "confidence": 0.45}]),
        _pv(2, "violation", 20.0, [{"type_id": "x", "t_event": 20.0, "confidence": 0.7}]),
        _pv(3, "no_violation", None, [{"type_id": "x", "t_event": 3.0, "confidence": 0.4}]),
        _pv(4, "no_violation", None, [{"type_id": "x", "t_event": 3.0, "confidence": 0.6}]),
    ]
    thr = fit_threshold(pvs)
    # only 0.45 keeps both violations (recall 1.0) and rejects the 0.4 FP; 0.5+ would lose video 1
    assert thr == 0.45


def test_fit_threshold_picks_middle_of_feasible_interval():
    pvs = [
        _pv(1, "violation", 10.0, [{"type_id": "x", "t_event": 10.5, "confidence": 0.9}]),
        _pv(2, "no_violation", None, [{"type_id": "x", "t_event": 3.0, "confidence": 0.2}]),
    ]
    thr = fit_threshold(pvs)
    assert 0.5 <= thr <= 0.6  # feasible (0.2, 0.9] -> median of the grid points 0.25..0.9


def test_lovo_groups_duplicates_together():
    pvs = [
        _pv(4, "violation", 57.0, [{"type_id": "x", "t_event": 57.0, "confidence": 0.9}], group="dup"),
        _pv(47, "violation", 68.0, [{"type_id": "x", "t_event": 68.0, "confidence": 0.9}], group="dup"),
        _pv(5, "no_violation", None, [], group="c5"),
        _pv(8, "no_violation", None, [{"type_id": "x", "t_event": 1.0, "confidence": 0.2}], group="c8"),
        _pv(9, "violation", 3.0, [{"type_id": "x", "t_event": 3.5, "confidence": 0.7}], group="g9"),
    ]
    res = lovo_evaluate(pvs)
    assert res["n_folds"] == 4
    assert res["recall_violation"] == 1.0 and res["fp"] == 0
    assert len(res["rows"]) == 5
