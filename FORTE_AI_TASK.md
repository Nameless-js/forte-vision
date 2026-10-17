# TASK: Build, train, validate and ship a fully local AI engine that detects cash-desk discipline violations on video (ForteBank case, Datathon 2026)

You are an autonomous senior ML/CV engineer working inside this repository. Your job is to take the case materials and the training videos that are already in this repository and deliver a **finished, self-verified, production-ready AI engine** (`forte_ai` Python package + CLI + reference API server) that a separate team will plug into their web service.

You work **end-to-end and autonomously**: analyze, design, build, train/calibrate, evaluate, fix, re-evaluate, package, document. You do **not** stop until the Definition of Done (Section 12) is met and the final verification (Section 13) passes in a clean environment. Nobody will answer questions mid-way; make reasonable decisions, log them in `ASSUMPTIONS.md`, and keep going.

Read this whole document before doing anything. Then execute the phases in Section 10.

---

## 1. The case in one page

ForteBank wants an AI service that analyzes video recordings of a bank cashier's workplace and finds **visually observable signs of cash-discipline violations**. For each video the service must say:

1. **Verdict**: `no_violation` or `violation` (video-level).
2. For every detected violation: **type**, **timecode (seconds)**, **description** of what is visible and why it may be a violation, **1–3 evidence frames** (JPEG, base64), and the **rule + normative source** (document title, clause/section).

Facts about the data and the evaluation:

- Training videos: ~40+ staged clips, 10–145 s, `.mov`, ≥29 fps, **no audio**, ~29 MB each. **Top-down camera, one cash desk**. In frame: the cashier, clients, cash collectors (инкассаторы).
- Labels: per video — `нарушение` + one timestamp (e.g. "22 секунда"), or `без нарушения`. **Violation types are NOT given**; you must derive them.
- Final test: 5+ unseen videos uploaded by the jury through an API. **The final video will be shot from a different camera angle.** Processing limit: **5 minutes per video**, otherwise the video counts as unprocessed. Evaluation is automatic from the JSON.
- The bank's priority: **missing a violation is unacceptable; false positives must be as few as possible.** Abuse of "insufficient data" is penalized. Verdict is judged per video.
- Scoring (100 pts): detection quality 25, localization quality (timecode + evidence frame) 15, classification quality 15, rule grounding 15 (no invented references, no unsupported legal claims), robustness to unseen videos/angles 10, product readiness 10, technical solution 10.
- Hard constraints: **everything runs locally** (no cloud LLM/VLM/recognition APIs; no sending video, frames or their descriptions to any external service during processing); after weights are downloaded the service must work **offline**; **no face recognition/identification**; **no audio**; only open-source models/code with **commercially permissive licenses**.
- Legal sources: **only Republic of Kazakhstan acts** (National Bank of RK, adilet.zan.kz). References without the exact clause are accepted, but invented or wrong references are penalized.
- The service must not claim a violation when the conclusion requires data that is not visible on video (e.g. correctness of a transaction or a system reconciliation). Output is a hint for a human reviewer, not a legal conclusion.

---

## 2. Repository inputs (what is already here)

- A `.docx` with the full technical specification (ТЗ) and FAQ, and an `.xlsx` with labels (`open_labels.xlsx`, sheet `labels`, columns: file name, timestamp, violation/no violation). They are in the repo root or in `docs/`. Find them by extension, read them completely (use `pandoc`/`python-docx` for docx and `openpyxl` for xlsx), and treat the ТЗ as the source of truth if anything here contradicts it.
- `public/` — all training videos (up to 48 files, `X-1.mov` … `X-48.mov`).

**Known quirks you must handle:**

- In the labels, the first rows use Latin `X` (`X-1`, `X-2`) and the rest use **Cyrillic `Х` (U+0425)** (`Х-3` …). Video file names may use either. Match videos to labels by the **numeric id**, never by raw string.
- Timestamps are free text: `"22 секунда"`, `"1минута 8 секунда"`. Parse to float seconds; write unit tests for the parser.
- Labels exist for 42 videos (22 `нарушение`, 20 `без нарушения`). Ids 6, 7, 9, 36, 41, 42 have **no label**. If such files exist, put them in an *unlabeled* split: use them for qualitative checks and robustness runs, never for metrics, and never guess labels for them.
- Only **one** timestamp is given per violation video. Treat it as the primary event; a video may contain more events — do not penalize yourself for finding an additional plausible one, but the labeled one must be found.

