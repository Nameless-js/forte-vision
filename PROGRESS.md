# PROGRESS

Single source of truth for the state of the ForteBank cash-desk violation engine (`forte_ai`).
One entry per phase / iteration. Newest entries at the bottom. All numbers are measured, never estimated.

---

## §0 — Reconnaissance (2026-10-17)

### Hardware (detected)

| item | value |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, **8188 MiB** VRAM, driver 555.97, CUDA 12.5 (WDDM) |
| CPU | AMD Ryzen 5 7535HS, 6 cores / 12 threads, 3.3 GHz |
| RAM | 15.2 GB total (5.3 GB free at detection time — host is memory-constrained) |
| Disk | C: 155.9 GB free |
| OS | Windows 11 Home 10.0.26200 (native, no WSL used) |
| Python | 3.12.10 in `.venv` (3.14.0 is also installed but too new for the CUDA/transformers wheel ecosystem) |
| iGPU | AMD Radeon (ignored) |

### Toolchain availability

| tool | status | consequence |
|---|---|---|
| git 2.52 | present | normal |
| ffmpeg / ffprobe | **absent** | decode with PyAV (bundled FFmpeg libs); re-encoding/augmentation via `imageio-ffmpeg` bundled binary; inventory via PyAV |
| make | **absent** | all Make targets implemented as `python scripts/run.py <target>` (cross-platform); `Makefile` still provided as a thin wrapper for Linux hosts |
| docker | **absent** | `Dockerfile` is written and lint-checked but cannot be built on this host; documented in LIMITATIONS.md |
| pandoc | absent | ТЗ docx read with stdlib zip/XML extraction |
| nvidia-smi | present | GPU monitoring |

### Network (probed with curl)

| endpoint | result |
|---|---|
| pypi.org | 200 (pip install works) |
| huggingface.co API | 200 (model download works) |
| download.pytorch.org/whl/cu124 | 200 |
| adilet.zan.kz/rus/docs/V1900019680 | 200 but 1.5 KB JS shell (no HTML text) |
| zakon.uchet.kz/rus/docs/V1900019680 | 200, 300 KB HTML (usable mirror) |
| prg.kz | 200 |
| github.com | 200 |

### Profile decision

**`gpu-small`** (NVIDIA 6–12 GB) per Section 7 of the task.
- detector: Grounding DINO tiny (zero-shot) first; fine-tuned RT-DETRv2-r18 / D-FINE-small on pseudo-labels if measured to be better;
- pose: RTMPose via `rtmlib` (ONNX Runtime);
- VLM: Qwen3-VL-2B-Instruct (bf16, ≈4.5 GB) or Qwen3-VL-4B-Instruct in 4-bit — decided by measured VRAM/time; served with `transformers` (vLLM is Linux-only);
- one heavy model on the GPU at a time; VLM loaded after perception, unloaded between videos if needed.

### Model licence check (Hugging Face API, 2026-10-17)

All candidates report `license: apache-2.0`, not gated: Qwen3-VL-2B/4B/8B-Instruct (+FP8), Qwen2.5-VL-7B-Instruct,
IDEA-Research/grounding-dino-tiny|base, google/owlv2-base-patch16-ensemble, PekingU/rtdetr_v2_r18vd|r50vd,
ustc-community/dfine-small|medium-coco, usyd-community/vitpose-base-simple|vitpose-plus-small. Details in LICENSES.md.

### Data

- `public/`: 42 `.mov` files, 288 MB total. Ids present: 1, 2, 3, 4, 5, 8, 10–35, 37–40, 43–48. Ids 6, 7, 9, 36, 41, 42 exist neither as files nor as labels → the *unlabeled* split is empty.
- Labels (`open/open_labels.xlsx`, sheet `labels`): 42 rows, **22 `нарушение` + 20 `без нарушения`**. Rows 1–2 use Latin `X`, the rest Cyrillic `Х`. Timestamps: `"N секунда"` and one `"1минута 8 секунда"`.
- **Byte-identical duplicates (md5):** `Х-4.mov ≡ Х-47.mov` (labels 57 s and 68 s → one physical video with two labeled events) and `Х-5.mov ≡ Х-48.mov` (both clean). Leave-one-video-out folds group by content hash so a video never validates against itself. See ASSUMPTIONS.md A-03.
- Video inventory (duration/fps/resolution/codec): see `analysis/inventory.md` (filled when PyAV is installed).

