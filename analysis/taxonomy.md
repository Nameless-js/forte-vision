# Violation Taxonomy — ForteBank Cash-Desk Engine (FINAL, team-assigned)

> **Status: FINAL.** These types are **assigned by our team**, not given by the organisers.
> The organisers supplied only one labeled timecode (`t_label`) per violation video with no type.
> Types were induced from frame-by-frame review of all 22 labeled events and all 20 clean videos
> (`analysis/review/<id>.md`, frame sheets in `analysis/review/frames/<id>/`), then adversarially
> verified: an independent skeptic re-opened the frames for every video and **agreed with the
> assigned type and event time in all 22 cases** (confidence 0.85–0.95 per video).
> `t_event` = the precise second the violation becomes visible per the final arbitration;
> all times carry ±0.5 s sampling tolerance (0.5 fps frame grid around labels).
>
> **Design constraint:** the final test videos are shot from a different angle, so every pattern
> below is defined by **relations** (cashier zone, desk/counter line, hands, object custody),
> never by pixel positions. Two mirrored training layouts (A: cashier near-side back-to-camera;
> B: cashier far-side facing camera) already force this.

Labeled events covered: ids 1, 2, 4, 11, 13, 15, 17, 18, 20, 22, 24, 26, 28, 30, 32, 33, 34, 38, 40, 44, 46, 47 (note: 4 and 47 are the **same file** with two separate events).

---

## Type 1 — `issue_without_count`

- **Russian name:** Выдача наличных без пересчёта в присутствии клиента
- **Definition:** The cashier hands cash to the client while no counting episode (hand leafing ≥3 s, or a completed machine pass: hopper feed → run → stacker retrieve) covered that cash in the client's presence in the preceding ~20 s window.
- **Observable pattern:** Cash blob transitions cashier-hands → client-hand across the desk midline: cashier wrist reaches >50% of desk depth, wrists converge 0.5–1 s, blob ends on the far side, cashier wrist retracts empty — with **no preceding count episode**. In video 1 the stack lay motionless on the counting-machine TOP at 14–19 s (no pass-through: no hopper feed, no run, no stacker retrieve) and was only fanned ~1.5 s at face level before the handover.
- **Timecode policy:** Omission anchored at the **first frame of the cashier's arm extension** with the cash toward the client (hand contact ~+0.5 s). Video 1: label 22 = last frame before extension; extension 22.5; contact 23.0. A contact-based detector firing at 23.0±0.5 is acceptable.
- **Rule card id:** `issue_without_count`
- **FP risks (clean-video evidence):** Returning an ID card/receipt uses the same arm extension (object is card-sized white, not a note stack) — clean 5 @55, 48 @55; a brief fan/show of the stack **after a genuine count** must not fire; the long reach to the counting machine (clean 3 @17–18) mimics a cross-desk handover; acceptance in the opposite direction (video 1 @10) is not an issuance.
- **Detection cues:** Cash-track state machine client→cashier→machine→cashier→client; count-episode detector = both wrists together ≥3 s with periodic leafing, OR hopper feed + stacker retrieve with notes moving; flag the cashier→client transition when no count episode exists in the window; genuine counts run several times longer than the ~1.5 s fan seen here.

| id | t_label | t_event | conf | note |
|----|---------|---------|------|------|
| 1 | 22 | 22.5 | 0.85 | Skeptic frame-verified: stack motionless on machine top 16–18 s, lifted off at 19.5–20; only static grip + ~1.5 s fan 20.5–22; extension 22.5, contact 23.0, client holds notes 23.5. Secondary readings: possible retention of part of the notes (yellowish item in right hand @25); the earlier acceptance @10 was itself uncounted. |

---

## Type 2 — `accept_without_count`

