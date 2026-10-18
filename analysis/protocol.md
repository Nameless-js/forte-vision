# Normal Cash-Desk Protocol, FP-Risk Catalogue and Scene Facts (FINAL)

Companion to `analysis/taxonomy.md`. Built from frame review of all 20 clean videos
(3, 5, 8, 10, 12, 14, 16, 19, 21, 23, 25, 27, 29, 31, 35, 37, 39, 43, 45, 48) and cross-checked
against the 22 labeled violation events. All times ±0.5 s (0.5–1 fps review sampling).

---

## 1. The normal protocol (нормальный протокол) — ordered steps

| # | Step | Typical timing | Clean evidence | Visual signature |
|---|------|----------------|----------------|------------------|
| 0 | Cashier at workplace, desk clear of cash, safe closed | state at t=0 | all 20 clean videos | Seated person at the operator position (near side, back to camera in Layout A; far side, facing camera in Layout B); no cash blob on the desk; safe front uniform grey (closed) |
| 1 | Client enters through the glass door, walks along the far side | 2–5 s from appearing behind the glass to the desk | 3 @2, 5 @2, 19 @3, 35 @3, 37 @4, 39 @2, 48 @2 | Track born in the top-left door ROI, moves along the far side of the desk |
| 2 | Client sits on the far-side chair | 4–6 s after entry | 3 @6, 5 @5–6, 19 @9, 35 @9, 37 @9, 39 @8, 48 @5 | Seated pose at the far-chair ROI facing the cashier/camera; a brief lean over the desk edge while sitting is normal |
| 3 | **ID presented and examined BEFORE any cash** | within 2–5 s of sitting; examination 2–5 s | 3 @7–11, 5 @8–13, 19 @8–10, 39 @7–10, 48 @8–13 | Card-sized white object crosses the desk midline client→cashier, held at the cashier's chest/face ≥2 s with head pitched down, then parked on the cashier's side |
| 4 | Cash handover client→cashier | ≤1 s crossing, 2–8 s after the ID check | 3 @12–13, 5 @17–18, 19 @11, 35 @8, 37 @8–9, 39 @12, 48 @17–18 | Wrists converge at the desk centre; small light bundle changes side; client often pulls it from a jacket/trouser pocket just before |
| 5 | **Hand count (полистный пересчёт) in front of the seated client** | 2–10 s | 5 @19–25, 3 @14–16, 37 @10–11, 48 @21–25; solo: 27 @1–8, 43 @19–23 | Both wrists together at chest height 20–40 cm apart, periodic thumb/finger leafing, head down |
| 6 | **Machine count** | feed ~2 s + run 4–8 s (hands idle) + stacker retrieve 1–2 s | 3 @17–18, 5 @26–32, 19 @13–21, 35 @12–21, 37 @12–13, 39 @12–23, 48 @26–33; solo 10/21/43/45 | Arm fully extended into the hopper ROI at the machine end of the desk; idle gap with hands in lap/on desk; a second reach to the front stacker brings the notes back |
| 7 | Laptop entry / paperwork | 5–10 s | 19 @25–33, 35 @22–28, 39 @21–28, 14 @129–141 | Typing pose at the laptop with the cash in hand or in view on the desk |
| 8 | **Storage in the safe BEFORE the client leaves** | door open ≤6 s total; insert 1–2 s; lock check 1–3 s | 5 @47–53, 19 @35–42, 35 @39–47, 39 @29–37 & 65–72, 48 @49–53 | Torso turn to the safe → lighter door panel appears (open) → arm inside → door shut → hand on handle/lock; the cashier stays seated/adjacent the whole time |
| 9 | ID / receipt returned AFTER the safe is closed | 1–2 s | 5 @55, 35 @49–50, 48 @55 | Reverse midline crossing with a card-sized object; client pockets it |
| 10 | Client stands and leaves; desk clear | 3–5 s | 5 @57–60, 19 @43–46, 35 @51–53, 39 @35–38, 48 @57–60 | Far chair empties, track exits via the door ROI; no cash blob remains on the desk |
| 11 | Gap before the next client | ≥4 s (4–7 s observed), desk clear | 5 @60→64, 19 @46→50, 39 @38→45, 48 @60→63 | Zero client-side tracks inside the room; cashier at the laptop; no cash out |

### Solo variant: securing before leaving the room

| Step | Typical timing | Clean evidence | Visual signature |
|------|----------------|----------------|------------------|
| Secure, then exit | safe handled 2–6 s; whole exit routine 10–30 s | 12 @10–36, 23 @4.5–13, 25 @4.5–27, 27 @9–22, 29 @5.5–13; arrival 31 | Cash (if any) carried in view to the safe, door closed and lock-checked, desk cleared, laptop screen dims/closes, only then the walk to the door — this ordering distinguishes a clean exit from `workplace_left_unattended` |

