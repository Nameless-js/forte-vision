"""Compare real package and CLI outputs, including evidence, for the same positive video."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    from forte_ai import Analyzer
    from forte_ai.labels import read_labels_csv
    from forte_ai.schema import validate_result
    out = ROOT / "reports" / "final" / "api_test"
    out.mkdir(parents=True, exist_ok=True)
    row = next(r for r in read_labels_csv(ROOT / "data" / "labels.csv") if r.video_id == 4)
    video = ROOT / row.path
    analyzer = Analyzer()
    try:
        direct = analyzer.analyze(video)
    finally:
        analyzer.close()
    path = out / "cli_result.json"
    subprocess.run([sys.executable, "-m", "forte_ai", "analyze", str(video), "--out", str(path)], cwd=ROOT, check=True)
    cli = json.loads(path.read_text(encoding="utf-8"))
    problems = validate_result(direct) + validate_result(cli)
    same = all(direct[k] == cli[k] for k in ("verdict", "violations"))
    report = {"ok": same and not problems and bool(direct["violations"]), "video_id": row.video_id, "verdict": direct["verdict"], "n_violations": len(direct["violations"]), "comparison": "verdict and full violations including evidence JPEGs; excludes job IDs, timings and cache counters", "schema_problems": problems}
    (out / "equivalence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
