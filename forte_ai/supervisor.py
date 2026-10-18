"""Persistent spawned inference process with a parent-enforced wall-clock timeout.

Use this boundary for untrusted uploads: Python threads cannot interrupt a hung CUDA call.
A timed-out analysis fails explicitly; it never becomes a clean-video verdict.
"""
from __future__ import annotations

import multiprocessing as mp
import time
from .errors import AnalysisError


def _serve(conn, config, profile, factory):
    try:
        if factory is None:
            from .analyzer import Analyzer
            factory = Analyzer
        analyzer = factory(config=config, profile=profile)
        while True:
            request = conn.recv()
            if request is None:
                break
            path, kwargs = request
            def progress(fraction, message):
                conn.send(("progress", (fraction, message)))
            try:
                result = analyzer.analyze(path, on_progress=progress, **kwargs)
                conn.send(("result", result))
            except Exception as exc:
                conn.send(("error", f"{type(exc).__name__}: {exc}"))
    except (EOFError, BrokenPipeError):
        pass
    except Exception as exc:
        try:
            conn.send(("error", f"{type(exc).__name__}: {exc}"))
        except (OSError, EOFError):
            pass
    finally:
        conn.close()


class SupervisedAnalyzer:
    """Sequential API, persistent weights; timeout covers child startup and inference.

    Not thread-safe: one instance belongs to one queue worker. Direct Analyzer remains
    available for trusted batch evaluation without process overhead.
    """
    def __init__(self, config=None, profile=None, hard_timeout_s=270.0, factory=None):
        if not 0 < float(hard_timeout_s) < 300:
            raise ValueError("hard_timeout_s must be between 0 and 300 seconds")
        self.config, self.profile = config, profile
        self.hard_timeout_s = float(hard_timeout_s)
        self.factory = factory
        self.process = None
        self.conn = None

    def _start(self):
        context = mp.get_context("spawn")
        self.conn, child = context.Pipe()
        self.process = context.Process(target=_serve, args=(child, self.config, self.profile, self.factory), daemon=True)
        self.process.start()
        child.close()

    def close(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=2)
            self.process.close()
            self.process = None
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def analyze(self, video_path, on_progress=None, cancel_event=None, **kwargs):
        started = time.monotonic()
        if self.process is None:
            self._start()
        try:
            self.conn.send((str(video_path), kwargs))
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise AnalysisError("analysis cancelled")
                remaining = self.hard_timeout_s - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError(f"analysis exceeded {self.hard_timeout_s:g} seconds; inference process stopped")
                if self.conn.poll(min(remaining, 0.1)):
                    kind, value = self.conn.recv()
                    if kind == "result":
                        return value
                    if kind == "error":
                        raise AnalysisError(value)
                    if kind == "progress" and on_progress is not None:
                        try:
                            on_progress(*value)
                        except Exception:
                            pass
                elif not self.process.is_alive():
                    raise AnalysisError(f"inference process exited with code {self.process.exitcode}")
        except TimeoutError:
            self.close()
            raise
        except (EOFError, BrokenPipeError, OSError) as exc:
            self.close()
            raise AnalysisError(f"inference process connection failed: {exc}") from exc
        except BaseException:
            self.close()
            raise
