from pathlib import Path

import pytest

from forte_ai.config import PROFILES, Config, deep_update

ROOT = Path(__file__).resolve().parents[1]


def test_deep_update_merges_nested():
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    deep_update(base, {"a": {"b": 10}, "e": 5})
    assert base == {"a": {"b": 10, "c": 2}, "d": 3, "e": 5}


@pytest.mark.parametrize("profile", PROFILES)
def test_profiles_load(profile):
    cfg = Config.load(profile=profile)
    assert cfg.profile == profile
    assert cfg.get("video.sample_fps") > 0
    assert cfg.get("time.deadline_s") <= cfg.get("time.hard_limit_s")
    assert cfg.get("time.vlm_cutoff_s") < cfg.get("time.deadline_s")
    if profile == "cpu":
        assert cfg.get("vlm.enabled") is False
        assert cfg.get("device") == "cpu"


def test_user_overrides_win():
    cfg = Config.load(config={"rules": {"counting_window_s": 99.0}}, profile="cpu", overrides={"seed": 7})
    assert cfg.get("rules.counting_window_s") == 99.0
    assert cfg.get("seed") == 7
    assert cfg.get("rules.unattended_cash_s") is not None  # defaults preserved


def test_user_config_file_beats_profile(tmp_path):
    p = tmp_path / "u.yaml"
    p.write_text("vlm:\n  model_id: some/other-model\n  load_in_4bit: true\n", encoding="utf-8")
    cfg = Config.load(config=str(p), profile="gpu-small")  # profile-gpu-small.yaml also sets vlm.model_id
    assert cfg.get("vlm.model_id") == "some/other-model"
    assert cfg.get("vlm.load_in_4bit") is True
    assert cfg.get("vlm.frames_per_query") is not None  # untouched profile/default keys survive


def test_unknown_profile_rejected():
    with pytest.raises(ValueError):
        Config.load(profile="tpu-huge")


def test_default_yaml_has_every_threshold_section():
    cfg = Config.load(profile="cpu")
    for key in ["video", "perception", "roles", "rules", "vlm", "verdict", "time", "cache"]:
        assert cfg.section(key), key
