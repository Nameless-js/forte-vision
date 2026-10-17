"""Pre-download every model weight used by the engine (needs network ONCE).

Hugging Face models are downloaded with `local_dir=` into models/hf/<org>__<name> (no symlinks, works on
Windows without developer mode); rtmlib ONNX files go to its own cache (~/.cache/rtmlib). After this script
finishes, the engine runs with HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 and no network.

Usage: python scripts/download_weights.py [--profile gpu-small|gpu-large|cpu] [--skip-vlm] [--skip-pose] [--skip-detector]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.config import Config  # noqa: E402
from forte_ai.models_util import local_dir_for  # noqa: E402


def dl_hf(repo_id: str) -> str:
    from huggingface_hub import snapshot_download

    t0 = time.time()
    dest = local_dir_for(repo_id)
    dest.mkdir(parents=True, exist_ok=True)
    path = snapshot_download(
        repo_id,
        local_dir=str(dest),
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.py", "*.tiktoken", "merges.txt", "vocab*", "*.jinja"],
        ignore_patterns=["*.bin", "*.pth", "*.onnx", "*.msgpack", "*.h5", "consolidated*"],
        max_workers=4,
    )
    size = sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file()) / 1e9
    print(f"  {repo_id}: ok in {time.time() - t0:.0f}s, {size:.2f} GB -> {path}", flush=True)
    return path


def dl_pose(mode: str, model: str, device: str) -> None:
    """rtmlib downloads its ONNX files on first construction (into ~/.cache/rtmlib)."""
    import rtmlib

    t0 = time.time()
    cls = rtmlib.Wholebody if model == "wholebody" else rtmlib.Body
    cls(mode=mode, backend="onnxruntime", device=device)
    print(f"  rtmlib {model}/{mode}: ok in {time.time() - t0:.0f}s", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=None)
    ap.add_argument("--skip-vlm", action="store_true")
    ap.add_argument("--skip-pose", action="store_true")
    ap.add_argument("--skip-detector", action="store_true")
    ap.add_argument("--extra", nargs="*", default=[], help="additional HF repo ids to download")
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    cfg = Config.load(profile=a.profile)
    print(f"profile={cfg.profile}; models dir: {local_dir_for('x/y').parent}")
    if not a.skip_detector:
        print("detector:")
        dl_hf(cfg.get("perception.detector.model_id"))
    if not a.skip_pose and cfg.get("perception.pose.backend") == "rtmlib":
        print("pose:")
        dl_pose(cfg.get("perception.pose.mode"), cfg.get("perception.pose.model"), "cpu")
    if not a.skip_vlm and cfg.get("vlm.enabled"):
        print("vlm:")
        dl_hf(cfg.get("vlm.model_id"))
    for rid in a.extra:
        dl_hf(rid)
    print("all weights downloaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