- **Russian name:** Приём наличных без полистного пересчёта
- **Definition:** Cash enters the cashier's custody (from a client, or extracted from a collection bag) and is disposed of — put down while the operation continues, stored in the safe, or counted only AFTER the client left — with no leaf-by-leaf or machine count in the presence of its source.
- **Observable pattern:** Handover client→cashier (or bag→desk) followed within seconds by put-down / safe-insert with no count episode in between; OR machine feed starting only after the client's track left the desk zone. Time-in-hand before at-rest is <~3 s (vs ≥8 s when counting).
- **Timecode policy:** Omission anchored at **the moment the uncounted cash is disposed of** — put down on the desk while the cashier resumes typing (47 @68.0), machine feed starting with the client already at the door (34 @12.5–13.0), or uncounted bundles carried to the safe / safe door opening (13 @46.0; cash inside at 50).
- **Rule card id:** `accept_without_count` (video 13 alternative card: `collection_bag_unchecked`)
- **FP risks (clean-video evidence):** Squaring/tidying a bundle 1–2 s right AFTER a genuine count (clean 39 @28–29 & 64–65, 43 @31–33); machine counting with hands idle looks like "no counting" to motion-only detectors (clean 19 @15–20); carrying already-counted cash to the safe (clean 5 @49–50, 35 @39–43, 39 @32–33, 27 @9–11); stowing the EMPTY bag at the safe (clean 14 @41–42).
- **Detection cues:** Measure time between cash receipt and at-rest; count episodes as in Type 1; gate the "in presence" clause on the client track being in the desk zone; bag variant: cash extracted from a bag reaches the safe ROI with the machine ROI never visited and no ≥8 s hand count.

| id | t_label | t_event | conf | note |
|----|---------|---------|------|------|
| 34 | 13 | 12.5 | 0.85 | Machine count starts only after the client turned away (11.5) and reached the door; hopper insertion at 13.0 (label). Also no ID shown at any time (secondary `no_id_check` reading, omission moment ~8.0–8.5, 5 s before the label — does not explain the labeled moment). |
| 47 | 68 | 68.0 | 0.8 | SAME FILE as video 4 (two events). Blue bundle held raised ~1.5–2 s, lowered to the desk at 68.0 next to client 1's beige cash, then typing; machine never touched. In-video contrast: operation 1 had an 8 s hand count. |
| 13 | 47 | 46.0 | 0.85 | Collection-bag contents → safe uncounted: bundles out @22/25, ~1 s glance @44, at the safe with cash @46.0, inside @50; the counting machine is never used. Alternative card `collection_bag_unchecked`; label timing (35 s after bag opening, at the safe) decides for the no-count reading. |

---

## Type 3 — `handover_without_documents`

- **Russian name:** Передача ценностей без проверки документов (без удостоверения личности / инкассаторская сумка без сопроводительных документов)
- **Definition:** Merged cluster (same omission shape): valuables change custody with NO document event — (a) client cash accepted without an identity document presented and examined first; (b) a collection bag accepted without the accompanying document, without seal/tag inspection, with the collector leaving immediately.
- **Observable pattern:** A valuables handover (cash blob or bag crosses to the cashier) with zero document-presentation patterns in the surrounding window: no small card/paper held at the cashier's chest/face ≥2 s beforehand, nothing passed back, no signing pose; for the bag additionally: no two-handed inspection of the bag top, and the collector exits <5 s after release (17: enter 3.5 → release 8.5 → exit 11).
- **Timecode policy:** Omission anchored at **the moment of acceptance** — the cashier's hand closes on the cash (2 @10.5; reach 10.0, cash laid at 9.0) or both hands hold the bag in the custody transfer (17 @8.0; bag placed 6.5–7.0 = organiser label).
- **Rule card id:** `no_id_check` (client cash) | `collection_bag_unchecked` (collection bag) — selected by carried-object class at fire time.
- **FP risks (clean-video evidence):** A legitimate ID presentation looks IDENTICAL to a cash handover until what follows (clean 3 @7–8: card held at face, then parked — vs cash going to the machine); the compliant collection handover (clean 16) matches video 17 until +5–8 s — there the document is examined @10–14 BEFORE the bag is released @16–17 and the bag-top inspection runs ≥5.7 s. **Test the window around the handover, never the placement frame alone.**
- **Detection cues:** Document-event detector (small bright card-sized object client→cashier, held at chest/face ≥2 s, usually returned/parked); bag-vs-notes classifier (cloth bag with rigid white top bar); fire on the first valuables handover with no document event since the counterpart entered; bags additionally need the missing seal inspection (two cashier wrists in bag bbox ≥3 s absent) and the collector's early exit.

