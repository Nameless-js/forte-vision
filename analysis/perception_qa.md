# Perception QA (Phase 3)

All numbers measured on the development machine (RTX 4060 Laptop 8 GB, Ryzen 5 7535HS), profile `gpu-small`,
perception cache version `p4`. Annotated sheets referenced below are in `analysis/perception_qa/` and
`analysis/prompt_probe/` (gitignored images; regenerate with the scripts named).

## Detector choice: zero-shot Grounding DINO tiny, scene-tuned phrases

Decision rule from TASK §10 Phase 3: zero-shot vs fine-tuned by measured precision on a hand-checked set.

* **Phrase probe** (`scripts/prompt_probe.py`, 6 frames from 4 videos × 40 phrases, top-2 boxes drawn per
  phrase, checked visually):
  * counting machine: "black printer" 0.71–0.82 on the machine in every frame; "money counting machine"
    0.46–0.50; "banknote counter"/"currency counter" grab the whole desk (rejected);
  * safe/cabinet: "metal cabinet", "grey metal box", "locker" 0.41–0.64 on the safe; "safe" alone picks the
    laptop (rejected);
  * cash: "banknotes", "money", "paper bills" find the hand-held stacks at 0.25–0.38; "cash" picks the
    counting machine (rejected); a green collection bag is also called "banknotes" (handled by the bag class);
  * phone: all phrases fire on the laptop corner and ID cards at 0.3–0.6 → phone needs score ≥ 0.45, landmark
    adjacency filtering and a 2 s hold in the rules;
  * document: "document" grabs the laptop screen and the foreground desk → area cap 4 % + landmark suppression;
  * bag: "money bag"/"sack" → the counting machine at 0.65–0.83 (!) → small objects inside a landmark are
    suppressed (cross-class suppression in `detector.py`);
  * person: robust (0.55–0.85 on real people) but also 0.4–0.6 on chairs, jackets and glass reflections.
* **Fine-tuning was not adopted**: pseudo-labels would come from this same detector, inheriting exactly the
  confusions listed above, and a closed-set model trained on one staged room loses the open-vocabulary
  robustness the final different-angle video needs. The confusions are instead handled by geometry
  (landmark suppression, area caps) and by the pose-backed person validity in Layer B. Recorded in
  ARCHITECTURE.md §1.

## Speed (`scripts/bench_detector.py`, 40 frames of X-1)

| detector input (short side) | batch | ms/frame | peak VRAM |
|---|---|---|---|
| 464 | 2 | 127 | 1.97 GB |
| 464 | 4 | 111 | 2.95 GB |
| 600 | 2 | 176 | 2.95 GB |
| 800 (processor default) | 2 | 277 | 4.22 GB |

Chosen: **480 px, batch 2** (default 800 px upsamples the 464-px-wide source for no gain).

Full perception over all 42 videos (cache p4, `analysis/perception_qa/timings.json`):

| metric | value |
|---|---|
| total wall | 1054 s for 1444 s of video |
| wall / duration | mean 0.77, max 1.21 |
| detector | 0.141 s per sampled frame |
| RTMPose | 0.016 s per sampled frame |
| longest video Х-14 (142.5 s) | **114.5 s** perception wall (detect 102 s, pose 10.6 s) |
| person tracks per video | min 2, median 4, max 13 |

## Visual QA findings that changed the design

1. `fp_sheet.jpg` (iter 1): the first cashier zone (dilated hull of full boxes) swallowed the client seat;
   the counter line passed through the cashier → replaced by the seated-anchor bisector and a radius zone.
2. `fp_sheet2.jpg` (iter 2): duplicate boxes of the same person (upper body inside full body) created phantom
   tracks → person NMS with containment ≥ 0.7 (cache p4).
3. `empty_start_check.jpg` (iter 7): in the empty-workplace intrusion videos the entrant is detected at
   0.71–0.77 already in the doorway, while glass-wall figures sit at 0.35–0.5 → behavioural (seat/dwell)
   rather than score-only gating.
4. `seat_check.jpg` (iter 9): the cashier stands at the glass door for several seconds before leaving; in
   this projection the door is as close to the counting machine as the seat is → the seat is the first
   stationary dwell of the cashier track, not an object-anchored median.

## Known perception limits (→ LIMITATIONS.md)

* person boxes on chairs/jackets/reflections up to 0.88 with a hallucinated full pose (RTMPose always returns
  17 keypoints) — mitigated, not eliminated;
* phone/document/id-card classes are unreliable at 464 px source width; the rules use them only as soft
  evidence, and Layer C (VLM) arbitrates.
