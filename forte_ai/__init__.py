"""forte_ai — fully local engine for detecting cash-desk discipline violations on video."""

__version__ = "0.1.0"

from .errors import AnalysisError  # noqa: F401

__all__ = ["AnalysisError", "__version__"]


def __getattr__(name):  # lazy import so that `forte_ai.labels` etc. work without torch
    if name == "Analyzer":
        from .analyzer import Analyzer

        return Analyzer
    raise AttributeError(name)
