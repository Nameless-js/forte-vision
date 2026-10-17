"""Phase 3 QA: run perception on selected videos, print timings, and render annotated contact sheets
(boxes, track ids, wrists) around the labeled time (or spread over the video for clean ones).

Usage: python scripts/perception_qa.py --ids 1 3 14 [--profile gpu-small] [--no-cache] [--sheets]
Outputs: analysis/perception_qa/<id>_sheet.jpg (gitignored) and analysis/perception_qa/timings.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.config import Config  # noqa: E402
from forte_ai.labels import read_labels_csv  # noqa: E402
from forte_ai.perception.detector import draw_detections  # noqa: E402
from forte_ai.perception.pipeline import PerceptionEngine, PerceptionResult  # noqa: E402
from forte_ai.perception.pose import draw_poses  # noqa: E402
from forte_ai.video import frame_at  # noqa: E402

OUT = ROOT / "analysis" / "perception_qa"


def grid(tiles, cols, tile_w):
    h0, w0 = tiles[0].shape[:2]
    th = int(round(h0 * tile_w / w0))
    rows = (len(tiles) + cols - 1) // cols
    canvas = np.zeros((rows * th, cols * tile_w, 3), np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        canvas[r * th : (r + 1) * th, c * tile_w : (c + 1) * tile_w] = cv2.resize(t, (tile_w, th))
    return canvas


def render_sheet(video_path: Path, pr: PerceptionResult, times: list[float], out_path: Path, crop=(0.27, 0.72)):
    tiles = []
    for t in times:
        # nearest sampled frame
        k = int(np.argmin([abs(f.t - t) for f in pr.frames]))
        fd, fp = pr.frames[k], pr.poses[k]
        fr = frame_at(video_path, fd.t)
        if fr is None:
            continue
        img = fr.image
        if pr.scale != 1.0:
            img = cv2.resize(img, (pr.det_width, pr.det_height))
        img = draw_detections(img, fd)
        img = draw_poses(img, fp)
        for tid, b in pr.per_frame_tracks[k].items():
            x1, y1, x2, y2 = [int(v) for v in b]
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 0), 1)
            cv2.putText(img, f"T{tid}", (x1, y2 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)
        h = img.shape[0]
        img = img[int(crop[0] * h) : int(crop[1] * h)]
        cv2.rectangle(img, (0, 0), (120, 22), (0, 0, 0), -1)
        cv2.putText(img, f"t={fd.t:5.1f}s", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(img)
    if tiles:
        cv2.imwrite(str(out_path), grid(tiles, cols=3, tile_w=640), [cv2.IMWRITE_JPEG_QUALITY, 85])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", type=int, default=[1, 3])
    ap.add_argument("--profile", default=None)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--config", default=None)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = Config.load(config=a.config, profile=a.profile)
    labels = {r.video_id: r for r in read_labels_csv(ROOT / "data" / "labels.csv")}
    eng = PerceptionEngine(cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    all_timings = {}
    for vid in a.ids:
        r = labels[vid]
        vp = ROOT / r.path
        t0 = time.time()
        pr = eng.run(vp, on_progress=lambda f, m: None, use_cache=not a.no_cache)
        wall = time.time() - t0
        n_per_cls = {}
        for f in pr.frames:
            for d in f.dets:
                n_per_cls[d.cls] = n_per_cls.get(d.cls, 0) + 1
        info = {
            "video_id": vid,
            "duration_s": pr.video["duration_s"],
            "wall_s": round(wall, 1),
            "from_cache": pr.from_cache,
            "timings": {k: round(v, 2) for k, v in pr.timings.items()},
            "model_load": {k: round(v, 1) for k, v in eng.load_timings.items()},
            "n_frames": len(pr.frames),
            "n_tracks": len(pr.tracks),
            "track_lengths": sorted([t.n for t in pr.tracks.values()], reverse=True)[:6],
            "dets_per_class_per_frame": {k: round(v / max(1, len(pr.frames)), 2) for k, v in sorted(n_per_cls.items())},
        }
        all_timings[vid] = info
        print(json.dumps(info, ensure_ascii=False))
        if a.sheets:
            if r.t_sec is not None:
                times = [r.t_sec + d for d in (-4, -3, -2, -1, 0, 1, 2, 3, 4)]
            else:
                dur = pr.video["duration_s"]
                times = [dur * k / 10 for k in range(1, 10)]
            render_sheet(vp, pr, times, OUT / f"{vid:02d}_sheet.jpg")
    (OUT / "timings.json").write_text(json.dumps(all_timings, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
