# Improvement research round 2: results (17 Nov 2026; rules in IMPROVE2_PREREGISTRATION.md)
**Baseline:** holdout (Nov 2023+) 1,519 trades, 42.5% won, +2.91% per trade, PF 1.57, drawdown at 1% risk −127.

| ID | Idea | Development (to Oct 2023) | Holdout | Verdict |
|---|---|---|---|---|
| R1 | Gap guard (no BUY if the open is > 0.5 ATR above the plan) | +4.08 → +4.00% | +2.91 → +2.85% | ❌ |
| R2 | Limit entry 0.25 ATR below the signal close (one day) | +4.08 → +4.13%, but win 46.7 → **46.3%** | **+3.13%**, PF 1.64, drawdown −127 → **−87**, win 42.7%, 85% of trades kept | ⚠️ near miss: fails only the "development win rate not lower" rule (−0.4 points) |
| R3 | Half profit at 2R | +4.08 → +3.65% | +2.91 → +2.51% | ❌ |
| R4 | No BUY within 5 trading days before results | +4.08 → **+4.18%**, drawdown −155 → −138 | +2.91 → **+2.92%**, win 42.7%, drawdown −127 → −124 | ✅ PASS (small, mostly a risk gain) |
| R5 | Best-first slot ranking (dip-buy A > B/C > RCP > Breakout) | total 145R → 127R | total 32R → 8R | ❌ worse than first-come |

**Recommendation:**
- Apply R4 to the live system and the TradingView indicator.
- Run R2 as a forward test: record live what a limit entry would have filled at. Adopt it only if the live record confirms.
