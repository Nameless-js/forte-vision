"""Evaluation protocol (Section 11): video-level, localization, classification, timing; train vs LOVO."""

from .metrics import (  # noqa: F401
    LOCALIZATION_TOLERANCES,
    PerVideo,
    compute_metrics,
    fit_threshold,
    lovo_evaluate,
    select_by_threshold,
)
