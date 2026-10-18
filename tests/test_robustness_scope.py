import math
import pytest
from scripts.robustness import VARIANTS, full_scope, until_epoch

def test_missing_variants_are_never_full_coverage():
    assert full_scope(42, VARIANTS, 378)
    assert not full_scope(42, VARIANTS, 377)
    assert not full_scope(42, ["hflip"], 42)
    assert not full_scope(41, VARIANTS, 369)

def test_timestamp_requires_timezone():
    assert math.isinf(until_epoch(None))
    assert until_epoch("2026-10-18T07:00:00+00:00") == until_epoch("2026-10-18T12:00:00+05:00")
    with pytest.raises(ValueError, match="explicit UTC offset"):
        until_epoch("2026-10-18T12:00:00")
