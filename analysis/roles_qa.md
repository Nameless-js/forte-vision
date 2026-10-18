# Roles & zones QA

Per-video calibration summary (behaviour-based; see forte_ai/perception/roles.py). `empty_start` means
nobody was at the workplace in the first seconds — там выбранный 'cashier'-трек на самом деле вошедший
посторонний, и правила переключаются в режим R10 (вход в пустой кассовый узел).

| id | label | cashier T | score | margin | presence | window anchor | counter conf | empty start | notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | violation | 1 | 0.80 | 0.12 | 0.99 | yes | 1.00 |  |  |
| 2 | violation | 1 | 0.73 | 0.12 | 0.99 | yes | 1.00 |  |  |
| 3 | no_violation | 1 | 0.83 | 0.16 | 0.99 | yes | 1.00 |  |  |
| 4 | violation | 1 | 0.84 | 0.29 | 1.00 | yes | 1.00 |  |  |
| 5 | no_violation | 2 | 0.83 | 0.15 | 1.00 | yes | 1.00 |  |  |
| 8 | no_violation | 1 | 0.84 | 0.20 | 0.99 | no | 0.20 |  |  |
| 10 | no_violation | 1 | 0.91 | 0.26 | 0.99 | no | 0.20 |  |  |
| 11 | violation | 2 | 0.75 | 0.04 | 0.52 | yes | 0.79 |  | cashier margin small: 0.746 vs 0.711; FLAGGED |
| 12 | no_violation | 1 | 0.70 | 0.02 | 0.97 | yes | 0.84 |  | cashier margin small: 0.700 vs 0.684; FLAGGED |
| 13 | violation | 1 | 0.87 | 0.26 | 0.98 | yes | 0.83 |  |  |
| 14 | no_violation | 1 | 0.81 | 0.27 | 1.00 | yes | 0.84 |  |  |
| 15 | violation | 1 | 0.73 | 0.09 | 0.95 | no | 0.20 |  |  |
| 16 | no_violation | 1 | 0.82 | 0.08 | 0.99 | yes | 1.00 |  |  |
| 17 | violation | 1 | 0.79 | 0.08 | 0.99 | yes | 1.00 |  |  |
| 18 | violation | 2 | 0.81 | 0.27 | 0.99 | yes | 1.00 |  |  |
| 19 | no_violation | 2 | 0.78 | 0.15 | 1.00 | yes | 1.00 |  |  |
| 20 | violation | 1 | 0.89 | 0.37 | 0.98 | no | 0.20 |  |  |
| 21 | no_violation | 1 | 0.86 | 0.40 | 0.99 | no | 0.20 |  |  |
| 22 | violation | 1 | 0.73 | 0.11 | 0.93 | yes | 0.96 |  |  |
| 23 | no_violation | 1 | 0.82 | 0.28 | 0.93 | no | 0.20 |  |  |
| 24 | violation | 1 | 0.76 | 0.15 | 0.89 | no | 0.20 |  |  |
| 25 | no_violation | 1 | 0.82 | 0.30 | 0.95 | yes | 1.00 |  |  |
| 26 | violation | 1 | 0.66 | 0.05 | 0.90 | no | 0.20 |  |  |
| 27 | no_violation | 1 | 0.79 | 0.25 | 0.95 | no | 0.20 |  |  |
| 28 | violation | 1 | 0.72 | 0.11 | 0.93 | no | 0.20 |  |  |
| 29 | no_violation | 1 | 0.72 | 0.13 | 0.92 | no | 0.20 |  |  |
| 30 | violation | 1 | 0.81 | 0.32 | 0.98 | no | 0.20 |  |  |
| 31 | no_violation | 1 | 0.72 | 0.27 | 0.90 | no | 0.20 |  |  |
| 32 | violation | 1 | 0.83 | 0.47 | 0.93 | no | 0.20 |  |  |
| 33 | violation | 1 | 0.68 | 0.23 | 0.94 | no | 0.20 |  |  |
| 34 | violation | 1 | 0.82 | 0.12 | 0.99 | yes | 1.00 |  |  |
| 35 | no_violation | 1 | 0.75 | 0.06 | 1.00 | yes | 1.00 |  |  |
| 37 | no_violation | 1 | 0.82 | 0.11 | 0.99 | yes | 1.00 |  |  |
| 38 | violation | 2 | 0.78 | 0.21 | 1.00 | yes | 1.00 |  |  |
| 39 | no_violation | 1 | 0.76 | 0.20 | 1.00 | yes | 1.00 |  |  |
| 40 | violation | 1 | 0.76 | 0.42 | 0.97 | no | 0.20 |  |  |
| 43 | no_violation | 1 | 0.82 | 0.23 | 0.99 | no | 0.20 |  |  |
| 44 | violation | 2 | 0.79 | 0.03 | 0.98 | yes | 0.80 |  | cashier margin small: 0.785 vs 0.751; FLAGGED |
| 45 | no_violation | 1 | 0.89 | 0.29 | 0.99 | no | 0.20 |  |  |
| 46 | violation | 1 | 0.91 | 0.37 | 0.99 | no | 0.20 |  |  |
| 47 | violation | 1 | 0.84 | 0.29 | 1.00 | yes | 1.00 |  |  |
| 48 | no_violation | 2 | 0.83 | 0.15 | 1.00 | yes | 1.00 |  |  |

Flagged for manual check: [11, 12, 44]

Flip/rotation invariance of the role logic is covered by tests/test_roles.py; end-to-end invariance is measured by `make robustness` (reports/robustness).