---

## 2. Collector (инкассатор) variant

Reconstructed from clean 16 (handover) and clean 14 (processing); violations 17 and 13 are staged
against steps 2–3 and 5 respectively.

1. **Entry.** Collector enters through the glass door carrying the sealed green cloth bag (rigid white top bar, tag) and stays BEYOND the far desk edge — he never crosses to the cashier's side, even though his bag may overlap the counting machine in 2-D (16 @3–8).
2. **Document BEFORE bag.** Before the bag is released he hands the accompanying card-sized document across the desk; the cashier examines it ~5 s at shoulder/face height and returns it (16 @9–15).
3. **Seal inspection at handover.** The bag is placed on the desk and released to the cashier only after the document check; the cashier grips the bag top two-handed and inspects the closure/seal for ≥5 s while the collector waits or sits in view (16 @16–22.7; clip ends mid-inspection). *Violation 17 = both steps missing: no document, no seal inspection, custody transfer @8.0, collector gone by 11 s.*
4. **Opening on camera** (may be a separate solo episode): tag/seal examined, closure cut with scissors, mouth opened (14 @0–30), contents tipped onto the desk (14 @31–33), bag inverted for the empty check (14 @35–39) and stowed.
5. **Full count BEFORE storage:** several counting-machine passes plus manual leaf-through, ~60 s total (14 @47–111). *Violation 13 = this step skipped: bundles go bag → desk → safe (@50) with the machine never touched and only a ~1 s glance.*
6. **Storage and record:** safe door closed and locked (14 @115–128), operation recorded on the laptop (14 @129–141).

**Detection notes:** the bag class switches the expected protocol from banknote counting to
document-check + seal-inspection; the compliant handover (16) and the violating one (17) are
pixel-identical until ~+5–8 s after bag placement, so rules must evaluate a **window** around
the handover, never the placement frame alone.

---

## 3. FP-risk catalogue (clean videos: what a naive rule would flag)

1. **ID card held at the cashier's face ≥2 s → phone FP:** clean 3 @9–11, 5 @9–13, 16 @10–14, 19 @9–10 & 56–57, 48 @9–12.
2. **Client hand/forearm crossing the desk midline** for handovers, or leaning over the desk when sitting/standing → `unauthorized_in_cash_zone` FP: clean 3 @7–8 & 12–13, 5 @8/17–18/55/68–70, 19 @8/11/43/54, 35 @8 & 51, 39 @7/12/51, 48 @8/17–18/55/69–70.
3. **Cashier turns away and opens the safe with cash in hand** → cashier-left / cash-unattended / safe-open FP: clean 5 @47–53, 19 @35–42 (door open ~37.5–41.5), 35 @39–47 (door open @44 while she faces the desk), 39 @29–37 & 65–72, 48 @49–53. Discriminators: seated/adjacent, closed ≤6 s, count already done.
4. **Cash disappears into the counting machine** → stored-without-count FP: clean 3 @17–20, 5 @26–32, 10 @7–8, 19 @14–21, 21 @13–15. Whitelist the machine ROI as a counting zone, never storage.
5. **Cashier stands/leaves with NO client and NO cash out** (end-of-shift / errand) → left-workplace FP: clean 12 @18–36, 23 @4.5–13, 25 @4.5–27, 27 @9–22, 29 @6.5–13, 8 @29–31 (bend below desk), arrival 31 @3–13. Gate on client-present OR valuables-exposed OR workplace-active.
6. **Cashier on the FAR side facing the camera** (Layout B: 8, 10, 12–15, 20–33, 43–46) → seat-side role rules mislabel her a client and her safe/machine use as unauthorized. Assign roles by behaviour/track history.
7. **Silhouettes and reflections behind the glass door/partition** → second-person / two-clients FP in almost every video (e.g. 1 @20–25, 2 @0–17, 8 @19–31, 14 @1–44, 22 @12–17 reflections, 29 @0–6, 44/45 @12–33). Mask beyond the door line; require feet inside the room polygon.
8. **Cash on the desk while the cashier sits right beside it** → unattended FP: clean 10 @15, 14 @31–51, 37 @14–15.9, 43 @19–23.4, 45 @31–33.3. Unattended requires cashier absence/distance, not cash alone.
9. **Bundle held against the torso while moving to the safe or counting** → pocketing FP: clean 14 @84–91 & 117–119, 21 @6–8, 27 @9–11, 39 @31 & 68.
10. **Sequential clients with a 4–7 s gap and a clear desk** → two_clients FP: clean 5 @60→64, 19 @46→50, 39 @38→45, 48 @60→63.
11. **Collection-bag handling by the cashier alone** (scissors at the closure, bag shaken/inverted for the empty check) → tamper / phone FP: clean 14 @8–16 & 35–39, 16 @17–22.7 (the seal inspection is CORRECT behaviour).
12. **Static desk telephone and client-held dark wallet/phone-like objects** → phone FP: telephone present in 10, 12, 22–24, 27–35, 37–40, 43–46; client objects 1 @9, 5 @6–56, 18 @19–22, 48 @6–56. Any phone rule concerns the cashier's hands only.
13. **Odd-colour note lying SEPARATELY next to the counted pack is the CORRECT handling** → suspect-note FP: clean 45 @10–31; one-by-one dealing during a manual recount: clean 43 @19–23.
14. **Laptop lid closing / dark folder on the desk** → tablet/phone FP: clean 12 @10–12, 24 @0–4, 25 @0–3.
15. **Machine run with hands idle** looks like "no counting" to motion-based count detectors: clean 5 @28–31, 19 @15–20. A machine pass counts as counting.
16. **Mid-clip exposure/colour shifts** cause spurious events and track ID switches: 11 @16–16.5, 12 @~33. Normalise illumination; use geometric track continuity.

