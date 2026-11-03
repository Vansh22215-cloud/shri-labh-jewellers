# IMPROVEMENTS.md - pre-registered proposals

Rules: every proposal states its reason **before** it is tested. The weekly job tests proposals with
`status: proposed`, runs the full validation gate in a sandbox, and promotes at most one per week - only if it
passes the gate AND beats the live version in most walk-forward periods AND has a higher walk-forward CAGR.
Results are written back here and in CHANGELOG.md. Recent paper trades alone never justify a change.

You (or Claude) can add a proposal by copying a block below and changing it.

```proposal
id: P1
status: rejected 2026-11-02 - P1: gate FAIL, beat live in 7/13 walk-forward periods, WF CAGR 7.13% vs live 6.79%, WF maxDD -17.35% vs -21.74%
written: 2026-11-02
reason: Quarterly results cause large overnight gaps that jump past stop-losses; skipping entries within 5 trading days before results should cut gap losses more than it costs in missed winners.
overrides: {"results_rule": "exclude"}
```

## Research backlog (written 2026-11-03, BEFORE any of these were tested)
Each is tested against the strategy that currently gives tips (aggressive line aN while nothing is validated),
one per weekday evening by the daily research session, with the rules in weekly.test_proposal (D60).

```proposal
id: R1
status: rejected 2026-11-03 - R1 vs a1: beat it in 4/13 walk-forward years, CAGR 8.43% vs 9.15%, worst fall -12.66% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Industry momentum persists (Moskowitz & Grinblatt 1999); only buying stocks whose industry is in the stronger half should avoid fighting sector headwinds.
overrides: {"min_sector_rank": 0.5}
```

```proposal
id: R2
status: proposed
written: 2026-11-03
reason: A trend change backed by above-average volume signals real institutional buying; requiring 1.2x average volume on the signal day should filter weak, noisy crossovers.
overrides: {"min_volume_mult": 1.2}
```

```proposal
id: R3
status: proposed
written: 2026-11-03
reason: Trend trades have a few very large winners; after selling half at target 1, trailing the rest with a 3-ATR stop instead of a fixed target 2 should let the big winners run.
overrides: {"exit_style": "targets_trail", "trail_atr_mult": 3.0}
```

```proposal
id: R4
status: proposed
written: 2026-11-03
reason: Cross-sectional momentum is one of the most robust effects in equities; requiring the stock to be stronger than 60% of the market should improve the quality of trend signals.
overrides: {"min_rs_filter": 60}
```

```proposal
id: R5
status: proposed
written: 2026-11-03
reason: Very volatile stocks gap through stops more often and suffer the low-volatility anomaly; skipping stocks that move more than 4% a day should cut the worst losses.
overrides: {"max_atr_pct": 4.0}
```

```proposal
id: R6
status: proposed
written: 2026-11-03
reason: Results cause gaps that jump stops; for the tips strategy, skipping entries within 5 trading days of results should cut gap losses (P1 reduced drawdown for v1).
overrides: {"results_rule": "exclude"}
```

```proposal
id: R7
status: proposed
written: 2026-11-03
reason: Delivery % shows whether buyers took shares home; requiring signal-day delivery to be at least 1.2x the stock's own 20-day average should keep trend changes backed by real investors and drop speculative ones.
overrides: {"min_delivery_ratio": 1.2}
```

```proposal
id: R8
status: proposed
written: 2026-11-03
reason: Breakouts to a new 20-day high with high volume AND unusually high delivery reflect accumulation by investors; this setup (ROADMAP D1) may beat the moving-average-cross entry with the same exits.
overrides: {"family": "delivery_breakout"}
```

```proposal
id: R9
status: proposed
written: 2026-11-03
reason: Stocks in one industry fall together on sector news; allowing at most 1 open trade per industry should spread risk and reduce drawdowns without hurting average returns (ROADMAP P2).
overrides: {"max_per_industry": 1}
```