### Next step
Install toolchain → `data/labels.csv` → `analysis/inventory.md` → commit skeleton → Phase 1 (frame review & taxonomy).

### §0 addendum (2026-10-17, after toolchain install)
- Toolchain installed into `.venv`: torch 2.6.0+cu124 (CUDA available, 8.59 GB reported), transformers 4.57.1, PyAV 15.1.0, OpenCV 5.0, rtmlib 0.0.16, onnxruntime-gpu 1.31, bitsandbytes 0.50.2, supervision 0.31. Frozen in `requirements.txt`.
- `data/labels.csv`: 42 rows (22 violation / 20 clean), every row matched to a file; LOVO groups = 40 (two duplicate-content pairs).
- `analysis/inventory.md`: 42 files, 293 MB, 1444 s total; all **464×848 portrait** h264 ≈30 fps, no audio; durations 11.6–142.5 s (median 22.7 s). Longest: Х-14 142.5 s, Х-39 78.7 s, Х-4 72.7 s.
- Phase 2 pulled forward (independent of GPU work): acts №231, №14, №88 and Law 191-IV fetched from the uchet.kz mirror, split by clause into `kb/laws/*.json` (152 clauses of the Rules №231); `kb/rule_cards.json` with 11 cards; verbatim-quote test green (`tests/test_kb.py`). `SOURCES.md` written.

## §1–§5 — Taxonomy, perception, M1 baseline and first iterations (2026-10-18, night)

- **Phase 1**: 42 per-video frame reviews written by a 43-agent workflow (`analysis/review/NN.md`; 41/42 done, id 44 pending — workflow resumed). Team taxonomy derived and stored in `analysis/taxonomy.json`: 7 observed types + 2 reserve. Key finding: 4 departure-type violations have NO client in frame; 4 intrusion videos have an EMPTY workplace at start; clean videos contain legitimate departures (valuables secured first) — the discriminators are documented in VIOLATION_TYPES.md.
- **Phase 3**: perception cached for all 42 videos. Grounding DINO tiny at 480 px short side (measured 111–127 ms/frame at batch 2–4; dets/frame stable), scene prompts chosen with `scripts/prompt_probe.py` (e.g. counting machine = "black printer" 0.78–0.82 vs "money counting machine" 0.46; safe = "grey metal box"; cash = "banknotes"/"money"). Cross-class suppression + per-class area caps added. Longest video (142.5 s): 167 s perception wall → within the 240 s budget pre-VLM.
- **Phase 4**: behaviour-based calibration rewritten after visual QA: window anchor = nearest sustained seated visitor; counter line = perpendicular bisector cashier↔anchor; cashier zone = radius around the seat + workplace anchors. Flip/rotation invariance covered by unit tests.
- **Phase 5 iterations** (no VLM, config threshold / LOVO on fitted threshold):
  | iter | recall | FP clean | notes |
  |---|---|---|---|
  | 001 | 13/22 (LOVO 16/22) | 17 | M1 baseline, naive rules; phone/left/intrusion over-fire |
  | 002 | 10/22 (13) | 10 (11) | new calibration; strict phone; established-service guard |
  | 003 | 7/22 (10) | 6 (8) | body-depth intrusion + co-occurrence/IoU guards |
  | → M2 | — | — | full rule rewrite from the reviewed taxonomy (R1a/R1b, R6 episode-based, R9b, R10 empty-start entry, counting with cash-fraction, cup class added — perception cache p3 rebuilding) |
- Git: tag `m1-baseline` at iter_001 commit.

