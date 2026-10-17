"""Probe which Grounding DINO phrases match which objects in this scene (development-time only).

For each phrase (queried ALONE) the top-k boxes are drawn on a few frames; one sheet per phrase group.
Usage: python scripts/prompt_probe.py --frames 1:12 1:20 3:10 14:30 4:40 --out analysis/prompt_probe
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.config import Config  # noqa: E402
from forte_ai.labels import read_labels_csv  # noqa: E402
from forte_ai.perception.detector import GroundingDinoDetector  # noqa: E402
from forte_ai.video import frame_at  # noqa: E402

GROUPS = {
    "machine": ["money counting machine", "banknote counter", "black printer", "black office machine", "currency counter"],
    "safe": ["safe", "metal cabinet", "grey metal box", "locker", "cash box"],
    "cash": ["banknotes", "money", "cash", "stack of money", "paper bills", "bundle of banknotes"],
    "phone": ["smartphone", "mobile phone", "cell phone"],
    "document": ["document", "paper", "sheet of paper", "receipt", "white paper"],
    "idcard": ["id card", "plastic card", "passport", "small card", "credit card"],
    "bag": ["bag", "money bag", "sack", "pouch", "backpack", "handbag", "black bag"],
    "misc": ["laptop", "open drawer", "desk drawer", "keyboard", "chair"],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", nargs="*", default=["1:12", "1:20", "1:23", "3:10", "14:30", "4:40"])
    ap.add_argument("--out", default=str(ROOT / "analysis" / "prompt_probe"))
    ap.add_argument("--topk", type=int, default=2)
    ap.add_argument("--thr", type=float, default=0.15)
    a = ap.parse_args()
    cfg = Config.load(profile="gpu-small")
    labels = {r.video_id: r for r in read_labels_csv(ROOT / "data" / "labels.csv")}
    frames = []
    for spec in a.frames:
        vid, t = spec.split(":")
        fr = frame_at(ROOT / labels[int(vid)].path, float(t))
        frames.append((f"{vid}@{t}s", fr.image))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    det_cfg = dict(cfg.section("perception")["detector"])
    det_cfg["box_threshold"] = a.thr
    det_cfg["class_thresholds"] = {}
    det_cfg["min_box_area_frac"] = 0.0
    for group, phrases in GROUPS.items():
        rows = []
        for phrase in phrases:
            det_cfg["prompts"] = {"obj": [phrase]}
            d = GroundingDinoDetector(det_cfg, "cuda")
            tiles = []
            for name, img in frames:
                fd = d.detect([img], [0], [0.0])[0]
                vis = img.copy()
                h = vis.shape[0]
                for k, det in enumerate(sorted(fd.dets, key=lambda x: -x.score)[: a.topk]):
                    x1, y1, x2, y2 = [int(v) for v in det.xyxy]
                    col = (0, 255, 255) if k == 0 else (0, 165, 255)
                    cv2.rectangle(vis, (x1, y1), (x2, y2), col, 2)
                    cv2.putText(vis, f"{det.score:.2f}", (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
                vis = vis[int(0.2 * h) : int(0.75 * h)]
                cv2.rectangle(vis, (0, 0), (300, 22), (0, 0, 0), -1)
                cv2.putText(vis, f"{phrase} | {name}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                tiles.append(vis)
            rows.append(np.concatenate(tiles, axis=1))
            d.unload()
        sheet = np.concatenate(rows, axis=0)
        s = min(1.0, 2000 / sheet.shape[1])
        sheet = cv2.resize(sheet, None, fx=s, fy=s)
        cv2.imwrite(str(out / f"{group}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
        print("wrote", out / f"{group}.jpg", sheet.shape)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
