"""Worker process: owns the models, processes queued jobs sequentially, deletes uploads afterwards.

Run: python -m server.worker [--profile gpu-small] [--poll 1.0]
"""

from __future__ import annotations

import argparse
import logging
import os
import time
import traceback
from pathlib import Path

from . import db

log = logging.getLogger("forte_ai.worker")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=os.environ.get("FORTE_PROFILE"))
    ap.add_argument("--config", default=os.environ.get("FORTE_CONFIG"))
    ap.add_argument("--poll", type=float, default=1.0)
    ap.add_argument("--deadline", type=float, default=float(os.environ.get("FORTE_DEADLINE_S", "240")))
    ap.add_argument("--once", action="store_true", help="exit after the queue is empty (tests)")
    ap.add_argument("--max-jobs", type=int, default=0)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from forte_ai.analyzer import Analyzer

    an = Analyzer(config=a.config, profile=a.profile)
    log.info("worker ready (profile %s); warming up models", an.cfg.profile)
    try:
        log.info("warmup: %s", an.warmup())
    except Exception as e:  # noqa: BLE001
        log.warning("warmup failed: %s", e)
    Path("server").mkdir(exist_ok=True)
    (Path("server") / "worker.ready").write_text(str(time.time()))
    n_done = 0
    idle = 0
    while True:
        con = db.connect()
        try:
            db.requeue_stale(con)
            job = db.claim_next(con)
        finally:
            con.close()
        if job is None:
            idle += 1
            if a.once and idle > 3:
                break
            time.sleep(a.poll)
            continue
        idle = 0
        jid, path = job["job_id"], job["path"]
        log.info("job %s: %s", jid, path)

        def on_progress(frac: float, msg: str, _jid=jid):
            c = db.connect()
            try:
                db.set_progress(c, _jid, frac, msg)
            finally:
                c.close()

        try:
            res = an.analyze(path, on_progress=on_progress, deadline_sec=a.deadline, job_id=jid)
            con = db.connect()
            try:
                db.finish_job(con, jid, res)
            finally:
                con.close()
            log.info("job %s done: %s (%d violations) in %.1fs", jid, res["verdict"], len(res["violations"]), res["stage_timings"].get("total", 0))
        except Exception as e:  # noqa: BLE001
            log.error("job %s failed: %s\n%s", jid, e, traceback.format_exc())
            con = db.connect()
            try:
                db.fail_job(con, jid, f"{type(e).__name__}: {e}")
            finally:
                con.close()
        finally:
            try:  # data hygiene: the uploaded video is deleted after processing
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
        n_done += 1
        if a.max_jobs and n_done >= a.max_jobs:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