### Iterations 5-12 (2026-10-18 morning) — rule layer convergence
Failure-analysis-driven loop, one systemic cause per iteration (reports/iter_005..012, debug dumps in analysis/):
| iter | change | LOVO recall | FP | note |
|---|---|---|---|---|
| 005 | p4 dedup + anchors | 16/22 | 15 | reflections became clients |
| 006 | reflection det-gating, intrusion guards | 16/22 | 11 | zone stickiness at door |
| 007 | pose-backed validity | 17/22 | 13 | glass people pass pose |
| 008 | full-pose+det intruders, room gates | 12/22 | 10 | departures still masked |
| 009 | (seat via anchors — no effect) | 12/22 | 10 | projection too compressed |
| 010 | first-stationary-dwell seat, door-linger departures | 16/22 | 14 | type acc 0.75, median Δt 1.9 s |
| 011 | strict cash-after, occlusion guard | 15/22 | 13 | securing gate razor-thin |
| 012 | seat-based R10, soft securing, R5w/R6b/R8/R12/R1c → VLM band | 17/22 | 13 | config-thr: 13/22 at 5 FP |
Key lesson recorded in ASSUMPTIONS/LIMITATIONS: chairs/jackets/reflections yield person boxes up to 0.88 with
hallucinated full pose; glass-door optics put real people at 0.35-0.55; only behavioural/temporal signals separate them.

### Iterations 13-17 (2026-10-18) — Layer C (local VLM) and rule refinements
| iter | change | config-thr recall / FP | LOVO recall / FP | notes |
|---|---|---|---|---|
| 013 | first VLM run: Qwen3-VL-2B, generative JSON checklist | 15/22 / 9 | 17/22 / 13 | VLM uninformative: same answers on true and false candidates (vlm_signal.md) |
| 014 | contrastive A/B logit scoring, both orders (2B) | 15/22 / 10 | 16/22 / 13 | AUC 0.59; departures 0.63 |
| 015 | same with Qwen3-VL-4B NF4 (vision tower bf16) | 15/22 / 8 | 16/22 / 13 | AUC 0.67; departures 0.77; mean 12.4 s/video |
| 016 | 4B default + R10 empty start + laptop probe + disengage time | 18/22 / 8 | 19/22 / 14 | departures AUC 0.86, overall 0.72 |
| 017 | anchor det-gating, at-window by distance, R9c visitor change, equipment-reach exclusion, laptop caps after VLM, cashier-owned phones, per-type VLM weights | **17/22 / 3** | **20/22 / 10** | accuracy 0.81 at config threshold |
Remaining errors after 017 (config threshold): FN 1 (issue 0.44), 2 (no-id 0.43), 20 (open safe, no candidate), 22 (departure looks like a proper lock — paired with clean 23), 34 (acceptance handover undetected); FP 14 (cashier opening a bag herself), 19 (machine reach read as issue + false desk cash), 31 (cashier arriving = identical to 32 intruder).

### Completion audit ? in progress (2026-10-18)

- Existing tests: 105 passed before changes; expanded suite: 120 passed, including real spawned-process
  timeout/recovery, verifier-mode policy, and missing-artifact quality-gate checks.
- Added persistent supervised inference to the reference worker (270 s timeout, explicit failed status,
  cleanup and next-job recovery); direct Analyzer remains soft-budget.
- Fixed wheel resource packaging and tested outside the checkout; corrected Docker Python base and CPU
  setup's torch selection. Docker is unavailable and has not been built.
- Full HTTP lifecycle passed; final verification is rerunning all checks into reports/final/.
- Iter_020 wrist-withdrawal safe hypothesis gave the same detection/localization/type metrics as iter_019;
  reverted it rather than adding an unmeasured inference claim. Default threshold still 0.5.
- Added source-hash-resumable verification and artifact-based FINAL_REPORT generation. Unmet quality gates
  must produce nonzero status and remain visible, not a false DONE marker.
- Full 42-video / nine-variant robustness verification is scheduled as part of the running verification.

### Deadline confirmed ? 12:00 Asia/Qyzylorda (2026-10-18)

- User explicitly requested delivery by 12:00. Full robustness could exceed the remaining time, so the
  initial video-first fill was stopped; its completed perception caches are preserved.
- Source hash matched the completed six validation stages before changing scheduling. Evidence lives in
  reports/final/deadline_continuation.json. Inference code/configuration was not changed for this adjustment.
- Resumed variant-first (all 42 videos for one transform, then the next), with perception cutoff 11:10 and
  cached-only verdict scoring cutoff 11:40. Partial coverage is explicitly reported and cannot pass the full
  378-run robustness gate. Added regression tests for coverage and explicit timezone handling: 122 tests pass.