| id | t_label | t_event | conf | note |
|----|---------|---------|------|------|
| 2 | 10 | 10.5 | 0.85 | No document at any time before/after cash pickup (frame-verified across the whole clip); object identified as cash only via machine loading @14 — an ID card is visually identical at this resolution; machine feed starts with the client still seated, so `accept_without_count` is excluded for the label; clip truncated at 17.1 s. |
| 17 | 7 | 8.0 | 0.9 | Collection bag handed with no accompanying document, no seal/tag inspection: both hands on the bag top bar at 8.0 (simultaneous hold = custody transfer), collector releases 8.5 and is gone by 11 s; cashier's post-departure bag handling (12–14 s, bag kept flat, unopened) does not satisfy the protocol. |

---

## Type 4 — `workplace_left_unattended`

- **Russian name:** Рабочее место / ценности оставлены без присмотра (кассир ушёл; наличные или открытый сейф без кассира)
- **Definition:** Merged cluster (identical departure action; the desk/safe state selects the rule card): the cashier separates from the active workplace — stands, walks to the door, exits the room — or exposed valuables (cash on the desk, open safe) are left with nobody within reach. In ALL seven stagings no client is present, so rules must NOT require a client track.
- **Observable pattern:** Cashier track leaves the desk polygon toward the door ROI and crosses the door line while the workplace stays active (lit laptop, machine on, items out). Aggravating state at separation: a cash object remains on the desk (15: collection bag; 26: banknote stack) or the safe door stands open (20: open from 2.0 s, never closed, cashier sits at the desk with her back to it).
- **Timecode policy:** Action anchored at the **FIRST frame the cashier is upright, detached from the last workplace contact and oriented/moving toward the exit** (not the door crossing): 11 @18.0–18.5 (last machine touch), 22 @14.0–14.5 (hand off safe 13.5, torso turns), 24 @8.0 (door opened; zone exit 6.0 also defensible), 28 @7.0 (upright, turned away), 26 @9.0–9.5 (rising with cash out), 15 @15.0 (walking to exit, bag on desk), 20 @4.5–5.0 (first frame separated ≥1 m from the open safe). Zone-exit detectors land within ±2 s of all labels; room-empty detectors fire 2–3 s late.
- **Rule card id:** `cash_left_unattended` (cash on desk / safe open at separation: 15, 20, 26) | `workplace_left_unsecured` (clean desk: 11, 22, 24, 28) | `cashier_left_during_service` (client present — branch kept for test videos, not staged in the train set).
- **FP risks (clean-video evidence):** Cashier walking to the safe/machine and staying in the zone (clean 5 @47–53, 25 @6–17); proper end-of-shift exit AFTER securing — desk clear + safe closed/locked before the door (clean 12 @18–36, 23 @4.5–13, 25 @19–27, 27 @14–22, 29 @6.5–13, arrival 31); carrying cash to the safe looks like leaving with cash (clean 21 @6–8, 27 @9–11); machine feed makes cash "disappear" (clean 10 @7–8); track loss from exposure shifts (11 @16.5, 12 @~33); seat-based cashier-absent rules fire throughout Layout-B videos.
- **Detection cues:** Desk polygon + door ROI + safe-door state classifier + cash-blob detector. Stand-up signature (bbox height jump, hip rise) → monotonic centroid motion to door → door crossing; workplace-active evidence (bright laptop ROI, machine LED, objects out). Alarm = (no person in desk zone ≥2–3 s AND workplace active) OR (cash-on-desk / safe-open AND nobody within ~1 m sustained ≥1.5–2 s). **Never condition on a client.**