**Data hygiene (non-negotiable):** videos are used only inside this project. Never upload them, frames, or descriptions to any external service or cloud annotation tool. Never commit videos or extracted frames to git (add `.gitignore`). Work on copies; never modify files in `public/`.

---

## 3. Agent frame viewing policy

`AGENT_MAY_VIEW_FRAMES: true`

- If `true`: you may extract frames / contact sheets from the training videos and look at them yourself (with your image reading tool) to understand what happens at each labeled timestamp. This is a development-time analysis step, not part of the service's processing path.
- If `false`: you must not look at frames yourself. Instead, run the **local** VLM (Section 6) on frames to produce descriptions, read the human notes in `analysis/human_notes.md` if present, and derive the taxonomy from that.

In both modes, the shipped service never calls any external AI. Never attempt face identification in either mode.

---

## 4. Target architecture (build this; deviate only with measured justification recorded in `ARCHITECTURE.md`)

A hybrid, explainable pipeline. Pure "ask a VLM about the whole video" is forbidden as the primary detector (imprecise timecodes, hallucinations, slow). Pure supervised video classification on 22 positives is forbidden as the primary detector (overfits, cannot generalize to new types/angles). Use both ideas as components.

### Layer A — Perception (deterministic CV; fast; exact frames)

1. **Decode & sample**: ffmpeg/PyAV; sample at 5 fps (configurable; 3 fps on CPU profile). Keep original frame indices and timestamps.
2. **Object detection** of: `person`, `cash` (banknotes/bundles), `bag` (collector bag), `document` (paper/receipt), `id_card` (identity document / small card), `phone`, `cash_drawer` (open/closed if visible), `counting_machine` (if present). Two acceptable routes — measure and pick:
   - Zero-shot open-vocabulary: Grounding DINO (`IDEA-Research/grounding-dino-tiny|base`, Apache-2.0) or OWLv2 (`google/owlv2-base-patch16-ensemble`, Apache-2.0).
   - Fine-tuned closed-set detector: RT-DETR v2 / D-FINE (Apache-2.0, available in `transformers`), trained on pseudo-labels produced by the open-vocabulary detector on a few hundred frames, cleaned by confidence/consistency filters (and by your own visual check if Section 3 allows). Validate with **leave-one-video-out** (frames from the same video never appear in both train and val).
3. **Person tracking**: ByteTrack (MIT; e.g. `supervision.ByteTrack`). Person identity exists only as a track id inside one video. No face models anywhere.
4. **Pose / hands**: RTMPose via `rtmlib` (Apache-2.0) or ViTPose (`transformers`, Apache-2.0). Needed for: whose hand holds/touches what, hand crossing the counter line, counting motion.
5. **Roles and zones without pixel coordinates** (this is what makes the system survive a different camera angle):
   - cashier = the track with the longest presence and smallest displacement, located on the side where cash storage/drawer is; cashier zone = convex hull of its positions (dilated);
   - counter line = boundary between the cashier zone and the other people's zone;
   - client = a track on the other side of the counter line near the window;
   - collector = a track that arrives with a `bag` and/or enters from the service side.
   - Auto-calibrate per video from the first seconds and keep updating; store the calibration in the result for debugging. Never hard-code pixel zones.
6. **Cache** all per-frame perception outputs per video (parquet/json keyed by video hash + pipeline version) so rule iteration is instant.

### Layer B — Events and rules (symbolic, temporal, explainable; produces candidates with exact timecodes)

From Layer A derive primitives per frame/track: `holds(person, object)`, `cash_on_counter`, `cash_on_cashier_desk_unsecured`, `handover(from, to, object, t)`, `counting_segment(start, end)` (periodic hand motion over cash lasting ≥2–3 s, or contact with a counting machine), `cashier_left_zone(t)`, `client_present_at_window`, `phone_in_hand(cashier)`, `hand_crossed_counter(client)`, `person_in_cashier_zone(non-cashier)`, `drawer_open`, `bag_handover`, `document_exchange`, `id_card_shown`.

Rules are small temporal conditions over these primitives, each producing a **candidate**: `{rule_id, t_event, t_window, confidence, facts[]}`. Timecode policy:
- for an action violation — the first frame where the condition becomes true;
- for an omission (a mandatory step skipped) — the moment of the action that should have been preceded by that step (e.g. the handover that happened without counting). Document this policy in `VIOLATION_TYPES.md` (the FAQ leaves it to the team).

The concrete rule set comes from the taxonomy you build in Phase 1. A starting hypothesis (verify against the videos, remove what is not there, add what is):

