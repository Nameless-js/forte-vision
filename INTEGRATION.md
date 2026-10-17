# INTEGRATION — how the web team plugs the engine in

The engine is a Python package (`forte_ai`). The recommended wiring is **in-process**: the backend's worker
imports `forte_ai.Analyzer`, loads the models once and calls `analyze()` per job. The reference server in
`server/` shows the complete lifecycle (upload → queue → worker → status → result) and can be used as-is.

## 1. Package API (primary)

```python
from forte_ai import Analyzer, AnalysisError

analyzer = Analyzer(device="auto", config="configs/default.yaml")   # loads all models ONCE (~10–30 s)
# optional: analyzer.warmup()  # load the VLM too, so the first job is not slower

def on_progress(fraction: float, stage_msg: str):   # 0.0..1.0, Russian stage text for the UI
    job.progress = fraction; job.stage = stage_msg

try:
    result = analyzer.analyze("path/to/video.mov", on_progress=on_progress, deadline_sec=240)
except AnalysisError as e:
    ...  # unrecoverable: corrupt file, no video stream, etc.
```

* `result` is the ТЗ §10 JSON (`job_id`, `status`, `verdict`, `violations[]` with `type`, `timecode_sec`,
  `description`, `evidence_frames[]{timestamp_sec,image_base64}`) plus extra keys the backend may pass through
  or drop: `type_id`, `rule{document,clause,quote,url}`, `confidence`, `facts[]`, `source`, `t_window`,
  `stage_timings`, `calibration`, `events`, `vlm`, `models`, `engine_version`, `profile`, `video`, `deadline`.
  The backend should set its own `job_id`/`status` (or pass `job_id=` to `analyze`).
* Thread safety: `analyze()` is serialised by an internal lock — call it from several threads if you like, the
  calls run one after another (one GPU, one model set). For parallel jobs run several worker processes.
* Models are loaded once per process; GPU memory is kept between videos (the VLM is loaded lazily on the first
  video that needs it; on 8 GB GPUs the detector is freed before the VLM and reloaded on the next video).
* Deterministic: fixed seeds, greedy decoding, cached perception keyed by file content.
* Offline: after `python scripts/download_weights.py` the process works with `HF_HUB_OFFLINE=1
  TRANSFORMERS_OFFLINE=1` and no network (see `scripts/offline_check.py`).
* `deadline_sec` (default 240): the VLM stages stop at `time.vlm_cutoff_s` (200 s) and the rule-based result is
  returned; the result carries `deadline.within_deadline`. The service never exceeds 300 s for the training
  videos on the development GPU (see `reports/timing/`).

## 2. CLI (subprocess wiring)

```
python -m forte_ai analyze video.mov --out result.json [--evidence-dir frames/] [--profile gpu-small] [--deadline 240]
python -m forte_ai batch inbox/ --out results/
```
Exit code 0 = valid result written; 3 = result written but it failed schema validation (should not happen);
non-zero otherwise. Each call loads the models (≈10–30 s) — use the package API or the worker for throughput.

## 3. Reference server (fallback / self-test)

```
set FORTE_API_KEY=<key>                     # Windows;  export FORTE_API_KEY=<key> on Linux
python -m server.worker --profile gpu-small  # process 1: owns the models, processes the SQLite queue
uvicorn server.app:app --host 0.0.0.0 --port 8000   # process 2: thin API
```
* `POST /api/v1/analyze` (multipart `file`, `.mov`) → `{"job_id": "...", "status": "processing"}`
* `GET /api/v1/jobs/{job_id}` → `{"job_id","status": "processing|done|failed","progress","stage", ...result}`
* Header `X-API-Key` is required on both; otherwise **401**. Unknown job → 404; non-.mov → 400.
* Jobs are persisted in SQLite (`FORTE_DB_PATH`), uploads in `FORTE_UPLOAD_DIR`; the uploaded file is deleted
  after processing (data hygiene). Progress from `on_progress` is written to the job row and exposed in
  `GET`. Jobs stuck in `processing` for > 15 min (worker crash) are marked `failed`.
* `python scripts/run.py api-test` starts both processes, uploads a video, polls until done, validates the JSON
  against `forte_ai/result_schema.json` and checks the 401/404 paths.
* Docker: `docker build -t forte-ai . && docker run --gpus all -p 8000:8000 -e FORTE_API_KEY=... forte-ai`
  (weights are baked in during the build; the container runs with `HF_HUB_OFFLINE=1`).

## 4. Alternative wiring

* **Folder queue**: a watcher moves `inbox/*.mov` to `processing/`, calls `analyzer.analyze()` and writes
  `results/<job_id>.json`; the frontend polls the results folder. Simple and robust for one GPU box.
* **Redis queue** (RQ/Celery): the API enqueues `{job_id, path}`; one worker process with a module-level
  `Analyzer` consumes jobs (`concurrency=1` per GPU); progress is written to Redis `job:<id>:progress`.
* Any of these must keep **one Analyzer per process** and run jobs sequentially per GPU.

## 5. Handling failures and the 5-minute limit

* Return `status: processing` immediately after upload; the jury polls.
* The engine's own budget is 240 s (configurable); the worst training video (142 s) takes well under that on
  an RTX 4060 Laptop (see `reports/timing/timing.json`). If your hardware is slower, lower
  `video.sample_fps` (5 → 3), `perception.detector.input_short_side` or disable the catch-all
  (`vlm.catch_all.enabled: false`) in a config overlay; the order of degradation is fps → resolution → VLM
  windows → VLM off.
* On `AnalysisError` or any exception mark the job `failed` with a short error string; never return an empty
  `done`.
* Verdict wording for the UI: `no_violation` → «Нарушение не обнаружено»; `violation` → «Обнаружены признаки
  возможных нарушений» (ТЗ §4). The result is a hint for a human reviewer, not a legal conclusion — show the
  `description` and the `rule` (document, clause, quote, URL) next to the evidence frames.
