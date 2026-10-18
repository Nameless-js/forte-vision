# Объединённое приложение

Для текущего `frontend/` используйте из корня `.venv/Scripts/python scripts/start_app.py` и откройте
http://127.0.0.1:5173. API: порт 8000; ключ создаётся в frontend/.env и подставляется Vite на сервере.
Backend `frontend.backend.main` напрямую вызывает процессный адаптер `forte_ai`; отдельный server.worker
для этого запуска не требуется. Хранилище по умолчанию — SQLite. Реальный анализ включён по умолчанию.
Фронтенд принимает `progress`/`stage`, а адаптер нормализует нормативные поля title/section.
Лимит процесса модели для веб-приложения — 250 с, внешнее ожидание — 270 с.

Ниже описан самостоятельный референсный API движка. Для объединённого приложения главный запуск указан выше.

# INTEGRATION ? connecting the local engine

## Public uploads: process-supervised API

The reference server uses a persistent spawned inference process. Model weights stay loaded between jobs.
The parent worker enforces `FORTE_HARD_TIMEOUT_S` (default 270 seconds, must be below 300), including child
startup. On timeout it terminates the inference process, records `status: failed`, deletes the upload,
and starts a fresh inference process for the next job. It never converts a timeout into `no_violation`.
Process cleanup has up to two 2-second waits. Queue waiting and HTTP upload time are additional: one GPU
processes one video at a time, so concurrent requests do not have an unconditional five-minute guarantee.

PowerShell, terminal 1:

```powershell
$env:FORTE_API_KEY = "replace-with-your-secret"
.venv/Scripts/python -m server.worker --profile gpu-small
```

PowerShell, terminal 2 (set the same key):

```powershell
$env:FORTE_API_KEY = "replace-with-your-secret"
.venv/Scripts/python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Linux uses `export FORTE_API_KEY=...` and `.venv/bin/python`.
Both processes must share `FORTE_DB_PATH` and `FORTE_UPLOAD_DIR` if overriding the defaults.
`FORTE_CACHE_DIR` overrides the inference cache location.

* `POST /api/v1/analyze`, multipart field `file`, header `X-API-Key`: returns `{job_id,status:processing}`.
* `GET /api/v1/jobs/{job_id}`, same header: returns `processing`, `done` with the result, or `failed` with an error.
* Missing/wrong key: 401; unknown job: 404; unsupported extension: 400; upload over configured limit: 413.
* SQLite persists jobs and progress. The uploaded video is deleted after the worker handles it.
* `/health` confirms the HTTP process is alive, not that the models have warmed up.

For another backend worker, use the same supervision boundary:

```python
from forte_ai.supervisor import SupervisedAnalyzer

# Create/use in one queue worker; no simultaneous calls on the same instance.
# On Windows, the application entry point must have an if __name__ == "__main__" guard.
analyzer = SupervisedAnalyzer(profile="gpu-small", hard_timeout_s=270)
try:
    result = analyzer.analyze("upload.mov", deadline_sec=240,
                              on_progress=lambda fraction, stage: print(fraction, stage))
except Exception:
    # The application records a failed job, never a clean verdict.
    raise
finally:
    analyzer.close()
```

## Direct Python API and CLI

```python
from forte_ai import Analyzer
analyzer = Analyzer(profile="gpu-small")
try:
    result = analyzer.analyze("video.mov", deadline_sec=240)
finally:
    analyzer.close()
```

Direct `Analyzer` is lock-serialised and useful for trusted batch evaluation. Its `deadline_sec` is a
**soft budget**: it stops new VLM work, but cannot interrupt an executing CUDA call or video decoder.
Use `SupervisedAnalyzer` or the reference worker for a hard process boundary.

```text
python -m forte_ai analyze video.mov --out result.json --profile gpu-small
python -m forte_ai batch inbox/ --out results/
```

The result follows `forte_ai/result_schema.json`: `job_id`, `status`, `verdict`, and `violations[]` with
`type`, `timecode_sec`, `description`, and 1?3 JPEG/base64 `evidence_frames`. Additional fields include
`type_id`, deterministic `rule{document,clause,quote,url}`, confidence, facts, timings, calibration and VLM
metadata. Do not display internal calibration as a user decision. Show the evidence and normative source.
UI verdicts: `no_violation` → «Нарушение не обнаружено»; `violation` → «Обнаружены признаки возможных нарушений».
The result requires human review.

## Models, offline execution and packaging

The measured `gpu-small` profile uses Grounding DINO tiny, RTMPose, and **Qwen3-VL-4B-Instruct NF4**.
The VLM compares two descriptions in both orders, then can generate a neutral Russian description.
Experimental catch-all detection is disabled by default; enable it explicitly only for a separately
measured experiment. CPU mode has no VLM and cannot report candidates that require VLM support.

Download weights once with `python scripts/download_weights.py --profile gpu-small`. On a new host,
transfer both `models/hf` and RTMPose's `~/.cache/rtmlib` files, or run that download script before going
offline. Set `FORTE_MODELS_DIR` if the HF weights live elsewhere. After download, the socket-guarded
`offline-check --no-cache` verifies local inference.

The wheel bundles default/profile configs, the JSON result schema and the normative KB. It does not
bundle multi-GB model weights. `python scripts/packaging_check.py` tests the wheel outside the source tree.
This test uses installed dependencies; it does not prove a clean dependency installation.

Docker uses Python 3.12 and PyTorch's CUDA wheels; the host needs the NVIDIA driver and GPU container
support. `docker build -t forte-ai .`, then `docker run --gpus all -p 8000:8000 -e FORTE_API_KEY=... forte-ai`.
Docker is unavailable on the development host: its build and runtime remain unverified.

## Validation and remaining limitations

```text
python scripts/run.py verify
python scripts/run.py verify --resume
```

Verification records each stage in `reports/final/verification.json`. Resume reuses successful stages
only when the Python/config source hash matches. `FINAL_REPORT.md` is generated from actual artifacts;
`--check` returns nonzero when quality requirements remain unmet. Successful tests do not mean the model
has met detection/localization targets. See FINAL_REPORT.md and LIMITATIONS.md before deploying.

For this delivery the user set a 12:00 deadline. The deadline continuation preserves previously measured
checks and explicitly reports a subset of robustness runs; it is not a full-suite pass. Its source-integrity
proof and exact schedule are under `reports/final/deadline_continuation.json`. Resume the full `verify`
when time permits to measure the remaining transforms.