| id | Russian type name (user-facing) | Observable pattern | Source (seed, see Section 5) |
|---|---|---|---|
| `issue_without_count` | Выдача наличных без пересчёта в присутствии клиента | cashier→client cash handover with no counting segment in the preceding window | №231 п. 31 пп. 4 |
| `accept_without_count` | Приём наличных без полистного пересчёта | client→cashier cash handover, then cash stored with no counting segment | №231 п. 19 пп. 2; п. 20 |
| `cashier_left_during_service` | Кассир покинул рабочее место до окончания обслуживания клиента | cashier track leaves the cashier zone while a client is at the window / an operation is open | №231 п. 22 |
| `cash_left_unattended` | Наличные оставлены без присмотра / не убраны в закрывающееся устройство | cash visible on desk/counter with no cashier hand nearby for N s, or cashier leaves with cash out / drawer open | №231 п. 20 (+ п. 80) |
| `phone_at_workplace` | Использование телефона (устройства с фото/видео) в кассовом узле | phone in cashier's hand / on desk being used | №231 п. 12 |
| `unauthorized_in_cash_zone` | Посторонний в зоне кассира / проникновение за барьер | non-cashier person or client's hand crosses into the cashier zone | ПП №14 п. 16; №231 п. 75 |
| `no_id_check` | Операция без предъявления документа, удостоверяющего личность | cash issued/accepted with no `id_card`/document exchange before the handover | №231 п. 19 пп. 1; п. 31 пп. 1 |
| `collection_bag_unchecked` | Инкассаторская сумка принята/выдана без проверки целостности, пломбы и сопроводительного документа | bag handover with no inspection and no document exchange | №231 п. 24, 25, 38, 39 |
| `two_clients_cash_mixed` | На рабочем месте наличные двух клиентов одновременно / второй клиент у окна во время операции | two client tracks at the window with cash on the desk | №231 п. 20, 21 |

### Layer C — Local VLM as verifier + describer (+ catch-all for unseen types)

- Model: `Qwen/Qwen3-VL-8B-Instruct` (preferred), `Qwen/Qwen3-VL-4B-Instruct` or `Qwen/Qwen3-VL-2B-Instruct` for small VRAM, fallback `Qwen/Qwen2.5-VL-7B-Instruct`. **Verify the license on the model card is Apache-2.0 before use**; do NOT use `Qwen2.5-VL-3B` (research license). Serve with vLLM (guided JSON decoding) or `transformers` (+ 4-bit bitsandbytes/AWQ when VRAM < 16 GB); llama.cpp GGUF on CPU/Apple Silicon if that is the only option. Temperature 0, fixed seeds.
- Input per candidate: 6–8 frames from `t_event ± 4 s` with the timestamp burned in, the structured facts from Layer B, the protocol checklist, and the question. Output: **strict JSON** — `{counted_money: yes|no|unclear, id_shown: ..., cashier_left: ..., phone_visible: ..., unauthorized_person: ..., bag_checked: ..., what_is_visible_ru: "...", confidence: 0..1}`. Validate the JSON; retry once on failure; fall back to template description.
- Roles: (1) reject false positives from Layer B; (2) write the Russian "what is visible" description; (3) a coarse pass over 10 s windows asking "any deviation from the protocol?" to catch types with no rule — such a hit becomes a violation only if it repeats on two adjacent windows AND nothing in Layer A contradicts it (this path is the main FP risk — keep it conservative and measure it separately).
- Cache VLM answers keyed by (video hash, window, frame set hash, prompt hash).
- **CPU-only profile**: skip Layer C entirely; descriptions come from templates filled with detected facts.

### Knowledge base (rule cards) — see Section 5

Deterministic mapping `type_id → rule card (document, clause, verbatim quote, URL)`. **No model ever generates a citation.** Models only describe what is visible; code attaches the source.

### Verdict policy

`violation` iff at least one candidate survives verification with calibrated confidence ≥ threshold. Thresholds are calibrated with leave-one-video-out on the labeled set with the objective: recall on violation videos = 100 % first, then minimize false positives on clean videos. Report train and cross-validated numbers separately.

### Time budget and watchdog

Hard cap **240 s** per video end-to-end (measured on the longest video on the target hardware). A watchdog stops further VLM calls at 200 s and returns the rule-based result; the service must never exceed 300 s. Log the time of every stage.

---

## 5. Knowledge base: verified normative sources (seed — re-verify, never extend without verification)

