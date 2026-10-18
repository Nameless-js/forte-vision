"""Qwen3-VL verifier/describer served locally with `transformers` (greedy decoding, strict JSON, cached)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

from ..models_util import resolve_model_path
from . import prompts as P

log = logging.getLogger(__name__)

_JSON_RE = re.compile(r"\{.*\}", re.S)


def extract_json(text: str) -> Optional[dict]:
    m = _JSON_RE.search(text or "")
    if not m:
        return None
    s = m.group(0)
    for cand in (s, s.replace("'", '"')):
        try:
            d = json.loads(cand)
            return d if isinstance(d, dict) else None
        except Exception:
            continue
    # trim trailing garbage after the last closing brace
    try:
        return json.loads(s[: s.rfind("}") + 1])
    except Exception:
        return None


def normalize_answer(d: dict, keys: list[str]) -> dict:
    out = {}
    for k in keys:
        v = d.get(k, "unclear")
        if k == "confidence":
            try:
                out[k] = float(max(0.0, min(1.0, float(v))))
            except Exception:
                out[k] = 0.0
        elif k == "what_is_visible_ru":
            out[k] = str(v).strip() if v is not None else ""
        else:
            out[k] = str(v).strip().lower() if v is not None else "unclear"
    return out


def burn_timestamp(img: np.ndarray, t: float) -> np.ndarray:
    out = img.copy()
    label = f"t={t:.1f}s"
    cv2.rectangle(out, (0, 0), (12 * len(label) + 10, 26), (0, 0, 0), -1)
    cv2.putText(out, label, (5, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def crop_roi(img: np.ndarray, roi: Optional[tuple[float, float, float, float]], margin: float = 0.12) -> np.ndarray:
    if roi is None:
        return img
    h, w = img.shape[:2]
    x1, y1, x2, y2 = roi
    mw, mh = (x2 - x1) * margin, (y2 - y1) * margin
    x1, y1 = int(max(0, x1 - mw)), int(max(0, y1 - mh))
    x2, y2 = int(min(w, x2 + mw)), int(min(h, y2 + mh))
    if x2 - x1 < 64 or y2 - y1 < 64:
        return img
    return img[y1:y2, x1:x2]


def fit_pixels(img: np.ndarray, max_pixels: int) -> np.ndarray:
    h, w = img.shape[:2]
    if h * w <= max_pixels:
        return img
    s = (max_pixels / (h * w)) ** 0.5
    return cv2.resize(img, (max(28, int(w * s)), max(28, int(h * s))), interpolation=cv2.INTER_AREA)


class VLMVerifier:
    def __init__(self, cfg: dict, cache_dir: Path, device: str = "cuda"):
        self.cfg = cfg
        self.model_id = cfg.get("model_id", "Qwen/Qwen3-VL-2B-Instruct")
        self.device = device
        self.max_new_tokens = int(cfg.get("max_new_tokens", 220))
        self.max_pixels = int(cfg.get("max_pixels", 360000))
        self.frames_per_query = int(cfg.get("frames_per_query", 6))
        self.cache_dir = Path(cache_dir) / "vlm"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.processor = None
        self.load_time = 0.0
        self.calls = 0
        self.call_time = 0.0
        self.prompt_version = "v1"

    # ------------------------------------------------------------------ loading
    def load(self) -> None:
        if self.model is not None:
            return
        import torch
        from transformers import AutoProcessor

        t0 = time.time()
        path = resolve_model_path(self.model_id)
        dtype = torch.bfloat16 if str(self.cfg.get("dtype", "bfloat16")) == "bfloat16" else torch.float16
        kwargs = {"torch_dtype": dtype, "device_map": self.device if self.device != "cpu" else None, "low_cpu_mem_usage": True}
        if bool(self.cfg.get("load_in_4bit", False)):
            from transformers import BitsAndBytesConfig

            # keep the vision tower (and the output head) in full precision: quantising the ViT costs most of
            # the visual accuracy for very little memory
            skip = list(self.cfg.get("quant_skip_modules", ["visual", "lm_head"]))
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=dtype, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, llm_int8_skip_modules=skip
            )
        try:
            from transformers import Qwen3VLForConditionalGeneration as Cls  # transformers >= 4.57
        except Exception:  # pragma: no cover
            from transformers import AutoModelForImageTextToText as Cls
        self.model = Cls.from_pretrained(path, **kwargs)
        if self.device == "cpu":
            self.model.to("cpu")
        self.model.eval()
        self.processor = AutoProcessor.from_pretrained(path)
        self.load_time = time.time() - t0
        log.info("VLM %s loaded in %.1fs", self.model_id, self.load_time)

    def unload(self) -> None:
        import torch

        self.model = None
        self.processor = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # ------------------------------------------------------------------ cache
    def _cache_key(self, video_md5: str, tag: str, frames: list[np.ndarray], prompt: str) -> str:
        h = hashlib.sha1()
        h.update(video_md5.encode())
        h.update(tag.encode())
        h.update(self.model_id.encode())
        h.update(self.prompt_version.encode())
        h.update(prompt.encode("utf-8"))
        for f in frames:
            small = cv2.resize(f, (32, 32), interpolation=cv2.INTER_AREA)
            h.update(small.tobytes())
        return h.hexdigest()

    # ------------------------------------------------------------------ generation
    def _generate(self, frames: list[np.ndarray], prompt: str) -> str:
        import torch
        from PIL import Image

        self.load()
        images = [Image.fromarray(f[:, :, ::-1]) for f in frames]
        content = [{"type": "image"} for _ in images] + [{"type": "text", "text": prompt}]
        messages = [{"role": "user", "content": content}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=images, return_tensors="pt")
        inputs = {k: (v.to(self.model.device) if hasattr(v, "to") else v) for k, v in inputs.items()}
        with torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False, temperature=None, top_p=None, top_k=None)
        gen = out[:, inputs["input_ids"].shape[1] :]
        return self.processor.batch_decode(gen, skip_special_tokens=True)[0]

    # ------------------------------------------------------------------ contrastive choice (logit scoring)
    def _choice_logprobs(self, frames: list[np.ndarray], prompt: str) -> tuple[float, float]:
        """One forward pass; returns (logP('A'), logP('B')) for the first answer token."""
        import torch
        from PIL import Image

        self.load()
        images = [Image.fromarray(f[:, :, ::-1]) for f in frames]
        content = [{"type": "image"} for _ in images] + [{"type": "text", "text": prompt}]
        messages = [{"role": "user", "content": content}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=images, return_tensors="pt")
        inputs = {k: (v.to(self.model.device) if hasattr(v, "to") else v) for k, v in inputs.items()}
        with torch.inference_mode():
            out = self.model(**inputs)
        logp = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
        tok = self.processor.tokenizer

        def lp(letter: str) -> float:
            ids = set()
            for variant in (letter, " " + letter):
                enc = tok.encode(variant, add_special_tokens=False)
                if len(enc) == 1:
                    ids.add(enc[0])
            if not ids:
                return -1e9
            return float(torch.logsumexp(logp[list(ids)], dim=0))

        return lp("A"), lp("B")

    def choice_score(self, video_md5: str, tag: str, frames: list[np.ndarray], question: str, viol: str, norm: str) -> tuple[Optional[float], bool]:
        """P(violation statement matches the frames), averaged over both option orders (removes position
        bias). Returns (p_violation in [0,1] or None on failure, from_cache)."""
        import math as _m

        from . import prompts as P

        prompt1 = P.choice_prompt(question, viol, norm)  # A = violation
        prompt2 = P.choice_prompt(question, norm, viol)  # A = normal
        key = self._cache_key(video_md5, "choice:" + tag, frames, prompt1 + "||" + prompt2)
        cp = self.cache_dir / f"{key}.json"
        if cp.exists():
            try:
                return json.loads(cp.read_text(encoding="utf-8")).get("p_violation"), True
            except Exception:
                pass
        t0 = time.time()
        try:
            a1, b1 = self._choice_logprobs(frames, prompt1)
            a2, b2 = self._choice_logprobs(frames, prompt2)
        except Exception as e:  # noqa: BLE001
            log.warning("choice scoring failed: %s", e)
            return None, False

        def p_first(a: float, b: float) -> float:
            m = max(a, b)
            ea, eb = _m.exp(a - m), _m.exp(b - m)
            return ea / (ea + eb)

        p_v = 0.5 * (p_first(a1, b1) + (1.0 - p_first(a2, b2)))
        self.calls += 2
        self.call_time += time.time() - t0
        cp.write_text(json.dumps({"p_violation": p_v, "lp": [a1, b1, a2, b2], "tag": tag, "model": self.model_id, "viol": viol, "norm": norm}, ensure_ascii=False), encoding="utf-8")
        return p_v, False

    def describe(self, video_md5: str, tag: str, frames: list[np.ndarray], prompt: str) -> tuple[str, bool]:
        """Short neutral Russian description of the frames (only for reported violations)."""
        key = self._cache_key(video_md5, "describe:" + tag, frames, prompt)
        cp = self.cache_dir / f"{key}.json"
        if cp.exists():
            try:
                return json.loads(cp.read_text(encoding="utf-8")).get("text", ""), True
            except Exception:
                pass
        t0 = time.time()
        saved = self.max_new_tokens
        self.max_new_tokens = int(self.cfg.get("describe_max_new_tokens", 90))
        try:
            txt = self._generate(frames, prompt).strip()
        finally:
            self.max_new_tokens = saved
        txt = re.sub(r"\s+", " ", txt).strip().strip('"').strip()
        self.calls += 1
        self.call_time += time.time() - t0
        cp.write_text(json.dumps({"text": txt, "tag": tag, "model": self.model_id}, ensure_ascii=False), encoding="utf-8")
        return txt, False

    def ask_json(self, video_md5: str, tag: str, frames: list[np.ndarray], prompt: str, keys: list[str]) -> tuple[Optional[dict], str, bool]:
        """Returns (answer or None, raw text, from_cache). Retries once on invalid JSON."""
        key = self._cache_key(video_md5, tag, frames, prompt)
        cp = self.cache_dir / f"{key}.json"
        if cp.exists():
            try:
                d = json.loads(cp.read_text(encoding="utf-8"))
                return d.get("answer"), d.get("raw", ""), True
            except Exception:
                pass
        t0 = time.time()
        raw = self._generate(frames, prompt)
        ans = extract_json(raw)
        if ans is None:
            raw2 = self._generate(frames, prompt + P.RETRY_SUFFIX)
            ans = extract_json(raw2)
            raw = raw + "\n---retry---\n" + raw2
        self.calls += 1
        self.call_time += time.time() - t0
        answer = normalize_answer(ans, keys) if ans is not None else None
        cp.write_text(json.dumps({"answer": answer, "raw": raw, "tag": tag, "model": self.model_id}, ensure_ascii=False), encoding="utf-8")
        return answer, raw, False

    # ------------------------------------------------------------------ frame selection
    def frames_for_window(self, frame_getter: Callable[[float], Optional[np.ndarray]], t0: float, t1: float, roi=None, n: Optional[int] = None) -> list[np.ndarray]:
        n = n or self.frames_per_query
        ts = np.linspace(t0, t1, n)
        out = []
        for t in ts:
            img = frame_getter(float(t))
            if img is None:
                continue
            img = crop_roi(img, roi)
            img = fit_pixels(img, self.max_pixels)
            out.append(burn_timestamp(img, float(t)))
        return out


# ---------------------------------------------------------------------- decision helpers
CONTRADICTION = {
    "workplace_left_unsecured": ("cashier_left", {"no"}),
    "personal_items_at_workplace": ("phone_visible", set()),  # judged by description only
    # type_id -> (answer key, values that contradict the candidate)
    "issue_without_count": ("counted_money", {"yes"}),
    "accept_without_count": ("counted_money", {"yes"}),
    "cashier_left_during_service": ("cashier_left", {"no"}),
    "cash_left_unattended": ("cashier_left", set()),  # judged by what_is_visible + confidence only
    "phone_at_workplace": ("phone_visible", {"no"}),
    "unauthorized_in_cash_zone": ("unauthorized_person", {"no"}),
    "no_id_check": ("id_shown", {"yes"}),
    "collection_bag_unchecked": ("bag_checked", {"yes", "no_bag"}),
    "two_clients_cash_mixed": ("unauthorized_person", set()),
    "handover_bypassing_transfer_device": ("cash_handover", {"none"}),
}

SUPPORT = {
    "workplace_left_unsecured": ("cashier_left", {"yes"}),
    "issue_without_count": ("counted_money", {"no"}),
    "accept_without_count": ("counted_money", {"no"}),
    "cashier_left_during_service": ("cashier_left", {"yes"}),
    "phone_at_workplace": ("phone_visible", {"yes"}),
    "unauthorized_in_cash_zone": ("unauthorized_person", {"yes"}),
    "no_id_check": ("id_shown", {"no"}),
    "collection_bag_unchecked": ("bag_checked", {"no"}),
}


def judge(type_id: str, answer: Optional[dict], reject_below: float, expect: Optional[tuple] = None) -> tuple[str, float]:
    """Return (verdict, delta) where verdict in {'reject','support','neutral'} and delta adjusts confidence.

    `expect` overrides the static maps: (answer_key, support_values, reject_values)."""
    if not answer:
        return "neutral", 0.0
    conf = float(answer.get("confidence", 0.0))
    if expect:
        key, good, bad = expect[0], set(expect[1]), set(expect[2])
        if answer.get(key) in bad and conf >= reject_below:
            return "reject", -0.35
        if answer.get(key) in good:
            return "support", 0.15 * max(0.5, conf)
        return "neutral", 0.0
    key, bad = CONTRADICTION.get(type_id, (None, set()))
    if key and answer.get(key) in bad and conf >= reject_below:
        return "reject", -0.35
    key, good = SUPPORT.get(type_id, (None, set()))
    if key and answer.get(key) in good:
        return "support", 0.15 * max(0.5, conf)
    return "neutral", 0.0
