# Evaluation report — iter_003

Created 2026-10-18 02:13:22 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM off. iter 3: body-depth intrusion with co-occurrence+IoU guards, cashier-present for two-clients

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.25; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 7/22 | 6 | 0.500 | 0.14 / 0.14 / 0.14 / 0.71 | 4.2 | - |
| train, fitted threshold | 10/22 | 8 | 0.524 | 0.40 / 0.40 / 0.40 / 0.80 | 3.5999999999999996 | - |
| **LOVO** | 10/22 | 8 | 0.524 | 0.40 / 0.40 / 0.40 / 0.80 | 3.5999999999999996 | - |

Timing: mean 0.1 s, max 1.2 s (video 14); total wall 5 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | - | violation | 0.25 | 22.6 | 0.6 | no_id_check |  | no_id_check@14.0(0.446), no_id_check@22.6(0.443) |
| 2 | violation | 10.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 3 | no_violation | - | - | violation | 0.25 | - | - | - |  | two_clients_cash_mixed@14.0(0.69), issue_without_count@14.6(0.75), no_id_check@14.6(0.45) |
| 4 | violation | 57.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 5 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@10.0(0.85) |
| 8 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.6(0.9), no_id_check@3.6(0.434), no_id_check@9.8(0.429) |
| 10 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 11 | violation | 18.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 12 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 13 | violation | 47.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 14 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.2(0.9), unauthorized_in_cash_zone@43.6(0.8), unauthorized_in_cash_zone@50.6(0.9) |
| 15 | violation | 15.0 | - | violation | 0.25 | 6.8 | 8.2 | cashier_left_during_service |  | no_id_check@6.0(0.449), cashier_left_during_service@6.8(0.95) |
| 16 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 17 | violation | 7.0 | - | violation | 0.25 | 7.8 | 0.8 | no_id_check |  | no_id_check@7.8(0.445) |
| 18 | violation | 20.0 | - | violation | 0.25 | 19.2 | 0.8 | no_id_check |  | no_id_check@11.2(0.45), no_id_check@19.2(0.45) |
| 19 | no_violation | - | - | violation | 0.25 | - | - | - |  | no_id_check@12.8(0.449) |
| 20 | violation | 5.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 21 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 22 | violation | 14.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 23 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 24 | violation | 8.0 | - | violation | 0.25 | 7.2 | 0.8 | cash_left_unattended |  | no_id_check@0.2(0.45), cash_left_unattended@7.2(0.652) |
| 25 | no_violation | - | - | violation | 0.25 | - | - | - |  | no_id_check@0.2(0.45) |
| 26 | violation | 9.0 | - | violation | 0.25 | 12.4 | 3.4 | unauthorized_in_cash_zone |  | unauthorized_in_cash_zone@0.2(0.9), unauthorized_in_cash_zone@12.4(0.76) |
| 27 | no_violation | - | - | violation | 0.25 | - | - | - |  | no_id_check@0.2(0.45), accept_without_count@3.4(0.7), cashier_left_during_service@8.2(0.95) |
| 28 | violation | 7.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 29 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 30 | violation | 13.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 31 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 32 | violation | 5.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 33 | violation | 6.0 | - | violation | 0.25 | 10.4 | 4.4 | unauthorized_in_cash_zone |  | unauthorized_in_cash_zone@10.4(0.9) |
| 34 | violation | 13.0 | - | violation | 0.25 | 9.2 | 3.8 | two_clients_cash_mixed |  | two_clients_cash_mixed@9.2(0.69) |
| 35 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 37 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 38 | violation | 33.0 | - | violation | 0.25 | 37.2 | 4.2 | two_clients_cash_mixed |  | two_clients_cash_mixed@37.2(0.71), two_clients_cash_mixed@45.2(0.73) |
| 39 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 40 | violation | 17.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 43 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 44 | violation | 16.0 | - | violation | 0.25 | 0.4 | 15.6 | unauthorized_in_cash_zone |  | unauthorized_in_cash_zone@0.4(0.9), no_id_check@0.4(0.45) |
| 45 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 46 | violation | 11.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 47 | violation | 68.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 48 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@10.0(0.85) |
