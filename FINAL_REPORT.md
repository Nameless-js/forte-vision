# FINAL REPORT — forte_ai

Generated from `reports/final` by `scripts/final_report.py`.

Hardware: NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`; VLM on.

## Detection, localization, classification

| setting | recall | FP clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold 0.5 | 17/22 | 1 | 0.857 | 29 % / 59 % / 71 % / 82 % | 2.0 | 71 % |
| train, fitted threshold 0.25 | 18/22 | 2 | 0.857 | 39 % / 61 % / 72 % / 83 % | 1.9 | 67 % |
| **leave-one-video-out** | 17/22 | 2 | 0.833 | 35 % / 59 % / 71 % / 82 % | 2.0 | 71 % |

## Time

Evaluation run: mean 1.5 s / video, max 21.7 s (cached perception).

| video | duration s | wall s (cold) | within 240 s |
|---|---|---|---|
| 14 | 142.5 | 110.7 | yes |
| 39 | 78.7 | 61.8 | yes |
| 4 | 72.7 | 70.2 | yes |

Watchdog (VLM slowed by 25 s per call): wall 54.0 s, VLM calls 2, skipped by deadline 1, returned before 300 s: True.

## Robustness

Runs: 12; verdict agreement 83 %; violation timecode within ±3.0 s 100 %; cashier role found 100 %.

| variant | verdict agreement | timecode ±3 s | role ok |
|---|---|---|---|
| hflip | 100 % | 100 % | 100 % |
| rot+10 | 100 % | 100 % | 100 % |
| rot-10 | 50 % | 100 % | 100 % |

## Offline & contract

Offline run: PASSED; network attempts: 0; audit hits: 0; face dependencies: [].
API test: PASSED (server up ✓, 401 without key ✓, 401 with wrong key ✓, 404 unknown job ✓, POST analyze -> job_id ✓, job lifecycle processing -> done ✓, JSON schema + semantics ✓, verdict present ✓, within 5 min ✓, upload deleted after processing ✓).

## Per-video (LOVO)

| id | label | t_label | team type | pred | t_pred | Δt | pred type | ok |
|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | issue_without_count | no_violation | - | - | - | - |
| 2 | violation | 10.0 | handover_without_documents | no_violation | - | - | - | - |
| 3 | no_violation | - | - | no_violation | - | - | - | - |
| 4 | violation | 57.0 | two_clients_cash_mixed | violation | 55.0 | 2.0 | two_clients_cash_mixed | True |
| 5 | no_violation | - | - | no_violation | - | - | - | - |
| 8 | no_violation | - | - | no_violation | - | - | - | - |
| 10 | no_violation | - | - | no_violation | - | - | - | - |
| 11 | violation | 18.0 | workplace_left_unattended | violation | 17.8 | 0.2 | handover_without_documents | False |
| 12 | no_violation | - | - | no_violation | - | - | - | - |
| 13 | violation | 47.0 | accept_without_count | violation | 60.8 | 13.8 | workplace_left_unattended | False |
| 14 | no_violation | - | - | no_violation | - | - | - | - |
| 15 | violation | 15.0 | workplace_left_unattended | violation | 16.4 | 1.4 | workplace_left_unattended | True |
| 16 | no_violation | - | - | violation | - | - | - | - |
| 17 | violation | 7.0 | handover_without_documents | violation | 2.2 | 4.8 | handover_without_documents | True |
| 18 | violation | 20.0 | two_clients_cash_mixed | violation | 19.2 | 0.8 | issue_without_count | False |
| 19 | no_violation | - | - | no_violation | - | - | - | - |
| 20 | violation | 5.0 | workplace_left_unattended | no_violation | - | - | - | - |
| 21 | no_violation | - | - | no_violation | - | - | - | - |
| 22 | violation | 14.0 | workplace_left_unattended | no_violation | - | - | - | - |
| 23 | no_violation | - | - | no_violation | - | - | - | - |
| 24 | violation | 8.0 | workplace_left_unattended | violation | 6.2 | 1.8 | workplace_left_unattended | True |
| 25 | no_violation | - | - | no_violation | - | - | - | - |
| 26 | violation | 9.0 | workplace_left_unattended | violation | 11.0 | 2.0 | workplace_left_unattended | True |
| 27 | no_violation | - | - | no_violation | - | - | - | - |
| 28 | violation | 7.0 | workplace_left_unattended | violation | 9.6 | 2.6 | workplace_left_unattended | True |
| 29 | no_violation | - | - | no_violation | - | - | - | - |
| 30 | violation | 13.0 | unauthorized_in_cash_zone | violation | 13.6 | 0.6 | unauthorized_in_cash_zone | True |
| 31 | no_violation | - | - | violation | - | - | - | - |
| 32 | violation | 5.0 | unauthorized_in_cash_zone | violation | 4.4 | 0.6 | unauthorized_in_cash_zone | True |
| 33 | violation | 6.0 | unauthorized_in_cash_zone | violation | 3.2 | 2.8 | unauthorized_in_cash_zone | True |
| 34 | violation | 13.0 | accept_without_count | no_violation | - | - | - | - |
| 35 | no_violation | - | - | no_violation | - | - | - | - |
| 37 | no_violation | - | - | no_violation | - | - | - | - |
| 38 | violation | 33.0 | two_clients_cash_mixed | violation | 36.2 | 3.2 | two_clients_cash_mixed | True |
| 39 | no_violation | - | - | no_violation | - | - | - | - |
| 40 | violation | 17.0 | unauthorized_in_cash_zone | violation | 3.6 | 13.4 | unauthorized_in_cash_zone | True |
| 43 | no_violation | - | - | no_violation | - | - | - | - |
| 44 | violation | 16.0 | suspect_note_mishandled | violation | 16.4 | 0.4 | workplace_left_unattended | False |
| 45 | no_violation | - | - | no_violation | - | - | - | - |
| 46 | violation | 11.0 | personal_items_at_workplace | violation | 11.2 | 0.2 | personal_items_at_workplace | True |
| 47 | violation | 68.0 | accept_without_count | violation | 55.0 | 13.0 | two_clients_cash_mixed | False |
| 48 | no_violation | - | - | no_violation | - | - | - | - |

## Definition of Done gates

These are internal engineering targets, not a claim about the jury score.

| gate | status | evidence / limitation |
|---|---|---|
| 1. Detection | UNMET | LOVO TP=17/22, FP=2; rule design used this dataset |
| 2. Localization | UNMET | within 2s=0.5882352941176471, within 5s=0.8235294117647058 |
| 3. Classification | UNMET | type accuracy=0.7058823529411765; types are team-assigned |
| 4. Grounding | PASSED | full unit test artifact includes verbatim KB quotation checks |
| 5. Robustness | UNMET | scope=subset, runs=12, agreement=0.8333333333333334, time=1.0, role=1.0 |
| 6. Time | PASSED | cold timing and actually exercised slow-inference watchdog; hard process timeout tested separately |
| 7. Offline & local | PASSED | full perception/VLM path with socket guard; see offline_report.json |
| 8. Contract | PASSED | real HTTP lifecycle plus package/CLI evidence equality |
| 9. Reproducibility | NOT VERIFIED | isolated wheel resources=True; Docker unavailable, fresh dependency installation not verified |
| 10. Docs | NOT VERIFIED | see narrative for unmet gates and exact reproduction commands |

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
