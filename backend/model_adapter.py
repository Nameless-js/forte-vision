"""The only module the ML teammate needs to replace. No network AI calls."""
from pathlib import Path

def analyze_video(path: Path) -> dict:
    """Return {verdict, violations}. Each violation follows the jury schema.

    evidence_frames contains 1–3 JPEG base64 strings and timestamp_sec.
    Optional rule: {title, section, url}. Do not derive results from filenames.
    Optional checks: [{id, status, note, timestamp_sec?, translations?}].
    See docs/ML_HANDOFF.md for IDs, unknown semantics and the test bench.
    This function must return within the server's 270 second inference budget.
    """
    raise NotImplementedError("Локальная модель ещё не подключена. Реализуйте backend/model_adapter.py")
