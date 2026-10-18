"""Connect the web API to the repository's fully local, process-supervised engine."""
from contextvars import ContextVar
import os
from pathlib import Path
import threading

from forte_ai.supervisor import SupervisedAnalyzer

analysis_progress = ContextVar("analysis_progress", default=None)
_lock = threading.Lock()
_cancel = threading.Event()
_engine = None


def analyze_video(path: Path) -> dict:
    """Real inference; preserves evidence/timestamps and adapts deterministic citations for React."""
    global _engine
    with _lock:
        if _engine is None:
            _engine = SupervisedAnalyzer(
                config=os.environ.get("FORTE_CONFIG"),
                profile=os.environ.get("FORTE_PROFILE"),
                # Leave room for cleanup and saving the result before the web server's 270s budget.
                hard_timeout_s=250,
            )
        value = _engine.analyze(path, deadline_sec=240, on_progress=analysis_progress.get(), cancel_event=_cancel)
        events = []
        for original in value.get("violations", []):
            event = dict(original)
            if event.get("rule"):
                rule = event["rule"]
                event["rule"] = {**rule, "title": rule.get("document", rule.get("title", "")),
                                 "section": rule.get("clause", rule.get("section", ""))}
            events.append(event)
        return {**value, "violations": events,
                "duration_sec": value.get("video", {}).get("duration_s")}


def close_analyzer():
    """Signal the active supervisor to stop, then close it in its owning thread/lock."""
    global _engine
    _cancel.set()
    with _lock:
        if _engine is not None:
            _engine.close()
            _engine = None
        _cancel.clear()