| id | t_label | t_event | conf | note |
|----|---------|---------|------|------|
| 11 | 18 | 18.5 | 0.8 | Laptop + counting machine (blue LED) left on; last workplace contact = hand on machine top @18.0–18.5, detached @19.0, exits @22–24, room empty @25. Desk items unverifiable as cash → card `workplace_left_unsecured`. Exposure shift @16.5 is lighting, not an event. |
| 22 | 14 | 14.5 | 0.8 | Safe keyhole handled 9–13.5 (locking motion, door never gapped); upright detached @14.0, torso turns to door @14.5, exits 17–17.5; room empty to clip end with the laptop lit. |
| 24 | 8 | 8.0 | 0.85 | Label = door-open instant (handle bar swung @8.0); desk-zone exit at 6.0 also defensible; laptop open, folder on desk; room empty 12–14.7. |
| 28 | 7 | 7.0 | 0.85 | First frame fully upright and turned to the door @7.0, hand only trailing on the desk edge; laptop display stays bright in the empty room. Hands together in the doorway @10–12 hidden (phone neither confirmed nor excluded). |
| 15 | 15 | 15.0 | 0.9 | Green collection bag + paper left in the open on the desk; left seat 8.5 but stayed in zone at the cabinet until ~13.5; walking to exit @15.0; room empty from ~17–18 with the bag out. Card `cash_left_unattended`. |
| 26 | 9 | 9.5 | 0.95 | Banknote stack laid on the desk @8.0 after a hand count; rise onset @9.0, half-risen oriented to door @9.5; cash out of reach @10.5; room empty ~15 to end with cash on desk. Card `cash_left_unattended`. |
| 20 | 5 | 4.5 | 0.85 | Safe-open variant: door swung open @2.0, never closed to clip end (~11.6 s); first frame separated ≥1 m from the open safe @4.5; label 5.0 = cashier reaches the desk with her back to the open safe, then sits and counts the retrieved cash. Card `cash_left_unattended`. |

---

## Type 5 — `unauthorized_in_cash_zone`

- **Russian name:** Посторонний в зоне кассира
- **Definition:** A person who is not the operating cashier enters the cashier's working zone (door → behind-desk strip → machine/safe corner) — in all four stagings while the workplace is unattended or the cashier is busy at the machine — and settles there (sits at the desk, parks personal items, touches equipment).
- **Observable pattern:** Operator position empty (or held by a different track) + a new track crosses the door line and reaches the desk/equipment strip; dwell, chair pull, seating and equipment contact confirm. In Layout B the door opens directly into the working zone.
- **Timecode policy:** Action anchored at the **first frame the non-cashier track is fully inside the cash zone**: 30 @13.0 (inside the door while the cashier stands at the machine), 32 @4.5 (fully inside, walking to desk; label 5 = at the chair), 33 @5.5 (standing in the safe/machine corner; label 6), 40 @17.5 (sits at the desk, hand to equipment — organisers labeled the settling, not the 4 s entry). Confirmation: seating (32 @8.5–9, 33 @8.5–9, 40 @18) and equipment contact (32 @14, 33 @9, 40 @17.5–25).
- **Rule card id:** `unauthorized_in_cash_zone`
- **FP risks (clean-video evidence):** The cashier herself entering/returning (clean 31 @3–8: the first person who takes the operator seat and runs the equipment IS the cashier) — needs track history / appearance re-ID, not clothing; clients walking to the far chair while the cashier is seated (all client videos); the collector standing at the desk end with his bag overlapping the machine in 2-D (clean 16 @4–8); silhouettes behind the glass partition.
- **Detection cues:** Maintain a cashier-present state from operator-seat/equipment occupancy history; per-layout zone polygon (safe + machine corner + behind-desk strip); alert when a track born in the door ROI reaches the polygon while cashier-absent (or ≠ cashier track) sustained ≥1–1.5 s; escalate on seating or wrist-in-equipment-ROI; mask everything beyond the glass line.

