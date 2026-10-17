# Violation taxonomy — draft (ForteBank Datathon, cash-desk video engine)

Built from the structured reviews of all 42 labeled training videos (22 violation labels in 21 files — videos 4 and 47 are the SAME file with two events at 57 s and 68 s; videos 5 and 48 are the same clean file; 20 clean videos). Types are clustered by OBSERVABLE pattern (what person boxes + hand keypoints + cash/bag/document boxes + safe/machine ROIs can test), merged to 8 clusters. The finer, card-level granularity of `analysis/taxonomy.json` (10 ids) is preserved inside clusters T3 and T4 as sub-variants selected by a trivially observable desk/object state.

## 0. Scene facts (perception invariants)

- Fixed corner camera, portrait 464x848, burned-in time top-left of every tile ("t=NN.Ns"); zoom tiles = crop of frame rows 27%–72% at native resolution. Review sampling 1 fps (0.5 fps around labels), so all times are ±0.5 s.
- Glass door at TOP-LEFT in every video; it is the only entrance. Everything beyond the door/glass partition line is another room — silhouettes and reflections there are background and must be masked.
- Two mirrored desk layouts occur:
  - **Layout A (canonical, client-service videos: 1, 2, 3, 4/47, 5/48, 16, 17, 18, 19, 34, 35, 37, 38, 39):** cashier seated on the NEAR side, back to camera; counting machine at the camera-LEFT desk end in 1–19, at the camera-RIGHT end next to the safe in 34–39; laptop on the opposite end; grey safe on a white pedestal to the RIGHT of the desk; client chair on the far side.
  - **Layout B (mostly solo/internal videos: 8, 10, 11–15, 20–33, 40, 43–46):** the cashier sits or stands on the FAR side FACING the camera; often no near-side chair. Seat-side role rules FAIL here — assign the role by BEHAVIOUR: the person who occupies the operator position and operates the laptop / counting machine / safe is the cashier.
- No transfer tray anywhere; the "counter line" is the desk surface between the two chairs. All handovers are hand-to-hand or via the desk centre (`handover_bypassing_transfer_device` is NOT applicable to this scene).
- Handover signature: a wrist crosses the desk midline, the counterpart wrist converges, wrists within a few px for 0.5–1 s, object changes side. Document = small white/light card held at the cashier's chest/face ≥2 s. Cash = small light rectangular blob (~15–30 px wide), often light-blue/beige/green.
- Typical durations (clean videos): client entry→seated 4–6 s; ID check 2–5 s; cash handover ≤1 s; hand count 2–10 s (leafing, both wrists together at chest height); machine pass = feed ~2 s + run 4–8 s (hands idle) + stacker retrieve 1–2 s; safe open ≤6 s with the cashier adjacent; client exit 3–5 s; inter-client gap 4–7 s with a clear desk.
- The safe door opens toward the camera/desk; "open" = a lighter door panel protruding from the grey box + dark interior gap (videos 5, 19, 20, 25, 35, 39). The white item on/near the counting machine and white papers are permanent distractors for cash detectors.
- Ignore: the white foreground desk edge at the bottom of every frame; the static black desk telephone (phone-FP); everything behind the glass.

## 1. Type table (8 clusters, 22 events)

| # | type_id | RU name | videos (t_label→t_event) | rule card(s) |
|---|---------|---------|--------------------------|--------------|
| T1 | issue_without_count | Выдача наличных без пересчёта в присутствии клиента | 1 (22→22.5) | issue_without_count |
| T2 | accept_without_count | Приём наличных без полистного пересчёта | 34 (13→12.5), 47 (68→68.0), 13 (47→46.0) | accept_without_count |
| T3 | handover_without_documents | Передача ценностей без проверки документов (без удостоверения личности / сумка без сопроводительных документов) | 2 (10→10.5), 17 (7→8.0) | no_id_check (client cash) \| collection_bag_unchecked (collector bag) — by object class |
| T4 | workplace_left_unattended | Рабочее место / ценности оставлены без присмотра | 11 (18→18.5), 22 (14→14.5), 24 (8→8.0), 28 (7→7.0), 15 (15→15.0), 26 (9→9.5), 20 (5→4.5) | cash_left_unattended (cash out / safe open) \| workplace_left_unsecured (clean desk) \| cashier_left_during_service (client present — not staged in train set) |
| T5 | unauthorized_in_cash_zone | Посторонний в зоне кассира | 30 (13→13.0), 32 (5→4.5), 33 (6→5.5), 40 (17→17.5) | unauthorized_in_cash_zone |
| T6 | two_clients_cash_mixed | Наличные двух клиентов одновременно / второй клиент при незавершённой операции | 4 (57→57.0), 38 (33→33.0), 18 (20→19.5) | two_clients_cash_mixed |
| T7 | suspect_note_mishandled | Купюра возвращена в пересчитанную пачку без повторной проверки | 44 (16→16.0) | suspect_note_mishandled |
| T8 | personal_items_at_workplace | Личные вещи / приём пищи и напитков на рабочем месте кассира | 46 (11→11.0) | personal_items_at_workplace |

