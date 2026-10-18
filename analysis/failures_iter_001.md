# Failure analysis — iter_001 (M1 baseline)

Baseline: rules only, no VLM, cached perception (Grounding DINO tiny @480 px, own ByteTrack, RTMPose-s),
first calibration (hull + half-plane cashier zone). Config threshold 0.5.
Measured (reports/iter_001): **recall 13/22, FP 17/20**, localization within ±2 s 38 %, ±5 s 85 %.

The headline "recall" is inflated: of the 13 "detected" violation videos, 9 were detected by a candidate that
has nothing to do with the labeled event (mostly phantom `phone_at_workplace` and `cashier_left_during_service`).
Only 30 (intrusion @11.6 vs 13), 33 (intrusion @9.8 vs 6) and partly 15/24/26 were near the real event.

## Root causes (each FP/miss is attributed to one primary cause)

| cause | layer | videos affected | evidence | fix (iteration) |
|---|---|---|---|---|
| **C1. Phone false positives** — open-vocabulary "phone" boxes on the laptop screen corner, the counting-machine display, an ID card or a banknote stack held at chest height; rule fired after 1 s within 6 % of the diagonal of any wrist | perception + rule | FP 5, 12, 16, 19, 21, 35, 37, 39, 45, 48; spurious "TP" 2, 4, 20, 32, 38, 47 | analysis/perception_qa/fp_sheet.jpg (id5/21/39/16 tiles: the "phone" box sits on the laptop corner / card) | min score 0.45, landmark-adjacency filter, tighter hand radius (4.5 %), pose required, 2 s duration (iter 2); class kept for the test set but no longer fires on training clean videos |
| **C2. Cashier zone geometry** — zone = dilated hull of full cashier boxes ∩ half-plane of an unstable counter line; any stand-up, lean or track-id switch "left the zone" | roles | FP 8, 14, 25, 27, 29, 31; spurious 13, 15, 24, 26, 44 | fp_sheet.jpg (id8/25: zone hull swallowing the client seat; counter line through the cashier) | counter line from a seated window anchor, radius zone around the seat + workplace anchors (iter 2), first-stationary-dwell seat (iter 10) |
| **C3. Intrusion = any client hand over the line** — in this barrier-less scene every normal handover crosses the desk midline | rule | FP 3, 12, 14, 29, 31; spurious 24, 25, 26, 44 | fp_sheet2.jpg (id3/14/21: client leaning to pass an item) | body-depth intrusion only, track age/score/pose guards, 2.5 s dwell (iter 3–11) |
| **C4. Duplicate / phantom person tracks** — upper-body + full-body boxes of one person, chairs and jackets, reflections in the glass wall create extra tracks that become "clients" or "intruders", and collapse the counter line onto the cashier | perception | FP 3, 5, 14, 19, 25, 29, 35, 39; all R9a two-client FPs | failures_iter_004.txt (dist_cc 0.004–0.014 in 3, 8, 13) | person NMS with containment (cache p4, iter 5), track detection-score gating, pose-backed validity (iter 6–8) |
| **C5. Missing rule families** — 4 departure violations with **no client** (11, 22, 24, 28), 4 entries into an **empty** workplace (30, 32, 33, 40), eating at the desk (46), note merged back after a machine count (44), acceptance counted only after the client left (34), collector bag without document (17) | taxonomy | MISS 11, 22, 28, 34, 40, 46, 17; mis-explained 24, 30, 32, 33, 44 | analysis/review/*.md, analysis/taxonomy.md | M2 rule rewrite from the reviewed taxonomy: R1b/R1c departures, R10 empty-start entry, R3b personal items (cup class), R11 suspect note, R6b late count, R8 document (iter 4–12) |
| **C6. Handover detector** — "hands within reach" fires continuously for two people seated across a desk | events | MISS 1 (issue @22 never isolated), 18 | handover debug of X-1 (wrists 9–24 px from the line all the time) | reach-based handover: wrist extended ≥10 % of the diagonal ahead of the torso and close to/past the line (iter 1→2) |
| **C7. Counting detector** — periodic hand motion without cash evidence counted as "counting", hiding issue/accept-without-count | events | MISS 1, 13, 34, 47 | counting segments in X-1 at 5–11 s (booklet/hands) | counting = sustained machine run with cash around it OR periodic motion with cash at the hands (dilated ±2 s) (iter 4–5) |

## Per-video

| id | label | outcome | primary cause | note |
|---|---|---|---|---|
| 1 | V@22 | miss | C6/C7 | only low-conf no_id_check; issue at 22.5 s not isolated |
| 2 | V@10 | spurious TP | C1 | phone @11.6 is the ID card; real type: handover without documents |
| 3 | clean | FP | C3/C4 | client leaning + duplicate track = "intrusion" |
| 4/47 | V@57/68 | spurious TP | C1 | phone FPs; real: second client while first cash out (57), accept without count (68) |
| 5/48 | clean | FP | C1 | phone FPs on card/laptop |
| 8 | clean | FP | C2/C4 | cashier crouching to a drawer = "left"; client hand = "intrusion" |
| 11 | V@18 | miss | C5 | departure without client — no rule |
| 12 | clean | FP | C1/C3 | |
| 13 | V@47 | spurious TP | C2 | "left" at 58.6; real: bag cash stored uncounted @46 |
| 14 | clean | FP | C2/C3/C4 | 142 s video, many phantoms |
| 15 | V@15 | ~TP | C2 | "left" @6.8 (8 s early); real departure @15 with bag left on the desk |
| 16, 19, 21, 35, 37, 39, 45 | clean | FP | C1 | phone FPs |
| 17 | V@7 | miss | C5 | collector bag without document |
| 18 | V@20 | miss | C6/C4 | second client not separated |
| 20 | V@5 | spurious TP | C1 | real: open safe left unattended |
| 22, 28 | V@14/7 | miss | C5 | departures without client |
| 24, 26 | V@8/9 | ~TP | C2/C5 | "left" near the label by accident of geometry |
| 25, 27, 29, 31 | clean | FP | C2 | legitimate departures/standing |
| 30, 33 | V@13/6 | TP-ish | — | intrusion near the label |
| 32 | V@5 | spurious TP | C1 | real: entry into empty workplace |
| 34 | V@13 | miss | C5/C7 | count started as the client left |
| 40 | V@17 | miss | C5 | entry into empty workplace (settling) |
| 44 | V@16 | spurious TP | C2 | real: suspect note merged back |
| 46 | V@11 | miss | C5 | eating/drinking at the desk |

## What M1 proved

The end-to-end chain (decode → perception → roles → rules → evidence JPEGs → ТЗ JSON) is valid on all 42
videos (0 schema problems), localization of the events that ARE found is reasonable (median 3.4 s), and the
remaining work is in roles/geometry and in the rule families — which is what iterations 2–12 addressed
(PROGRESS.md iteration table).
