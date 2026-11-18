# Round 17: a third lot for strong winners (written 18 Nov 2026, BEFORE running)
**Base (what is live now, D133):** a second lot when a trend trade is up ≥ 8% at day 15, sized to the real stop-loss (≤ 1% risk).

**Rule P2:**
- **Trigger:** the trade is also up ≥ 15% at the close of day 30.
- **Third lot:** bought at the next open and exits with the trade.
- **Sizing:** to the real stop-loss, so it loses ≤ 1% of capital (the Turtle idea of adding units as the move continues).
- **Evidence from development** (`recycle_explore.py`): trades up ≥ 8% at day 30 earned 1.51× (top-300) and 1.08× (all stocks) per day compared with a fresh signal.

**Test:** the ₹45,000 account (`improve10.sim`), random order, median of 15 runs, both sets, both periods. The comparison is base vs base + P2.

**PASS:** in both periods and both sets, yearly growth ≥ base + 1.0 point, and the worst fall is no more than 2.0 points deeper.
