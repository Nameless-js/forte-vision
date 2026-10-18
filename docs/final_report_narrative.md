## Status and unmet gates

This is an evaluated local prototype, not a declaration of production readiness. The table above is the
source of measured gate status. Internal targets in FORTE_AI_TASK.md are stricter than merely having a
working API. Detection, localization and classification targets remain unmet; they have not been lowered.

More than six improvement iterations were tried. Three materially different approaches are preserved:
(1) symbolic/temporal rule and role refinements (iter_001?012), (2) generative JSON verification with a local
2B VLM (013), and (3) contrastive two-order scoring with 2B then 4B NF4 (014?019). The latter reduced false
alarms substantially but did not solve missing small cash detections, close safe geometry or ambiguous
workplace entry. A further safe-wrist-withdrawal experiment (020) did not improve the metrics and was reverted.
No timestamps or video IDs are used as lookup-based inference decisions.

The per-video table includes development LOVO thresholds; the deployed default is the separately reported
config threshold, not each fold's threshold. LOVO refits thresholds, while rules, prompt phrases and the
team taxonomy were developed using the full open set. The type metric uses the event nearest the label
among reported events. Thus it does not establish that every event in a video has the correct type.
Localization percentages are conditional on detected positive videos; missed videos are not in that denominator.

The most important remaining cases are: 1 (counting/issue ambiguity), 2 and 34 (cash/handover not detected),
20 (open-safe geometry), 22 versus clean 23 (securing/locking proxy), 31 versus 32 (legitimate arrival versus
intruder without identity/access data), and 13/44/47 (correct video verdict can come from the wrong event).
Further gains require better small-object annotations/detection and an independent validation set. Adding
per-video exceptions would conceal these limits and would not demonstrate generalization.

## What was completed

* A persistent inference subprocess for the public worker, with a parent-enforced timeout, explicit failure,
  process cleanup and recovery. Tests cover an actually hanging inference process and the next successful job.
* The timing watchdog now delays both first-token choice scoring and text generation, counts exercised slow
  calls and checks that later work is skipped. The previous 3.6 s watchdog artifact did not exercise its delay.
* Runtime configs, normative KB and result schema are included in a built wheel and checked outside the repo.
* Docker no longer asks Ubuntu 22.04's standard repository for Python 3.12; it uses a Python 3.12 base. CPU
  setup does not reinstall CUDA-pinned torch from the development freeze. Docker itself remains unverified.
* Verification runs every stage, records exit codes, supports source-hash resume and fails its quality check
  when evidence is missing or a target is not met. Errors during evaluation cannot silently count as success.
* Optional verifier modes now honor catch-all configuration and explicit support/rejection rules. Catch-all
  is disabled in the measured default and has no claimed unseen-type recall.

## Reproduction

On Windows use Python 3.12 (`py -3.12`); on Linux use `python3.12`.

```text
py -3.12 scripts/run.py setup
.venv/Scripts/python scripts/download_weights.py --profile gpu-small
.venv/Scripts/python scripts/run.py verify
.venv/Scripts/python scripts/run.py verify --resume
.venv/Scripts/python scripts/final_report.py --check
```

On Linux replace `.venv/Scripts/python` with `.venv/bin/python`. Training videos and labels must be supplied
under `public/` and `open/`; model weights are not part of Git or the wheel. The full verification includes
378 variants and can take hours. The final `--check` is expected to exit nonzero while gates above remain unmet.

`reports/final/verification.json` records checks actually run. Unit tests, cold timing, socket-guarded offline
inference, HTTP lifecycle, package/CLI equivalence and wheel resources each have separate artifacts. This
does not prove a fresh dependency install, a Docker build, a public URL or a finished frontend. The original
engine task assigns the frontend and real service integration to another part of the team.

## Limits of delivery

The development host has no Docker executable. No Docker success, clean-clone dependency installation or
external deployment is asserted. Source changes are left available for review; unrelated existing changes
are preserved. The public worker uses a hard process timeout, while direct Analyzer remains a soft-budget
API. Timeouts fail explicitly; passing this reliability test does not mean a valid classification is always
returned before five minutes.

## User deadline and robustness coverage

The user explicitly set 12:00 on 2026-10-18, Asia/Qyzylorda (07:00 UTC). The initial full, video-first
robustness fill was stopped to reserve time for scoring and delivery. Existing caches were retained.
`deadline_continuation.json` proves the source snapshot matched the already completed checks before the
scheduling change. The continuation uses variant-first coverage across all 42 videos, stops perception at
11:10 local time and cached-only scoring at 11:40. `summary.json` reports `n_runs`, `n_expected`, coverage and
missing runs; a subset never passes the full robustness gate. Only the actually evaluated rows contribute
to the reported subset metrics. A geometric role-consistency score compares positions to the original
calibration; it does not independently establish that the original role assignment was correct.

To finish the omitted transforms later, run the ordinary full verification (existing perception caches are
reused). The deadline continuation was invoked as:

```text
.venv/Scripts/python scripts/deadline_verify.py --until-utc 2026-10-18T07:00:00+00:00
```

## Expedited finish requested by the user

The user subsequently requested completion as soon as possible. This supersedes the 11:10 / 11:40 schedule
above. The long perception fill was stopped, retaining completed caches. Final scoring was bounded to two
minutes on four videos (1, 2, 3, 4) and three transforms (horizontal flip and rotations +/-10 degrees).
The actual completed run count is in `robustness/summary.json`; its `full_suite_expected_runs` is 378.
This is a limited smoke test, not proof of full robustness or unseen-angle accuracy. No omitted transform
or video is counted as passed. Existing full-data accuracy, API, offline, equivalence and cold-timing checks
are retained because inference code was unchanged. Final wheel/schema checks are repeated for delivery.
