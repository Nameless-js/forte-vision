"""The engine entry point: Analyzer(device, config).analyze(video) -> ТЗ result dict (+ engine extras)."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from . import __version__
from .config import Config
from .errors import AnalysisError
from .events.primitives import build_frame_states
from .events.rules import run_rules, select_violations
from .kb import KnowledgeBase
from .perception.pipeline import PerceptionEngine, PerceptionResult
from .perception.roles import Calibration, calibrate
from .report import Candidate, build_result
from .video import frame_at, probe

log = logging.getLogger(__name__)
ProgressCb = Optional[Callable[[float, str], None]]


class Deadline:
    def __init__(self, deadline_s: float, vlm_cutoff_s: float, hard_limit_s: float):
        self.t0 = time.time()
        self.deadline_s = float(deadline_s)
        self.vlm_cutoff_s = float(vlm_cutoff_s)
        self.hard_limit_s = float(hard_limit_s)

    def elapsed(self) -> float:
        return time.time() - self.t0

    def remaining(self) -> float:
        return self.deadline_s - self.elapsed()

    def vlm_allowed(self, est_call_s: float = 6.0) -> bool:
        return self.elapsed() + est_call_s < self.vlm_cutoff_s


class Analyzer:
    """Loads all models once; analyze() is safe for sequential calls from several threads (serialised by a lock)."""

    def __init__(self, device: str = "auto", config: Optional[str | dict] = None, profile: Optional[str] = None, kb_dir: Optional[str] = None):
        overrides = {"device": device} if device not in (None, "auto") else None
        self.cfg = Config.load(config=config, profile=profile, overrides=overrides)
        self.kb = KnowledgeBase(Path(kb_dir) if kb_dir else None)
        self._seed(int(self.cfg.get("seed", 42)))
        self.perception = PerceptionEngine(self.cfg)
        self.vlm = None
        if bool(self.cfg.get("vlm.enabled", False)) and self.cfg.get("device") != "cpu":
            from .vlm.verifier import VLMVerifier

            self.vlm = VLMVerifier(self.cfg.section("vlm"), Path(self.cfg.get("cache.dir", "data/cache")), self.cfg.get("device", "cuda"))
        self._lock = threading.Lock()
        self.engine_version = __version__

    @staticmethod
    def _seed(seed: int) -> None:
        import random

        random.seed(seed)
        np.random.seed(seed)
        try:
            import torch

            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        except Exception:
            pass

    # ------------------------------------------------------------------ lifecycle
    def warmup(self) -> dict:
        """Load every model now (so that the first analyze() call is not slower)."""
        t0 = time.time()
        self.perception.ensure_models()
        if self.vlm is not None:
            self._ensure_vlm()
        return {"warmup_s": round(time.time() - t0, 1)}

    def close(self) -> None:
        self.perception.unload()
        if self.vlm is not None:
            self.vlm.unload()

    def _ensure_vlm(self) -> bool:
        """Load the VLM; if VRAM is short, free the detector first (it is reloaded lazily next time)."""
        if self.vlm is None:
            return False
        if self.vlm.model is not None:
            return True
        try:
            import torch

            if torch.cuda.is_available():
                free, total = torch.cuda.mem_get_info()
                need = float(self.cfg.get("vlm.min_free_vram_gb", 5.0)) * 1e9
                if free < need:
                    log.info("freeing perception models before loading the VLM (free %.1f GB)", free / 1e9)
                    self.perception.unload()
            self.vlm.load()
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("VLM unavailable (%s); continuing with rule-based results", e)
            try:
                self.vlm.unload()
            except Exception:
                pass
            return False

    # ------------------------------------------------------------------ main
    def analyze(self, video_path: str | Path, on_progress: ProgressCb = None, deadline_sec: Optional[float] = None, job_id: Optional[str] = None, use_cache: bool = True, collect_all: bool = False) -> dict:
        with self._lock:
            return self._analyze(Path(video_path), on_progress, deadline_sec, job_id, use_cache, collect_all)

    def _progress(self, cb: ProgressCb, frac: float, msg: str) -> None:
        if cb:
            try:
                cb(float(max(0.0, min(1.0, frac))), msg)
            except Exception:  # the UI callback must never break the analysis
                pass

    def _analyze(self, video_path: Path, cb: ProgressCb, deadline_sec, job_id, use_cache: bool, collect_all: bool) -> dict:
        cfg = self.cfg
        tcfg = cfg.section("time")
        dl = Deadline(deadline_sec or tcfg.get("deadline_s", 240), tcfg.get("vlm_cutoff_s", 200), tcfg.get("hard_limit_s", 300))
        timings: dict[str, float] = {}
        job_id = job_id or uuid.uuid4().hex[:8]
        if not video_path.exists():
            raise AnalysisError(f"video not found: {video_path}")

        # ---- 1. probe
        t = time.time()
        self._progress(cb, 0.01, "Открытие видео")
        info = probe(video_path)
        if info.duration_s <= 0:
            raise AnalysisError("video has zero duration or cannot be decoded")
        timings["probe"] = time.time() - t

        # ---- 2. perception (Layer A)
        t = time.time()
        w = cfg.get("time.progress_stage_weights", {}) or {}
        w_dec = float(w.get("decode", 0.05)) + float(w.get("detect", 0.45)) + float(w.get("track_pose", 0.15))
        pr: PerceptionResult = self.perception.run(video_path, on_progress=lambda f, m: self._progress(cb, 0.02 + w_dec * f, m), use_cache=use_cache, info=info)
        timings["perception"] = time.time() - t
        for k, v in pr.timings.items():
            timings[f"perception.{k}"] = round(float(v), 3)

        # ---- 3. roles / zones
        t = time.time()
        self._progress(cb, 0.68, "Определение ролей и зон")
        cal: Calibration = calibrate(pr.frames, pr.poses, pr.tracks, pr.per_frame_tracks, cfg.section("roles"), pr.det_width, pr.det_height)
        timings["roles"] = time.time() - t

        # ---- 4. primitives + rules (Layer B)
        t = time.time()
        self._progress(cb, 0.72, "Поиск событий по правилам")
        prim_cfg = dict(cfg.section("roles"))
        prim_cfg.update(cfg.section("rules"))
        prim_cfg["kpt_threshold"] = cfg.get("perception.pose.kpt_threshold", 0.3)
        states = build_frame_states(pr, cal, prim_cfg)
        rule_cfg = dict(cfg.section("rules"))
        rule_cfg.setdefault("counter_margin_frac", cfg.get("roles.counter_margin_frac", 0.06))
        candidates, events = run_rules(states, cal, rule_cfg, pr.sample_fps, info.duration_s)
        if bool(cfg.get("rules.laptop_probe", True)):
            self._refine_departures(video_path, pr, candidates, info.duration_s)
        timings["rules"] = time.time() - t
        for c in candidates:
            c.annotate = self._annotation_for(c, cal, states, pr)

        # ---- 5. VLM verification + catch-all (Layer C)
        vlm_info = {"enabled": self.vlm is not None, "calls": 0, "cached": 0, "skipped_deadline": 0, "rejected": [], "catch_all_hits": []}
        if self.vlm is not None and bool(cfg.get("vlm.verify_candidates", True)) and (candidates or bool(cfg.get("vlm.catch_all.enabled", False))):
            t = time.time()
            self._progress(cb, 0.78, "Проверка событий визуально-языковой моделью")
            candidates = self._vlm_stage(video_path, info, pr, cal, states, candidates, dl, vlm_info, cb)
            timings["vlm"] = time.time() - t

        # ---- 6. verdict + report
        t = time.time()
        self._progress(cb, 0.93, "Формирование отчёта")
        vcfg = cfg.section("verdict")
        chosen = select_violations(candidates, float(vcfg.get("threshold", 0.5)), vcfg.get("per_type_thresholds", {}), int(cfg.get("rules.max_violations_per_video", 6)))
        if chosen and self.vlm is not None and str(cfg.get("vlm.mode", "json")) == "choice":
            self._describe_chosen(video_path, info, pr, cal, chosen, dl, vlm_info)
        extras = {
            "engine_version": self.engine_version,
            "profile": cfg.profile,
            "video": {"path": str(video_path.name), "duration_s": round(info.duration_s, 3), "fps": round(info.fps, 3), "width": info.width, "height": info.height, "content_md5": info.content_md5},
            "calibration": cal.to_dict(),
            "events": events.to_dict(),
            "vlm": vlm_info,
            "models": {"detector": cfg.get("perception.detector.model_id"), "pose": f"rtmlib/{cfg.get('perception.pose.mode')}", "vlm": cfg.get("vlm.model_id") if self.vlm is not None else None},
        }
        if collect_all:
            extras["candidates_all"] = [
                {"type_id": c.type_id, "t_event": round(c.t_event, 2), "t_window": [round(c.t_window[0], 2), round(c.t_window[1], 2)], "confidence": round(c.confidence, 3), "facts": c.facts, "source": c.source, "vlm": c.vlm, "rule_id": c.rule_id}
                for c in sorted(candidates, key=lambda c: c.t_event)
            ]
        rep_cfg = {"evidence_frames": vcfg.get("evidence_frames", 3), "evidence_jpeg_quality": cfg.get("video.evidence_jpeg_quality", 85), "evidence_max_width": cfg.get("video.evidence_max_width", 1280)}
        result = build_result(video_path, chosen, self.kb, rep_cfg, extras, job_id=job_id, scale=pr.scale)
        timings["report"] = time.time() - t
        timings["total"] = dl.elapsed()
        result["stage_timings"] = {k: round(float(v), 3) for k, v in timings.items()}
        result["deadline"] = {"deadline_s": dl.deadline_s, "vlm_cutoff_s": dl.vlm_cutoff_s, "elapsed_s": round(dl.elapsed(), 2), "within_deadline": dl.elapsed() <= dl.deadline_s}
        self._progress(cb, 1.0, "Готово")
        return result

    # ------------------------------------------------------------------ VLM stage
    def _vlm_stage(self, video_path: Path, info, pr, cal, states, candidates: list[Candidate], dl: Deadline, vlm_info: dict, cb: ProgressCb) -> list[Candidate]:
        from .vlm import prompts as P
        from .vlm.verifier import judge

        if not dl.vlm_allowed():
            vlm_info["skipped_deadline"] += 1
            return candidates
        if not self._ensure_vlm():
            return candidates
        vcfg = self.cfg.section("vlm")
        half = float(vcfg.get("window_half_s", 4.0))
        reject_below = float(vcfg.get("reject_below_confidence", 0.35))
        roi = self._roi(cal, pr)
        getter = lambda t: (lambda f: None if f is None else f.image)(frame_at(video_path, t))  # noqa: E731
        kept: list[Candidate] = []
        est_call = float(vcfg.get("est_call_s", 6.0))
        mode = str(vcfg.get("mode", "json"))
        if mode == "choice":
            return self._vlm_choice_stage(video_path, info, roi, getter, candidates, dl, vlm_info, cb, vcfg, half)
        for i, c in enumerate(sorted(candidates, key=lambda c: -c.confidence)):
            if not dl.vlm_allowed(est_call):
                vlm_info["skipped_deadline"] += 1
                kept.append(c)
                continue
            t0, t1 = max(0.0, c.t_event - half), min(info.duration_s, c.t_event + half)
            frames = self.vlm.frames_for_window(getter, t0, t1, roi)
            card = self.kb.get(c.type_id)
            prompt = P.verify_prompt(c.type_id, card.name_ru, c.facts, c.t_event, (t0, t1), question=c.vlm_question)
            ans, raw, cached = self.vlm.ask_json(info.content_md5, f"verify:{c.type_id}:{c.t_event:.1f}", frames, prompt, P.VERIFY_SCHEMA_KEYS)
            vlm_info["calls"] += 1
            vlm_info["cached"] += int(cached)
            verdict, delta = judge(c.type_id, ans, reject_below, expect=c.vlm_expect)
            c.vlm = {"verdict": verdict, "answer": ans}
            if ans and ans.get("what_is_visible_ru"):
                c.description_ru = f"На {c.t_event:.1f} с: {ans['what_is_visible_ru']}".replace(".0 с", " с")
            c.confidence = float(max(0.0, min(1.0, c.confidence + delta)))
            if verdict == "reject":
                vlm_info["rejected"].append({"type_id": c.type_id, "t_event": round(c.t_event, 2), "answer": ans})
            kept.append(c)
            self._progress(cb, 0.78 + 0.12 * (i + 1) / max(1, len(candidates)), f"Проверка события {i + 1} из {len(candidates)}")
        # conservative catch-all pass over 10 s windows
        ccfg = vcfg.get("catch_all", {}) or {}
        if bool(ccfg.get("enabled", False)):
            kept.extend(self._catch_all(video_path, info, roi, getter, states, cal, kept, dl, vlm_info, ccfg))
        return kept

    def _vlm_choice_stage(self, video_path, info, roi, getter, candidates: list[Candidate], dl: Deadline, vlm_info: dict, cb: ProgressCb, vcfg: dict, half: float) -> list[Candidate]:
        """Contrastive verification: P(violation statement | frames) from first-token logits, averaged over both
        option orders. Moves each candidate's confidence by w·(2p−1); never creates candidates."""
        from .vlm import prompts as P

        w = float(vcfg.get("choice_weight", 0.35))
        est_call = float(vcfg.get("est_choice_s", 4.0))
        n_frames = int(vcfg.get("frames_per_query", 6))
        order = sorted(candidates, key=lambda c: -c.confidence)
        for i, c in enumerate(order):
            pair = c.vlm_choice or P.CHOICE_STATEMENTS_RU.get(c.type_id)
            if pair is None:
                continue
            if not dl.vlm_allowed(est_call):
                vlm_info["skipped_deadline"] += 1
                continue
            if c.vlm_window:
                t0, t1 = max(0.0, c.vlm_window[0]), min(info.duration_s, c.vlm_window[1])
            else:
                t0, t1 = max(0.0, c.t_event - half), min(info.duration_s, c.t_event + half)
            if t1 - t0 < 1.0:
                t0, t1 = max(0.0, c.t_event - half), min(info.duration_s, c.t_event + half)
            frames = self.vlm.frames_for_window(getter, t0, t1, roi, n=n_frames)
            if not frames:
                continue
            p_v, cached = self.vlm.choice_score(info.content_md5, f"{c.type_id}:{c.rule_id}:{c.t_event:.1f}", frames, "", pair[0], pair[1])
            vlm_info["calls"] += 0 if cached else 2
            vlm_info["cached"] += int(cached)
            if p_v is None:
                continue
            delta = w * (2.0 * p_v - 1.0)
            c.confidence = float(max(0.0, min(1.0, c.confidence + delta)))
            c.vlm = {"mode": "choice", "p_violation": round(float(p_v), 3), "delta": round(delta, 3), "window": [round(t0, 1), round(t1, 1)]}
            if p_v < 0.5:
                vlm_info["rejected"].append({"type_id": c.type_id, "t_event": round(c.t_event, 2), "p_violation": round(float(p_v), 3)})
            self._progress(cb, 0.78 + 0.12 * (i + 1) / max(1, len(order)), f"Проверка события {i + 1} из {len(order)}")
        return candidates

    def _describe_chosen(self, video_path: Path, info, pr, cal, chosen: list[Candidate], dl: Deadline, vlm_info: dict) -> None:
        """Neutral Russian 'what is visible' text for the reported violations only (bounded by the watchdog)."""
        if self.vlm is None or self.vlm.model is None or not bool(self.cfg.get("vlm.describe", True)):
            return
        from .vlm import prompts as P

        half = float(self.cfg.get("vlm.window_half_s", 4.0))
        roi = self._roi(cal, pr)
        getter = lambda t: (lambda f: None if f is None else f.image)(frame_at(video_path, t))  # noqa: E731
        for c in chosen:
            if not dl.vlm_allowed(float(self.cfg.get("vlm.est_describe_s", 7.0))):
                vlm_info["skipped_deadline"] += 1
                break
            t0, t1 = max(0.0, c.t_event - half), min(info.duration_s, c.t_event + half)
            frames = self.vlm.frames_for_window(getter, t0, t1, roi, n=int(self.cfg.get("vlm.frames_per_query", 6)))
            try:
                txt, cached = self.vlm.describe(info.content_md5, f"{c.type_id}:{c.t_event:.1f}", frames, P.DESCRIBE_PROMPT_RU)
            except Exception as e:  # noqa: BLE001
                log.warning("describe failed: %s", e)
                continue
            vlm_info["calls"] += 0 if cached else 1
            vlm_info["cached"] += int(cached)
            if txt and any("Ѐ" <= ch <= "ӿ" for ch in txt):
                c.description_ru = f"На {c.t_event:.1f} с (окно {t0:.0f}–{t1:.0f} с): {txt}".replace(".0 с", " с")

    def _catch_all(self, video_path, info, roi, getter, states, cal, existing: list[Candidate], dl: Deadline, vlm_info: dict, ccfg: dict) -> list[Candidate]:
        from .vlm import prompts as P

        win = float(ccfg.get("window_s", 10.0))
        stride = float(ccfg.get("stride_s", 10.0))
        max_w = int(ccfg.get("max_windows", 12))
        min_rep = int(ccfg.get("min_repeats", 2))
        conf0 = float(ccfg.get("confidence", 0.55))
        # only windows where somebody besides the cashier is present (service happening) are asked
        starts = [s for s in np.arange(0.0, max(0.0, info.duration_s - 1.0), stride)][:max_w]
        hits = []
        for t0 in starts:
            if not dl.vlm_allowed():
                vlm_info["skipped_deadline"] += 1
                break
            t1 = min(info.duration_s, t0 + win)
            busy = any(s.client_ids for s in states if t0 <= s.t <= t1)
            if not busy:
                hits.append(None)
                continue
            frames = self.vlm.frames_for_window(getter, t0, t1, roi)
            ans, raw, cached = self.vlm.ask_json(info.content_md5, f"catchall:{t0:.1f}", frames, P.catch_all_prompt(t0, t1), ["deviation", "deviation_type", "what_is_visible_ru", "confidence"])
            vlm_info["calls"] += 1
            vlm_info["cached"] += int(cached)
            hits.append((t0, t1, ans) if ans and ans.get("deviation") == "yes" and ans.get("deviation_type") not in ("none",) else None)
        out: list[Candidate] = []
        type_map = {"cashier_left": "cashier_left_during_service", "phone": "phone_at_workplace", "unauthorized_person": "unauthorized_in_cash_zone", "cash_unattended": "cash_left_unattended", "no_count": "issue_without_count", "no_id": "no_id_check", "bag_unchecked": "collection_bag_unchecked", "other": "protocol_deviation_other"}
        for i in range(len(hits) - min_rep + 1):
            group = hits[i : i + min_rep]
            if all(g is not None for g in group) and len({g[2].get("deviation_type") for g in group}) == 1:
                t0, t1, ans = group[0]
                tid = type_map.get(ans.get("deviation_type"), "protocol_deviation_other")
                # Layer A must not contradict: e.g. "cashier_left" requires the cashier to be absent in that window
                if tid == "cashier_left_during_service" and all(s.cashier_present and s.cashier_in_zone for s in states if t0 <= s.t <= group[-1][1]):
                    continue
                if any(abs(e.t_event - (t0 + t1) / 2) < win and e.type_id == tid for e in existing):
                    continue  # already covered by a rule candidate
                c = Candidate(tid, round((t0 + t1) / 2, 1), (t0, group[-1][1]), conf0 * max(0.5, float(ans.get("confidence", 0.5))), [f"VLM: отклонение на окнах {t0:.0f}–{group[-1][1]:.0f} с"], source="vlm_catch_all", description_ru=f"На {t0:.0f}–{t1:.0f} с: {ans.get('what_is_visible_ru', '')}")
                c.vlm = {"verdict": "catch_all", "answer": ans}
                vlm_info["catch_all_hits"].append({"type_id": tid, "t0": t0, "t1": group[-1][1]})
                out.append(c)
        return out

    # ------------------------------------------------------------------ evidence probes (pixel checks)
    def _laptop_screen_state(self, video_path: Path, pr, t_dep: float, duration: float) -> Optional[str]:
        """'stays_on' | 'turned_off' | 'never_on' | None. Brightness of the upper part of the (static) laptop
        box sampled before and after a departure: an unlocked screen left lit in an empty room vs a
        workstation locked/closed before leaving."""
        import cv2

        boxes = [d.xyxy for f in pr.frames for d in f.by_class("laptop")]
        if len(boxes) < max(5, 0.2 * len(pr.frames)):
            return None
        b = np.median(np.asarray(boxes), axis=0) / (pr.scale or 1.0)
        x1, y1, x2, y2 = [int(round(v)) for v in b]
        w, h = x2 - x1, y2 - y1
        if w < 12 or h < 12:
            return None
        sx1, sx2, sy1, sy2 = x1 + int(0.12 * w), x2 - int(0.12 * w), y1 + int(0.08 * h), y1 + int(0.55 * h)
        thr_v = int(self.cfg.get("rules.laptop_bright_v", 170))

        def bright_at(t: float) -> Optional[float]:
            fr = frame_at(video_path, max(0.0, min(duration - 0.05, t)))
            if fr is None:
                return None
            roi = fr.image[max(0, sy1):sy2, max(0, sx1):sx2]
            if roi.size == 0:
                return None
            v = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[..., 2]
            return float(np.mean(v > thr_v))

        before = [x for x in (bright_at(t_dep - d) for d in (14.0, 10.0, 6.0)) if x is not None]
        after = [x for x in (bright_at(t) for t in (t_dep + 2.0, t_dep + 4.0, duration - 0.3)) if x is not None and True]
        if not before or not after:
            return None
        on = float(self.cfg.get("rules.laptop_on_frac", 0.20))
        off = float(self.cfg.get("rules.laptop_off_frac", 0.10))
        was_on, still_on, now_off = max(before) >= on, min(after) >= on, max(after) <= off
        if was_on and still_on:
            return "stays_on"
        if was_on and now_off:
            return "turned_off"
        if not was_on and max(after) <= off:
            return "never_on"
        return None

    def _refine_departures(self, video_path: Path, pr, candidates: list[Candidate], duration: float) -> None:
        boost = float(self.cfg.get("rules.laptop_stays_on_boost", 0.15))
        pen = float(self.cfg.get("rules.laptop_turned_off_penalty", 0.20))
        for c in candidates:
            if c.rule_id not in ("R1b", "R1c") or c.type_id != "workplace_left_unsecured":
                continue
            try:
                state = self._laptop_screen_state(video_path, pr, c.t_event, duration)
            except Exception as e:  # noqa: BLE001
                log.warning("laptop probe failed: %s", e)
                state = None
            if state == "stays_on":
                c.confidence = min(1.0, c.confidence + boost)
                c.facts.append("экран ноутбука остаётся включённым (не заблокирован) после ухода кассира")
            elif state == "turned_off":
                c.confidence = max(0.0, c.confidence - pen)
                c.facts.append("перед уходом экран ноутбука погашен/заблокирован")

    # ------------------------------------------------------------------ drawing helpers
    @staticmethod
    def _roi(cal: Calibration, pr) -> Optional[tuple[float, float, float, float]]:
        """Attention region in original pixels: cashier hull + landmarks + the counter neighbourhood."""
        pts = list(cal.cashier_hull)
        for v in cal.workplace_objects.values():
            pts.append(v)
        for tid in cal.client_tracks:
            st = pr.tracks.get(tid)
            if st is not None and st.boxes:
                b = np.asarray(st.boxes)
                pts.append((float(np.median(b[:, 0])), float(np.median(b[:, 1]))))
                pts.append((float(np.median(b[:, 2])), float(np.median(b[:, 3]))))
        if len(pts) < 2:
            return None
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        s = 1.0 / pr.scale if pr.scale else 1.0
        return (min(xs) * s, min(ys) * s, max(xs) * s, max(ys) * s)

    @staticmethod
    def _annotation_for(c: Candidate, cal: Calibration, states, pr) -> dict:
        k = int(np.argmin([abs(s.t - c.t_event) for s in states])) if states else None
        ann: dict = {"boxes": {}, "points": [], "zone": cal.cashier_hull, "text": f"t={c.t_event:.1f}s {c.type_id}"}
        if k is None:
            return ann
        s = states[k]
        if s.cashier_box:
            ann["boxes"]["cashier"] = s.cashier_box
        assigned = pr.per_frame_tracks[k]
        for tid in s.client_ids:
            if tid in assigned:
                ann["boxes"][f"client#{tid}"] = assigned[tid]
        for d in s.cash[:3]:
            ann["boxes"][f"cash#{round(d.score, 2)}"] = d.xyxy
        for d in pr.frames[k].by_class("phone")[:1]:
            ann["boxes"]["phone"] = d.xyxy
        for d in pr.frames[k].by_class("bag")[:1]:
            ann["boxes"]["bag"] = d.xyxy
        ann["points"] = list(s.cashier_hands) + [h for hs in s.client_hands.values() for h in hs]
        # counter line segment through the counter point, perpendicular to the normal
        nx, ny = cal.counter_normal
        px, py = cal.counter_point
        L = 0.4 * cal.diag
        ann["counter"] = ((px - ny * L, py + nx * L), (px + ny * L, py - nx * L))
        return ann
