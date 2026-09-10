# Round 2 → Round 3

| Metric | Round 2 | Round 3 | Delta |
|---|---:|---:|---:|
| Overall Case Pass Rate | 75.00% (9/12) | 100.00% (12/12) | +25.00 pp |
| Calculation Accuracy | 81.82% (9/11) | 100.00% (11/11) | +18.18 pp |
| Workflow Path Accuracy | 72.73% (8/11) | 100.00% (11/11) | +27.27 pp |
| First-Level Driver Accuracy | 100.00% (8/8) | 100.00% (8/8) | +0.00 pp |
| Nested Driver Accuracy | 100.00% (4/4) | 100.00% (4/4) | +0.00 pp |
| Routing Validity | 100.00% (9/9) | 100.00% (11/11) | +0.00 pp |
| Evidence Coverage | 100.00% (34/34) | 100.00% (35/35) | +0.00 pp |
| Unsupported Claim Rate | 0.00% (0/34) | 0.00% (0/35) | +0.00 pp |
| Required Claim Coverage | 50.00% (2/4) | 100.00% (4/4) | +50.00 pp |
| Correct Stop Rate | 100.00% (12/12) | 100.00% (12/12) | +0.00 pp |
| Hard Constraint Violations | 0 | 0 | +0 |

The three dimension/evidence cases now pass. GMV Channel/Category queries retain the input metric for dimension localization; open diagnosis localizes Orders after nested decomposition. All nine prior passes remain passes. No unsupported claim or hard constraint violation was introduced.

Regressions: NONE

Golden Set and Round 2 fixture business data: unchanged (SHA-256 verified). Expected leakage: PASS. Offline Mock LLM + synthetic SQLite only. Software tests: 93 passed / 0 failed / 1 live skipped.

Evidence Coverage measures references for emitted core claims, not independent proof of all real-world facts. The 12-case synthetic benchmark does not establish production or live-provider accuracy. Ratio denominators vary with applicable checks/output counts. No Agent changes were made after this Round 3 run.
