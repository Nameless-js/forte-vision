"""Build data/labels.csv from open/open_labels.xlsx and public/*.mov.

Usage: python scripts/build_labels.py [--xlsx open/open_labels.xlsx] [--videos public] [--out data/labels.csv]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forte_ai.labels import (  # noqa: E402
    build_label_rows,
    index_videos,
    lovo_groups,
    read_labels_xlsx,
    write_labels_csv,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=str(ROOT / "open" / "open_labels.xlsx"))
    ap.add_argument("--videos", default=str(ROOT / "public"))
    ap.add_argument("--out", default=str(ROOT / "data" / "labels.csv"))
    ap.add_argument("--no-md5", action="store_true")
    a = ap.parse_args()

    raw = read_labels_xlsx(Path(a.xlsx))
    videos = index_videos(Path(a.videos))
    rows = build_label_rows(raw, videos, ROOT, with_md5=not a.no_md5)
    write_labels_csv(rows, Path(a.out))

    labeled = [r for r in rows if r.split == "labeled"]
    c = Counter(r.label for r in labeled)
    missing = [r.video_id for r in labeled if not r.path]
    print(
        f"wrote {a.out}: {len(rows)} rows ({len(labeled)} labeled: {dict(c)}; "
        f"{len(rows) - len(labeled)} unlabeled)"
    )
    print(f"label rows without a video file: {missing or 'none'}")
    groups = lovo_groups(rows)
    dups = {k[:8]: v for k, v in groups.items() if len(v) > 1}
    print(f"LOVO groups: {len(groups)}; duplicate-content groups: {dups or 'none'}")
    for r in rows:
        t = "-" if r.t_sec is None else f"{r.t_sec:g}"
        print(f"  {r.video_id:>3} {r.label or '-':<13} t={t:<6} {r.path}  [{r.raw_timestamp}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