Build `kb/` with: raw act texts split by clause (`kb/laws/*.json`, one entry per пункт with number and verbatim text), `kb/rule_cards.json`, and a test that asserts every quote in a rule card occurs **verbatim** in the stored act text. If the internet is available, fetch the acts (adilet.zan.kz requires JavaScript; the mirrors `https://zakon.uchet.kz/rus/docs/<id>` and `https://prg.kz` serve HTML; cite the adilet URL as canonical). If fetching is impossible, store the seed quotes below, mark them `verified_by_agent: false` in the cards, and say so in `SOURCES.md`.

Seed, already checked against the act text by a human before this task:

**Source 1 — main document.** Постановление Правления Национального Банка Республики Казахстан от 29 ноября 2019 года № 231 «Об утверждении Правил осуществления кассовых операций и операций по инкассации банкнот, монет и ценностей в банках второго уровня, филиалах банков-нерезидентов Республики Казахстан, Национальном операторе почты и юридических лицах, исключительной деятельностью которых является инкассация банкнот, монет и ценностей». Registered by the Ministry of Justice on 03.12.2019, № 19680. Canonical URL: `https://adilet.zan.kz/rus/docs/V1900019680`.

- п. 12 — «Хранение личных вещей, наличных денег и ценностей работников банка осуществляется вне кассового узла»; bringing in medicines, medical devices and communication devices *without photo/video functions* is allowed.
- п. 19 — accepting cash: пп. 1 «проводит визуальную идентификацию клиента, вносящего наличные деньги, с документом, удостоверяющим его личность»; пп. 2 «принимает банкноты с полистным пересчетом, монеты с пересчетом по кружкам с проверкой на подлинность и платежность»; пп. 4 сверка суммы; пп. 6 «выдает клиенту документ, подтверждающий проведение кассовой операции по приему наличных денег».
- п. 20 — «Наличные деньги принимаются и пересчитываются кассовым работником в присутствии клиента.» «На рабочем месте кассового работника находятся наличные деньги клиента.» Previously accepted cash is kept in special lockable devices at the workplace (metal cabinet, safe, cart, desk drawers, cabinet).
- п. 21 — cash is accepted separately per each incoming cash document.
- п. 22 — «Кассовому работнику не допускается покидать рабочее место до окончания обслуживания клиента.»
- п. 23 — accepted cash is formed, packed and handed to the cash supervisor (may happen several times a day).
- п. 24 — accepting cash from a collection unit: check the accompanying document details, register the amount, check bag integrity and seals.
- п. 25 — if bag integrity is broken, open and recount in the presence of the collection worker; draw up an act on shortage/surplus.
- п. 31 — issuing cash: пп. 1 «проводит визуальную идентификацию клиента по данным документа, удостоверяющего личность»; пп. 4 «пересчитывает подготовленные к выдаче наличные деньги в присутствии клиента, выдает клиенту наличные деньги»; пп. 6 issues a confirming document.
- п. 33 — «Кассовый работник осуществляет выдачу наличных денег клиентам только в упаковке банка.»
- п. 35 — «Клиент пересчитывает полученные наличные деньги, не отходя от кассы, или в помещении для пересчета … в присутствии кассового работника или контролирующего работника.»
- п. 38, 39 — issuing cash to a collection unit on an accompanying document; collection worker accepts per п. 107.
- п. 59 — suspicious banknotes are handled in the presence of the client.
- п. 75 — «Вход в кладовую и (или) сейфовую комнату разрешается лицам, ответственным за сохранность наличных денег» (others only by order and escorted).
- п. 76 — keys/access codes are held by responsible persons.
- п. 80 — keys to the special devices at the cashier's workplace.

**Source 2 — premises and security.** Постановление Правления Национального Банка Республики Казахстан от 24 февраля 2020 года № 14 «Об утверждении Правил организации охраны и устройства помещений банков второго уровня, филиалов банков-нерезидентов Республики Казахстан, Национального оператора почты, юридических лиц, исключительной деятельностью которых является инкассация банкнот, монет и ценностей, и юридических лиц, осуществляющих деятельность исключительно через обменные пункты…». Registered 27.02.2020, № 20075. Canonical URL: `https://adilet.zan.kz/rus/docs/V2000020075`.

- п. 2 пп. 12 — loading area «исключающее доступ и просмотр посторонних лиц».
- п. 7, 8 — composition of the cash unit; separated from other rooms by a lockable service entrance.
- п. 16 — each cash desk has its own lockable door (пп. 1); protective means for the cashier (пп. 2); window opening with protection against theft (пп. 3); transfer devices (пп. 4); partitions separating cashiers' workplaces (пп. 5); CCTV cameras at each cash desk (пп. 6). **Note:** п. 16 (and 11, 13(3), 14) are suspended until 01.01.2027 by Resolution № 88 of 24.12.2024 with a temporary wording — state this in `SOURCES.md` and `LIMITATIONS.md` and quote the wording that is in force.
- п. 21 — restrict third-party access and viewing during cash collection.

