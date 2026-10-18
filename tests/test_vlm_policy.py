from types import SimpleNamespace
import pytest
from forte_ai.analyzer import Analyzer
from forte_ai.config import Config
from forte_ai.report import Candidate

@pytest.mark.parametrize("enabled", [True, False])
def test_choice_mode_respects_explicit_catch_all_setting(enabled):
    analyzer = object.__new__(Analyzer)
    analyzer.cfg = Config({"vlm": {"mode": "choice", "catch_all": {"enabled": enabled}}})
    analyzer._ensure_vlm = lambda: True
    analyzer._roi = lambda *args: None
    analyzer._vlm_choice_stage = lambda *args: []
    sentinel = object()
    analyzer._catch_all = lambda *args: [sentinel]
    result = analyzer._vlm_stage(None, None, None, None, [], [], SimpleNamespace(vlm_allowed=lambda: True), {}, None)
    assert result == ([sentinel] if enabled else [])

@pytest.mark.parametrize("answer, eligible", [
    (None, False),
    ({"mode":"choice", "p_violation":.6}, True),
    ({"mode":"choice", "p_violation":.4}, False),
    ({"verdict":"support", "answer":{"confidence":.8}}, True),
    ({"verdict":"support", "answer":{"confidence":.2}}, False),
    ({"verdict":"reject", "answer":{"confidence":.9}}, False),
])
def test_support_requirement_applies_in_both_verifier_modes(answer, eligible):
    candidate = Candidate("cash_left_unattended", 1., (0., 2.), .8, needs_support=True, vlm=answer)
    assert candidate.eligible is eligible
