# Evaluation report — iter_019

Created 2026-10-18 08:29:40 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM on. iter 19: explicit eligibility — VLM-arbitrated candidates need p>=0.5, laptop-locked departures blocked; threshold fitted only over eligible candidates

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.25; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 17/22 | 1 | 0.857 | 0.29 / 0.59 / 0.71 / 0.82 | 2.0 | 0.71 |
| train, fitted threshold | 18/22 | 2 | 0.857 | 0.39 / 0.61 / 0.72 / 0.83 | 1.9 | 0.67 |
| **LOVO** | 17/22 | 2 | 0.833 | 0.35 / 0.59 / 0.71 / 0.82 | 2.0 | 0.71 |

Timing: mean 1.6 s, max 22.3 s (video 1); total wall 66 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | issue_without_count | no_violation | 0.55 | - | - | - |  |  |
| 2 | violation | 10.0 | handover_without_documents | no_violation | 0.25 | - | - | - |  |  |
| 3 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 4 | violation | 57.0 | two_clients_cash_mixed | violation | 0.25 | 55.0 | 2.0 | two_clients_cash_mixed | yes | two_clients_cash_mixed@55.0(0.62) |
| 5 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 8 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 10 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 11 | violation | 18.0 | workplace_left_unattended | violation | 0.25 | 17.8 | 0.2 | handover_without_documents | no | workplace_left_unattended@8.0(1.0), workplace_left_unattended@14.0(1.0), handover_without_documents@17.8(0.443) |
| 12 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 13 | violation | 47.0 | accept_without_count | violation | 0.25 | 60.8 | 13.8 | workplace_left_unattended | no | handover_without_documents@0.2(0.482), workplace_left_unattended@60.8(0.657) |
| 14 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 15 | violation | 15.0 | workplace_left_unattended | violation | 0.25 | 16.4 | 1.4 | workplace_left_unattended | yes | workplace_left_unattended@16.4(1.0) |
| 16 | no_violation | - | - | violation | 0.25 | - | - | - |  | handover_without_documents@14.4(0.482) |
| 17 | violation | 7.0 | handover_without_documents | violation | 0.25 | 2.2 | 4.8 | handover_without_documents | yes | handover_without_documents@2.2(0.633) |
| 18 | violation | 20.0 | two_clients_cash_mixed | violation | 0.25 | 19.2 | 0.8 | issue_without_count | no | two_clients_cash_mixed@15.6(0.85), issue_without_count@19.2(0.657), handover_without_documents@19.2(0.45) |
| 19 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 20 | violation | 5.0 | workplace_left_unattended | no_violation | 0.25 | - | - | - |  |  |
| 21 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 22 | violation | 14.0 | workplace_left_unattended | no_violation | 0.25 | - | - | - |  |  |
| 23 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 24 | violation | 8.0 | workplace_left_unattended | violation | 0.25 | 6.2 | 1.8 | workplace_left_unattended | yes | workplace_left_unattended@6.2(0.986) |
| 25 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 26 | violation | 9.0 | workplace_left_unattended | violation | 0.25 | 11.0 | 2.0 | workplace_left_unattended | yes | workplace_left_unattended@11.0(0.968) |
| 27 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 28 | violation | 7.0 | workplace_left_unattended | violation | 0.25 | 9.6 | 2.6 | workplace_left_unattended | yes | workplace_left_unattended@9.6(1.0) |
| 29 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 30 | violation | 13.0 | unauthorized_in_cash_zone | violation | 0.25 | 13.6 | 0.6 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@13.6(0.9) |
| 31 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@9.4(0.95) |
| 32 | violation | 5.0 | unauthorized_in_cash_zone | violation | 0.25 | 4.4 | 0.6 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@4.4(0.95) |
| 33 | violation | 6.0 | unauthorized_in_cash_zone | violation | 0.25 | 3.2 | 2.8 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@3.2(0.95) |
| 34 | violation | 13.0 | accept_without_count | no_violation | 0.25 | - | - | - |  |  |
| 35 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 37 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 38 | violation | 33.0 | two_clients_cash_mixed | violation | 0.25 | 36.2 | 3.2 | two_clients_cash_mixed | yes | two_clients_cash_mixed@36.2(0.85), two_clients_cash_mixed@57.2(0.62) |
| 39 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 40 | violation | 17.0 | unauthorized_in_cash_zone | violation | 0.25 | 3.6 | 13.4 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@3.6(0.95) |
| 43 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 44 | violation | 16.0 | suspect_note_mishandled | violation | 0.25 | 16.4 | 0.4 | workplace_left_unattended | no | workplace_left_unattended@16.4(1.0) |
| 45 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 46 | violation | 11.0 | personal_items_at_workplace | violation | 0.25 | 11.2 | 0.2 | personal_items_at_workplace | yes | personal_items_at_workplace@11.2(1.0) |
| 47 | violation | 68.0 | accept_without_count | violation | 0.25 | 55.0 | 13.0 | two_clients_cash_mixed | no | two_clients_cash_mixed@55.0(0.62) |
| 48 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