| id | t_label | t_event | conf | note |
|----|---------|---------|------|------|
| 30 | 13 | 13.0 | 0.9 | Man in dark jacket fully inside the door @13.0 while the cashier is occupied at the counting machine (chair empty, pushed back); steps to the chair 13.5, hand on chair back 14.5–15, dwells through 18. |
| 32 | 5 | 4.5 | 0.75 | Enters the empty room (no cashier ever present), fully inside @4.5, at the chair @5 (label), sits 8.5–9, handles the counting-machine hopper/stacker 13–21. Entrant's clothing matches the usual cashier — role decided from the empty operator seat + staging logic, not clothing. |
| 33 | 6 | 5.5 | 0.75 | Enters the unattended room; fully inside the safe/machine corner @5.5, dwell @6 (label), chair pull 6.5–8, sits 8.5–9, hand on the device ≥5 s from 9.0; second man watches from the door 12–14.3. |
| 40 | 17 | 17.5 | 0.7 | Enters with personal bag (on desk against machine @10) and jacket (on desk @15), touches safe corner @8; organisers labeled the **settling** — begin-to-sit + first equipment reach @17.5, seated 18.5, handles device 19–25. Secondary card `personal_items_at_workplace`; "cashier arriving in street clothes" reading not fully excluded. |

---

## Type 6 — `two_clients_cash_mixed`

- **Russian name:** Наличные двух клиентов одновременно / второй клиент при незавершённой операции
- **Definition:** A new client enters or is served while the previous client's operation is still open — the previous cash is still out on the desk (not stored, not returned); the two clients' cash can end up side by side on the cashier's side.
- **Observable pattern:** `cash_on_desk` state persists from client A's operation beyond A's exit (or while A is still seated with an open operation); a NEW, appearance-different track crosses the door and reaches the desk while the state holds. Hard confirmation: two distinct bundles simultaneously on the cashier's side (4/47 @66–68: beige + blue side by side).
- **Timecode policy:** Action anchored at the **first frame client B is inside the room (door crossing) while A's cash/operation is still open**: 4 @57.0 (B through door; A's bundle out since 44, A left at 53), 38 @33.0 (B crosses threshold; strict at-desk condition true 36.0), 18 @19.5 (cashier's arm extends to the standing second person while A's operation is open; B at desk 19.0). If a rule requires seating / a second bundle, it fires at 36.0 (38) / 66.0 (4) — organisers labeled the entry/engagement moment.
- **Rule card id:** `two_clients_cash_mixed`
- **FP risks (clean-video evidence):** Normal sequential service with a 4–7 s gap and a CLEAR desk (clean 5 @60→64, 19 @46→50, 39 @38→45, 48 @60→63); client A standing while his own cash is out (4 @49–50); white ID cards/receipts misdetected as cash; the same client returning (re-ID needed; in 38 glasses/collar separate the two men); a collector entering while the desk is being cleared.
- **Detection cues:** Per-operation cash-blob ownership and persistence; reset events = blob enters safe/drawer ROI or is handed back across the midline; a new door-crossing track (appearance-different) while `cash_on_desk` is true → onset; confirm at seating / second simultaneous bundle; **condition on `cash_on_desk`, never on two tracks alone.**

| id | t_label | t_event | conf | note |
|----|---------|---------|------|------|
| 4 | 57 | 57.0 | 0.9 | Same file as 47 (second event @68 = `accept_without_count`). Client 1's counted beige bundle never stored (visible @53–56, safe closed); client 2 first fully inside @57.0 (partial at doorway 56.5), sits @60, card @61, blue bundle @65–66; beige + blue side by side @66–68. |
| 38 | 33 | 33.0 | 0.9 | Client 1 left @25–26 with his machine-counted bundle still on the desk (motionless from 27, never stored/returned); appearance-different client 2 (glasses, white collared pullover) at the handle 32.0–32.5, FIRST inside @33.0, sits @36, served @37–49 with the bundle still out. |
| 18 | 20 | 19.5 | 0.7 | No banknotes confirmed anywhere — "second person served during open operation" reading: client 1 seated with his light-blue item on the desk (operation visibly open), second person (white top) inside @18.5, at the desk corner @19.0; cashier's arm extends to him @19.5, takes an item hand-to-hand @20.5–21. `unauthorized_in_cash_zone` / `no_id_check` readings not fully excluded. |

---

## Type 7 — `suspect_note_mishandled`

