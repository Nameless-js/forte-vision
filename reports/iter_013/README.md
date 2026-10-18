# Evaluation report — iter_013

Created 2026-10-18 08:00:34 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM on. iter 13: FIRST VLM-verified run (Qwen3-VL-2B bf16), catch-all off

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.05; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 15/22 | 9 | 0.619 | 0.27 / 0.47 / 0.67 / 0.80 | 2.2 | 0.67 |
| train, fitted threshold | 17/22 | 13 | 0.571 | 0.41 / 0.59 / 0.76 / 0.88 | 1.6 | 0.71 |
| **LOVO** | 17/22 | 13 | 0.571 | 0.41 / 0.59 / 0.76 / 0.88 | 1.6 | 0.71 |

Timing: mean 13.8 s, max 56.1 s (video 11); total wall 579 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | issue_without_count | violation | 0.05 | 22.6 | 0.6 | handover_without_documents | no | handover_without_documents@14.0(0.583), handover_without_documents@22.6(0.097), issue_without_count@22.6(0.07) |
| 2 | violation | 10.0 | handover_without_documents | violation | 0.05 | 13.6 | 3.6 | handover_without_documents | yes | handover_without_documents@13.6(0.085) |
| 3 | no_violation | - | - | violation | 0.05 | - | - | - |  | handover_without_documents@16.8(0.1), issue_without_count@16.8(0.07) |
| 4 | violation | 57.0 | two_clients_cash_mixed | violation | 0.05 | 59.4 | 2.4 | two_clients_cash_mixed | yes | two_clients_cash_mixed@9.2(0.985), handover_without_documents@9.6(0.1), two_clients_cash_mixed@59.4(0.985) |
| 5 | no_violation | - | - | violation | 0.05 | - | - | - |  | personal_items_at_workplace@10.0(0.885), issue_without_count@25.6(0.07) |
| 8 | no_violation | - | - | no_violation | 0.05 | - | - | - |  |  |
| 10 | no_violation | - | - | no_violation | 0.05 | - | - | - |  |  |
| 11 | violation | 18.0 | workplace_left_unattended | violation | 0.05 | 17.8 | 0.2 | handover_without_documents | no | workplace_left_unattended@8.0(1.0), handover_without_documents@17.8(0.578), accept_without_count@19.8(0.25) |
| 12 | no_violation | - | - | violation | 0.05 | - | - | - |  | workplace_left_unattended@34.8(0.585) |
| 13 | violation | 47.0 | accept_without_count | violation | 0.05 | 59.8 | 12.8 | accept_without_count | yes | handover_without_documents@0.2(0.615), accept_without_count@59.8(0.35), workplace_left_unattended@61.0(0.745) |
| 14 | no_violation | - | - | violation | 0.05 | - | - | - |  | handover_without_documents@0.6(0.13), suspect_note_mishandled@50.0(0.05) |
| 15 | violation | 15.0 | workplace_left_unattended | violation | 0.05 | 16.6 | 1.6 | workplace_left_unattended | yes | workplace_left_unattended@16.6(0.833) |
| 16 | no_violation | - | - | violation | 0.05 | - | - | - |  | handover_without_documents@14.4(0.13) |
| 17 | violation | 7.0 | handover_without_documents | violation | 0.05 | 7.8 | 0.8 | handover_without_documents | yes | handover_without_documents@2.2(0.13), handover_without_documents@7.8(0.098) |
| 18 | violation | 20.0 | two_clients_cash_mixed | violation | 0.05 | 19.2 | 0.8 | handover_without_documents | no | handover_without_documents@11.2(0.096), two_clients_cash_mixed@15.6(0.985), handover_without_documents@19.2(0.1) |
| 19 | no_violation | - | - | violation | 0.05 | - | - | - |  | two_clients_cash_mixed@7.0(0.985), handover_without_documents@7.6(0.1) |
| 20 | violation | 5.0 | workplace_left_unattended | no_violation | 0.05 | - | - | - |  |  |
| 21 | no_violation | - | - | no_violation | 0.05 | - | - | - |  |  |
| 22 | violation | 14.0 | workplace_left_unattended | violation | 0.05 | 15.4 | 1.4 | workplace_left_unattended | yes | handover_without_documents@0.2(0.615), workplace_left_unattended@15.4(0.585) |
| 23 | no_violation | - | - | violation | 0.05 | - | - | - |  | workplace_left_unattended@15.0(0.69) |
| 24 | violation | 8.0 | workplace_left_unattended | violation | 0.05 | 6.4 | 1.6 | workplace_left_unattended | yes | workplace_left_unattended@6.4(0.772) |
| 25 | no_violation | - | - | violation | 0.05 | - | - | - |  | workplace_left_unattended@13.8(0.585) |
| 26 | violation | 9.0 | workplace_left_unattended | violation | 0.05 | 11.2 | 2.2 | workplace_left_unattended | yes | workplace_left_unattended@11.2(0.805) |
| 27 | no_violation | - | - | violation | 0.05 | - | - | - |  | workplace_left_unattended@10.2(0.585) |
| 28 | violation | 7.0 | workplace_left_unattended | violation | 0.05 | 9.8 | 2.8 | workplace_left_unattended | yes | workplace_left_unattended@9.8(0.86) |
| 29 | no_violation | - | - | violation | 0.05 | - | - | - |  | workplace_left_unattended@10.0(0.805) |
| 30 | violation | 13.0 | unauthorized_in_cash_zone | violation | 0.05 | 13.6 | 0.6 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@13.6(1.0) |
| 31 | no_violation | - | - | no_violation | 0.05 | - | - | - |  |  |
| 32 | violation | 5.0 | unauthorized_in_cash_zone | no_violation | 0.05 | - | - | - |  |  |
| 33 | violation | 6.0 | unauthorized_in_cash_zone | no_violation | 0.05 | - | - | - |  |  |
| 34 | violation | 13.0 | accept_without_count | no_violation | 0.05 | - | - | - |  |  |
| 35 | no_violation | - | - | violation | 0.05 | - | - | - |  | handover_without_documents@11.4(0.085) |
| 37 | no_violation | - | - | no_violation | 0.05 | - | - | - |  |  |
| 38 | violation | 33.0 | two_clients_cash_mixed | violation | 0.05 | 36.2 | 3.2 | two_clients_cash_mixed | yes | handover_without_documents@10.2(0.083), two_clients_cash_mixed@36.2(0.985), handover_without_documents@41.4(0.57) |
| 39 | no_violation | - | - | violation | 0.05 | - | - | - |  | handover_without_documents@11.0(0.085), handover_without_documents@17.6(0.085), handover_without_documents@55.8(0.585) |
| 40 | violation | 17.0 | unauthorized_in_cash_zone | no_violation | 0.05 | - | - | - |  |  |
| 43 | no_violation | - | - | no_violation | 0.05 | - | - | - |  |  |
| 44 | violation | 16.0 | suspect_note_mishandled | violation | 0.05 | 16.6 | 0.6 | workplace_left_unattended | no | workplace_left_unattended@16.6(0.862) |
| 45 | no_violation | - | - | no_violation | 0.05 | - | - | - |  |  |
| 46 | violation | 11.0 | personal_items_at_workplace | violation | 0.05 | 11.2 | 0.2 | personal_items_at_workplace | yes | personal_items_at_workplace@11.2(0.75) |
| 47 | violation | 68.0 | accept_without_count | violation | 0.05 | 60.4 | 7.6 | handover_without_documents | no | two_clients_cash_mixed@9.2(0.985), handover_without_documents@9.6(0.1), two_clients_cash_mixed@59.4(0.985) |
| 48 | no_violation | - | - | violation | 0.05 | - | - | - |  | personal_items_at_workplace@10.0(0.885), issue_without_count@25.6(0.07) |
