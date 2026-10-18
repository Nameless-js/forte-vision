# Evaluation report — iter_014

Created 2026-10-18 08:07:23 on NVIDIA GeForce RTX 4060 Laptop GPU (8.6 GB), torch 2.6.0+cu124, Windows-11-10.0.26200-SP0; profile `gpu-small`, VLM on. iter 14: VLM contrastive choice mode (Qwen3-VL-2B bf16, A/B logits both orders), catch-all off

Videos: 42 (22 violation / 20 clean). Config threshold 0.5; fitted threshold 0.1; LOVO folds 40.

| setting | recall (violations) | FP on clean | accuracy | loc ±1/±2/±3/±5 s | median Δt | type acc |
|---|---|---|---|---|---|---|
| train, config threshold | 15/22 | 10 | 0.595 | 0.20 / 0.47 / 0.67 / 0.87 | 2.2 | 0.80 |
| train, fitted threshold | 17/22 | 13 | 0.571 | 0.41 / 0.59 / 0.76 / 0.88 | 1.6 | 0.76 |
| **LOVO** | 16/22 | 13 | 0.548 | 0.44 / 0.62 / 0.81 / 0.88 | 1.5 | 0.75 |

Timing: mean 9.0 s, max 36.9 s (video 11); total wall 379 s.
Schema problems: 0 video(s).

## Per-video (LOVO)

