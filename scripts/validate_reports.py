"""Validate every result JSON under a reports directory against the contract (used by `make verify`).

Usage: python scripts/validate_reports.py reports/final
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.schema import validate_result  # noqa: E402


def main() -> int:
    d = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "reports" / "final")
    files = sorted(p for p in d.rglob("*.json") if p.parent.name in ("results",) or p.name in ("job_result_full.json",))
    bad = 0
    for p in files:
        try:
            res = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"INVALID JSON {p}: {e}")
            bad += 1
            continue
        probs = validate_result(res)
        if probs:
            bad += 1
            print(f"FAIL {p}: {probs[:3]}")
    print(f"validated {len(files)} result files under {d}: {len(files) - bad} ok, {bad} failed")
    return 0 if (files and bad == 0) else 2


if __name__ == "__main__":
    raise SystemExit(main())
