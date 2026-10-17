# SOURCES — normative base of the engine

Only acts of the Republic of Kazakhstan are used. Canonical publication: adilet.zan.kz (Эталонный контрольный банк НПА).
Because adilet renders documents with JavaScript only, the texts were fetched (2026-10-17) from the HTML mirror
`https://zakon.uchet.kz/rus/docs/<id>` and stored verbatim, split by clause, in `kb/laws/*.json`
(`scripts/kb_build.py`). The canonical adilet URL is cited everywhere. Every quote in `kb/rule_cards.json` is
checked verbatim against the stored text by `tests/test_kb.py`; the SHA-256 of each fetched page is stored in the JSON.

**No model generates citations.** The engine maps a detected `type_id` to exactly one rule card; the card text is
attached by code. Descriptions state only what is visible on video. The output is a hint for a human reviewer,
not a legal conclusion (ТЗ §7).

## Documents

| id in kb | document | status |
|---|---|---|
| `nbrk_231_2019` | Постановление Правления Национального Банка РК от 29.11.2019 **№ 231** «Об утверждении Правил осуществления кассовых операций и операций по инкассации банкнот, монет и ценностей в банках второго уровня, филиалах банков-нерезидентов Республики Казахстан, Национальном операторе почты и юридических лицах, исключительной деятельностью которых является инкассация банкнот, монет и ценностей» (рег. МЮ РК 03.12.2019 № 19680). https://adilet.zan.kz/rus/docs/V1900019680 | fetched, 152 clauses of the Rules parsed, text as amended (incl. amendment of 10.11.2025 to п. 12) |
| `nbrk_14_2020` | Постановление Правления Национального Банка РК от 24.02.2020 **№ 14** «Об утверждении Правил организации охраны и устройства помещений банков второго уровня, филиалов банков-нерезидентов Республики Казахстан, Национального оператора почты, юридических лиц, исключительной деятельностью которых является инкассация банкнот, монет и ценностей, и юридических лиц, осуществляющих деятельность исключительно через обменные пункты …» (рег. МЮ РК 27.02.2020 № 20075). https://adilet.zan.kz/rus/docs/V2000020075 | fetched, 24 clauses parsed |
| `nbrk_88_2024` | Постановление Правления Национального Банка РК от 24.12.2024 **№ 88** «О внесении изменений в постановление … № 14». https://adilet.zan.kz/rus/docs/V2400035552 | fetched; used only to document the suspension below |
| `law_191_iv_2009` | Закон РК от 28.08.2009 **№ 191-IV** «О противодействии легализации (отмыванию) доходов, полученных преступным путем, и финансированию терроризма». https://adilet.zan.kz/rus/docs/Z090000191_ | fetched, articles parsed; **secondary reference only** (ст. 5 п. 3 пп. 1 for `no_id_check`) |

All cards are marked `verified_by_agent: true` because every act was fetched and the quote test passes.
No seed quote had to be stored unverified.

### Suspended clauses of № 14 (important)

The mirror page marks that **the effect of п. 11, п. 13 пп. 3), п. 14 and п. 16 is suspended until 01.01.2027**
by Resolution № 88 of 24.12.2024, and that during the suspension these clauses are in force in a *temporary
wording*. The parser stores that temporary wording as variant `@temporary` with `in_force_until: 01.01.2027`.
The rule cards that cite п. 16 (`unauthorized_in_cash_zone`, `handover_bypassing_transfer_device`) quote the
temporary wording that is in force today and say so in the `clause` field. The permanent (new) wording that
takes effect on 01.01.2027 is available in `kb/laws/nbrk_88_2024.json` for reference. See also LIMITATIONS.md.

Title note for № 231: the resolution body of № 231 also temporarily suspends (with a shorter wording) its own
title and the title/п. 1 of the Rules — the words «филиалах банков-нерезидентов Республики Казахстан» are
absent in the temporary title. Citations use the registered full title; the substantive clauses used by the
engine (п. 12, 19–25, 31, 33, 35, 38, 39, 59, 75, 76, 80) are not affected.

## Clause → violation type → how it is observed on video

| document | clause | verbatim quote (stored) | type_id | observed on video as |
|---|---|---|---|---|
| № 231 | п. 31 пп. 4 | «пересчитывает подготовленные к выдаче наличные деньги в присутствии клиента, выдает клиенту наличные деньги» | `issue_without_count` | cashier → client cash handover with no counting motion / counting machine in the preceding window |
| № 231 | п. 19 пп. 2; п. 20 | «принимает банкноты с полистным пересчетом …»; «Наличные деньги принимаются и пересчитываются кассовым работником в присутствии клиента.» | `accept_without_count` | client → cashier cash handover, cash stored without a counting segment |
| № 231 | п. 22 | «Кассовому работнику не допускается покидать рабочее место до окончания обслуживания клиента.» | `cashier_left_during_service` | cashier track leaves the cashier zone while a client is at the window |
| № 231 | п. 20 (+ п. 80) | «Все ранее принятые наличные деньги хранятся в специальных устройствах, … закрывающихся на ключ …» | `cash_left_unattended` | cash on the desk with no cashier nearby, or cashier leaves with cash out |
| № 231 | п. 12 | «Допускается внос … средств связи, не имеющих функции фото и видео фиксации.» | `phone_at_workplace` | smartphone in the cashier's hand / in use at the desk |
| № 14 | п. 16 пп. 1 (temporary wording) (+ пп. 3; № 231 п. 75) | «каждая касса имеет отдельный вход с закрывающейся на замок дверью» | `unauthorized_in_cash_zone` | non-cashier person or a client's hand crosses into the cashier zone — mapping marked approximate |
| № 231 | п. 19 пп. 1; п. 31 пп. 1 (+ Закон 191-IV ст. 5) | «проводит визуальную идентификацию клиента, вносящего наличные деньги, с документом, удостоверяющим его личность» | `no_id_check` | cash issued/accepted with no document shown before the handover |
| № 231 | п. 24 пп. 1, 3, 4 (+ п. 25, 38) | «3) проверяет целостность сумки; 4) проверяет правильность пломбирования сумки.» | `collection_bag_unchecked` | bag handover with no inspection and no document exchange |
| № 231 | п. 20; п. 21 | «На рабочем месте кассового работника находятся наличные деньги клиента.» | `two_clients_cash_mixed` | two clients at the window with cash on the desk |
| № 14 | п. 16 пп. 4 (temporary wording) | «передняя часть кассы оборудуется специальными транспортирующими устройствами для передачи наличных денег и ценностей» | `handover_bypassing_transfer_device` | cash handed over the barrier instead of through the tray — mapping marked approximate |
| № 231 | п. 19, п. 31 (general order) | «Кассовый работник банка осуществляет следующие действия:» | `protocol_deviation_other` | catch-all for deviations found by the VLM pass; mapping explicitly approximate, human check required |

The final list of types actually emitted by the engine (after the frame review of the training videos) is in
`VIOLATION_TYPES.md` and `analysis/taxonomy.md`; cards that no rule or verifier can produce are kept in the
file but never emitted.

## What is never claimed

Anything that requires data not visible on video: correctness of a posting or reconciliation, amounts, the
authenticity of banknotes, identities of persons, the content of documents, whether a signature matched a
specimen (№ 231 п. 19 пп. 3, п. 31 пп. 2), whether a receipt was issued in the system. See LIMITATIONS.md.

## Reproduce

```
python scripts/kb_build.py --fetch --html data/laws_raw --out kb/laws   # network needed once
python -m pytest tests/test_kb.py -q
```