**Source 3 — optional, secondary.** Закон Республики Казахстан от 28 августа 2009 года № 191-IV «О противодействии легализации (отмыванию) доходов, полученных преступным путем, и финансированию терроризма», ст. 5 (надлежащая проверка клиентов). Use only for `no_id_check` as a secondary reference and only after you have fetched and stored the article text; otherwise omit it.

Citation rules: cite document title + number + date + clause; quote verbatim; prefer the exact пункт/подпункт; if a video shows a pattern you cannot map to a verified clause, output the type with the closest verified clause and say explicitly in the description that the mapping is approximate — never fabricate.

---

## 6. Output contract and integration interface

### 6.1 Result JSON (exactly per the ТЗ; the backend returns it as-is)

```json
{
  "job_id": "3f2a9c1e",
  "status": "done",
  "verdict": "violation",
  "violations": [
    {
      "type": "Выдача наличных без пересчёта в присутствии клиента",
      "timecode_sec": 44.2,
      "description": "Что видно на видео и почему это может быть нарушением",
      "evidence_frames": [
        { "timestamp_sec": 44.2, "image_base64": "/9j/4AAQ..." }
      ]
    }
  ]
}
```

- `verdict` ∈ {`no_violation`, `violation`}; `violations` is `[]` when `no_violation`.
- `timecode_sec`: float seconds from video start.
- `evidence_frames`: 1–3 JPEG frames (quality ~85, max width 1280), base64 without data-URI prefix. Provide one clean frame at `t_event` and one annotated frame (boxes/roles/arrow) at `t_event`, optionally `t_event ± 1 s`.
- The engine's own result object additionally carries (as extra keys the backend may pass through or drop): `type_id`, `rule` `{document, clause, quote, url}`, `confidence`, `facts[]`, `stage_timings`, `calibration`, `engine_version`. The ТЗ keys above must be present verbatim.
- Every user-facing string (type, description) is in **Russian**. Descriptions state only observable facts: "На 44,2 с кассир передаёт клиенту пачку наличных через передаточное устройство; в предшествующие 15 с не зафиксировано пересчёта (движений перебора банкнот/использования счётной машины). Это может указывать на выдачу наличных без пересчёта в присутствии клиента (Правила…, п. 31 пп. 4)." Never claim anything about transactions, postings, reconciliations, amounts, identities.

### 6.2 Python package API (the primary integration; the web team imports it — no HTTP between engine and backend)

```python
from forte_ai import Analyzer

analyzer = Analyzer(device="auto", config="configs/default.yaml")   # loads all models ONCE
result = analyzer.analyze(
    "path/to/video.mov",
    on_progress=lambda fraction, stage_msg: ...,   # 0.0..1.0, Russian stage text for the UI
    deadline_sec=240,
)
# result: dict in the schema of 6.1 (plus extra keys). Raises forte_ai.AnalysisError on unrecoverable failure.
```

Requirements: thread-safe for sequential calls; models loaded once per process; GPU memory released between videos; deterministic; works with `HF_HUB_OFFLINE=1` after the first download; no network access during `analyze`.

### 6.3 CLI

`python -m forte_ai analyze <video.mov> --out result.json [--evidence-dir dir] [--profile auto|gpu-large|gpu-small|cpu]`
`python -m forte_ai batch <dir> --out results/` and `python -m forte_ai eval --labels data/labels.csv --videos public/ --out reports/`.

### 6.4 Reference API server (thin, for self-testing and as a fallback for the team)

FastAPI app in `server/`: `POST /api/v1/analyze` (multipart field `file`, `.mov`) → `{"job_id": ...}`; `GET /api/v1/jobs/{job_id}` → `{"job_id","status": "processing|done|failed", ...result}`; header `X-API-Key` checked against env `FORTE_API_KEY`; requests without a valid key → 401. One **separate worker process** owns the models and processes jobs sequentially from a queue; jobs persisted in SQLite; progress from `on_progress` is exposed in the job status; the uploaded file is deleted after processing (data hygiene). Provide `make api-test` that starts the server, uploads a video with `curl -F file=@... -H "X-API-Key: ..."`, polls until done, and validates the JSON against the schema.

### 6.5 Alternative wiring (document in `INTEGRATION.md`)

