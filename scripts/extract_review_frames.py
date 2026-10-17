"""Phase 1 helper: extract review material for every labeled video (development-time only).

For each violation video: 1 fps frames for t_label-6 .. t_label+6 with burned-in timestamps and a
3x3 contact sheet (t-4..t+4) plus a denser 0.5 s sheet (t-2..t+2); for every video: a 1 fps timeline
strip (whole video) split into pages of 6x5 tiles.

Outputs go to analysis/review/frames/<id>/ (gitignored: never commit extracted frames).
Usage: python scripts/extract_review_frames.py [--ids 1 2 ...] [--only-violations]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.labels import read_labels_csv  # noqa: E402
from forte_ai.video import iter_frames, probe  # noqa: E402

OUT = ROOT / "analysis" / "review" / "frames"


def burn(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    cv2.rectangle(out, (0, 0), (max(120, 11 * len(text) + 16), 28), (0, 0, 0), -1)
    cv2.putText(out, text, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def grid(tiles: list[np.ndarray], cols: int, tile_w: int) -> np.ndarray:
    if not tiles:
        return np.zeros((10, 10, 3), np.uint8)
    h0, w0 = tiles[0].shape[:2]
    tile_h = int(round(h0 * tile_w / w0))
    rows = math.ceil(len(tiles) / cols)
    canvas = np.zeros((rows * tile_h, cols * tile_w, 3), np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        canvas[r * tile_h : (r + 1) * tile_h, c * tile_w : (c + 1) * tile_w] = cv2.resize(t, (tile_w, tile_h), interpolation=cv2.INTER_AREA)
    return canvas


def desk_crop(img: np.ndarray, y0: float = 0.27, y1: float = 0.72) -> np.ndarray:
    """Crop the desk area (development-time only; the engine never uses fixed crops)."""
    h = img.shape[0]
    return img[int(y0 * h) : int(y1 * h), :]


def extract_window(path: Path, center: float, half: float, step: float, max_side: int = 960) -> list[tuple[float, np.ndarray]]:
    frames = []
    start = max(0.0, center - half)
    for fr in iter_frames(path, sample_fps=1.0 / step, max_side=max_side, start_s=start, end_s=center + half):
        frames.append((fr.t, fr.image))
    return frames


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(ROOT / "data" / "labels.csv"))
    ap.add_argument("--ids", nargs="*", type=int)
    ap.add_argument("--only-violations", action="store_true")
    ap.add_argument("--timeline-fps", type=float, default=1.0)
    a = ap.parse_args()

    rows = read_labels_csv(Path(a.labels))
    for r in rows:
        if a.ids and r.video_id not in a.ids:
            continue
        if a.only_violations and r.label != "violation":
            continue
        if not r.path:
            continue
        vp = ROOT / r.path
        info = probe(vp)
        od = OUT / f"{r.video_id:02d}"
        od.mkdir(parents=True, exist_ok=True)
        # timeline strip: 1 fps, 6 columns x 5 rows per page (full frame) + zoomed desk-crop pages 4x4
        tiles, zooms = [], []
        for fr in iter_frames(vp, sample_fps=a.timeline_fps, max_side=None):
            tiles.append(burn(fr.image, f"id{r.video_id} t={fr.t:6.1f}s"))
            zooms.append(burn(desk_crop(fr.image), f"id{r.video_id} t={fr.t:6.1f}s"))
        per_page = 30
        for pi in range(0, len(tiles), per_page):
            page = grid(tiles[pi : pi + per_page], cols=6, tile_w=320)
            cv2.imwrite(str(od / f"timeline_p{pi // per_page + 1:02d}.jpg"), page, [cv2.IMWRITE_JPEG_QUALITY, 80])
        per_zpage = 16
        for pi in range(0, len(zooms), per_zpage):
            page = grid(zooms[pi : pi + per_zpage], cols=4, tile_w=464)
            cv2.imwrite(str(od / f"zoom_p{pi // per_zpage + 1:02d}.jpg"), page, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if r.label == "violation" and r.t_sec is not None:
            t0 = float(r.t_sec)
            # 1 fps frames t-6..t+6 (individual files, full frame)
            for t, img in extract_window(vp, t0, 6.0, 1.0):
                cv2.imwrite(str(od / f"f_{t:06.2f}.jpg"), burn(img, f"id{r.video_id} t={t:6.2f}s (label {t0:.0f}s)"), [cv2.IMWRITE_JPEG_QUALITY, 85])
            # 3x3 contact sheets (full frame) t-4..t+4 at 1 s and t-2..t+2 at 0.5 s
            sheet = [burn(img, f"t={t:5.1f}s") for t, img in extract_window(vp, t0, 4.0, 1.0)][:9]
            cv2.imwrite(str(od / "sheet_1s.jpg"), grid(sheet, cols=3, tile_w=480), [cv2.IMWRITE_JPEG_QUALITY, 85])
            sheet2 = [burn(img, f"t={t:5.2f}s") for t, img in extract_window(vp, t0, 2.0, 0.5)][:9]
            cv2.imwrite(str(od / "sheet_05s.jpg"), grid(sheet2, cols=3, tile_w=480), [cv2.IMWRITE_JPEG_QUALITY, 85])
            # zoomed desk-crop sheets around the label: 3x3 at 1 s (t-4..t+4) and 3x3 at 0.5 s (t-2..t+2)
            z1 = [burn(desk_crop(img), f"t={t:5.1f}s") for t, img in extract_window(vp, t0, 4.0, 1.0, max_side=None)][:9]
            cv2.imwrite(str(od / "zoom_label_1s.jpg"), grid(z1, cols=3, tile_w=464), [cv2.IMWRITE_JPEG_QUALITY, 88])
            z2 = [burn(desk_crop(img), f"t={t:5.2f}s") for t, img in extract_window(vp, t0, 2.0, 0.5, max_side=None)][:9]
            cv2.imwrite(str(od / "zoom_label_05s.jpg"), grid(z2, cols=3, tile_w=464), [cv2.IMWRITE_JPEG_QUALITY, 88])
            # wider zoomed context: t-10..t+10 at 1 s, 4 columns (21 tiles -> 6 rows)
            z3 = [burn(desk_crop(img), f"t={t:5.1f}s") for t, img in extract_window(vp, t0, 10.0, 1.0, max_side=None)]
            cv2.imwrite(str(od / "zoom_label_wide.jpg"), grid(z3, cols=4, tile_w=464), [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(f"id {r.video_id:>2} {r.label:<13} dur={info.duration_s:6.1f}s tiles={len(tiles)} -> {od}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