Event count: 1+3+2+7+4+3+1+1 = 22. ✔

## 2. Types in detail

### T1. issue_without_count — «Выдача наличных без пересчёта в присутствии клиента»
- **Definition:** the cashier hands cash to the client while no counting episode (hand leafing ≥3 s, or a completed machine pass: hopper feed → run → stacker retrieve) covered that cash in the client's presence in the preceding window (~20 s).
- **Observable pattern:** cash blob transitions cashier-hands → client-hand across the desk midline (cashier wrist reaches >50% desk depth, wrists converge, blob ends on the far side, cashier wrist retracts empty) with no preceding count episode. In video 1 the stack lay MOTIONLESS on the machine top 14–19 s (no pass-through evidenced) and was only fanned ~1.5 s at face level before the handover.
- **Timecode policy (omission):** first frame of the cashier's arm extension with the cash toward the client (video 1: 22.5 s; hand contact 23.0; organiser label 22 = last frame before extension). Contact-based detectors fire at +0.5 s — acceptable.
- **Rule card:** `issue_without_count`.
- **Videos:** 1 (t_label 22, t_event 22.5, conf 0.6; secondary readings: possible retention of part of the notes — yellowish item stays in her right hand at 25 s; the earlier acceptance at 10 s was also uncounted).
- **FP risks:** returning an ID card/receipt (same arm extension; object is card-sized white, not a note stack) — clean 5 @55 s, 48 @55 s; showing the counted stack / brief fan after a GENUINE count must not fire; the cashier's long reach to the counting machine (clean 3 @17–18 s) mimics a cross-desk handover; accepting cash (opposite direction, video 1 @10 s).
- **Detection cues:** cash-track state machine client→cashier→machine→cashier→client; count-episode detector (wrists together ≥3 s with periodic leafing, or hopper feed + stacker retrieve with notes visibly moving); flag the cashier→client transition if no count episode found; genuine counts are several times longer than the ~1.5 s fan seen here.

