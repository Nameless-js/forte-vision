# LIMITATIONS — known failure cases and boundaries

The engine outputs **hints for a human reviewer**, not legal or disciplinary conclusions (ТЗ §7). Every
description states only what is visible; confidence is reported per violation.

## What is never claimed (not visible on video)

* Correctness of postings, reconciliations, amounts, balances — any system state.
* Authenticity of banknotes; the content, validity or ownership of documents; whether a signature matches.
* Person identities. People exist only as per-video track ids with roles (cashier / client / collector)
  assigned from behaviour. **No face recognition is used or installed** (checked by `scripts/offline_check.py`).
* Audio events (no audio is read).
* Whether a receipt / confirming document was actually issued in the system (п. 19 пп. 6, п. 31 пп. 6).
* Whether the safe is locked (a key turn is not reliably distinguishable from touching the door).

## Known hard cases from the training set (failure analyses in analysis/ and reports/)

1. **Safe door state** (video 20): "walked away from an open safe" relies on a weak geometric proxy
   (safe-dwell then walk-away with cash out) arbitrated by the local VLM looking for an open door. A closed
   dark-fronted safe can be mistaken either way.
2. **A rejected note merged back into the counted pack** (video 44): geometrically identical to the correct
   handling (note kept aside, videos 43/45). The rule fires at low confidence and relies on the VLM; this is
   the most fragile detection in the engine.
3. **Departure after securing valuables** (clean 25/27 vs violations 11/22): discriminated by cumulative
   hands-at-safe time before leaving. A cashier who locks the safe *quickly* (< `securing_min_s`) and leaves
   may be flagged; one who fiddles with the lock for long without storing anything may be missed.
4. **Phone-like objects**: dark rectangular items (tablet/folder/card holder) in the cashier's hand can
   produce a phone candidate; counting at chest height can resemble phone use. The VLM rejects most of these;
   residual risk remains on the CPU profile (no VLM).
5. **People behind the glass walls and reflections** can create short person tracks; they are filtered by the
   seated-anchor and depth requirements, but a person standing directly behind the glass near the door for a
   long time could still be mis-read as a second client.
6. **Track-id switches** on long occlusions: the cashier's track can split; rules guard against the known
   consequences (phantom intrusion at video start, phantom second client), at the cost of ignoring a real
   intruder who appears in the very first second of a video.
7. **Collector protocol** is modelled only as bag-handover + inspection + document heuristics on one training
   video (17); unusual collection procedures may be mis-typed as client operations.

## Engineering limits

* **5-minute budget**: measured end-to-end ≤ 240 s on the longest training video (142.5 s) on an RTX 4060
  Laptop (reports/timing). On slower hardware reduce `video.sample_fps`, then the detector input size, then
  disable the VLM catch-all (INTEGRATION.md). The soft watchdog stops starting new VLM work after its cutoff; it cannot interrupt an active call.
  The reference worker adds a 270 s process timeout and records an explicit failure on timeout.
* **CPU profile**: no VLM verification → more false positives and template descriptions; expected to be used
  only when no NVIDIA GPU exists.
* **Docker**: the image is defined and reviewed (`Dockerfile`), but could not be *built* on the development
  machine (no Docker on native Windows 11 Home without WSL); the build is expected to work on a standard
  Linux Docker host, and `scripts/api_test.py --base-url` can validate a running container.
* **Suspended clauses**: п. 11, 13(3), 14, 16 of ПП НБ РК № 14 act in a temporary wording until 01.01.2027
  (Resolution № 88 of 24.12.2024). Cards citing п. 16 quote the temporary wording and say so (SOURCES.md).
* The final jury video is announced to be shot **from a different angle**: all geometry is relative
  (per-video calibration, no pixel constants) and the robustness suite (flips, rotations, perspective,
  scale, brightness, crop, re-encode) measures the degradation — see reports/robustness. A radically
  different scene (several desks, a physical barrier with a transfer tray) would reduce rule coverage to the
  types that do not depend on the single-desk layout; the VLM catch-all remains active in that case.

## Completion-audit limitations

* The latest complete evaluation and unmet quality targets are recorded in FINAL_REPORT.md. A correct
  video-level verdict can still correspond to the wrong event or type (notably videos 13, 44 and 47).
* Cash is not reliably detected in videos 2 and 34, preventing handover-driven rules from proposing events.
  In video 20, safe interaction geometry can miss the open-safe candidate. A sustained wrist-withdrawal
  experiment (iter_020) did not improve metrics and was reverted.
* The laptop screen heuristic and safe-interaction duration are visual proxies, not proof of system locking
  or a safe being locked. Departure 22 and clean clip 23 remain difficult to separate reliably.
* In an initially empty workplace, a cashier arriving for legitimate work (31) can look like an intruder (32).
  The system has no identity or access-control data. It must not be interpreted as determining legal authority.
* Rules were designed from all open videos. LOVO refits the verdict threshold with duplicate-content grouping;
  it is not a held-out validation of rule discovery, prompts, taxonomy or detector phrase selection.
* Augmented views test sensitivity to transformations of the existing recordings. Even a full augmentation
  suite cannot prove performance on a genuinely new physical camera angle or a different cash desk.
* The 240 s cold benchmarks exclude service startup/warmup; the public worker's 270 s hard timeout includes
  child startup but excludes HTTP upload and waiting behind other queued videos. No concurrent throughput SLA
  is established on one GPU. Timeout yields `failed`, not a fabricated `no_violation`.
* RTMPose used ONNX Runtime CPU fallback on the development host; the CUDA provider was unavailable there.
* A wheel resource/import check uses the existing dependency environment. A fresh install and Docker run are
  separate checks and cannot be claimed from a successful wheel build.
