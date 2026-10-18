import time
import pytest
from forte_ai.errors import AnalysisError
from forte_ai.supervisor import SupervisedAnalyzer

class FakeAnalyzer:
    def __init__(self, **kwargs):
        self.n = 0
    def analyze(self, path, on_progress=None, **kwargs):
        if path == "hang":
            time.sleep(60)
        if path == "bad":
            raise ValueError("bad video")
        self.n += 1
        on_progress(0.5, "working")
        return {"n": self.n}


def test_persistent_process_progress_timeout_and_recovery():
    runner = SupervisedAnalyzer(factory=FakeAnalyzer, hard_timeout_s=15)
    seen = []
    try:
        assert runner.analyze("ok", on_progress=lambda *x: seen.append(x)) == {"n": 1}
        assert runner.analyze("ok") == {"n": 2}
        assert seen == [(0.5, "working")]
        runner.hard_timeout_s = 0.3
        start = time.monotonic()
        with pytest.raises(TimeoutError, match="process stopped"):
            runner.analyze("hang")
        assert time.monotonic() - start < 6
        assert runner.process is None
        runner.hard_timeout_s = 15
        assert runner.analyze("ok") == {"n": 1}
        with pytest.raises(AnalysisError, match="bad video"):
            runner.analyze("bad")
        assert runner.process is None
    finally:
        runner.close()

@pytest.mark.parametrize("limit", [0, -1, 300])
def test_invalid_timeout(limit):
    with pytest.raises(ValueError):
        SupervisedAnalyzer(hard_timeout_s=limit)


def test_cancel_stops_active_process_and_allows_restart():
    import threading
    runner = SupervisedAnalyzer(factory=FakeAnalyzer, hard_timeout_s=15)
    cancelled = threading.Event()
    try:
        runner.analyze("ok")
        timer = threading.Timer(.2, cancelled.set)
        timer.start()
        started = time.monotonic()
        with pytest.raises(AnalysisError, match="cancelled"):
            runner.analyze("hang", cancel_event=cancelled)
        timer.join()
        assert time.monotonic() - started < 6
        assert runner.process is None
        assert runner.analyze("ok") == {"n": 1}
    finally:
        runner.close()