- Timing now proven: cold cache 110.7 / 61.8 / 70.2 s on videos 14 / 39 / 4. Slow-VLM test observed two real
  25 s injected delays, skipped subsequent work and returned a valid result in 54.0 s.
- Positive-video Python/CLI outputs are identical including JPEG evidence; offline uncached perception/VLM
  completed in 55.0 s with four VLM scoring calls and zero outbound connection attempts.

### Expedited finish (2026-10-18, after deadline clarification)

- User then requested finishing sooner. The 11:10/11:40 schedule is superseded: stopped the long cache fill
  and retained completed caches. No inference model, rules or thresholds were changed for this decision.
- Final robustness smoke test: four videos (1?4), hflip and +/-10-degree rotations, cached perception only,
  with a two-minute scoring cutoff. Actual coverage is in reports/final/robustness/summary.json. This subset
  cannot pass the full 378-run robustness requirement.
- Revalidating result JSONs, rebuilding the deliverable wheel and regenerating the final report. Quality
  requirements remain unmet and will be stated explicitly; no unconditional production-ready/DONE claim.

### Completion pass finished ? expedited delivery (2026-10-18)

- 122 tests passed; all 43 result JSON files validated. Real HTTP lifecycle, uncached offline execution,
  positive-video CLI/package equality, and isolated wheel-resource check passed.
- Cold-cache longest-video maximum: 110.7 s. Slow-VLM watchdog exercised two 25 s delays,
  returned in 54 s and skipped subsequent work. Hard process timeout/recovery separately unit-tested.
- Deployment threshold 0.5: 17/22 positives, 1/20 false positives.
  LOVO: 17/22 positives, 2/20 false positives. Quality targets remain unmet.
- Expedited robustness: 12/378 full-suite variants (four videos, three transforms), verdict
  agreement 83.3%. Two verdict changes under -10-degree rotation. This is a smoke test;
  the full robustness gate is not passed. No long validation jobs are intentionally left running.
- Final wheel: reports/final/packaging/forte_ai-0.1.0-py3-none-any.whl; weights excluded.
- FINAL_REPORT.md is regenerated from artifacts. Quality check correctly exits 2. Docker and clean dependency
  installation remain unverified. Changes are left for review; no external deployment or Git commit performed.

### Frontend integration (2026-10-18)

- Connected frontend/backend/model_adapter.py directly to the local SupervisedAnalyzer. Persistent model
  process, 250 s hard timeout, explicit cancellation and single active GPU request. Root inference rules,
  weights and thresholds unchanged. Added cancellation support to the supervisor for server shutdown.
- Frontend displays real progress/stages and evidence; citation document/clause normalized to title/section.
  Real analysis is the default, including after loading a new video. Demo remains explicit and labeled.
- Added scripts/start_app.py: one command starts Vite + the integrated FastAPI API, generates a local key,
  and defaults to SQLite. The Vite proxy keeps the key server-side. Existing media/history/checks preserved.
- 140 Python tests passed across engine and frontend backend. React TypeScript/build, all 315 translation
  entries (both themes / three languages), and feature checks passed.
- Genuine end-to-end proxy/API/GPU check on video 4 passed in 29.0 s: violation, valid JPEG evidence,
  normative citation, processing lifecycle, history persistence and upload cleanup. See reports/integration/.
- Repaired Cyrillic encoding in the earlier delivery/readme notes while updating common startup instructions.
- Original ML quality limitations remain; integration does not claim improved detection accuracy.


## Подготовка GitHub-сдачи (2026-10-18)

- README переписан для запуска жюри с чистого клона: Windows/Linux, GPU/CPU, веса, API, ключ, ограничения и диагностика.
- `scripts/run.py setup` больше не требует закрытый набор видео: пересборка разметки пропускается, если датасет не предоставлен.
- В Git включены локальные шрифты frontend; ключи, базы и тестовый runtime исключены.
- Повторно пройдены 140 тестов, pip check, сборка интерфейса и проверки переводов/функций.
- Из экспортированного Git-дерева без датасета/весов/секретов повторно пройдены 140 тестов; отдельные npm ci и production-сборка успешны. Python-зависимости при этой проверке использованы из существующей .venv; их полная свежая установка не заявляется.
