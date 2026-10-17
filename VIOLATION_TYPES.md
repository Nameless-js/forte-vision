# VIOLATION_TYPES — types the engine recognises

Types are **team-assigned**: the organisers provide only «нарушение» + one timestamp per video; the taxonomy
below was built by reviewing the frames of all 42 training videos (analysis/review/, analysis/taxonomy.json)
and clustering the 22 labeled events. The test set may contain unseen types; those are caught by the
conservative VLM pass and reported as the nearest type or as «Иное отклонение» (`protocol_deviation_other`).

Every type maps to exactly one rule card in `kb/rule_cards.json` (document, clause, verbatim quote, adilet
URL). Models never generate citations; code attaches the card. Cards whose legal mapping is approximate say
so in the card (`mapping_note_ru`) and in the result description.

| type_id | Russian name (user-facing) | observable pattern | rule card | training videos (id@label s) |
|---|---|---|---|---|
| `issue_without_count` | Выдача наличных без пересчёта в присутствии клиента | cashier→client cash handover with no counting segment (hand leafing with cash at the hands, or counting machine run) in the preceding window | №231 п. 31 пп. 4 | 1@22 |
| `accept_without_count` | Приём наличных без полистного пересчёта в присутствии клиента | cash acquired from a client/collector during an episode; no counting while the counter-party is still present (count after departure, storing uncounted, or no count at all) | №231 п. 19 пп. 2; п. 20 | 13@47, 34@13, 47@68 |
| `workplace_left_unsecured` | Кассир покинул рабочее место, не обеспечив сохранность ценностей | the cashier walks out, the room stays empty; no sustained safe interaction before leaving (and/or the workplace stays "live": laptop on, items out) | №231 п. 20 (+22, 80), mapping approximate | 11@18, 22@14, 24@8, 28@7 |
| `cash_left_unattended` | Наличные (сейф) оставлены без присмотра | cash visible on the cashier's side with no cashier near it; or the cashier departs leaving cash out; or the safe is left open unattended | №231 п. 20 (+80) | 15@15, 20@5, 26@9 |
| `phone_at_workplace` | Использование телефона на рабочем месте кассира | phone-like object in the cashier's hand for ≥2 s | №231 п. 12 | — (none in training; kept for the test set) |
| `personal_items_at_workplace` | Личные вещи / еда и напитки на рабочем месте кассира | cup/bottle/food in the cashier's hand at the desk | №231 п. 12 | 46@11 |
| `unauthorized_in_cash_zone` | Посторонний в зоне кассира | (a) a second person comes deep to the cashier's side while she works; (b) a person enters an EMPTY cash workplace and settles at the equipment | №14 п. 16 пп. 1 (temp. wording), mapping approximate | 30@13, 32@5, 33@6, 40@17 |
| `two_clients_cash_mixed` | Наличные двух клиентов одновременно / второй клиент во время операции | two visitors at the window during one live operation; or a new visitor arrives while the previous operation's cash is still out | №231 п. 20; п. 21 | 4@57, 18@20, 38@33 |
| `no_id_check` | Операция без предъявления документа, удостоверяющего личность | cash handover with no document/card shown since the episode start (conservative; low base confidence) | №231 п. 19 пп. 1; п. 31 пп. 1 | 2@10 |
| `collection_bag_unchecked` | Инкассаторская сумка принята без проверки | collector bag handover without inspection dwell and without document exchange | №231 п. 24 пп. 1, 3, 4 | 17@7 |
| `handover_bypassing_transfer_device` | Передача наличных минуя передаточное устройство | kept in the KB; **never emitted**: the training scene has no transfer tray, so the pattern is undefined there | №14 п. 16 пп. 4, approximate | — |
| `protocol_deviation_other` | Иное отклонение от порядка кассовой операции | VLM catch-all hit repeated on two adjacent windows and not contradicted by Layer A | №231 п. 19/31 (general order), approximate | — |

Video 44 (@16 s): review pending; provisionally carried as `unknown_pending_review` in analysis/taxonomy.json
and excluded from type-accuracy metrics until the arbitration lands.

## Timecode policy (ТЗ FAQ B.10 leaves it to the team)

* **Action violations** (`cashier_left_during_service`, `workplace_left_unsecured`, `cash_left_unattended`,
  `phone_at_workplace`, `personal_items_at_workplace`, `unauthorized_in_cash_zone`,
  `two_clients_cash_mixed`): `timecode_sec` = the first sampled frame (5 fps grid) where the condition
  becomes true — e.g. the first frame the cashier is outside the zone, the first frame the intruder is at
  the equipment, the first frame the second client is at the window.
* **Omission violations** (`issue_without_count`, `accept_without_count`, `no_id_check`,
  `collection_bag_unchecked`): `timecode_sec` = the moment of the action that should have been preceded by
  the skipped step — the handover executed without counting / without an ID check; for an acceptance never
  counted in the client's presence, the storing moment, or the moment the client walks away with the cash
  still uncounted.
* The organisers' labels in the training set anchor on the same moments (verified per video in
  `analysis/review/`); deviations found there are listed in `analysis/taxonomy.json` as `t_event` vs `t_label`.

## Known look-alike normal actions (FP risks, from the clean-video reviews)

* Securing routine before leaving (items into the safe, lock check) — vs `workplace_left_unsecured`;
  discriminated by cumulative hands-at-safe time before the departure (`securing_min_s`).
* Turning booklet pages / adjusting a hair clip / holding a card at face level — vs counting or phone.
* Reflections and people behind the glass wall — vs intrusion / second client (filtered by the seated-anchor
  requirement and intrusion depth).
* The client leaning over the desk to pass an item — vs intrusion (filtered by body-depth, not hand reach).
* The cashier walking to the safe/counting machine — vs leaving the workplace (workplace anchors are part of
  the zone).