### T2. accept_without_count — «Приём наличных без полистного пересчёта»
- **Definition:** cash enters the cashier's custody (from a client, or extracted from a collection bag) and is disposed of — put down and the operation continues, stored in the safe, or counted only AFTER the client has left — with no leaf-by-leaf or machine count in the presence of its source.
- **Observable pattern:** handover client→cashier (or bag→desk) followed within seconds by put-down/safe-insert without a count episode in between; OR the machine feed starts only after the client's track left the desk zone.
- **Timecode policy (omission):** the moment the uncounted cash is disposed of — put down on the desk while the cashier resumes typing (47 @68.0: bundle lowered after a ~1.5 s glance), machine feed starting with the client already at the door (34 @12.5–13.0), uncounted bundles carried to the safe / door opening (13 @46.0; cash inside at 50 s).
- **Rule card:** `accept_without_count`.
- **Videos:** 34 (13→12.5, conf 0.6; also no ID shown — secondary no_id reading); 47 (68→68.0, conf 0.6; SAME FILE as video 4 — second event in one video; the first client's operation provides in-video contrast with an 8 s hand count); 13 (47→46.0, conf 0.6; collection-bag contents → safe uncounted; alternative reading collection_bag_unchecked — label timing 35 s after bag opening decides for the no-count reading).
- **FP risks:** squaring/tidying a bundle 1–2 s right AFTER a genuine count (clean 39 @28–29 s and 64–65 s, 43 @31–33 s); machine counting with hands idle looks like "no counting" to motion-only detectors (clean 19 @15–20 s); carrying already-counted cash to the safe (clean 5 @49–50, 35 @39–43, 39 @32–33, 27 @9–11); bag-to-safe of the EMPTY bag (14 @41–42 s).
- **Detection cues:** measure time-in-hand between receipt and at-rest (<~3 s here vs ~8 s+ when counting); count episodes as in T1; gate the "in presence" clause on the client track being in the desk zone; for the bag variant: cash extracted from a bag reaching the safe ROI with the machine ROI never visited and no ≥8 s hand-count.

### T3. handover_without_documents — «Передача ценностей без проверки документов»
Merged cluster (two single-video stagings with the same omission shape).
- **Definition:** valuables change custody with NO document event: (a) client cash accepted without an identity document presented and examined first; (b) a collection bag accepted without the accompanying document being handled, without seal/tag inspection, the collector leaving immediately.
- **Observable pattern:** a valuables handover (cash blob or bag crosses to the cashier) with zero document-presentation patterns in the surrounding window — no small card/paper held at the cashier's chest/face ≥2 s beforehand, nothing passed back, no writing/signing pose; for the bag: no two-handed inspection of the bag top before/at acceptance and the collector exits <5 s after release.
- **Timecode policy (omission):** the moment of acceptance — the cashier's hand closes on the cash (2 @10.5; reach 10.0, client laid it at 9.0) or both hands hold the bag in the custody transfer (17 @8.0; bag placed 6.5–7.0 = organiser label).
- **Rule card:** by object class — `no_id_check` for client cash, `collection_bag_unchecked` for a collection bag.
- **Videos:** 2 (10→10.5, conf 0.6; client's first action is laying cash, no document ever; caveat — the light-blue object is identified as cash only because it is loaded into the machine; clip ends at 17.1 s); 17 (7→8.0, conf 0.7; no document, no seal check, collector gone by 11 s).
- **FP risks:** a legitimate ID presentation looks IDENTICAL to a cash handover until what follows (clean 3 @7–8 s: card picked up and held at face, later parked — vs cash going to the machine); the compliant collection handover (clean 16) is identical to video 17 until +5–8 s — there the document is examined at 10–14 s BEFORE the bag is released at 16–17 s and the bag-top inspection runs ≥5.7 s; so the rule must test the window around the handover, not the placement frame.
- **Detection cues:** document-event detector (small bright card-sized object client→cashier, held at chest/face ≥2 s, usually returned or parked on the desk); object classifier bag vs notes (cloth bag with rigid white top bar); fire on the first valuables handover with no document event since the counterpart entered; for bags additionally require the missing seal-inspection (two cashier wrists inside the bag bbox ≥3 s) and the collector's early exit.

### T4. workplace_left_unattended — «Рабочее место / ценности оставлены без присмотра»
Merged cluster: identical departure action; the desk/safe state selects the rule card. In ALL seven stagings no client is present → rules must NOT require a client track.
- **Definition:** the cashier separates from the active workplace — stands, walks to the door, exits the room — or exposed valuables (cash on the desk, open safe) are left with nobody within reach.
- **Observable pattern:** the cashier track leaves the desk polygon toward the door ROI and crosses the door line while the workplace stays active (lit laptop screen, counting machine on, items out). Aggravating state at separation: a cash object remains on the desk (15 — collection bag; 26 — banknote stack) or the safe door stands open (20 — door open from 2.0 s, never closed; she sits at the desk with her back to it).
- **Timecode policy (action):** FIRST frame the cashier is upright, detached from the last workplace contact and oriented/moving toward the exit — not the door crossing. Labels confirm: 11 @18.0–18.5 (last touch of the machine before walking), 22 @14.0–14.5 (hand off the safe 13.5, torso turns 14.5), 24 @8.0 (door opened; desk-zone exit at 6.0 also defensible), 28 @7.0 (fully upright, turned away), 26 @9.0–9.5 (rising with cash on the desk), 15 @15.0 (walking to exit past the chair, bag on desk), 20 @4.5–5.0 (first frame separated ≥1 m from the open safe). A zone-exit detector fires within ±2 s of all seven labels; a room-empty detector fires 2–3 s late.
- **Rule cards:** `cash_left_unattended` when a cash object is on the desk or the safe is open at separation (15, 20, 26); `workplace_left_unsecured` otherwise (11, 22, 24, 28); `cashier_left_during_service` if a client is present (not staged in the training set — keep the branch for test videos).
- **Videos:** 11 (18→18.5, 0.6; machine/laptop left on; desk items unverifiable as cash), 22 (14→14.5, 0.55; safe key handled 9–13.5 s, lock state unknown), 24 (8→8.0, 0.55; laptop open, folder on desk), 28 (7→7.0, 0.6; laptop stays bright), 15 (15→15.0, 0.8; green bag + paper left on desk, room empty from 17 s), 26 (9→9.5, 0.85; banknote stack on desk from 8.0 s, room empty from ~15 s), 20 (5→4.5, 0.6; safe open from 2.0 s to clip end while she works at the desk).
- **FP risks:** the cashier walking to the safe/machine and staying in the zone (clean 5 @47–53, 25 @6–17 s); a proper end-of-shift exit AFTER securing — desk clear + safe closed/locked before the door (clean 12 @18–36, 23 @4.5–13, 25 @19–27, 27 @14–22, 29 @6.5–13, 31 entry); carrying cash to the safe looks like leaving with cash (clean 21 @6–8, 27 @9–11); machine-feed makes cash "disappear" (clean 10 @7–8); track loss from lighting changes (11 @16.5, 12 @~33) or occlusion; seat-based cashier-absent rules fire all through Layout-B videos.
- **Detection cues:** desk polygon + door ROI + safe-door state classifier + cash-blob detector; stand-up signature (bbox height jump, hip rise) → monotonic centroid motion to the door → door crossing; workplace-active evidence (bright laptop ROI, machine LED, objects on desk); alarm = (no person in desk zone ≥2–3 s AND workplace active) OR (cash-on-desk/safe-open AND nobody within ~1 m, sustained ≥1.5–2 s); never condition on a client.

### T5. unauthorized_in_cash_zone — «Посторонний в зоне кассира»
- **Definition:** a person who is not the operating cashier enters the cashier's working zone (door → desk strip → machine/safe corner) — in all four stagings while the workplace is unattended or the cashier is busy at the machine — and settles there (sits at the desk, parks personal items, touches equipment).
- **Observable pattern:** operator position empty (or held by a different track) + a new track crosses the door line and reaches the desk/equipment strip; dwell, chair pull, seating and equipment contact confirm. The door opens directly into the working zone in Layout B.
- **Timecode policy (action):** first frame the non-cashier track is fully inside the cash zone: 30 @13.0 (inside the door while the cashier stands at the machine; at her chair from 13.5), 32 @4.5 (fully inside, walking to the desk; organiser label 5 = at the desk chair), 33 @5.5 (standing in the safe/machine corner; label 6), 40 @17.5 (sits at the desk, hand to equipment; entered at 4 s — the organisers labeled the settling, not the entry). Confirmation events: seating (32 @8.5–9, 33 @8.5–9, 40 @18) and equipment contact (32 @14, 33 @9, 40 @17.5–25).
- **Rule card:** `unauthorized_in_cash_zone`.
- **Videos:** 30 (13→13.0, 0.8), 32 (5→4.5, 0.6), 33 (6→5.5, 0.6), 40 (17→17.5, 0.5; personal bag against the machine @10 s and jacket on the desk @15 s — secondary personal_items_at_workplace reading; could also be staged as the cashier arriving in street clothes).
- **FP risks:** the cashier herself entering/returning (clean 31 @3–8 s: the first person who takes the operator seat and runs the equipment IS the cashier — need track history/appearance re-ID, not clothing: in 32/33 the entrant's clothing matches the usual cashier); every client walking to the far chair while the cashier is seated (all client videos); the collector standing at the desk end with his bag overlapping the machine in 2-D (clean 16 @4–8 s); people behind the glass partition.
- **Detection cues:** maintain a cashier-present state from operator-seat/equipment occupancy history; per-layout zone polygon (safe + machine corner + behind-desk strip); alert when a track born in the door ROI reaches that polygon while cashier-absent (or ≠ cashier track), sustained ≥1–1.5 s; escalate on seating or wrist-in-equipment-ROI; mask the glass.

### T6. two_clients_cash_mixed — «Наличные двух клиентов одновременно»
- **Definition:** a new client enters / is served while the previous client's operation is still open — the previous cash is still out on the desk (not stored, not returned); the two clients' cash can end up side by side.
- **Observable pattern:** cash_on_desk state persists from client A's operation beyond A's exit; a NEW track (different appearance) crosses the door and reaches the desk while the state holds; hard confirmation = two distinct bundles on the cashier's side (4/47 @66–68 s: beige + blue side by side).
- **Timecode policy (action):** first frame client B is inside the room while A's cash is still out: 4 @57.0 (B through the door; A's beige bundle on the desk since 44 s; A left at 53 s), 38 @33.0 (B crosses the threshold; strict at-desk condition true at 36.0), 18 @19.5 (the cashier engages B — arm extended to the standing second person — while A's operation is open, A seated, A's card on the desk; B at the desk from 19.0). If the rule requires seating/second bundle, fire at 36.0 (38) / 66.0 (4) — the organisers labeled the ENTRY/engagement moment.
- **Rule card:** `two_clients_cash_mixed`.
- **Videos:** 4 (57→57.0, 0.72; same file as 47 — the 68 s event is T2), 38 (33→33.0, 0.8), 18 (20→19.5, 0.55; no banknotes confirmed — "second person served during an open operation" reading; see unclear list).
- **FP risks:** normal sequential service with a 4–7 s gap and a CLEAR desk (clean 5 @60→64, 19 @46→50, 39 @38→45, 48 @60→63); client A standing up while his own cash is out (4 @49–50); white ID cards/receipts misdetected as cash; the same client returning (re-ID needed — in 38 glasses/collar separate the two men); a collector entering while the desk is being cleared.
- **Detection cues:** per-operation cash-blob ownership and persistence; reset events = blob enters safe/drawer ROI or is handed back across the midline; a new door-crossing track (appearance-different) while cash_on_desk is true → onset; confirm at seating / second simultaneous bundle; condition on cash_on_desk, never on two tracks alone.

### T7. suspect_note_mishandled — «Купюра возвращена в пересчитанную пачку без проверки»
- **Definition:** banknote(s) left in the counting machine hopper after the count (rejected/not counted) are retrieved by hand and merged into the already-counted pack without a detector check or machine re-run.
- **Observable pattern:** after the stacker was emptied, a hand pulls remaining note(s) of a DIFFERENT colour out of the hopper (44 @13.3 s); during the manual recount the odd note is separated in a raised hand (one hand pins the pack, the other holds a single folded note at chest height >0.5 s), then slides into the pack and never reappears; detector ROI untouched, no second hopper load.
- **Timecode policy (action):** the merge moment — the separated note disappears into the counted pack (44: separated clearest 15.99–16.03, merged by 16.06–16.10; organiser label 16 s exactly).
- **Rule card:** `suspect_note_mishandled`.
- **Videos:** 44 (16→16.0, conf 0.55; palming cannot be fully excluded, but close-ups at 18.4/19.5 s show the tan band INSIDE the final stack).
- **FP risks:** clean 45 handles the same situation CORRECTLY — the odd yellow-orange note stays SEPARATE on the desk (~10–31 s): a naive "two colours on desk" detector false-positives there; dealing notes one-by-one during a manual recount (clean 43 @19–23 s) shares the drop motion; loading the hopper shares the raised-arm-with-notes pose (distinguish by phase: before vs after the count); dark clothing/hair blobs at chest height mimic a concealed object.
- **Detection cues:** colour-split note tracking (mint-green vs tan/brown classes); hopper-remainder event (hand in hopper ROI after stacker-empty); separated-note hold ≥0.5 s then disappearance into the pack with no detector-ROI contact and no machine re-run before the pack is laid flat.

### T8. personal_items_at_workplace — «Личные вещи / еда и напитки на рабочем месте кассира»
- **Definition:** the cashier eats/drinks at the cash desk or keeps personal items (bag, jacket, food, drinks) at the workplace.
- **Observable pattern:** cup/bottle/food-wrapper objects appear on the desk or in the cashier's hand (46: snack pack @7 s, bottle @9 s, lidded cup @11 s — stashed behind the counting machine); repeated hand-to-mouth motion with the object in hand (4 sips @14–17.5 s).
- **Timecode policy (action):** first frame the consumable/personal object is unambiguous at the workplace (46 @11.0 — cup gripped in the raised hand above the machine = organiser label; first sip 13.5–14.0 as confirmation).
- **Rule card:** `personal_items_at_workplace`.
- **Videos:** 46 (11→11.0, conf 0.75). Related evidence: 40 (personal bag @10 s + jacket @15 s on the desk) is counted under T5 but carries this card as a secondary.
- **FP risks:** a banded banknote bundle resembles the flat yellow snack pack; a hand raised to adjust hair mimics a sip (require an object at mouth height); the small white/blue bottle resembles a phone; a stamp/receipt roll near the chest looks like a held cup; the over-the-machine reach is the same motion as loading the hopper (distinguish by retrieved object: cylindrical vs fanned flexible notes).
- **Detection cues:** object detector classes cup/bottle/wrapper in the desk ROI or at hand keypoints; hand-to-mouth repetition ≥2 or dwell ≥1.5 s with the object; context: no client, no transaction objects active.

## 3. Normal protocol (from the 20 clean videos)

### Client cash-acceptance flow (clean 3, 5/48, 19, 35, 37, 39)

| # | Step | Typical timing | Visual signature | Clean evidence |
|---|------|----------------|------------------|----------------|
| 1 | Cashier at workplace, desk clear | state at t=0 | seated at operator position; no cash blob; safe closed | all clean videos |
| 2 | Client enters through the glass door | 2–5 s door→desk | track born in door ROI, walks along the far side | 3 @2, 5 @2, 19 @3, 35 @3, 37 @4, 39 @2, 48 @2 |
| 3 | Client sits on the far chair | 4–6 s after entry | seated pose at far-chair ROI, faces camera (Layout A) | 3 @6, 5 @5–6, 19 @9, 35 @9, 37 @9, 39 @8, 48 @5 |
| 4 | ID presented and examined BEFORE cash | within 2–5 s of sitting; check 2–5 s | card-sized white object crosses midline → held at cashier chest/face ≥2 s → parked on desk | 3 @7–11, 5 @8–13, 19 @8–10, 39 @7–10, 48 @8–13 (35/37: single handover, check not separable) |
| 5 | Cash handover client→cashier | ≤1 s crossing | wrists converge at desk centre; light blob changes side | 3 @12–13, 5 @17–18, 19 @11, 35 @8, 37 @8–9, 39 @12, 48 @17–18 |
| 6 | Hand count (полистный) | 2–10 s | both wrists together at chest height, periodic leafing, head down | 5 @19–25, 3 @14–16, 37 @10–11, 48 @21–25 |
| 7 | Machine count | feed ~2 s; run 4–8 s hands idle; retrieve 1–2 s | arm extended into hopper ROI; idle gap; second reach to stacker | 3 @17–18, 5 @26–32, 19 @13–21, 35 @12–21, 37 @12–13, 39 @12–23, 48 @26–33 |
| 8 | Laptop entry / paperwork | 5–10 s | typing pose; cash in hand or in view | 19 @25–33, 35 @22–28, 39 @21–28 |
| 9 | Storage in the safe before the client leaves | open ≤6 s total; insert 1–2 s; lock 1–3 s | torso turn → door panel open → arm inside → door shut → hand on lock; cashier stays seated/adjacent | 5 @47–53, 19 @35–42, 35 @39–47, 39 @29–37 and 65–72, 48 @49–53 |
| 10 | ID/receipt returned AFTER the safe is closed | 1–2 s | reverse midline crossing with a card-sized object | 5 @55, 35 @49–50, 48 @55 |
| 11 | Client stands and leaves | 3–5 s | far chair empties, track exits via door ROI; desk clear of cash | 5 @57–60, 19 @43–46, 35 @51–53, 39 @35–38, 48 @57–60 |
| 12 | Gap before the next client | ≥4 s, desk clear | zero client-side tracks; no cash blob | 5 @60–64, 19 @46–50, 39 @38–45, 48 @60–63 |

### Collector (инкассация) variant (clean 16 handover; clean 14 processing)
1. Collector enters with the sealed green bag, stays BEYOND the far desk edge (16 @3–8 s).
2. Accompanying document handed across the desk; cashier examines it ~5 s at shoulder/face height and returns it (16 @9–15 s) — BEFORE the bag is released.
3. Bag placed on the desk; cashier takes it two-handed and inspects the top/closure/seal ≥5 s while the collector waits/sits in view (16 @16–22.7 s).
4. (Later/solo) bag opened ON CAMERA: seal strip examined, cut with scissors, mouth opened (14 @0–30 s); contents tipped out (14 @31–33); bag inverted for the empty-check (14 @35–39) and stowed.
5. Full count before storage: multiple machine passes + manual leaf-through, ~60 s total (14 @47–111 s).
6. Storage in the safe, door closed and locked (14 @115–128), operation recorded on the laptop (14 @129–141).

### Solo/internal cash handling (clean 8, 10, 21, 25, 27, 43, 45; departures 12, 23, 29, 31)
- Safe opened only with the cashier adjacent, ≤3–5 s, closed and lock-checked immediately (8 @19–27, 21 @0–5, 25 @8–24, 27 @11–17).
- Cash carried in view hand→machine/desk; counted by machine and/or hand before or right after storage (10, 21, 27, 43, 45).
- A machine-rejected/odd note is kept SEPARATE on the desk (45 @10–31 s) — the clean counterpart of T7.
- Before leaving the room: desk cleared of cash/valuables, safe closed/locked, (often) screen locked — only then the door (12 @10–36, 23 @5–15, 25 @19–27, 27 @14–22, 29 @5.5–13, 31 arrival).

## 4. FP-risk catalogue (clean-video moments that look like violations)

1. ID card held at the cashier's face ≥2 s → phone FP: 3 @9–11, 5 @9–13, 16 @10–14, 19 @9–10 & 56–57, 48 @9–12.
2. Client hand/forearm crossing the desk midline for handovers → unauthorized FP: 3 @7–8 & 12–13, 5 @8, 17–18, 55, 68–70, 19 @8, 11, 54, 39 @7, 12, 51, 48 @8, 17–18, 55, 69–70; client leaning over the desk when sitting/standing: 5 @5 & 68, 19 @43, 35 @8 & 51.
3. Cashier turns away and opens the safe with cash in hand → left/unattended/safe-open FP: 5 @47–53, 19 @35–42 (door open ~37.5–41.5), 35 @39–47 (door open @44 while she faces the desk), 39 @29–37 & 65–72, 48 @47–53. Discriminators: seated/adjacent, closed ≤6 s, count already done.
4. Cash disappears into the counting machine → stored-without-count FP: 3 @17–20, 10 @7–8, 19 @14–21, 21 @13–15, 5 @26–32. Whitelist the machine ROI as a counting zone, never storage.
5. Cashier stands/leaves with NO client and NO cash out → left-workplace FP: 12 @18–36, 23 @4.5–13, 25 @4.5–27, 27 @9–22, 29 @6.5–13, 8 @29–31 (bend below desk); arrival 31 @3–13. Gate on client-present OR valuables-exposed.
6. Cashier on the FAR side facing the camera (Layout B: 8, 10, 12–15, 20–33, 43–46) → seat-side role rules mis-assign her as a client and her safe/machine use as unauthorized. Assign roles by behaviour/track history.
7. Silhouettes/reflections behind the glass door/partition → second-person/two-clients FP: present in almost every video (e.g., 1 @20–25, 2 @0–17, 8 @19–31, 14 @1–44, 22 @12–17 reflections, 29 @0–6, 44/45 @12–33). Mask beyond the door line; require feet inside the room polygon.
8. Cash on the desk while the cashier sits right next to it → unattended FP: 10 @15, 14 @31–51, 43 @19–23.4, 45 @31–33.3, 37 @14–15.9. Unattended requires cashier absence/distance, not cash alone.
9. Bundle held against the torso while moving to the safe → pocketing FP: 14 @84–91 & 117–119, 27 @9–11, 39 @31 & 68, 21 @6–8.
10. Sequential clients with a 4–7 s gap and a clear desk → two-clients FP: 5 @60→64, 19 @46→50, 39 @38→45, 48 @60→63.
11. Collection-bag handling by the cashier alone — scissors at the closure, bag shaken/inverted → tamper/phone FP: 14 @8–16 & 35–39, 16 @17–22.7 (seal inspection), 15 @0–5 (bag inspection before the violation).
12. Static desk telephone and client-held dark wallet/phone-like objects → phone FP: telephone in 10, 12, 22–24, 27–35, 37–40, 43–46; client objects 1 @9, 5 @6–56, 18 @19–22, 48 @6–56. The phone rule concerns the CASHIER's hands only.
13. Odd-colour note lying separately next to the counted pack → suspect-note FP: 45 @10–31 (this is the CORRECT handling); 43 @19–23 one-by-one dealing.
14. Laptop lid closing / folder on desk → tablet-phone FP: 12 @10–12, 24 @0–4, 25 @0–3.
15. Machine run with hands idle (clean 19 @15–20, 5 @28–31) → "no counting" FP for motion-based count detectors; count machine passes as counting.
16. Exposure/colour shifts mid-clip (11 @16–16.5, 12 @~33) → spurious motion events and track ID switches; use geometry, not colour histograms.

## 5. Unclear / flagged videos

| id | issue |
|----|-------|
| 2 | Single exemplar of the no-ID staging; the light-blue object is "cash" only because it is machine-loaded (an ID card is visually identical at this resolution); clip ends @17.1 s before the count completes, so accept_without_count is not fully excluded. |
| 13 | Label @47 s sits on the safe-deposit → assigned T2 (accept_without_count); the collection-bag reading (bag opened solo, no collector, no document) remains plausible — collection_bag_unchecked as alternative card. |
| 18 | No banknotes confirmed anywhere; "second person served while the first operation is open" — T6 chosen on label timing (19.5 s = engagement), but unauthorized_in_cash_zone / no_id_check readings are not excluded (conf 0.55). |
| 11 | Desk items unverifiable as cash → card choice workplace_left_unsecured vs cash_left_unattended uncertain; possible pick-up from the machine @18–18.5 s (hands occluded 19–20 s). |
| 22 | Safe lock state unknowable (door closed in every frame); left-workplace vs safe-related unattended reading; what the hidden left hand does @14.0–14.5 s is unknown. |
| 32 | Entrant's clothing matches the usual cashier; if she IS the cashier arriving, nothing violating is visible at the label — T5 rests on the empty operator seat + staging logic. |
| 33 | Same role ambiguity as 32; the exact violation second depends on the zone boundary (door line 4.5–5.0 vs safe corner 5.5–6.0 vs equipment contact 9.0). |
| 40 | Three readings: unauthorized (chosen, conf 0.5), personal_items_at_workplace (bag @10 s, jacket @15 s), or the cashier arriving in street clothes. |
| 44 | Merge-without-check (chosen) vs palming/присвоение: the tan band is visible INSIDE the final stack, but >1 tan note cannot be excluded; the insertion happens on the camera-hidden side of the pack. |
| 1 | Secondary reading: possible retention of part of the notes (yellowish item in the cashier's right hand @22–25 s, left hand occluded 22.5–24 s); also the earlier acceptance @10 s was itself uncounted. |
| 24, 28 | No client present in any T4 staging → the literal "during service" clause never holds; card mapping goes to workplace_left_unsecured. Keep the cashier_left_during_service branch for test videos with a client. |

## 6. Reconciliation with analysis/taxonomy.json

The provisional team file uses 10 card-level ids. This draft clusters them into 8 observable types: `no_id_check` + `collection_bag_unchecked` → T3 (card picked by object class: notes vs bag); `workplace_left_unsecured` + `cash_left_unattended` → T4 (card picked by desk/safe state at separation). All per-video t_event values are identical to taxonomy.json. Detectors are built per cluster; rule-card citation is resolved at fire time from the observable sub-state, so `kb/rule_cards.json` granularity is fully preserved.