- **Russian name:** Купюра возвращена в пересчитанную пачку без повторной проверки
- **Definition:** Banknote(s) left in the counting-machine hopper after the count (rejected / not counted) are retrieved by hand and merged into the already-counted pack without a detector check or a machine re-run.
- **Observable pattern:** After the stacker was emptied, a hand pulls remaining note(s) of a DIFFERENT colour out of the hopper (44 @13.3); during the manual recount the odd note is separated in a raised hand (one hand pins the pack, the other holds a single folded note at chest height >0.5 s), then slides into the pack and never reappears; detector ROI untouched, no second hopper load. Clean counterpart: video 45 keeps the odd note SEPARATE on the desk.
- **Timecode policy:** Action anchored at **the merge moment** — the separated note disappears into the counted pack (44: separated clearest 15.99–16.03, merged 16.06–16.10; organiser label 16 s exactly).
- **Rule card id:** `suspect_note_mishandled`
- **FP risks (clean-video evidence):** Clean 45 handles the same situation correctly — odd yellow-orange note kept SEPARATE on the desk ~10–31 s (a naive two-colours-on-desk detector false-positives there); one-by-one dealing during a manual recount (clean 43 @19–23) shares the drop motion; loading the hopper shares the raised-arm pose (distinguish by phase: before vs after the count); dark vest/hair blobs at chest height mimic a concealed object.
- **Detection cues:** Colour-split note tracking (mint-green vs tan/brown); hopper-remainder event (hand in hopper ROI after stacker-empty); separated-note hold ≥0.5 s then disappearance into the pack with no detector-ROI contact and no machine re-run before the pack is laid flat.

| id | t_label | t_event | conf | note |
|----|---------|---------|------|------|
| 44 | 16 | 16.0 | 0.75 | 30-fps frame check: greens dropped 15.93–15.96, tan note retained and raised 15.99–16.03, merged by 16.1; skeptic brackets the merge between the 16.0 and 16.5 tiles (note raised at 16.0, gone at 16.5, both hands squaring ONE stack 17–18); machine never re-run, detector never touched after 13 s. Tan band visible INSIDE the final stack @18.4/19.5 argues merge, not palming (palming not fully excluded if >1 tan note). |

---

## Type 8 — `personal_items_at_workplace`

- **Russian name:** Личные вещи / приём пищи и напитков на рабочем месте кассира
- **Definition:** The cashier eats/drinks at the cash desk or keeps personal items (bag, jacket, food, drinks) at the workplace.
- **Observable pattern:** Cup/bottle/food-wrapper objects appear on the desk or in the cashier's hand (46: snack pack @7, bottle @9, lidded takeaway cup @11 — stashed behind the counting machine); repeated hand-to-mouth motion with the object (4 sips @14–17.5).
- **Timecode policy:** Action anchored at the **first frame the consumable/personal object is unambiguous at the workplace** (46 @11.0 — cup gripped in the raised hand above the machine = organiser label; first sip 13.5–14.0 as confirmation).
- **Rule card id:** `personal_items_at_workplace`
- **FP risks (clean-video evidence):** A banded banknote bundle resembles the flat yellow snack pack at this resolution; a hand raised to adjust hair mimics a sip (require an object at mouth height); the small white/blue bottle resembles a phone; the over-the-machine reach is the same motion as loading the hopper — distinguish by the retrieved object (cylindrical vs fanned flexible notes).
- **Detection cues:** Object classes cup/bottle/wrapper in the desk ROI or at hand keypoints; hand-to-mouth repetition ≥2 or dwell ≥1.5 s with the object at the mouth; context gate: no client present, no transaction objects active.

| id | t_label | t_event | conf | note |
|----|---------|---------|------|------|
| 46 | 11 | 11.0 | 0.9 | Right arm extended over the machine gripping a beige lidded takeaway cup @11.0 (unambiguous); weaker earlier cues: yellow snack pack @7, blue-capped bottle @9–10.5; drinking confirmed by repeated sips @14, 15, 16, 17. Video 40's bag+jacket (counted under Type 5) carries this card as secondary. |

---

## Full assignment table — all 22 labeled events

