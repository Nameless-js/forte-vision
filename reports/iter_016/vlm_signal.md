# VLM signal report — iter_016

candidates with a VLM answer: 0; POS = within ±5 s of the label in a violation video, NEG = any candidate in a clean video.

## Verdicts (reject / support / neutral) per engine type

| type | POS verdicts | NEG verdicts |
|---|---|---|

## Answer distributions (only keys whose answers differ between POS and NEG)

| type | key | POS | NEG | separability |
|---|---|---|---|---|

## Choice mode: p_violation (POS vs NEG)

| type | n POS | mean POS | n NEG | mean NEG | AUC |
|---|---|---|---|---|---|
| accept_without_count | 1 | 0.69 | 0 | nan | - |
| collection_bag_unchecked | 1 | 0.72 | 2 | 0.54 | 1.00 |
| issue_without_count | 2 | 0.68 | 3 | 0.50 | 1.00 |
| no_id_check | 6 | 0.55 | 6 | 0.53 | 0.54 |
| personal_items_at_workplace | 1 | 1.00 | 0 | nan | - |
| phone_at_workplace | 0 | nan | 2 | 0.52 | - |
| suspect_note_mishandled | 0 | nan | 1 | 0.11 | - |
| two_clients_cash_mixed | 3 | 0.57 | 1 | 0.56 | 0.33 |
| unauthorized_in_cash_zone | 3 | 0.83 | 1 | 1.00 | 0.33 |
| workplace_left_unsecured | 7 | 0.93 | 5 | 0.60 | 0.86 |
| **all** | 24 | 0.74 | 21 | 0.55 | 0.72 |