Subprocess CLI call; folder queue (`inbox/*.mov` → `results/<job_id>.json`); Redis queue. Describe how the backend team should run the worker, pass progress, and handle failures and the 5-minute limit.

---

## 7. Hardware profiles and performance

First thing in Phase 0: detect hardware (`nvidia-smi`, `torch.cuda.is_available()`, VRAM, `nproc`, RAM, disk, Apple MPS) and network (can `pip install`? can download from Hugging Face?). Write the result to `PROGRESS.md`. Then select a profile and keep the whole pipeline inside the budget:

| profile | hardware | detector | pose | VLM |
|---|---|---|---|---|
| `gpu-large` | NVIDIA ≥ 16 GB | fine-tuned RT-DETR/D-FINE or Grounding DINO base | RTMPose/ViTPose | Qwen3-VL-8B (bf16 or AWQ) |
| `gpu-small` | NVIDIA 6–12 GB | fine-tuned small detector / Grounding DINO tiny | RTMPose | Qwen3-VL-4B/2B 4-bit, fewer windows |
| `cpu` | no GPU / Apple MPS | small detector via ONNX Runtime, 3 fps | RTMPose (ONNX) | none (templates) — or a tiny GGUF VLM only if measured to fit |

Measure throughput on the longest video **early** (end of Phase 3) and again at the end. If the budget is not met, reduce fps, resolution, VLM windows — in that order. If weights cannot be downloaded at all, stop after writing exactly what is missing in `PROGRESS.md` under `BLOCKED` — this is the only acceptable reason to stop before the Definition of Done.

---

## 8. Licenses (record every model/library in `LICENSES.md`)

Allowed: Apache-2.0, MIT, BSD (e.g. Grounding DINO, OWLv2, RT-DETR, D-FINE, rtmlib/RTMPose, ViTPose, ByteTrack, `supervision`, SAM2, DINOv2, SigLIP2, Qwen3-VL / Qwen2.5-VL-7B/72B, vLLM, llama.cpp, bge-m3, multilingual-e5, Chroma/FAISS).
Forbidden: Ultralytics YOLO (AGPL-3.0), YOLO-World (GPL), `boxmot` (AGPL), VideoMAE v2 weights (CC-BY-NC), Qwen2.5-VL-3B (research license), anything "non-commercial", any cloud AI API.
If unsure about a license, check the model card / repo and write down what you found.

---

## 9. Engineering standards

- Repo layout:
  ```
  forte_ai/            package: video.py, perception/{detector,pose,tracker,roles}.py, events/{primitives,rules}.py,
                       vlm/{verifier,prompts}.py, kb/{rule_cards.json,laws/,retriever.py}, report.py, analyzer.py, cli.py
  configs/             default.yaml + profile yamls (all thresholds live here, never in code)
  server/              reference FastAPI server + worker
  scripts/             data prep, frame extraction, pseudo-labeling, training, eval, robustness, timing
  data/                labels.csv, splits, cache/ (gitignored), pseudo_labels/ (gitignored)
  analysis/            frame review notes, taxonomy.md, failure analyses
  tests/               pytest: label parsing, rules on synthetic event streams, schema validation, KB quote test, timecode policy, API contract
  reports/             eval outputs per iteration (metrics.json + per-video table + confusion)
  docs: README.md ARCHITECTURE.md VIOLATION_TYPES.md SOURCES.md LIMITATIONS.md INTEGRATION.md LICENSES.md ASSUMPTIONS.md PROGRESS.md FINAL_REPORT.md
  Makefile  pyproject.toml  Dockerfile  .gitignore
  ```
