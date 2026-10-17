"""Structured configuration: configs/default.yaml + profile overlay + user overrides."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
CONFIG_DIR = REPO_ROOT / "configs"
PROFILES = ("gpu-large", "gpu-small", "cpu")


def deep_update(base: dict, upd: Mapping) -> dict:
    for k, v in upd.items():
        if isinstance(v, Mapping) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = copy.deepcopy(v) if isinstance(v, (dict, list)) else v
    return base


def detect_profile() -> str:
    """Pick a hardware profile from torch.cuda (no torch -> cpu)."""
    try:
        import torch

        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            return "gpu-large" if vram_gb >= 15.0 else "gpu-small"
    except Exception:
        pass
    return "cpu"


class Config:
    """Dict-backed config with dotted-path access: cfg.get('rules.counting_window_s')."""

    def __init__(self, data: dict):
        self._d = data

    # ---- access ----
    def get(self, path: str, default: Any = None) -> Any:
        cur: Any = self._d
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def __getitem__(self, key: str) -> Any:
        return self._d[key]

    def section(self, key: str) -> dict:
        v = self._d.get(key, {})
        return v if isinstance(v, dict) else {}

    def to_dict(self) -> dict:
        return copy.deepcopy(self._d)

    def set(self, path: str, value: Any) -> None:
        cur = self._d
        parts = path.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = value

    @property
    def profile(self) -> str:
        return self._d.get("profile", "cpu")

    # ---- loading ----
    @classmethod
    def load(
        cls,
        config: Optional[str | Path | Mapping] = None,
        profile: Optional[str] = None,
        overrides: Optional[Mapping] = None,
        config_dir: Optional[Path] = None,
    ) -> "Config":
        cdir = Path(config_dir) if config_dir else CONFIG_DIR
        data = yaml.safe_load((cdir / "default.yaml").read_text(encoding="utf-8")) or {}
        if config is not None:
            if isinstance(config, Mapping):
                user = dict(config)
            else:
                p = Path(config)
                if not p.is_absolute() and not p.exists():
                    p = REPO_ROOT / p
                user = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
            deep_update(data, user)
        prof = profile or os.environ.get("FORTE_PROFILE") or data.get("profile", "auto")
        if prof in (None, "", "auto"):
            prof = detect_profile()
        if prof not in PROFILES:
            raise ValueError(f"unknown profile {prof!r}; expected one of {PROFILES} or 'auto'")
        pfile = cdir / f"profile-{prof}.yaml"
        if pfile.exists():
            deep_update(data, yaml.safe_load(pfile.read_text(encoding="utf-8")) or {})
        data["profile"] = prof
        if config is not None and isinstance(config, Mapping):
            deep_update(data, dict(config))  # explicit user dict wins over the profile
        if overrides:
            deep_update(data, overrides)
        if data.get("device", "auto") == "auto":
            data["device"] = "cpu" if prof == "cpu" else "cuda"
        return cls(data)
