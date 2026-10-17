"""Benchmark Grounding DINO speed/recall vs input size and batch size on sampled frames of one video.

Usage: python scripts/bench_detector.py --id 1 --n 40 --sizes 464 600 800 --batches 2 4
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.config import Config  # noqa: E402
from forte_ai.labels import read_labels_csv  # noqa: E402
from forte_ai.perception.detector import GroundingDinoDetector  # noqa: E402
from forte_ai.video import iter_frames  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, default=1)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--sizes", nargs="*", type=int, default=[464, 600, 800])
    ap.add_argument("--batches", nargs="*", type=int, default=[2, 4])
    a = ap.parse_args()
    cfg = Config.load(profile="gpu-small")
    labels = {r.video_id: r for r in read_labels_csv(ROOT / "data" / "labels.csv")}
    vp = ROOT / labels[a.id].path
    frames = []
    for fr in iter_frames(vp, sample_fps=5.0):
        frames.append(fr)
        if len(frames) >= a.n:
            break
    imgs = [f.image for f in frames]
    idx = [f.index for f in frames]
    ts = [f.t for f in frames]
    det_cfg = dict(cfg.section("perception")["detector"])
    det = GroundingDinoDetector(det_cfg, "cuda")
    import torch

    for size in a.sizes:
        det.processor.image_processor.size = {"shortest_edge": size, "longest_edge": int(size * 1333 / 800)}
        for bs in a.batches:
            det.batch_size = bs
            det.detect(imgs[:bs], idx[:bs], ts[:bs])  # warm-up
            torch.cuda.synchronize()
            t0 = time.time()
            out = det.detect(imgs, idx, ts)
            torch.cuda.synchronize()
            dt = time.time() - t0
            counts = {}
            for fd in out:
                for d in fd.dets:
                    counts[d.cls] = counts.get(d.cls, 0) + 1
            mem = torch.cuda.max_memory_allocated() / 1e9
            print(f"size={size} batch={bs}: {dt / len(imgs) * 1000:.0f} ms/frame, peak VRAM {mem:.2f} GB, dets/frame {{{', '.join(f'{k}:{v / len(imgs):.2f}' for k, v in sorted(counts.items()))}}}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
