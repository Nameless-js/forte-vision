"""Model path resolution: repo-local `models/hf/<org>__<name>` first (downloaded by scripts/download_weights.py
without symlinks, which Windows forbids for non-admin users), then the Hugging Face cache (offline-capable)."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def models_dir() -> Path:
    return Path(os.environ.get("FORTE_MODELS_DIR") or (REPO_ROOT / "models" / "hf"))


def local_dir_for(repo_id: str) -> Path:
    return models_dir() / repo_id.replace("/", "__")


def resolve_model_path(repo_id: str) -> str:
    """Return a local directory if the weights were downloaded into models/hf, else the repo id."""
    if os.path.isdir(repo_id):
        return repo_id
    d = local_dir_for(repo_id)
    if d.is_dir() and any(d.glob("*.json")):
        return str(d)
    return repo_id
