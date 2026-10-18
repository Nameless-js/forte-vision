# Evaluation report — iter_007

Created 2026-10-18 03:09:02 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM off. iter 7: pose-backed person validity (chairs/jackets/reflections rejected), det-weighted cashier score, body-scaled solo zone

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.25; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 14/22 | 9 | 0.595 | 0.21 / 0.29 / 0.36 / 0.64 | 3.4 | 0.57 |
| train, fitted threshold | 17/22 | 13 | 0.571 | 0.41 / 0.41 / 0.47 / 0.71 | 3.2 | 0.53 |
| **LOVO** | 17/22 | 13 | 0.571 | 0.41 / 0.41 / 0.47 / 0.71 | 3.2 | 0.53 |

Timing: mean 0.2 s, max 0.5 s (video 4); total wall 7 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | issue_without_count | violation | 0.25 | 22.6 | 0.6 | handover_without_documents | no | handover_without_documents@14.0(0.448), handover_without_documents@22.6(0.447) |
| 2 | violation | 10.0 | handover_without_documents | violation | 0.25 | 13.6 | 3.6 | handover_without_documents | yes | handover_without_documents@13.6(0.434) |
| 3 | no_violation | - | - | violation | 0.25 | - | - | - |  | handover_without_documents@16.8(0.45) |
| 4 | violation | 57.0 | two_clients_cash_mixed | violation | 0.25 | 59.4 | 2.4 | two_clients_cash_mixed | yes | two_clients_cash_mixed@9.2(0.85), handover_without_documents@9.6(0.45), two_clients_cash_mixed@59.4(0.85) |
| 5 | no_violation | - | - | violation | 0.25 | - | - | - |  | personal_items_at_workplace@10.0(0.75) |
| 8 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@3.6(0.778) |
| 10 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 11 | violation | 18.0 | workplace_left_unattended | violation | 0.25 | 17.8 | 0.2 | handover_without_documents | no | workplace_left_unattended@8.0(0.95), handover_without_documents@17.8(0.443), accept_without_count@19.8(0.6) |
| 12 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 13 | violation | 47.0 | accept_without_count | violation | 0.25 | 59.8 | 12.8 | accept_without_count | yes | accept_without_count@59.8(0.7) |
| 14 | no_violation | - | - | violation | 0.25 | - | - | - |  | suspect_note_mishandled@50.0(0.4) |
| 15 | violation | 15.0 | workplace_left_unattended | violation | 0.25 | 5.6 | 9.4 | unauthorized_in_cash_zone | no | unauthorized_in_cash_zone@5.6(0.9) |
| 16 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 17 | violation | 7.0 | handover_without_documents | violation | 0.25 | 7.8 | 0.8 | handover_without_documents | yes | handover_without_documents@7.8(0.448) |
| 18 | violation | 20.0 | two_clients_cash_mixed | violation | 0.25 | 19.2 | 0.8 | handover_without_documents | no | handover_without_documents@11.2(0.446), two_clients_cash_mixed@15.6(0.85), handover_without_documents@19.2(0.45) |
| 19 | no_violation | - | - | violation | 0.25 | - | - | - |  | two_clients_cash_mixed@7.0(0.85), handover_without_documents@7.6(0.45) |
| 20 | violation | 5.0 | workplace_left_unattended | no_violation | 0.25 | - | - | - |  |  |
| 21 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@12.6(0.842) |
| 22 | violation | 14.0 | workplace_left_unattended | violation | 0.25 | 13.4 | 0.6 | unauthorized_in_cash_zone | no | unauthorized_in_cash_zone@6.4(0.81), unauthorized_in_cash_zone@13.4(0.794) |
| 23 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 24 | violation | 8.0 | workplace_left_unattended | violation | 0.25 | 4.6 | 3.4 | unauthorized_in_cash_zone | no | unauthorized_in_cash_zone@4.6(0.9) |
| 25 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 26 | violation | 9.0 | workplace_left_unattended | violation | 0.25 | 18.0 | 9.0 | workplace_left_unattended | yes | workplace_left_unattended@18.0(0.9) |
| 27 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@18.6(0.794) |
| 28 | violation | 7.0 | workplace_left_unattended | violation | 0.25 | 6.2 | 0.8 | unauthorized_in_cash_zone | no | unauthorized_in_cash_zone@6.2(0.89) |
| 29 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 30 | violation | 13.0 | unauthorized_in_cash_zone | no_violation | 0.25 | - | - | - |  |  |
| 31 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@17.6(0.9) |
| 32 | violation | 5.0 | unauthorized_in_cash_zone | no_violation | 0.25 | - | - | - |  |  |
| 33 | violation | 6.0 | unauthorized_in_cash_zone | violation | 0.25 | 12.0 | 6.0 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@12.0(0.826) |
| 34 | violation | 13.0 | accept_without_count | no_violation | 0.25 | - | - | - |  |  |
| 35 | no_violation | - | - | violation | 0.25 | - | - | - |  | handover_without_documents@11.4(0.435) |
| 37 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 38 | violation | 33.0 | two_clients_cash_mixed | violation | 0.25 | 36.2 | 3.2 | two_clients_cash_mixed | yes | handover_without_documents@10.2(0.433), two_clients_cash_mixed@36.2(0.85), handover_without_documents@41.4(0.435) |
| 39 | no_violation | - | - | violation | 0.25 | - | - | - |  | handover_without_documents@11.0(0.435), handover_without_documents@17.6(0.435), handover_without_documents@55.8(0.45) |
| 40 | violation | 17.0 | unauthorized_in_cash_zone | violation | 0.25 | 13.6 | 3.4 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@13.6(0.794) |
| 43 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@3.2(0.9) |
| 44 | violation | 16.0 | suspect_note_mishandled | no_violation | 0.25 | - | - | - |  |  |
| 45 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@3.4(0.9) |
| 46 | violation | 11.0 | personal_items_at_workplace | violation | 0.25 | 11.2 | 0.2 | personal_items_at_workplace | yes | unauthorized_in_cash_zone@3.6(0.9), personal_items_at_workplace@11.2(0.75), unauthorized_in_cash_zone@14.2(0.9) |
| 47 | violation | 68.0 | accept_without_count | violation | 0.25 | 60.4 | 7.6 | handover_without_documents | no | two_clients_cash_mixed@9.2(0.85), handover_without_documents@9.6(0.45), two_clients_cash_mixed@59.4(0.85) |
| 48 | no_violation | - | - | violation | 0.25 | - | - | - |  | personal_items_at_workplace@10.0(0.75) |
