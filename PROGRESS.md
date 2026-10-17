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