---

## 4. Scene facts useful for perception

- **Camera & frame:** fixed corner camera, oblique high view, portrait 464×848; burned-in time top-left ("t=NN.Ns"). Review zoom tiles crop frame rows 27–72% at native resolution. Review sampling 1 fps (0.5 fps around labels) → all times ±0.5 s.
- **Door:** the glass door at TOP-LEFT is the only entrance. Everything beyond the door/partition line is another room — silhouettes/reflections there must be masked (require feet inside the room polygon).
- **Two mirrored layouts:**
  - **Layout A** (client-service videos 1, 2, 3, 4/47, 5/48, 16–19, 34–39): cashier on the NEAR side with her back to the camera; client chair on the far side; counting machine at the camera-LEFT desk end in videos 1–19 but at the camera-RIGHT end next to the safe in 34–39 (mirrored); laptop at the opposite end; grey safe on a white pedestal to the RIGHT of the desk.
  - **Layout B** (solo/internal videos 8, 10, 11–15, 20–33, 40, 43–46): the cashier sits/stands on the FAR side FACING the camera, often with no near-side chair, and the safe may be behind her. Seat-side role rules FAIL here — assign the cashier role by BEHAVIOUR (the track that occupies the operator position and operates laptop / counting machine / safe) and by track history from t=0. In Layout B the door opens directly into the working zone.
- **Positions relative to the cashier (relational, angle-independent):** the counting machine sits at one END of the desk within one arm-reach of the seated cashier; the laptop at the opposite end; the safe/cabinet is a separate grey box on a pedestal beside the desk, 1–3 steps from the operator seat, door swinging toward the camera/desk; the client chair is directly across the counter line from the operator seat; the door is on the far side of the room from the operator seat in Layout A and adjacent to the working zone in Layout B.
- **No transfer tray exists:** the counter line is the desk surface between the two chairs; all handovers are hand-to-hand or via the desk centre (`handover_bypassing_transfer_device` is inapplicable in this branch).
- **Handover signature:** a wrist crosses the desk midline, the counterpart wrist converges, wrists within a few px for 0.5–1 s, the object changes side; the giver's hand retracts empty.
- **Document:** small white/light card held at the cashier's chest/face ≥2 s, head pitched down, then returned or parked.
- **Cash:** small light rectangular blob ~15–30 px wide at training resolution (light-blue / beige / green / tan); banded bundles read as a solid block, fanned notes as a flared light shape.
- **Safe "open":** a lighter door panel protruding from the grey box plus a dark interior gap; "closed" = uniform grey front.
- **What counting looks like:**
  - *By hand:* both wrists together at chest height 20–40 cm apart, periodic thumb/finger leafing, head down, 2–10 s (collector volumes ~60 s); distinct from a 1–2 s squaring/tidying motion.
  - *By machine:* three phases — hopper feed (~2 s, arm extended over the machine top), run (4–8 s, hands idle in lap/on desk, notes rippling), stacker retrieve (1–2 s reach to the machine FRONT). A completed count requires all three.
- **Typical clean durations:** client entry→seated 4–6 s; ID check 2–5 s; cash handover ≤1 s; hand count 2–10 s; machine pass ~7–12 s total; safe open ≤6 s with the cashier adjacent; client exit 3–5 s; inter-client gap 4–7 s with a clear desk; collection-bag seal inspection ≥5 s; full bag count ~60 s.
- **Permanent distractors:** static black desk telephone (phone FP); white papers / white item at the counting machine (cash FP); the white foreground desk edge at the bottom of every frame (another desk — ignore); mid-clip exposure/colour shifts (11 @16.5, 12 @~33) that break colour-based tracking — prefer geometry.
