# Completion failure review

Evidence: reports/final/results/*.json, per_video.csv and metrics.json. These are development results; the labeled timestamps were used only for this analysis and evaluation.

## Missed positive videos at deployed threshold 0.5

* Video 1: label 22.0 s, team type issue_without_count.
* Video 2: label 10.0 s, team type handover_without_documents.
* Video 20: label 5.0 s, team type workplace_left_unattended.
* Video 22: label 14.0 s, team type workplace_left_unattended.
* Video 34: label 13.0 s, team type accept_without_count.

## Root causes inspected

* Video 1: eligible issue-without-count candidate at 22.6 s has confidence 0.436; the 0.5 deployed threshold rejects it. Lowering the global threshold changes false alarms and held-out threshold behavior, not perception quality.
* Videos 2 and 34: no handovers or rule candidates were produced. Small cash detections are absent/sparse. The late-count pattern in 34 is also masked by the client episode lasting through counting. There is no reliable evidence from which a verdict threshold alone can recover these events.
* Video 20: the safe interaction is observed but the R12 geometry gates fail to propose an open-safe event. Iteration 020 tested sustained wrist withdrawal as an alternate retreat cue. It did not improve aggregate detection/localization/classification and was reverted.
* Video 22: R1b proposes 15.2 s and the VLM supports it (p=0.659), but the laptop-screen heuristic blocks it. Clean 23 and other legitimate departures use similar cues. A dark screen is not proof of system locking or safe security.
* Clean video 31: R10 flags 9.4 s as entry into an empty cash workplace. Without identity/access-control information, legitimate arrival and intrusion can look alike; the model confidently agrees with the visible entry without establishing authorization.
* Videos 13, 44 and 47 can receive a correct video-level verdict from the wrong event/type. They are not evidence of successful detection of the labeled violation.

## Why the quality targets remain unmet

Previous iterations include rules-only refinements, generative JSON VLM verification, and contrastive 2B/4B verification. The measured 4B approach improved false alarms but did not meet the strict 22/22, <=1 FP, timecode and classification targets. Further threshold changes on these same 42 videos cannot establish independent generalization. Improved small-object annotations/detection, safe-state evidence and an independently filmed validation set are needed. No per-video lookup or timestamp exception was added.

## Verification fixes

The previous 3.6 s timing watchdog patched only text generation while default verification uses choice logits. The revised test patches both paths, records the actual delayed-call count, and checks later work is skipped. Hard hangs are tested separately at the spawned-process boundary; timeouts fail explicitly. Wheel resource isolation, real API lifecycle, positive-video CLI/package equality, and uncached socket-guarded offline inference have separate artifacts under reports/final/.
