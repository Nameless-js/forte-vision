# VLM signal report — iter_014

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
| accept_without_count | 1 | 0.56 | 0 | nan | - |
| collection_bag_unchecked | 1 | 0.64 | 2 | 0.57 | 1.00 |
| issue_without_count | 2 | 0.52 | 3 | 0.41 | 0.83 |
| no_id_check | 6 | 0.26 | 6 | 0.22 | 0.53 |
| personal_items_at_workplace | 1 | 0.96 | 0 | nan | - |
| phone_at_workplace | 0 | nan | 2 | 0.58 | - |
| suspect_note_mishandled | 0 | nan | 1 | 0.42 | - |
| two_clients_cash_mixed | 3 | 0.35 | 1 | 0.40 | 0.00 |
| unauthorized_in_cash_zone | 1 | 0.83 | 0 | nan | - |
| workplace_left_unsecured | 6 | 0.80 | 5 | 0.72 | 0.63 |
| **all** | 21 | 0.54 | 20 | 0.46 | 0.59 |