| id | type_id | t_label | t_event | conf | one-line evidence |
|----|---------|---------|---------|------|-------------------|
| 1 | issue_without_count | 22 | 22.5 | 0.85 | Arm extends with uncounted notes 22.5; contact 23.0; no count episode in the preceding 20 s |
| 2 | handover_without_documents | 10 | 10.5 | 0.85 | Hand closes on client's cash with zero document events in the whole clip |
| 4 | two_clients_cash_mixed | 57 | 57.0 | 0.9 | Client 2 fully inside @57 while client 1's bundle still out; beige+blue side by side @66–68 |
| 11 | workplace_left_unattended | 18 | 18.5 | 0.8 | Last machine touch 18.0–18.5, then walks out; laptop + machine left on |
| 13 | accept_without_count | 47 | 46.0 | 0.85 | Bag cash to safe uncounted; at the safe with bundles @46, inside @50; machine never used |
| 15 | workplace_left_unattended | 15 | 15.0 | 0.9 | Walking to exit @15 with collection bag + paper exposed on the desk |
| 17 | handover_without_documents | 7 | 8.0 | 0.9 | Bag custody transfer @8.0; no document, no seal inspection; collector gone by 11 |
| 18 | two_clients_cash_mixed | 20 | 19.5 | 0.7 | Cashier engages second person @19.5 while client 1's operation is open |
| 20 | workplace_left_unattended | 5 | 4.5 | 0.85 | First frame ≥1 m from the open safe @4.5; door open 2.0 s → clip end |
| 22 | workplace_left_unattended | 14 | 14.5 | 0.8 | Upright detached @14.0, turns to door @14.5, exits 17; lock state unknowable |
| 24 | workplace_left_unattended | 8 | 8.0 | 0.85 | Door opened @8.0 (label); zone exit 6.0 also defensible; laptop open |
| 26 | workplace_left_unattended | 9 | 9.5 | 0.95 | Rising @9.0–9.5 with the counted banknote stack left on the desk |
| 28 | workplace_left_unattended | 7 | 7.0 | 0.85 | Fully upright turned to door @7.0; laptop bright in the empty room |
| 30 | unauthorized_in_cash_zone | 13 | 13.0 | 0.9 | Intruder fully inside @13.0 while cashier busy at the machine; dwells at her chair |
| 32 | unauthorized_in_cash_zone | 5 | 4.5 | 0.75 | Non-operator enters empty room @4.5, sits @8.5–9, handles machine 13–21 |
| 33 | unauthorized_in_cash_zone | 6 | 5.5 | 0.75 | Fully inside the safe/machine corner @5.5; sits 8.5–9; hand on device ≥5 s |
| 34 | accept_without_count | 13 | 12.5 | 0.85 | Machine feed starts @12.5–13.0 with the client already at the door |
| 38 | two_clients_cash_mixed | 33 | 33.0 | 0.9 | Client 2 first inside @33.0 while client 1's counted bundle still on the desk |
| 40 | unauthorized_in_cash_zone | 17 | 17.5 | 0.7 | Settling labeled: begin-to-sit + equipment reach @17.5 (entry was @4–5); bag/jacket parked |
| 44 | suspect_note_mishandled | 16 | 16.0 | 0.75 | Separated tan note raised @16.0, merged into the counted pack by 16.1–16.5; no re-check |
| 46 | personal_items_at_workplace | 11 | 11.0 | 0.9 | Takeaway cup gripped above the machine @11.0; sips @14–17.5; snack @7, bottle @9 |
| 47 | accept_without_count | 68 | 68.0 | 0.8 | Blue bundle put down uncounted @68.0 (held <2 s, no leafing, machine untouched) |

---

## Disputed / uncertain — how each was resolved

The skeptic re-opened the frames for **all 22 events** and agreed with the assigned type and
time in every case (no type or time was overturned). The items below are the residual
uncertainties flagged during drafting, with the final resolution.

