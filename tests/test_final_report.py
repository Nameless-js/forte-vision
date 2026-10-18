import json
from scripts.final_report import evaluate_gates

def test_empty_artifacts_never_pass(tmp_path):
    assert all(g["status"] != "PASSED" for g in evaluate_gates(tmp_path))

def test_local_wheel_is_not_docker_reproducibility(tmp_path):
    p = tmp_path / "packaging"
    p.mkdir()
    (p / "report.json").write_text(json.dumps({"ok": True}))
    gate = evaluate_gates(tmp_path)[8]
    assert gate["status"] == "NOT VERIFIED"

def test_bad_recall_fails_even_if_other_metrics_look_good(tmp_path):
    (tmp_path / "metrics.json").write_text(json.dumps({"lovo": {"tp": 21, "fn": 1, "fp": 0, "classification_accuracy": 1., "localization": {"within_2s": 1., "within_5s": 1.}}, "schema_problems": {}}))
    assert evaluate_gates(tmp_path)[0]["status"] == "UNMET"
