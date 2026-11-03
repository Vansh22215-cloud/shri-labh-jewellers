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
status: rejected 2026-11-03 - R2 vs a1: beat it in 8/13 walk-forward years, CAGR 4.41% vs 9.15%, worst fall -18.36% vs -9.92%, gate FAIL
written: 2026-11-03
reason: A trend change backed by above-average volume signals real institutional buying; requiring 1.2x average volume on the signal day should filter weak, noisy crossovers.
overrides: {"min_volume_mult": 1.2}
```

```proposal
id: R3
status: rejected 2026-11-03 - R3 vs a1: beat it in 5/13 walk-forward years, CAGR 7.65% vs 9.15%, worst fall -13.22% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Trend trades have a few very large winners; after selling half at target 1, trailing the rest with a 3-ATR stop instead of a fixed target 2 should let the big winners run.
overrides: {"exit_style": "targets_trail", "trail_atr_mult": 3.0}
```

```proposal
id: R4
status: rejected 2026-11-03 - R4 vs a1: beat it in 6/13 walk-forward years, CAGR 5.56% vs 9.15%, worst fall -11.31% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Cross-sectional momentum is one of the most robust effects in equities; requiring the stock to be stronger than 60% of the market should improve the quality of trend signals.
overrides: {"min_rs_filter": 60}
```

```proposal
id: R5
status: rejected 2026-11-03 - R5 vs a1: beat it in 7/13 walk-forward years, CAGR 7.1% vs 9.15%, worst fall -16.83% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Very volatile stocks gap through stops more often and suffer the low-volatility anomaly; skipping stocks that move more than 4% a day should cut the worst losses.
overrides: {"max_atr_pct": 4.0}
```

```proposal
id: R6
status: rejected 2026-11-03 - R6 vs a1: beat it in 2/13 walk-forward years, CAGR 7.87% vs 9.15%, worst fall -15.71% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Results cause gaps that jump stops; for the tips strategy, skipping entries within 5 trading days of results should cut gap losses (P1 reduced drawdown for v1).
overrides: {"results_rule": "exclude"}
```

```proposal
id: R7
status: rejected 2026-11-03 - R7 vs a1: beat it in 7/13 walk-forward years, CAGR 4.28% vs 9.15%, worst fall -11.89% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Delivery % shows whether buyers took shares home; requiring signal-day delivery to be at least 1.2x the stock's own 20-day average should keep trend changes backed by real investors and drop speculative ones.
overrides: {"min_delivery_ratio": 1.2}
```

```proposal
id: R8
status: rejected 2026-11-03 - R8 vs a1: beat it in 6/13 walk-forward years, CAGR 4.64% vs 9.15%, worst fall -10.85% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Breakouts to a new 20-day high with high volume AND unusually high delivery reflect accumulation by investors; this setup (ROADMAP D1) may beat the moving-average-cross entry with the same exits.
overrides: {"family": "delivery_breakout"}
```

```proposal
id: R9
status: rejected 2026-11-03 - R9 vs a1: beat it in 6/13 walk-forward years, CAGR 6.97% vs 9.15%, worst fall -13.32% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Stocks in one industry fall together on sector news; allowing at most 1 open trade per industry should spread risk and reduce drawdowns without hurting average returns (ROADMAP P2).
overrides: {"max_per_industry": 1}
```

```proposal
id: R10
status: rejected 2026-11-03 - R10 vs a1: beat it in 4/13 walk-forward years, CAGR 3.6% vs 9.15%, worst fall -13.21% vs -9.92%, gate FAIL
written: 2026-11-03
reason: 65% of a1 trades end on the 25-day time limit because targets of 2R/4R (with a wide 3-ATR stop) are rarely reached; nearer targets (1R sell half, 2R rest) should convert more of the move into realised profit within the holding window.
overrides: {"target1_r": 1.0, "target2_r": 2.0}
```

```proposal
id: R11
status: rejected 2026-11-03 - R11 vs a1: beat it in 6/13 walk-forward years, CAGR 7.42% vs 9.15%, worst fall -10.31% vs -9.92%, gate FAIL
written: 2026-11-03
reason: With small positions (~Rs 5,300) Zerodha's Rs 15.34 DP charge per sell is ~0.3% of the trade, and selling half at target 1 pays it twice; a single full exit at one target (2R) halves DP costs and should lift the thin per-trade edge.
overrides: {"target1_r": 2.0, "target2_r": 2.0}
```

```proposal
id: R12
status: proposed
written: 2026-11-03
reason: FIIs are the largest informed participants in Nifty futures; when their index-futures positions are less than 30% long they are heavily hedged/bearish, and new long swing trades should face a hostile market - skipping new entries then should cut losses (ROADMAP I1).
overrides: {"min_fii_long_pct": 30}
```

```proposal
id: R13
status: proposed
written: 2026-11-03
reason: History shows Nifty opens ~0.7% lower after an S&P 500 fall of more than 1.5% (correlation 0.47); such risk-off nights often start weak days, so skipping new entries at that open should avoid buying into global selling (ROADMAP I3).
overrides: {"skip_if_us_drop_pct": 1.5}
```

```proposal
id: R14
status: proposed
written: 2026-11-03
reason: Calibration shows ~50% of a1 trades end at the 25-day limit while still drifting and only 16% reach T1; price momentum persists for 1-3 months in the literature, so allowing 40 trading days should let more of that drift be captured.
overrides: {"max_hold_days": 40}
```

```proposal
id: R15
status: proposed
written: 2026-11-03
reason: 12-1 month momentum is the most documented equity anomaly; a moving-average cross in a stock that is ALSO in the top 30% by 12-month momentum is trend continuation rather than a bounce in a long-term loser, so its trades should be better.
overrides: {"min_mom12_rank": 0.7}
```
