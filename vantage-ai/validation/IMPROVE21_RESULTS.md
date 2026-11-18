# Round 21 results: stress test of the live setup, ₹51,000 (18 Nov 2026): ✅ robust, no flags
**Top-300 trade set.** Each cell: yearly growth % / worst fall %.

| Holdout (Nov 2023+) | B (next open) | C (3:20 pm close) | C + ADD MORE (live) |
|---|---|---|---|
| S0 normal | 14.8 / −20.1 | 15.8 / −20.2 | **18.8 / −19.2** |
| S1 costs 0.6% | 12.9 / −20.8 | 14.5 / −21.6 | **15.5 / −21.1** |
| S2 every buy 0.3% worse | 13.5 / −21.2 | 15.5 / −20.4 | **18.4 / −19.5** |
| S3 30% of tips missed | 14.2 / −20.4 | 15.8 / −18.1 | **18.8 / −18.5** |
| S4 all three | 11.0 / −21.4 | 12.8 / −20.2 | **15.4 / −20.1** |

**Development:**
- S0: B 18.9, C 20.4, C + ADD MORE 20.5.
- S4: B 15.7, C 16.0, C + ADD MORE 16.9.

**Verdict:**
- No stress makes the live rules worse than the plain setup.
- The live rules do not depend on perfect execution.
- Even with all three problems at once, the live setup made about 15% a year in the recent years.