1. **id 2** — the light-blue object is "cash" only because it is machine-loaded (an ID card is visually identical at 464×848); clip ends @17.1 s. **Resolved:** kept `handover_without_documents` @10.5 — the skeptic confirmed zero document events across the whole clip and that the machine feed starts @~14 with the client still seated, excluding `accept_without_count` for the labeled moment (conf 0.85).
2. **id 13** — label @47 vs the collection-bag reading (bag opened solo, no collector, no accompanying document). **Resolved:** kept `accept_without_count` @46.0 — the label sits on the safe deposit 35 s after bag opening, and the frames show the full no-count chain (glance ~1 s, machine never used); `collection_bag_unchecked` retained as the alternative rule card.
3. **id 18** — no banknotes confirmed anywhere. **Resolved:** kept `two_clients_cash_mixed` @19.5 (conf 0.7) — the labeled moment is the cashier engaging the second person during client 1's visibly open operation; the second person stays on the client side (refutes `unauthorized_in_cash_zone`) and the passed white item is document-like and examined @22 (weakens `no_id_check`). The merged type's definition explicitly covers "second client served during an unfinished operation".
4. **id 11** — desk items unverifiable as cash; possible pick-up from the machine @18–18.5 (hands occluded 19–20). **Resolved:** kept `workplace_left_unattended` @18.5 with rule card `workplace_left_unsecured` (clean-desk branch); the skeptic confirmed the laptop and machine LED stay on and nothing identifiable is in her hands. The @16.5 brightness shift is lighting, not an event.
5. **id 22** — safe lock state unknowable; hidden left hand @14.0–14.5. **Resolved:** kept `workplace_left_unattended` @14.5 — the keyhole motions 9–13.5 are consistent with locking (door never gaps), and the type does not depend on the lock state; card `workplace_left_unsecured`. The hidden-hand ambiguity (key pocketing vs small phone) stays unresolved but does not affect the type.
6. **id 32** — the entrant's clothing matches the usual cashier. **Resolved:** kept `unauthorized_in_cash_zone` @4.5 (conf 0.75) — the role is decided by behaviour and track history, not clothing: the operator position was empty from t=0 and no cashier ever appears; the staging (empty room, equipment handling) matches the intruder pattern. For deployment the rule must use cashier-present state history, never appearance.
7. **id 33** — same role ambiguity as 32; zone boundary choice (door line 4.5–5.0 / corner 5.5–6.0 / contact 9.0). **Resolved:** kept @5.5 = first frame fully inside the safe/machine corner, matching the label @6; seating and equipment contact are confirmation, not the event.
8. **id 40** — three readings (unauthorized / personal items / cashier in street clothes). **Resolved:** kept `unauthorized_in_cash_zone` @17.5 (conf 0.7) — the operator chair stays empty throughout and the organisers labeled the settling (sit + equipment reach @17.5), not the item placements (@10, @15) — the label time itself discriminates against `personal_items_at_workplace`, which is retained as the secondary card.
9. **id 44** — merge vs palming. **Resolved:** kept `suspect_note_mishandled` @16.0 — the tan band visible INSIDE the final stack @18.4/19.5 argues merge; the skeptic bracketed the merge between the 16.0 and 16.5 frames. Palming is not fully excluded if more than one tan note was in the hopper; conf 0.75.
10. **id 1** — secondary reading: possible retention of part of the notes (yellowish item in the right hand @22–25). **Resolved:** kept `issue_without_count` @22.5 — the labeled moment is unambiguously the issuance of uncounted cash; the retention reading stays a note, and the earlier acceptance @10 (itself uncounted) is a second, unlabeled omission in the same clip.
11. **id 24** — no client present, so a literal "left during service" clause never holds. **Resolved:** kept `workplace_left_unattended` @8.0 with card `workplace_left_unsecured`; the `cashier_left_during_service` branch is kept in the rule card mapping for test videos that do stage a client.
12. **id 28** — same no-client caveat as 24; hands hidden in the doorway @10–12. **Resolved:** kept `workplace_left_unattended` @7.0; possible phone use can be neither confirmed nor excluded and does not affect the type.

**t_label vs t_event conventions observed in the labels:** omission types anchor on the disposal/acceptance/extension moment; departure types anchor on the first detached-and-oriented frame (not the door crossing); intrusion types anchor on the first-fully-inside frame except video 40 (settling); labels sit within ±1 s of these anchors in 21/22 cases (13 is −1.0 s).
