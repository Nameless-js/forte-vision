"""`make robustness`: augmentation suite (Section 12, gate 5).

For every labeled video create variants — horizontal flip, rotation ±10°, perspective warp, 0.75x scale,
brightness ±25 %, 10 % crop, 720p re-encode — run the engine on each and compare verdict / timecode / cashier
role with the original. Variants are written to data/augmented/ (gitignored) with the bundled imageio-ffmpeg
binary (re-encode) or OpenCV + ffmpeg (geometric/photometric).

Usage: python scripts/robustness.py [--out reports/robustness] [--ids ...] [--variants hflip rot+10 ...] [--no-vlm]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.labels import read_labels_csv  # noqa: E402
from forte_ai.video import iter_frames, probe  # noqa: E402

AUG_DIR = ROOT / "data" / "augmented"
VARIANTS = ["hflip", "rot+10", "rot-10", "persp", "scale075", "bright+25", "bright-25", "crop10", "reenc720"]


def ffmpeg_bin() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def transform_frame(img: np.ndarray, variant: str) -> np.ndarray:
    h, w = img.shape[:2]
    if variant == "hflip":
        return cv2.flip(img, 1)
    if variant.startswith("rot"):
        ang = float(variant[3:])
        M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
        return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    if variant == "persp":
        d = 0.06
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = np.float32([[w * d, h * d * 0.5], [w * (1 - d * 0.5), 0], [w, h], [w * d * 0.5, h * (1 - d)]])
        M = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    if variant == "scale075":
        return cv2.resize(img, (int(w * 0.75) // 2 * 2, int(h * 0.75) // 2 * 2), interpolation=cv2.INTER_AREA)
    if variant.startswith("bright"):
        f = 1.0 + float(variant[6:]) / 100.0
        return np.clip(img.astype(np.float32) * f, 0, 255).astype(np.uint8)
    if variant == "crop10":
        x0, y0 = int(w * 0.05), int(h * 0.05)
        c = img[y0 : h - y0, x0 : w - x0]
        return c[: (c.shape[0] // 2) * 2, : (c.shape[1] // 2) * 2]
    return img


def expected_point(variant: str, xn: float, yn: float, w: int, h: int) -> tuple[float, float]:
    """Map a normalised point of the original frame into the normalised frame of the variant, using exactly
    the transform applied in transform_frame (so role checks are geometry-aware, not just 'a cashier found')."""
    x, y = xn * w, yn * h
    if variant == "hflip":
        return 1.0 - xn, yn
    if variant.startswith("rot"):
        ang = float(variant[3:])
        M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
        xx = M[0, 0] * x + M[0, 1] * y + M[0, 2]
        yy = M[1, 0] * x + M[1, 1] * y + M[1, 2]
        return xx / w, yy / h
    if variant == "persp":
        d = 0.06
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = np.float32([[w * d, h * d * 0.5], [w * (1 - d * 0.5), 0], [w, h], [w * d * 0.5, h * (1 - d)]])
        M = cv2.getPerspectiveTransform(src, dst)
        v = M @ np.array([x, y, 1.0])
        return float(v[0] / v[2]) / w, float(v[1] / v[2]) / h
    if variant == "crop10":
        return (xn - 0.05) / 0.9, (yn - 0.05) / 0.9
    return xn, yn  # scale, brightness, re-encode keep normalised coordinates


def make_variant(src: Path, variant: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    ff = ffmpeg_bin()
    if variant == "reenc720":
        # 720p re-encode (portrait source: scale the long side to 1280 keeping aspect, even dims)
        cmd = [ff, "-y", "-loglevel", "error", "-i", str(src), "-vf", "scale='if(gt(iw,ih),1280,-2)':'if(gt(iw,ih),-2,1280)'", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-an", str(dst)]
        subprocess.run(cmd, check=True)
        return
    info = probe(src)
    first = None
    proc = None
    for fr in iter_frames(src, sample_fps=0):  # every frame
        out = transform_frame(fr.image, variant)
        if proc is None:
            h, w = out.shape[:2]
            cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{info.fps:.3f}", "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(dst)]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            first = (w, h)
        if out.shape[1] != first[0] or out.shape[0] != first[1]:
            out = cv2.resize(out, first)
        proc.stdin.write(out.tobytes())
    if proc is not None:
        proc.stdin.close()
        proc.wait()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(ROOT / "data" / "labels.csv"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "robustness"))
    ap.add_argument("--ids", nargs="*", type=int)
    ap.add_argument("--variants", nargs="*", default=VARIANTS)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--no-vlm", action="store_true")
    ap.add_argument("--only-make", action="store_true", help="only create the augmented files")
    ap.add_argument("--perception-only", action="store_true", help="phase 1: only fill the perception cache for all variants")
    ap.add_argument("--config", default=None, help="config overlay for the analyzer (phase 2)")
    ap.add_argument("--tol", type=float, default=3.0)
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [r for r in read_labels_csv(Path(a.labels)) if r.split == "labeled" and r.path]
    if a.ids:
        rows = [r for r in rows if r.video_id in a.ids]
    # make variants
    jobs = []
    for r in rows:
        for v in a.variants:
            dst = AUG_DIR / v / f"{r.video_id:02d}.mp4"
            make_variant(ROOT / r.path, v, dst)
            jobs.append((r, v, dst))
    print(f"augmented files ready: {len(jobs)}")
    if a.only_make:
        return 0
    if a.perception_only:
        # phase 1: fill the perception cache for every variant (rule/VLM-independent, GPU-heavy)
        from forte_ai.config import Config
        from forte_ai.perception.pipeline import PerceptionEngine

        eng = PerceptionEngine(Config.load(profile=a.profile))
        t_all = time.time()
        for i, (r, v, dst) in enumerate(jobs):
            t0 = time.time()
            try:
                pr = eng.run(dst, use_cache=True)
                status = "cache" if pr.from_cache else f"{time.time() - t0:.0f}s"
            except Exception as e:  # noqa: BLE001
                status = f"ERROR {e}"
            print(f"[{i + 1}/{len(jobs)}] id {r.video_id:>2} {v:<9} {status}", flush=True)
        print(f"perception cache filled for {len(jobs)} variants in {time.time() - t_all:.0f} s")
        return 0

    from forte_ai.analyzer import Analyzer

    an = Analyzer(config=a.config, profile=a.profile)
    if a.no_vlm:
        an.cfg.set("vlm.enabled", False)
        an.vlm = None
    base: dict[int, dict] = {}
    results = []
    for r in rows:
        res = an.analyze(ROOT / r.path, use_cache=True)
        base[r.video_id] = res
    for r, v, dst in jobs:
        t0 = time.time()
        try:
            res = an.analyze(dst, use_cache=True)
            err = ""
        except Exception as e:  # noqa: BLE001
            res, err = {"verdict": "error", "violations": [], "calibration": {}}, str(e)
        b = base[r.video_id]
        b_ts = [x["timecode_sec"] for x in b["violations"]]
        v_ts = [x["timecode_sec"] for x in res["violations"]]
        verdict_agree = b["verdict"] == res["verdict"]
        # timecode agreement: for violation videos compare the event nearest to the label
        dt = None
        if r.label == "violation" and b_ts and v_ts and r.t_sec is not None:
            tb = min(b_ts, key=lambda t: abs(t - r.t_sec))
            tv = min(v_ts, key=lambda t: abs(t - r.t_sec))
            dt = abs(tb - tv)
        # cashier role agreement: the cashier's normalised centre should map to the transformed position; we
        # check the weaker but transform-independent invariant that a cashier was found and has high presence
        cal_b, cal_v = b.get("calibration", {}), res.get("calibration", {})
        role_ok = False
        if cal_v.get("cashier_track") is not None and cal_b.get("cashier_center_norm"):
            bx, by = cal_b["cashier_center_norm"]
            ex, ey = expected_point(v, bx, by, int(cal_b.get("frame_w", 464)), int(cal_b.get("frame_h", 848)))
            vx, vy = cal_v["cashier_center_norm"]
            fw, fh = int(cal_v.get("frame_w", 464)), int(cal_v.get("frame_h", 848))
            dist = ((ex - vx) * fw) ** 2 + ((ey - vy) * fh) ** 2
            role_ok = dist ** 0.5 <= 0.08 * (fw ** 2 + fh ** 2) ** 0.5
        results.append({"video_id": r.video_id, "label": r.label, "t_label": r.t_sec, "variant": v, "base_verdict": b["verdict"], "verdict": res["verdict"], "verdict_agree": verdict_agree, "base_t": b_ts, "var_t": v_ts, "dt": dt, "time_ok": (dt is not None and dt <= a.tol) if (r.label == "violation" and b_ts) else None, "role_ok": role_ok, "elapsed": round(time.time() - t0, 1), "error": err})
        print(f"id {r.video_id:>2} {v:<9} base={b['verdict']:<12} var={res['verdict']:<12} agree={verdict_agree} dt={dt} role_ok={role_ok} {err}", flush=True)
    n = len(results)
    agree = sum(1 for x in results if x["verdict_agree"]) / n if n else 0
    timed = [x for x in results if x["time_ok"] is not None]
    time_ok = sum(1 for x in timed if x["time_ok"]) / len(timed) if timed else None
    roles = sum(1 for x in results if x["role_ok"]) / n if n else 0
    per_variant = {}
    for v in a.variants:
        xs = [x for x in results if x["variant"] == v]
        tv = [x for x in xs if x["time_ok"] is not None]
        per_variant[v] = {"verdict_agreement": sum(1 for x in xs if x["verdict_agree"]) / len(xs) if xs else None, "timecode_within_tol": (sum(1 for x in tv if x["time_ok"]) / len(tv)) if tv else None, "role_ok": sum(1 for x in xs if x["role_ok"]) / len(xs) if xs else None}
    summary = {"n_runs": n, "verdict_agreement": agree, "timecode_within_tol": time_ok, "tol_s": a.tol, "role_ok": roles, "per_variant": per_variant, "gate_verdict_ge_0.90": agree >= 0.90, "gate_timecode_ge_0.80": (time_ok is None) or time_ok >= 0.80}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "per_run.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else ["video_id"])
        w.writeheader()
        w.writerows(results)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
