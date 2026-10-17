# Evaluation report — iter_004

Created 2026-10-18 02:37:19 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM off. iter 4: M2 rules (taxonomy-driven), p3 perception with cup class

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.25; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 14/22 | 13 | 0.500 | 0.07 / 0.21 / 0.36 / 0.71 | 3.5999999999999996 | 0.43 |
| train, fitted threshold | 15/22 | 15 | 0.476 | 0.27 / 0.33 / 0.47 / 0.73 | 3.2 | 0.33 |
| **LOVO** | 15/22 | 15 | 0.476 | 0.20 / 0.27 / 0.40 / 0.67 | 3.4 | 0.33 |

Timing: mean 0.2 s, max 1.2 s (video 14); total wall 8 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | issue_without_count | violation | 0.25 | 22.6 | 0.6 | no_id_check | no | no_id_check@14.0(0.448), personal_items_at_workplace@20.2(0.76), no_id_check@22.6(0.447) |
| 2 | violation | 10.0 | no_id_check | no_violation | 0.25 | - | - | - |  |  |
| 3 | no_violation | - | - | violation | 0.25 | - | - | - |  | two_clients_cash_mixed@4.2(0.85), issue_without_count@11.4(0.748), no_id_check@11.4(0.45) |
| 4 | violation | 57.0 | two_clients_cash_mixed | no_violation | 0.25 | - | - | - |  |  |
| 5 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@10.0(0.75), personal_items_at_workplace@10.8(0.75), issue_without_count@25.6(0.745) |
| 8 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.6(0.9), no_id_check@3.6(0.443), no_id_check@9.8(0.439) |
| 10 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 11 | violation | 18.0 | workplace_left_unsecured | violation | 0.25 | 8.8 | 9.2 | cashier_left_during_service | no | unauthorized_in_cash_zone@5.4(0.9), cashier_left_during_service@8.8(0.95) |
| 12 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.2(0.9) |
| 13 | violation | 47.0 | accept_without_count | no_violation | 0.25 | - | - | - |  |  |
| 14 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.2(0.9), unauthorized_in_cash_zone@42.4(0.9), unauthorized_in_cash_zone@50.6(0.9) |
| 15 | violation | 15.0 | cash_left_unattended | violation | 0.25 | 0.2 | 14.8 | no_id_check | no | no_id_check@0.2(0.45) |
| 16 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 17 | violation | 7.0 | collection_bag_unchecked | violation | 0.45 | 12.6 | 5.6 | accept_without_count | no | accept_without_count@12.6(0.7) |
| 18 | violation | 20.0 | two_clients_cash_mixed | violation | 0.25 | 19.2 | 0.8 | no_id_check | no | no_id_check@11.2(0.45), two_clients_cash_mixed@15.6(0.85), no_id_check@19.2(0.45) |
| 19 | no_violation | - | - | violation | 0.25 | - | - | - |  | issue_without_count@12.8(0.748), no_id_check@12.8(0.45), issue_without_count@21.0(0.738) |
| 20 | violation | 5.0 | cash_left_unattended | no_violation | 0.25 | - | - | - |  |  |
| 21 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 22 | violation | 14.0 | workplace_left_unsecured | violation | 0.25 | 11.2 | 2.8 | unauthorized_in_cash_zone | no | unauthorized_in_cash_zone@6.4(0.794), unauthorized_in_cash_zone@11.2(0.794) |
| 23 | no_violation | - | - | violation | 0.25 | - | - | - |  | cash_left_unattended@12.2(0.42) |
| 24 | violation | 8.0 | workplace_left_unsecured | violation | 0.25 | 4.8 | 3.2 | unauthorized_in_cash_zone | no | personal_items_at_workplace@0.2(0.85), no_id_check@0.2(0.45), unauthorized_in_cash_zone@4.8(0.858) |
| 25 | no_violation | - | - | violation | 0.25 | - | - | - |  | personal_items_at_workplace@0.2(0.85), no_id_check@0.2(0.45), unauthorized_in_cash_zone@4.4(0.9) |
| 26 | violation | 9.0 | cash_left_unattended | violation | 0.25 | 12.4 | 3.4 | unauthorized_in_cash_zone | no | unauthorized_in_cash_zone@0.2(0.9), unauthorized_in_cash_zone@12.4(0.778), cash_left_unattended@18.0(0.9) |
| 27 | no_violation | - | - | violation | 0.25 | - | - | - |  | no_id_check@0.2(0.45), personal_items_at_workplace@4.0(0.8), unauthorized_in_cash_zone@8.2(0.794) |
| 28 | violation | 7.0 | workplace_left_unsecured | no_violation | 0.25 | - | - | - |  |  |
| 29 | no_violation | - | - | violation | 0.25 | - | - | - |  | two_clients_cash_mixed@1.2(0.614), issue_without_count@9.8(0.745), no_id_check@9.8(0.449) |
| 30 | violation | 13.0 | unauthorized_in_cash_zone | violation | 0.25 | 11.6 | 1.4 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@11.6(0.826), unauthorized_in_cash_zone@15.8(0.874), two_clients_cash_mixed@15.8(0.662) |
| 31 | no_violation | - | - | violation | 0.25 | - | - | - |  | no_id_check@2.4(0.44), unauthorized_in_cash_zone@17.0(0.81) |
| 32 | violation | 5.0 | unauthorized_in_cash_zone | violation | 0.25 | 13.4 | 8.4 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@13.4(0.778) |
| 33 | violation | 6.0 | unauthorized_in_cash_zone | violation | 0.25 | 10.4 | 4.4 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@10.4(0.9), two_clients_cash_mixed@11.4(0.654) |
| 34 | violation | 13.0 | accept_without_count | violation | 0.25 | 9.2 | 3.8 | two_clients_cash_mixed | no | two_clients_cash_mixed@9.2(0.85) |
| 35 | no_violation | - | - | violation | 0.25 | - | - | - |  | two_clients_cash_mixed@5.2(0.85) |
| 37 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 38 | violation | 33.0 | two_clients_cash_mixed | violation | 0.25 | 36.0 | 3.0 | two_clients_cash_mixed | yes | two_clients_cash_mixed@5.4(0.638), two_clients_cash_mixed@36.0(0.85) |
| 39 | no_violation | - | - | violation | 0.25 | - | - | - |  | no_id_check@55.8(0.45) |
| 40 | violation | 17.0 | unauthorized_in_cash_zone | no_violation | 0.25 | - | - | - |  |  |
| 43 | no_violation | - | - | violation | 0.25 | - | - | - |  | personal_items_at_workplace@18.0(0.82) |
| 44 | violation | 16.0 | suspect_note_mishandled | violation | 0.25 | 0.4 | 15.6 | unauthorized_in_cash_zone | no | unauthorized_in_cash_zone@0.4(0.9), no_id_check@0.4(0.45) |
| 45 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 46 | violation | 11.0 | personal_items_at_workplace | violation | 0.25 | 10.0 | 1.0 | personal_items_at_workplace | yes | personal_items_at_workplace@10.0(0.85) |
| 47 | violation | 68.0 | accept_without_count | no_violation | 0.25 | - | - | - |  |  |
| 48 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@10.0(0.75), personal_items_at_workplace@10.8(0.75), issue_without_count@25.6(0.745) |
