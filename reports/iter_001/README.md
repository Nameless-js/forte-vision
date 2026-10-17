# Evaluation report — iter_001

Created 2026-10-18 02:06:14 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM off. M1 baseline: rules only, no VLM, cached perception

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.25; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 13/22 | 17 | 0.381 | 0.15 / 0.38 / 0.46 / 0.85 | 3.4 | - |
| train, fitted threshold | 16/22 | 17 | 0.452 | 0.31 / 0.50 / 0.56 / 0.88 | 1.9000000000000001 | - |
| **LOVO** | 16/22 | 17 | 0.452 | 0.31 / 0.50 / 0.56 / 0.88 | 1.9000000000000001 | - |

Timing: mean 0.3 s, max 1.1 s (video 14); total wall 12 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | - | violation | 0.25 | 22.6 | 0.6 | no_id_check |  | no_id_check@14.0(0.446), no_id_check@22.6(0.443) |
| 2 | violation | 10.0 | - | violation | 0.25 | 11.6 | 1.6 | phone_at_workplace |  | phone_at_workplace@11.6(0.76) |
| 3 | no_violation | - | - | violation | 0.25 | - | - | - |  | no_id_check@16.8(0.45), unauthorized_in_cash_zone@18.4(0.76) |
| 4 | violation | 57.0 | - | violation | 0.25 | 60.8 | 3.8 | phone_at_workplace |  | phone_at_workplace@12.2(0.85), phone_at_workplace@21.0(0.744), phone_at_workplace@60.8(0.85) |
| 5 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@8.0(0.85), phone_at_workplace@21.0(0.712), phone_at_workplace@31.6(0.85) |
| 8 | no_violation | - | - | violation | 0.25 | - | - | - |  | cashier_left_during_service@2.2(0.878), no_id_check@4.0(0.432), phone_at_workplace@14.6(0.728) |
| 10 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 11 | violation | 18.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 12 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@28.8(0.696), unauthorized_in_cash_zone@31.4(0.68) |
| 13 | violation | 47.0 | - | violation | 0.25 | 58.6 | 11.6 | cashier_left_during_service |  | phone_at_workplace@0.6(0.68), cashier_left_during_service@58.6(0.902) |
| 14 | no_violation | - | - | violation | 0.25 | - | - | - |  | cashier_left_during_service@0.0(0.95), cash_left_unattended@32.4(0.8), unauthorized_in_cash_zone@48.6(0.9) |
| 15 | violation | 15.0 | - | violation | 0.25 | 6.8 | 8.2 | cashier_left_during_service |  | cashier_left_during_service@6.8(0.95) |
| 16 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@9.8(0.776) |
| 17 | violation | 7.0 | - | violation | 0.25 | 7.8 | 0.8 | no_id_check |  | no_id_check@7.8(0.444) |
| 18 | violation | 20.0 | - | violation | 0.25 | 19.4 | 0.6 | no_id_check |  | no_id_check@11.2(0.45), no_id_check@19.4(0.449) |
| 19 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@7.6(0.824), no_id_check@12.8(0.449), phone_at_workplace@32.8(0.76) |
| 20 | violation | 5.0 | - | violation | 0.25 | 8.4 | 3.4 | phone_at_workplace |  | phone_at_workplace@8.4(0.68) |
| 21 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@7.8(0.85) |
| 22 | violation | 14.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 23 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 24 | violation | 8.0 | - | violation | 0.25 | 6.4 | 1.6 | cashier_left_during_service |  | unauthorized_in_cash_zone@0.2(0.9), cashier_left_during_service@0.2(0.822), two_clients_cash_mixed@0.4(0.73) |
| 25 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.2(0.9), phone_at_workplace@0.2(0.85), no_id_check@0.2(0.45) |
| 26 | violation | 9.0 | - | violation | 0.25 | 8.4 | 0.6 | phone_at_workplace |  | unauthorized_in_cash_zone@0.2(0.9), no_id_check@0.2(0.45), phone_at_workplace@0.6(0.85) |
| 27 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@0.4(0.85), cashier_left_during_service@8.2(0.95) |
| 28 | violation | 7.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 29 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@1.2(0.696), unauthorized_in_cash_zone@1.6(0.66), unauthorized_in_cash_zone@5.4(0.84) |
| 30 | violation | 13.0 | - | violation | 0.25 | 11.6 | 1.4 | unauthorized_in_cash_zone |  | unauthorized_in_cash_zone@11.6(0.82), unauthorized_in_cash_zone@15.8(0.68) |
| 31 | no_violation | - | - | violation | 0.25 | - | - | - |  | cashier_left_during_service@0.0(0.95), unauthorized_in_cash_zone@2.4(0.9), phone_at_workplace@13.0(0.85) |
| 32 | violation | 5.0 | - | violation | 0.25 | 9.2 | 4.2 | phone_at_workplace |  | phone_at_workplace@9.2(0.84) |
| 33 | violation | 6.0 | - | violation | 0.25 | 9.8 | 3.8 | unauthorized_in_cash_zone |  | unauthorized_in_cash_zone@9.8(0.9) |
| 34 | violation | 13.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 35 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@12.6(0.712), phone_at_workplace@19.8(0.712) |
| 37 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@8.2(0.76) |
| 38 | violation | 33.0 | - | violation | 0.25 | 36.4 | 3.4 | phone_at_workplace |  | phone_at_workplace@7.2(0.76), phone_at_workplace@13.2(0.696), phone_at_workplace@29.0(0.808) |
| 39 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@0.2(0.712), phone_at_workplace@3.6(0.776), phone_at_workplace@10.4(0.68) |
| 40 | violation | 17.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 43 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 44 | violation | 16.0 | - | violation | 0.25 | 13.8 | 2.2 | phone_at_workplace |  | cashier_left_during_service@0.0(0.95), unauthorized_in_cash_zone@0.2(0.9), no_id_check@12.0(0.443) |
| 45 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@20.8(0.728), phone_at_workplace@25.4(0.792) |
| 46 | violation | 11.0 | - | no_violation | 0.25 | - | - | - |  |  |
| 47 | violation | 68.0 | - | violation | 0.25 | 67.6 | 0.4 | phone_at_workplace |  | phone_at_workplace@12.2(0.85), phone_at_workplace@21.0(0.744), phone_at_workplace@60.8(0.85) |
| 48 | no_violation | - | - | violation | 0.25 | - | - | - |  | phone_at_workplace@8.0(0.85), phone_at_workplace@21.0(0.712), phone_at_workplace@31.6(0.85) |
