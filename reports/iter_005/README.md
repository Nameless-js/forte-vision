# Evaluation report — iter_005

Created 2026-10-18 03:00:10 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM off. iter 5: person dedup (p4), anchor separation, storage clusters, score-aware absence, dilated-cash counting, team-type mapping

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.25; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 15/22 | 12 | 0.548 | 0.07 / 0.27 / 0.47 / 0.67 | 4.0 | 0.60 |
| train, fitted threshold | 17/22 | 14 | 0.548 | 0.24 / 0.35 / 0.53 / 0.65 | 3.0 | 0.59 |
| **LOVO** | 16/22 | 14 | 0.524 | 0.19 / 0.31 / 0.50 / 0.62 | 3.5 | 0.56 |

Timing: mean 0.2 s, max 0.9 s (video 14); total wall 9 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | issue_without_count | violation | 0.25 | 6.0 | 16.0 | handover_without_documents | no | two_clients_cash_mixed@5.0(0.85), handover_without_documents@6.0(0.45) |
| 2 | violation | 10.0 | handover_without_documents | no_violation | 0.25 | - | - | - |  |  |
| 3 | no_violation | - | - | violation | 0.25 | - | - | - |  | handover_without_documents@6.2(0.45), two_clients_cash_mixed@6.8(0.85) |
| 4 | violation | 57.0 | two_clients_cash_mixed | violation | 0.25 | 59.4 | 2.4 | two_clients_cash_mixed | yes | two_clients_cash_mixed@9.2(0.85), handover_without_documents@9.6(0.45), two_clients_cash_mixed@59.4(0.85) |
| 5 | no_violation | - | - | violation | 0.25 | - | - | - |  | handover_without_documents@5.4(0.45), two_clients_cash_mixed@6.6(0.85), personal_items_at_workplace@10.0(0.75) |
| 8 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 10 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 11 | violation | 18.0 | workplace_left_unattended | violation | 0.25 | 17.8 | 0.2 | handover_without_documents | no | workplace_left_unattended@8.4(0.95), handover_without_documents@17.8(0.443), accept_without_count@19.8(0.6) |
| 12 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.2(0.9) |
| 13 | violation | 47.0 | accept_without_count | violation | 0.25 | 59.8 | 12.8 | accept_without_count | yes | accept_without_count@59.8(0.7) |
| 14 | no_violation | - | - | violation | 0.25 | - | - | - |  | workplace_left_unattended@82.4(0.86), workplace_left_unattended@86.4(0.926), workplace_left_unattended@92.0(0.854) |
| 15 | violation | 15.0 | workplace_left_unattended | no_violation | 0.25 | - | - | - |  |  |
| 16 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 17 | violation | 7.0 | handover_without_documents | no_violation | 0.45 | - | - | - |  |  |
| 18 | violation | 20.0 | two_clients_cash_mixed | violation | 0.25 | 19.2 | 0.8 | handover_without_documents | no | handover_without_documents@11.2(0.446), two_clients_cash_mixed@15.6(0.85), handover_without_documents@19.2(0.45) |
| 19 | no_violation | - | - | violation | 0.25 | - | - | - |  | two_clients_cash_mixed@7.0(0.85), handover_without_documents@7.6(0.45), two_clients_cash_mixed@53.8(0.844) |
| 20 | violation | 5.0 | workplace_left_unattended | no_violation | 0.25 | - | - | - |  |  |
| 21 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 22 | violation | 14.0 | workplace_left_unattended | violation | 0.25 | 11.2 | 2.8 | unauthorized_in_cash_zone | no | unauthorized_in_cash_zone@0.2(0.9), unauthorized_in_cash_zone@11.2(0.9), workplace_left_unattended@19.2(0.9) |
| 23 | no_violation | - | - | violation | 0.25 | - | - | - |  | workplace_left_unattended@12.2(0.42) |
| 24 | violation | 8.0 | workplace_left_unattended | violation | 0.25 | 12.6 | 4.6 | workplace_left_unattended | yes | unauthorized_in_cash_zone@0.2(0.9), workplace_left_unattended@12.6(0.9) |
| 25 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.2(0.9) |
| 26 | violation | 9.0 | workplace_left_unattended | violation | 0.25 | 18.0 | 9.0 | workplace_left_unattended | yes | workplace_left_unattended@18.0(0.45) |
| 27 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@0.4(0.9), unauthorized_in_cash_zone@18.4(0.81) |
| 28 | violation | 7.0 | workplace_left_unattended | no_violation | 0.25 | - | - | - |  |  |
| 29 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 30 | violation | 13.0 | unauthorized_in_cash_zone | violation | 0.25 | 11.6 | 1.4 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@11.6(0.826), unauthorized_in_cash_zone@15.8(0.874) |
| 31 | no_violation | - | - | violation | 0.25 | - | - | - |  | unauthorized_in_cash_zone@11.8(0.81), unauthorized_in_cash_zone@15.6(0.9) |
| 32 | violation | 5.0 | unauthorized_in_cash_zone | violation | 0.25 | 13.4 | 8.4 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@13.4(0.778) |
| 33 | violation | 6.0 | unauthorized_in_cash_zone | violation | 0.25 | 10.0 | 4.0 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@10.0(0.9) |
| 34 | violation | 13.0 | accept_without_count | violation | 0.25 | 6.4 | 6.6 | two_clients_cash_mixed | no | two_clients_cash_mixed@6.4(0.85) |
| 35 | no_violation | - | - | violation | 0.25 | - | - | - |  | workplace_left_unattended@40.4(0.95) |
| 37 | no_violation | - | - | violation | 0.25 | - | - | - |  | two_clients_cash_mixed@7.4(0.85), handover_without_documents@8.4(0.45), accept_without_count@10.4(0.6) |
| 38 | violation | 33.0 | two_clients_cash_mixed | violation | 0.25 | 36.0 | 3.0 | two_clients_cash_mixed | yes | two_clients_cash_mixed@5.6(0.85), handover_without_documents@6.0(0.45), two_clients_cash_mixed@36.0(0.85) |
| 39 | no_violation | - | - | violation | 0.25 | - | - | - |  | two_clients_cash_mixed@6.4(0.85), handover_without_documents@6.6(0.45), two_clients_cash_mixed@17.6(0.85) |
| 40 | violation | 17.0 | unauthorized_in_cash_zone | no_violation | 0.25 | - | - | - |  |  |
| 43 | no_violation | - | - | violation | 0.25 | - | - | - |  | workplace_left_unattended@22.4(0.42) |
| 44 | violation | 16.0 | suspect_note_mishandled | violation | 0.25 | 17.6 | 1.6 | workplace_left_unattended | no | workplace_left_unattended@7.4(0.95), workplace_left_unattended@17.6(0.872) |
| 45 | no_violation | - | - | no_violation | 0.25 | - | - | - |  |  |
| 46 | violation | 11.0 | personal_items_at_workplace | violation | 0.25 | 11.2 | 0.2 | personal_items_at_workplace | yes | personal_items_at_workplace@11.2(0.75) |
| 47 | violation | 68.0 | accept_without_count | violation | 0.25 | 60.4 | 7.6 | handover_without_documents | no | two_clients_cash_mixed@9.2(0.85), handover_without_documents@9.6(0.45), two_clients_cash_mixed@59.4(0.85) |
| 48 | no_violation | - | - | violation | 0.25 | - | - | - |  | handover_without_documents@5.4(0.45), two_clients_cash_mixed@6.6(0.85), personal_items_at_workplace@10.0(0.75) |
