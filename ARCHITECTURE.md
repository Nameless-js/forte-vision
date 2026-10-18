# ARCHITECTURE

A hybrid, explainable pipeline. Pure "ask a VLM about the whole video" is not used as the primary detector
(imprecise timecodes, hallucinations, slow); pure supervised video classification on 22 positives is not used
either (overfits, cannot generalise to new types/angles). Both ideas are components:

```
video.mov
   │  PyAV decode, 5 fps sampling (3 fps on cpu), ≤960 px, original timestamps kept
   ▼
Layer A — deterministic perception (forte_ai/perception/)
   │  Grounding DINO tiny (zero-shot, scene-tuned phrases) → person/cash/bag/document/id_card/phone/
   │  storage/counting_machine/laptop/cup boxes; cross-class suppression; per-class area caps
   │  ByteTrack (own implementation, Kalman+Hungarian) → person tracks (ids live only inside one video)
   │  RTMPose (rtmlib, ONNX) on tracked persons → wrists/elbows
   │  caching: data/cache/perception/<md5>_<ver>_<cfghash>.json.gz  → rule iteration is instant
   ▼
Roles & zones (forte_ai/perception/roles.py) — relative geometry only, no pixel constants
   │  cashier = argmax(presence, staticness, early appearance, proximity to equipment, cash handling)
   │  window anchor = nearest sustained SEATED visitor; counter line = perpendicular bisector
   │  cashier zone = radius around the seat + workplace anchors (safe, counting machine)
   │  per-video calibration stored in the result for debugging; invariant to flips/rotations (tested)
   ▼
Layer B — events & rules (forte_ai/events/) — symbolic, temporal, explainable
   │  primitives per frame: hands, cash/phone/cup near hands, cash on counter/cashier side, document shown,
   │  bag handling, machine activity, intrusion depth, people count
   │  events: episodes, reach-based handovers with direction, counting segments (machine-run OR periodic
   │  hand motion WITH cash at hands), storage dwell, departures, empty-start mode
   │  rules R1a/R1b/R2/R3/R3b/R4/R5/R6/R7/R8/R9a/R9b/R10 → candidates {type_id, t_event, window, conf, facts}
   ▼
Layer C — local VLM (forte_ai/vlm/, Qwen3-VL-4B-Instruct NF4, contrastive A/B logits in both orders, cached)
   │  per candidate: 6 frames t±4 s with burned-in timestamps + facts + type-specific question
   │  → reject/support/neutral (confidence delta), Russian "what is visible" description
   │  conservative catch-all over 10 s windows (hit must repeat on 2 adjacent windows and not contradict A)
   │  watchdog: no new VLM calls after time.vlm_cutoff_s (200 s); deadline 240 s; hard cap < 300 s
   ▼
Verdict & report (forte_ai/report.py)
      violation iff ≥1 candidate ≥ calibrated threshold (LOVO-fitted); ТЗ §10 JSON; 1–3 JPEG evidence
      frames (clean@t, annotated@t, clean@t+1 s); citation attached from kb/rule_cards.json by code
```

## Design decisions and their measured justification

1. **Zero-shot detector over fine-tuned.** Grounding DINO tiny with scene-tuned phrases gives stable
   detections of every object class the rules need (analysis/prompt_probe), while a closed-set detector
   trained on pseudo-labels from 42 clips of ONE staged room would inherit the pseudo-labeler's errors and
   lose the open-vocabulary robustness needed for the different-angle test video. Measured detector cost
   111–127 ms/frame (480 px, batch 2–4) fits the 240 s budget at 5 fps for the longest video (167 s
   perception wall on 142.5 s video). A fine-tune remains possible via `scripts/` if a larger dataset appears.
2. **Behavioural roles, not positions.** The training set itself contains at least two camera placements and
   4 videos where the only person is NOT a cashier; the cashier score combines presence, staticness, early
   appearance, equipment proximity and cash handling, and the zone/counter are derived per video. Flip- and
   rotation-invariance is unit-tested (tests/test_roles.py).
3. **Own ByteTrack.** supervision 0.31 removed the ByteTrack class; the tracker is ~150 lines of
   Kalman + two-stage Hungarian association (algorithm of Zhang et al. 2022), deterministic, dependency-free.
4. **Rules carry the recall; the VLM trims FPs.** Every rule follows an observable pattern documented from
   the labeled videos (VIOLATION_TYPES.md); thresholds live in configs/ and are calibrated leave-one-video-out
   (duplicate-content videos share a fold). The VLM never creates a verdict on its own: catch-all hits must
   repeat and must not contradict Layer A, and they map to the generic card with an explicit
   "approximate mapping" note.
5. **Determinism.** Fixed seeds, greedy VLM decoding, content-hash caches for perception and VLM answers;
   `analyze()` is lock-serialised; CLI and package produce identical JSON for the same video (tested).
6. **Citations are code, not text generation.** `kb/rule_cards.json` is the only source of legal references;
   a test asserts every quote appears verbatim in the stored act text fetched from the official mirror.

## Historical benchmark (gpu-small, RTX 4060 Laptop 8 GB; see FINAL_REPORT.md for final measurements)

| stage | longest video (142.5 s) | typical 20 s video |
|---|---|---|
| decode+detect+track+pose | ~167 s cold, ~0 s cached | ~25–50 s cold |
| roles + rules | < 0.5 s | < 0.1 s |
| VLM verify (per candidate) | ~3–8 s | ~3–8 s |
| report (evidence JPEGs) | < 1 s | < 1 s |

Degradation order when over budget (INTEGRATION.md): sample_fps 5→3 → detector input 480→416 → fewer VLM
windows → VLM off (template descriptions). The engine budget is soft. The public worker supervises a separate inference process and marks a timed-out job failed at its 270 s limit; it does not invent a clean verdict.

## Completion audit

`server/worker.py` delegates inference to `forte_ai/supervisor.py`. A persistent spawned process keeps
weights alive; its parent can terminate and recreate it after a hung decoder, Python inference or CUDA call.
Tests exercise real process timeout, progress forwarding, exception propagation and recovery.
`Analyzer` itself remains the direct, soft-budget API.

The current default uses contrastive 4B NF4 verification. The old generative JSON verifier remains optional;
its explicit contradictions veto candidates. Rules tagged `needs_support` require positive verification
in either mode. Experimental catch-all is disabled by default and is not a measured claim of unseen-type
coverage. A switch to JSON mode or catch-all requires fresh evaluation.

The wheel build copies canonical `configs/` and `kb/` into package resources and includes the JSON schema.
Docker uses Python 3.12 with CUDA userspace libraries from PyTorch wheels. Docker build/runtime has not been
verified on this Windows host. Full quality gates are assessed from artifacts, not documentation assertions.