| id | label | t_label | team type | pred | thr | t_pred | Δt | pred type | ok | events |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 22.0 | issue_without_count | violation | 0.1 | 22.6 | 0.6 | issue_without_count | yes | handover_without_documents@14.0(0.33), issue_without_count@22.6(0.397), handover_without_documents@22.6(0.285) |
| 2 | violation | 10.0 | handover_without_documents | no_violation | 0.35 | - | - | - |  |  |
| 3 | no_violation | - | - | violation | 0.1 | - | - | - |  | issue_without_count@16.8(0.415), handover_without_documents@16.8(0.279) |
| 4 | violation | 57.0 | two_clients_cash_mixed | violation | 0.1 | 59.4 | 2.4 | two_clients_cash_mixed | yes | two_clients_cash_mixed@9.2(0.744), handover_without_documents@9.6(0.196), two_clients_cash_mixed@59.4(0.743) |
| 5 | no_violation | - | - | violation | 0.1 | - | - | - |  | personal_items_at_workplace@10.0(0.806), issue_without_count@25.6(0.327) |
| 8 | no_violation | - | - | no_violation | 0.1 | - | - | - |  |  |
| 10 | no_violation | - | - | no_violation | 0.1 | - | - | - |  |  |
| 11 | violation | 18.0 | workplace_left_unattended | violation | 0.1 | 17.8 | 0.2 | handover_without_documents | no | workplace_left_unattended@8.0(1.0), handover_without_documents@17.8(0.453), accept_without_count@19.8(0.644) |
| 12 | no_violation | - | - | violation | 0.1 | - | - | - |  | workplace_left_unattended@34.8(0.638) |
| 13 | violation | 47.0 | accept_without_count | violation | 0.1 | 59.8 | 12.8 | accept_without_count | yes | handover_without_documents@0.2(0.378), accept_without_count@59.8(0.78), workplace_left_unattended@61.0(0.85) |
| 14 | no_violation | - | - | violation | 0.1 | - | - | - |  | handover_without_documents@0.6(0.502), suspect_note_mishandled@50.0(0.348) |
| 15 | violation | 15.0 | workplace_left_unattended | violation | 0.1 | 16.6 | 1.6 | workplace_left_unattended | yes | workplace_left_unattended@16.6(0.92) |
| 16 | no_violation | - | - | violation | 0.1 | - | - | - |  | handover_without_documents@14.4(0.56) |
| 17 | violation | 7.0 | handover_without_documents | violation | 0.1 | 7.8 | 0.8 | handover_without_documents | yes | handover_without_documents@2.2(0.581), handover_without_documents@7.8(0.438) |
| 18 | violation | 20.0 | two_clients_cash_mixed | violation | 0.1 | 19.2 | 0.8 | issue_without_count | no | handover_without_documents@11.2(0.192), two_clients_cash_mixed@15.6(0.726), issue_without_count@19.2(0.464) |
| 19 | no_violation | - | - | violation | 0.1 | - | - | - |  | two_clients_cash_mixed@7.0(0.78), handover_without_documents@7.6(0.12) |
| 20 | violation | 5.0 | workplace_left_unattended | no_violation | 0.1 | - | - | - |  |  |
| 21 | no_violation | - | - | no_violation | 0.1 | - | - | - |  |  |
| 22 | violation | 14.0 | workplace_left_unattended | violation | 0.1 | 15.4 | 1.4 | workplace_left_unattended | yes | handover_without_documents@0.2(0.374), workplace_left_unattended@15.4(0.63) |
| 23 | no_violation | - | - | violation | 0.1 | - | - | - |  | workplace_left_unattended@15.0(0.782) |
| 24 | violation | 8.0 | workplace_left_unattended | violation | 0.1 | 6.4 | 1.6 | workplace_left_unattended | yes | workplace_left_unattended@6.4(0.95) |
| 25 | no_violation | - | - | violation | 0.1 | - | - | - |  | workplace_left_unattended@13.8(0.509) |
| 26 | violation | 9.0 | workplace_left_unattended | violation | 0.1 | 11.2 | 2.2 | workplace_left_unattended | yes | workplace_left_unattended@11.2(0.921) |
| 27 | no_violation | - | - | violation | 0.1 | - | - | - |  | workplace_left_unattended@10.2(0.506) |
| 28 | violation | 7.0 | workplace_left_unattended | violation | 0.1 | 9.8 | 2.8 | workplace_left_unattended | yes | workplace_left_unattended@9.8(0.891) |
| 29 | no_violation | - | - | violation | 0.1 | - | - | - |  | workplace_left_unattended@10.0(0.899) |
| 30 | violation | 13.0 | unauthorized_in_cash_zone | violation | 0.1 | 13.6 | 0.6 | unauthorized_in_cash_zone | yes | unauthorized_in_cash_zone@13.6(1.0) |
| 31 | no_violation | - | - | no_violation | 0.1 | - | - | - |  |  |
| 32 | violation | 5.0 | unauthorized_in_cash_zone | no_violation | 0.1 | - | - | - |  |  |
| 33 | violation | 6.0 | unauthorized_in_cash_zone | no_violation | 0.1 | - | - | - |  |  |
| 34 | violation | 13.0 | accept_without_count | no_violation | 0.1 | - | - | - |  |  |
| 35 | no_violation | - | - | violation | 0.1 | - | - | - |  | handover_without_documents@11.4(0.209) |
| 37 | no_violation | - | - | no_violation | 0.1 | - | - | - |  |  |
| 38 | violation | 33.0 | two_clients_cash_mixed | violation | 0.1 | 36.2 | 3.2 | two_clients_cash_mixed | yes | handover_without_documents@10.2(0.155), two_clients_cash_mixed@36.2(0.761), handover_without_documents@41.4(0.405) |
| 39 | no_violation | - | - | violation | 0.1 | - | - | - |  | handover_without_documents@11.0(0.22), handover_without_documents@17.6(0.294), handover_without_documents@55.8(0.348) |
| 40 | violation | 17.0 | unauthorized_in_cash_zone | no_violation | 0.1 | - | - | - |  |  |
| 43 | no_violation | - | - | no_violation | 0.1 | - | - | - |  |  |
| 44 | violation | 16.0 | suspect_note_mishandled | violation | 0.1 | 16.6 | 0.6 | workplace_left_unattended | no | workplace_left_unattended@16.6(0.866) |
| 45 | no_violation | - | - | no_violation | 0.1 | - | - | - |  |  |
| 46 | violation | 11.0 | personal_items_at_workplace | violation | 0.1 | 11.2 | 0.2 | personal_items_at_workplace | yes | personal_items_at_workplace@11.2(1.0) |
| 47 | violation | 68.0 | accept_without_count | violation | 0.1 | 60.4 | 7.6 | handover_without_documents | no | two_clients_cash_mixed@9.2(0.744), handover_without_documents@9.6(0.196), two_clients_cash_mixed@59.4(0.743) |
| 48 | no_violation | - | - | violation | 0.1 | - | - | - |  | personal_items_at_workplace@10.0(0.806), issue_without_count@25.6(0.327) |
