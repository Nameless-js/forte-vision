"""Per-video perception cache keyed by (content md5, pipeline version, config hash)."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Optional


def config_hash(cfg_sections: dict) -> str:
    s = json.dumps(cfg_sections, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


class PerceptionCache:
    def __init__(self, root: Path, enabled: bool = True, pipeline_version: str = "p1"):
        self.root = Path(root) / "perception"
        self.enabled = enabled
        self.version = pipeline_version
        if enabled:
            self.root.mkdir(parents=True, exist_ok=True)

    def key(self, content_md5: str, cfg_hash: str) -> str:
        return f"{content_md5}_{self.version}_{cfg_hash}"

    def path(self, content_md5: str, cfg_hash: str) -> Path:
        return self.root / (self.key(content_md5, cfg_hash) + ".json.gz")

    def load(self, content_md5: str, cfg_hash: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        p = self.path(content_md5, cfg_hash)
        if not p.exists():
            return None
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save(self, content_md5: str, cfg_hash: str, data: dict[str, Any]) -> Optional[Path]:
        if not self.enabled:
            return None
        p = self.path(content_md5, cfg_hash)
        tmp = p.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        tmp.replace(p)
        return p
