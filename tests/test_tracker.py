import numpy as np

from forte_ai.perception.bytetrack import ByteTrack, iou_matrix
from forte_ai.perception.detector import Detection, FrameDetections
from forte_ai.perception.tracker import PersonTracker


def test_iou_matrix():
    a = np.array([[0, 0, 10, 10]], np.float32)
    b = np.array([[0, 0, 10, 10], [5, 5, 15, 15], [20, 20, 30, 30]], np.float32)
    m = iou_matrix(a, b)
    assert np.isclose(m[0, 0], 1.0) and np.isclose(m[0, 1], 25 / 175) and m[0, 2] == 0


def test_two_people_keep_ids_through_occlusion_gap():
    bt = ByteTrack(track_activation_threshold=0.3, lost_track_buffer=5, minimum_matching_threshold=0.8, minimum_consecutive_frames=2)
    ids_a, ids_b = set(), set()
    for k in range(30):
        boxes = [[100 + k, 100, 150 + k, 220]]  # person A moving right
        scores = [0.9]
        if k < 10 or k > 13:  # person B disappears for 4 frames
            boxes.append([300, 400 + k, 360, 520 + k])
            scores.append(0.8)
        out = bt.update(np.array(boxes, np.float32), np.array(scores, np.float32))
        for tid, box in out:
            if box[0] < 250:
                ids_a.add(tid)
            else:
                ids_b.add(tid)
    assert len(ids_a) == 1 and len(ids_b) == 1 and ids_a != ids_b


def test_low_score_detections_only_keep_existing_tracks():
    bt = ByteTrack(track_activation_threshold=0.5, minimum_consecutive_frames=1)
    out = bt.update(np.array([[0, 0, 10, 10]], np.float32), np.array([0.2], np.float32))
    assert out == []  # low score cannot create a track
    bt.update(np.array([[0, 0, 10, 10]], np.float32), np.array([0.9], np.float32))
    out = bt.update(np.array([[1, 1, 11, 11]], np.float32), np.array([0.2], np.float32))
    assert len(out) == 1  # but can continue one


def test_person_tracker_wrapper_collects_states():
    tr = PersonTracker({"track_activation_threshold": 0.3, "lost_track_buffer": 5, "minimum_matching_threshold": 0.8, "minimum_consecutive_frames": 2}, 5.0)
    for k in range(10):
        fd = FrameDetections(k, k / 5.0, 464, 848, [Detection("person", 0.9, (100, 100 + k, 200, 300 + k)), Detection("cash", 0.5, (10, 10, 20, 20))])
        tr.update(fd)
    tracks = tr.finished(min_frames=3)
    assert len(tracks) == 1
    st = next(iter(tracks.values()))
    assert st.n >= 8 and st.first_t <= 0.4 and st.last_t == 1.8
