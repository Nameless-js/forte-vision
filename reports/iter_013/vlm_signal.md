# VLM signal report — iter_013

candidates with a VLM answer: 57; POS = within ±5 s of the label in a violation video, NEG = any candidate in a clean video.

## Verdicts (reject / support / neutral) per engine type

| type | POS verdicts | NEG verdicts |
|---|---|---|
| accept_without_count | {'reject': 1} | {} |
| collection_bag_unchecked | {'reject': 1} | {'reject': 2} |
| issue_without_count | {'reject': 2} | {'reject': 3} |
| no_id_check | {'reject': 5, 'support': 1} | {'reject': 5, 'support': 1} |
| personal_items_at_workplace | {'neutral': 1} | {} |
| phone_at_workplace | {} | {'support': 2} |
| suspect_note_mishandled | {} | {'reject': 1} |
| two_clients_cash_mixed | {'support': 3} | {'support': 1} |
| unauthorized_in_cash_zone | {'support': 1} | {} |
| workplace_left_unsecured | {'support': 6} | {'support': 5} |

## Answer distributions (only keys whose answers differ between POS and NEG)

| type | key | POS | NEG | separability |
|---|---|---|---|---|
| collection_bag_unchecked | cash_handover | {'cashier_to_client': 1} | {'cashier_to_client': 1, 'client_to_cashier': 1} | 0.50 |
| collection_bag_unchecked | phone_visible | {'no': 1} | {'yes': 1, 'no': 1} | 0.50 |
| issue_without_count | id_shown | {'no': 1, 'yes': 1} | {'yes': 1, 'no': 2} | 0.17 |
| no_id_check | bag_checked | {'yes': 5, 'no': 1} | {'yes': 4, 'no': 2} | 0.17 |
| no_id_check | counted_money | {'yes': 5, 'no': 1} | {'yes': 6} | 0.17 |
| two_clients_cash_mixed | phone_visible | {'no': 2, 'yes': 1} | {'no': 1} | 0.33 |
| workplace_left_unsecured | cash_handover | {'cashier_to_client': 1, 'client_to_cashier': 5} | {'cashier_to_client': 1, 'client_to_cashier': 3, 'none': 1} | 0.23 |
