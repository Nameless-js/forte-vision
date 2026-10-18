# Evaluation report — iter_015

Created 2026-10-18 08:16:23 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM on. iter 15: VLM contrastive choice mode with Qwen3-VL-4B NF4 (vision tower bf16), catch-all off

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.15; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 15/22 | 8 | 0.643 | 0.47 / 0.60 / 0.80 / 0.87 | 1.6 | 0.67 |
| train, fitted threshold | 17/22 | 13 | 0.571 | 0.41 / 0.59 / 0.76 / 0.88 | 1.6 | 0.71 |
| **LOVO** | 16/22 | 13 | 0.548 | 0.44 / 0.62 / 0.81 / 0.88 | 1.5 | 0.69 |

Timing: mean 12.4 s, max 49.0 s (video 1); total wall 521 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | issue_without_count | violation | 0.15 | 22.6 | 0.6 | handover_without_documents | no | handover_without_documents@14.0(0.392), handover_without_documents@22.6(0.621), issue_without_count@22.6(0.436) |
| 2 | violation | 10.0 | handover_without_documents | no_violation | 0.45 | - | - | - |  |  |
| 3 | no_violation | - | - | violation | 0.15 | - | - | - |  | issue_without_count@16.8(0.423), handover_without_documents@16.8(0.403) |
| 4 | violation | 57.0 | two_clients_cash_mixed | violation | 0.15 | 59.4 | 2.4 | two_clients_cash_mixed | yes | two_clients_cash_mixed@9.2(0.899), handover_without_documents@9.6(0.443), two_clients_cash_mixed@59.4(0.859) |
| 5 | no_violation | - | - | violation | 0.15 | - | - | - |  | personal_items_at_workplace@10.0(0.76), issue_without_count@25.6(0.42) |
| 8 | no_violation | - | - | no_violation | 0.15 | - | - | - |  |  |
| 10 | no_violation | - | - | no_violation | 0.15 | - | - | - |  |  |
| 11 | violation | 18.0 | workplace_left_unattended | violation | 0.15 | 17.8 | 0.2 | handover_without_documents | no | workplace_left_unattended@8.0(1.0), handover_without_documents@17.8(0.759), accept_without_count@19.8(0.731) |
| 12 | no_violation | - | - | violation | 0.15 | - | - | - |  | workplace_left_unattended@34.8(0.624) |
| 13 | violation | 47.0 | accept_without_count | violation | 0.15 | 59.8 | 12.8 | accept_without_count | yes | handover_without_documents@0.2(0.482), accept_without_count@59.8(0.853), workplace_left_unattended@61.0(0.782) |
| 14 | no_violation | - | - | violation | 0.15 | - | - | - |  | handover_without_documents@0.6(0.541) |
| 15 | violation | 15.0 | workplace_left_unattended | violation | 0.15 | 16.6 | 1.6 | workplace_left_unattended | yes | workplace_left_unattended@16.6(1.0) |
| 16 | no_violation | - | - | violation | 0.15 | - | - | - |  | handover_without_documents@14.4(0.482) |
| 17 | violation | 7.0 | handover_without_documents | violation | 0.15 | 7.8 | 0.8 | handover_without_documents | yes | handover_without_documents@2.2(0.633), handover_without_documents@7.8(0.644) |
| 18 | violation | 20.0 | two_clients_cash_mixed | violation | 0.15 | 19.2 | 0.8 | issue_without_count | no | two_clients_cash_mixed@15.6(0.995), issue_without_count@19.2(0.657), handover_without_documents@19.2(0.212) |
| 19 | no_violation | - | - | violation | 0.15 | - | - | - |  | two_clients_cash_mixed@7.0(0.89), handover_without_documents@7.6(0.448) |
| 20 | violation | 5.0 | workplace_left_unattended | no_violation | 0.15 | - | - | - |  |  |
| 21 | no_violation | - | - | no_violation | 0.15 | - | - | - |  |  |
| 22 | violation | 14.0 | workplace_left_unattended | violation | 0.15 | 15.4 | 1.4 | workplace_left_unattended | yes | handover_without_documents@0.2(0.494), workplace_left_unattended@15.4(0.45) |
| 23 | no_violation | - | - | violation | 0.15 | - | - | - |  | workplace_left_unattended@15.0(0.773) |
| 24 | violation | 8.0 | workplace_left_unattended | violation | 0.15 | 6.4 | 1.6 | workplace_left_unattended | yes | workplace_left_unattended@6.4(0.986) |
| 25 | no_violation | - | - | violation | 0.15 | - | - | - |  | workplace_left_unattended@13.8(0.318) |
| 26 | violation | 9.0 | workplace_left_unattended | violation | 0.15 | 11.2 | 2.2 | workplace_left_unattended | yes | workplace_left_unattended@11.2(0.867) |
| 27 | no_violation | - | - | violation | 0.15 | - | - | - |  | workplace_left_unattended@10.2(0.437) |
| 28 | violation | 7.0 | workplace_left_unattended | violation | 0.15 | 9.8 | 2.8 | workplace_left_unattended | yes | workplace_left_unattended@9.8(1.0) |
| 29 | no_violation | - | - | violation | 0.15 | - | - | - |  | workplace_left_unattended@10.0(1.0) |
| 30 | violation | 13.0 | unauthorized_in_cash_zone | violation | 0.15 | 13.6 | 0.6 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@13.6(0.894) |
| 31 | no_violation | - | - | no_violation | 0.15 | - | - | - |  |  |
| 32 | violation | 5.0 | unauthorized_in_cash_zone | no_violation | 0.15 | - | - | - |  |  |
| 33 | violation | 6.0 | unauthorized_in_cash_zone | no_violation | 0.15 | - | - | - |  |  |
| 34 | violation | 13.0 | accept_without_count | no_violation | 0.15 | - | - | - |  |  |
| 35 | no_violation | - | - | violation | 0.15 | - | - | - |  | handover_without_documents@11.4(0.303) |
| 37 | no_violation | - | - | no_violation | 0.15 | - | - | - |  |  |
| 38 | violation | 33.0 | two_clients_cash_mixed | violation | 0.15 | 36.2 | 3.2 | two_clients_cash_mixed | yes | handover_without_documents@10.2(0.382), two_clients_cash_mixed@36.2(0.846), handover_without_documents@41.4(0.672) |
| 39 | no_violation | - | - | violation | 0.15 | - | - | - |  | handover_without_documents@11.0(0.485), handover_without_documents@17.6(0.61), handover_without_documents@55.8(0.512) |
| 40 | violation | 17.0 | unauthorized_in_cash_zone | no_violation | 0.15 | - | - | - |  |  |
| 43 | no_violation | - | - | no_violation | 0.15 | - | - | - |  |  |
| 44 | violation | 16.0 | suspect_note_mishandled | violation | 0.15 | 16.6 | 0.6 | workplace_left_unattended | no | workplace_left_unattended@16.6(1.0) |
| 45 | no_violation | - | - | no_violation | 0.15 | - | - | - |  |  |
| 46 | violation | 11.0 | personal_items_at_workplace | violation | 0.15 | 11.2 | 0.2 | personal_items_at_workplace | yes | personal_items_at_workplace@11.2(1.0) |
| 47 | violation | 68.0 | accept_without_count | violation | 0.15 | 60.4 | 7.6 | handover_without_documents | no | two_clients_cash_mixed@9.2(0.899), handover_without_documents@9.6(0.443), two_clients_cash_mixed@59.4(0.859) |
| 48 | no_violation | - | - | violation | 0.15 | - | - | - |  | personal_items_at_workplace@10.0(0.76), issue_without_count@25.6(0.42) |
