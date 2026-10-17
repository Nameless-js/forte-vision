"""Pre-download every model weight used by the engine into the local caches (needs network ONCE).

After this script finishes, the engine runs with HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1.
Usage: python scripts/download_weights.py [--profile gpu-small|gpu-large|cpu] [--skip-vlm] [--skip-pose]
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


def dl_hf(repo_id: str) -> str:
    from huggingface_hub import snapshot_download

    t0 = time.time()
    # skip optional big artifacts that transformers does not need at runtime
    path = snapshot_download(
        repo_id,
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.py", "*.tiktoken", "merges.txt", "vocab*"],
        ignore_patterns=["*.bin", "*.pth", "*.onnx", "*.msgpack", "*.h5", "consolidated*"],
    )
    print(f"  {repo_id}: ok in {time.time() - t0:.0f}s -> {path}", flush=True)
    return path


def dl_pose(mode: str, model: str, device: str) -> None:
    """rtmlib downloads its ONNX files on first construction (into ~/.cache/rtmlib)."""
    import rtmlib

    t0 = time.time()
    backend = "onnxruntime"
    cls = rtmlib.Wholebody if model == "wholebody" else rtmlib.Body
    cls(mode=mode, backend=backend, device=device)
    print(f"  rtmlib {model}/{mode}: ok in {time.time() - t0:.0f}s", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=None)
    ap.add_argument("--skip-vlm", action="store_true")
    ap.add_argument("--skip-pose", action="store_true")
    ap.add_argument("--skip-detector", action="store_true")
    a = ap.parse_args()
    cfg = Config.load(profile=a.profile)
    print(f"profile={cfg.profile}; HF cache: {os.environ.get('HF_HOME') or '~/.cache/huggingface'}")
    if not a.skip_detector:
        print("detector:")
        dl_hf(cfg.get("perception.detector.model_id"))
    if not a.skip_pose and cfg.get("perception.pose.backend") == "rtmlib":
        print("pose:")
        dl_pose(cfg.get("perception.pose.mode"), cfg.get("perception.pose.model"), "cpu")
    if not a.skip_vlm and cfg.get("vlm.enabled"):
        print("vlm:")
        dl_hf(cfg.get("vlm.model_id"))
    print("all weights downloaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