- Python ≥ 3.10, `pyproject.toml`, pinned versions in a lock/requirements file, `make setup`, `make test`, `make eval`, `make robustness`, `make timing`, `make api-test`, `make verify`.
- Logging with stage timings; structured config; seeds fixed; code and comments in English; user-facing strings in Russian.
- Git: commit after every milestone with a meaningful message; `main` is always runnable (M1 baseline first — see Phase 5 — then improvements).
- Dockerfile that builds the engine + reference server with weights baked in or downloaded in a build step, and runs offline afterwards (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`).
- Tests must pass before every commit that touches rules/eval.

---

## 10. Workflow — phases and deliverables

### Phase 0 — Reconnaissance (deliverable: `PROGRESS.md` §0, `data/labels.csv`, `analysis/inventory.md`)
Read the ТЗ docx and FAQ fully; read the labels; inventory videos with `ffprobe` (duration, fps, resolution, codec); build `data/labels.csv` (`video_id, path, label, t_sec`); detect hardware/network; choose the profile; create the repo skeleton, `ASSUMPTIONS.md`, `.gitignore`.

### Phase 1 — Taxonomy from the data (deliverable: `analysis/review/<video_id>.md`, `analysis/taxonomy.md`, `analysis/protocol.md`)
For each **violation** video: extract frames at 1 fps for `t_label − 6 … t_label + 6` and a 3×3 contact sheet; plus a 1 fps timeline strip of the whole video. Review them (per Section 3 policy) and write: who is where, what objects move, what exactly happens at `t_label`, and the candidate type. For the **clean** videos review timeline strips and write the normal protocol (sequence of steps of a correct operation: client approaches → ID/document → cash handover → counting → storing → receipt → client leaves; collector arrival → bag → document → inspection …).
Cluster the 22 events into types (expect 4–8). For each type: `type_id`, Russian name, observable pattern, timecode policy, mapped rule card id, list of videos. Also record which **normal** actions look similar to each violation (these are your FP risks). This taxonomy is the ground truth for type-level metrics (mark it "team-assigned" in reports).

### Phase 2 — Knowledge base (deliverable: `kb/`, `SOURCES.md`, KB tests green)
Fetch and store act texts split by clause; create rule cards for every type (and the catch-all); write the verbatim-quote test; write `SOURCES.md` with document → clause → type → "how it is observed on video" table.

### Phase 3 — Perception pipeline (deliverable: cached perception for all videos, `analysis/perception_qa.md`)
Implement decode/sample, detection, tracking, pose with caching. Render annotated contact sheets / short annotated clips for several videos and check them (per Section 3). Measure per-stage timing on the longest video. Decide zero-shot vs fine-tuned detector by measured precision on a small hand-checked set (if frame viewing is allowed) or by consistency metrics (track stability, detection persistence) otherwise. If fine-tuning: pseudo-label with the open-vocabulary detector, filter, train with leave-one-video-out validation, record metrics.

### Phase 4 — Roles and zones (deliverable: calibration for every video, `analysis/roles_qa.md`)
Implement auto-calibration; verify that the cashier is identified correctly in all 42+ videos (and that the method does not depend on absolute pixel positions — test on horizontally flipped and rotated copies).

### Phase 5 — Events, rules, M1 baseline (deliverable: `reports/iter_001/`, tag `m1-baseline`)
Implement primitives and rules for the taxonomy; run `make eval`; produce per-video table (label, t_label, predicted verdict, t_pred, |Δt|, type, rule facts). Do failure analysis in `analysis/failures_iter_001.md`: for every missed violation and every false positive explain the cause (perception, roles, rule logic, threshold) and the fix. At this point the end-to-end JSON must already be valid: this is the first shippable milestone.

### Phase 6 — VLM verifier (GPU profiles; deliverable: `reports/iter_00N/`)
Implement the structured-JSON verifier with caching and the watchdog; measure its effect on FPs and on time; implement the conservative catch-all pass; keep it switchable in config.

### Phase 7 — Calibration, robustness, timing
Calibrate thresholds with leave-one-video-out; produce train vs cross-validated metrics. Build the robustness suite (`make robustness`): for every labeled video create variants — horizontal flip, rotation ±10°, perspective warp, 0.75× scale, brightness ±25 %, 10 % crop, 720p re-encode — and compare verdicts/timecodes to the originals. Build `make timing` on the 3 longest videos. Iterate Phases 5–7 until the gates in Section 12 pass; each iteration gets its own `reports/iter_XXX/` and a `PROGRESS.md` entry with the numbers and what changed.

### Phase 8 — Packaging and documentation
CLI, reference server, Docker, offline mode, `INTEGRATION.md`, all docs in Section 9, `LICENSES.md`, `LIMITATIONS.md` (known failure cases from your failure analyses, what is not visible on video and therefore never claimed, the suspended п. 16 note), `FINAL_REPORT.md`. Then run the final verification (Section 13).

Parallelism: you may run independent work (KB, perception, server) with subagents, but a single source of truth lives in the repo and `PROGRESS.md`.

---

## 11. Evaluation protocol (implement in `forte_ai/eval` and `scripts/eval.py`)

- Video-level: accuracy, **recall on violation videos**, **false-positive count/rate on clean videos**, confusion matrix.
- Localization: for each violation video with a predicted violation, `Δt = min over predicted events |t_pred − t_label|`; report the share within ±1 s, ±2 s, ±3 s, ±5 s and the median.
- Classification: predicted `type_id` vs the team-assigned type from `analysis/taxonomy.md`.
- Per-stage timing; max and mean end-to-end time.
- Everything reported twice: on the full labeled set with fitted thresholds and under **leave-one-video-out** cross-validation (thresholds and any learned component fitted without the held-out video).
- Robustness: verdict agreement and timecode agreement between originals and augmented variants.
- Every eval writes `reports/iter_XXX/metrics.json`, `per_video.csv`, `README.md` (human summary).

---

## 12. Definition of Done — all gates must pass (measured, not asserted)

1. **Detection**: cross-validated recall on violation videos = **22/22**; false positives on the 20 clean videos ≤ **1** (target 0). Catch-all VLM path alone must not add more than 1 FP.
2. **Localization**: among detected labeled violations, ≥ **80 %** within ±2 s and ≥ **95 %** within ±5 s of `t_label`; every violation has 1–3 valid JPEG evidence frames, at least one of them from within ±1 s of `timecode_sec`.
3. **Classification**: every detected violation carries a `type_id` from the taxonomy and a rule card; cross-validated type accuracy ≥ **80 %** against the team-assigned types.
4. **Grounding**: every emitted rule citation exists in `kb/rule_cards.json`; every quote passes the verbatim test; `SOURCES.md` lists only fetched/verified acts (or clearly flags unverified seeds).
5. **Robustness**: verdict agreement ≥ **90 %** and, for violations, timecode within ±3 s in ≥ **80 %** across the augmentation suite; roles are identified correctly on flipped/rotated copies of all videos.
6. **Time**: end-to-end ≤ **240 s** on the longest video on the selected profile, watchdog tested (simulate a slow VLM and prove the result is returned before 300 s).
7. **Offline & local**: a full run with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` and the network disabled (e.g. `unshare -n` or an iptables/env block) succeeds; `grep`/code audit proves there are no outbound calls in the processing path; no face models in dependencies.
8. **Contract**: `make api-test` passes (401 without key; job lifecycle; JSON schema validation; `verdict`/`violations` semantics); CLI and package API produce identical results for the same video.
9. **Reproducibility**: fresh clone into a temp dir → follow `README.md` literally → `make setup && make test && make eval` succeed; Docker image builds and `make api-test` passes against the container.
10. **Docs**: all documents in Section 9 exist, are current, and `FINAL_REPORT.md` contains the final metrics tables, hardware used, per-video results, known failure cases and the exact commands to reproduce.

If a gate still fails after **six** full improvement iterations with at least three materially different approaches tried, record the evidence (what was tried, numbers, why it is limited by hardware/data) in `FINAL_REPORT.md` under "Unmet gates", keep improving everything else, and never silently relax a number. The session may end only when every gate is either PASSED or documented this way. Never report a gate as passed without the artifact (`reports/...`) proving it.

---

## 13. Final verification (run from a clean state before you declare completion)

1. `git status` clean; commit everything.
2. Fresh clone into a temp directory; new virtual environment; execute `README.md` step by step exactly as a stranger would.
3. `make verify` = `make test` + `make eval` + `make robustness` + `make timing` + offline run + `make api-test` + schema validation of every result in `reports/final/`.
4. Re-read the ТЗ and FAQ once more and tick every requirement in a checklist in `FINAL_REPORT.md` (interface contract, verdict wording, evidence frames, Russian texts, local-only, no faces, no audio, licenses, 5-minute limit, portability).
5. Only then write the last `PROGRESS.md` entry "DONE" with the final metrics and stop.

---

## 14. Operating rules

- Work autonomously; never wait for a human; record every non-obvious decision in `ASSUMPTIONS.md`.
- Keep `PROGRESS.md` current: one entry per phase/iteration with timestamp, what was done, metrics, next step. A human may interrupt you at any time and must be able to understand the state and run the current best version.
- Start simple, get end-to-end JSON early (M1), then improve by failure analysis — never by blind parameter tweaking. Prefer rules that generalize over rules that fit one video.
- Never overfit: anything learned or any threshold is validated leave-one-video-out; report both numbers; if the gap is large, simplify.
- Never use the labeled timestamps inside the inference path (they are for evaluation only).
- Never identify faces, never use audio, never call external AI, never upload data, never use forbidden licenses, never fabricate a citation.
- When something fails (download, OOM, slow), degrade gracefully according to Section 7 and write it down; do not stop.
- Measure before deciding; keep caches so that iterations are fast; keep the GPU budget in mind (one model at a time if VRAM is tight; unload the VLM when not needed).
- Do not build the web frontend or the real backend — that is another team's job. Build the engine, the CLI, the reference server, the tests and the documents.

Begin with Phase 0 now.
