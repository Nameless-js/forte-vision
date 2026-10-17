"""Roles/zones calibration on synthetic tracks: the cashier must be found by behaviour, not by pixel position,
so the result must be invariant to horizontal flips and 90-degree rotations of the whole scene."""

import numpy as np
import pytest

from forte_ai.perception.detector import Detection, FrameDetections
from forte_ai.perception.pose import FramePoses
from forte_ai.perception.roles import calibrate
from forte_ai.perception.tracker import TrackState

W, H = 464, 848
CFG = {"calibration_seconds": 12.0, "cashier_min_presence": 0.5, "cashier_zone_dilate_frac": 0.12, "client_max_dist_frac": 0.45, "collector_bag_iou": 0.05, "min_track_frames": 5}


def _scene(transform=lambda x, y: (x, y), n=100, fps=5.0, with_bag=False):
    """Cashier seated near the bottom (static, present all the time); client walks in from the top at t=2s,
    sits across the desk from t=5s; a counting machine sits next to the cashier; cash appears near the cashier."""
    frames, poses, per_frame = [], [], []
    tracks = {1: TrackState(1, 0.0, 0.0), 2: TrackState(2, 2.0, 2.0), 3: TrackState(3, 0.0, 0.0)}

    def box(cx, cy, w, h):
        x1, y1 = transform(cx - w / 2, cy - h / 2)
        x2, y2 = transform(cx + w / 2, cy + h / 2)
        return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    for k in range(n):
        t = k / fps
        fd = FrameDetections(k, t, W, H)
        assigned = {}
        # cashier: static at (230, 560) with tiny jitter
        cb = box(230 + np.sin(k) * 3, 560 + np.cos(k) * 3, 120, 200)
        fd.dets.append(Detection("person", 0.9, cb))
        assigned[1] = cb
        tracks[1].boxes.append(cb); tracks[1].times.append(t); tracks[1].frame_indices.append(k); tracks[1].n += 1; tracks[1].last_t = t
        # counting machine static near the cashier's left
        fd.dets.append(Detection("counting_machine", 0.8, box(90, 500, 70, 60)))
        # client: enters at t=2 from the top-left door, sits at (260, 330) from t=5
        if t >= 2.0:
            if t < 5.0:
                cx, cy = 80 + (t - 2.0) / 3.0 * 180, 180 + (t - 2.0) / 3.0 * 150
            else:
                cx, cy = 260 + np.sin(k) * 2, 330 + np.cos(k) * 2
            kb = box(cx, cy, 110, 180)
            fd.dets.append(Detection("person", 0.85, kb))
            assigned[2] = kb
            tracks[2].boxes.append(kb); tracks[2].times.append(t); tracks[2].frame_indices.append(k); tracks[2].n += 1; tracks[2].last_t = t
            if with_bag:
                fd.dets.append(Detection("bag", 0.7, box(cx + 30, cy + 60, 50, 40)))
        # a person far away in the background (through the glass), static
        bb = box(60, 120, 50, 90)
        fd.dets.append(Detection("person", 0.6, bb))
        assigned[3] = bb
        tracks[3].boxes.append(bb); tracks[3].times.append(t); tracks[3].frame_indices.append(k); tracks[3].n += 1; tracks[3].last_t = t
        # cash near the cashier's hands between 8 and 12 s
        if 8.0 <= t <= 12.0:
            fd.dets.append(Detection("cash", 0.6, box(240, 480, 30, 20)))
        frames.append(fd)
        poses.append(FramePoses(k, t))
        per_frame.append(assigned)
    return frames, poses, tracks, per_frame


def test_cashier_found_on_plain_scene():
    frames, poses, tracks, pft = _scene()
    cal = calibrate(frames, poses, tracks, pft, CFG, W, H)
    assert cal.cashier_track == 1
    assert 2 in cal.client_tracks
    assert 3 not in cal.client_tracks  # background person is too far from the counter line
    # the cashier's own position is on the positive side of the counter line, the client on the negative side
    assert cal.signed_dist_to_counter(cal.cashier_center) > 0
    assert cal.signed_dist_to_counter((260, 330)) < 0
    assert cal.in_cashier_zone((230, 560))
    assert not cal.in_cashier_zone((260, 300))
    assert cal.counting_machine_point is not None


@pytest.mark.parametrize(
    "name,tf",
    [
        ("hflip", lambda x, y: (W - x, y)),
        ("vflip", lambda x, y: (x, H - y)),
        ("rot90", lambda x, y: (H - y, x)),  # 90 degrees clockwise into an 848x464 frame
        ("rot180", lambda x, y: (W - x, H - y)),
    ],
)
def test_cashier_invariant_to_flip_and_rotation(name, tf):
    frames, poses, tracks, pft = _scene(transform=tf)
    w, h = (H, W) if name == "rot90" else (W, H)
    cal = calibrate(frames, poses, tracks, pft, CFG, w, h)
    assert cal.cashier_track == 1, name
    assert 2 in cal.client_tracks, name
    cx, cy = tf(230, 560)
    kx, ky = tf(260, 330)
    assert cal.signed_dist_to_counter((cx, cy)) > 0, name
    assert cal.signed_dist_to_counter((kx, ky)) < 0, name


def test_collector_detected_by_bag():
    frames, poses, tracks, pft = _scene(with_bag=True)
    cal = calibrate(frames, poses, tracks, pft, CFG, W, H)
    assert cal.cashier_track == 1
    assert 2 in cal.collector_tracks


def test_no_tracks_gives_empty_calibration():
    cal = calibrate([FrameDetections(0, 0.0, W, H)], [FramePoses(0, 0.0)], {}, [{}], CFG, W, H)
    assert cal.cashier_track is None
    assert "no tracks" in cal.notes[0]


def test_calibration_serialises_normalised_coordinates():
    frames, poses, tracks, pft = _scene()
    d = calibrate(frames, poses, tracks, pft, CFG, W, H).to_dict()
    assert 0 <= d["cashier_center_norm"][0] <= 1 and 0 <= d["cashier_center_norm"][1] <= 1
    assert all(0 <= v[0] <= 1.2 and 0 <= v[1] <= 1.2 for v in d["cashier_hull_norm"])
