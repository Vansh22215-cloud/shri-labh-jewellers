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
status: rejected 2026-11-04 - R12 vs a1: beat it in 0/13 walk-forward years, CAGR 8.8% vs 8.8% (needs +0.40), worst fall -9.92% vs -9.92%, gate FAIL
written: 2026-11-03
reason: FIIs are the largest informed participants in Nifty futures; when their index-futures positions are less than 30% long they are heavily hedged/bearish, and new long swing trades should face a hostile market - skipping new entries then should cut losses (ROADMAP I1).
overrides: {"min_fii_long_pct": 30}
```

```proposal
id: R13
status: rejected 2026-11-04 - R13 vs a1: beat it in 5/13 walk-forward years, CAGR 7.91% vs 8.8% (needs +0.41), worst fall -13.07% vs -9.92%, gate FAIL
written: 2026-11-03
reason: History shows Nifty opens ~0.7% lower after an S&P 500 fall of more than 1.5% (correlation 0.47); such risk-off nights often start weak days, so skipping new entries at that open should avoid buying into global selling (ROADMAP I3).
overrides: {"skip_if_us_drop_pct": 1.5}
```

```proposal
id: R14
status: rejected 2026-11-04 - R14 vs a1: beat it in 7/13 walk-forward years, CAGR 7.87% vs 8.8% (needs +0.41), worst fall -12.94% vs -9.92%, gate FAIL
written: 2026-11-03
reason: Calibration shows ~50% of a1 trades end at the 25-day limit while still drifting and only 16% reach T1; price momentum persists for 1-3 months in the literature, so allowing 40 trading days should let more of that drift be captured.
overrides: {"max_hold_days": 40}
```

```proposal
id: R15
status: rejected 2026-11-04 - R15 vs a1: beat it in 7/13 walk-forward years, CAGR 4.36% vs 8.8% (needs +0.42), worst fall -17.46% vs -9.92%, gate FAIL
written: 2026-11-03
reason: 12-1 month momentum is the most documented equity anomaly; a moving-average cross in a stock that is ALSO in the top 30% by 12-month momentum is trend continuation rather than a bounce in a long-term loser, so its trades should be better.
overrides: {"min_mom12_rank": 0.7}
```

```proposal
id: R16
status: rejected 2026-11-03 - R16 vs a1: beat it in 7/13 walk-forward years, CAGR 7.25% vs 9.15%, worst fall -8.73% vs -9.92%, gate FAIL
written: 2026-11-03
reason: William O'Neil's CANSLIM (strong recent earnings growth + new highs + leadership) is one of the best-documented growth-stock methods; using point-in-time quarterly EPS growth >= 25% with a 52-week-high breakout should pick stronger trends than the moving-average cross (ROADMAP S2). Coverage: ~208 large stocks with EPS history.
overrides: {"family": "canslim"}
```

```proposal
id: A1
status: rejected 2026-11-04 - A1 vs a1: beat it in 8/13 walk-forward years, CAGR 8.06% vs 8.8% (needs +0.42), worst fall -13.66% vs -9.92%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (MACD line crosses above its signal line while above zero, above the 200-day average) may time entries better than the current rule.
overrides: {"family": "macd_cross"}
```

```proposal
id: A2
status: PROMOTED to a2 on 2026-11-04 - A2 vs a1: beat it in 7/13 walk-forward years, CAGR 9.76% vs 8.8% (needs +0.43), worst fall -10.84% vs -9.92%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (14-day RSI crosses up through 50 (momentum turning positive) in a long-term uptrend) may time entries better than the current rule.
overrides: {"family": "rsi50_cross"}
```

```proposal
id: A3
status: PROMOTED to a3 on 2026-11-04 - A3 vs a2: beat it in 8/13 walk-forward years, CAGR 12.41% vs 9.76% (needs +0.43), worst fall -10.71% vs -10.84%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (Stochastic %K crosses above %D from below 20 (oversold turn) in a long-term uptrend) may time entries better than the current rule.
overrides: {"family": "stoch_cross"}
```

```proposal
id: A4
status: rejected 2026-11-04 - A4 vs a3: beat it in 0/13 walk-forward years, CAGR 4.11% vs 12.41% (needs +0.43), worst fall -18.43% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (ADX above 25 (strong trend) and +DI crosses above -DI) may time entries better than the current rule.
overrides: {"family": "adx_dmi"}
```

```proposal
id: A5
status: rejected 2026-11-04 - A5 vs a3: beat it in 3/13 walk-forward years, CAGR 7.39% vs 12.41% (needs +0.44), worst fall -17.03% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (Supertrend (10, 3) flips from down to up) may time entries better than the current rule.
overrides: {"family": "supertrend_flip"}
```

```proposal
id: A6
status: rejected 2026-11-04 - A6 vs a3: beat it in 5/13 walk-forward years, CAGR 5.11% vs 12.41% (needs +0.44), worst fall -18.63% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (close breaks above the Ichimoku cloud with Tenkan above Kijun) may time entries better than the current rule.
overrides: {"family": "ichimoku_breakout"}
```

```proposal
id: A7
status: rejected 2026-11-04 - A7 vs a3: beat it in 8/13 walk-forward years, CAGR 10.75% vs 12.41% (needs +0.44), worst fall -12.22% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (Money Flow Index crosses up through 20 (selling exhausted) in a long-term uptrend) may time entries better than the current rule.
overrides: {"family": "mfi_reversal"}
```

```proposal
id: A8
status: rejected 2026-11-04 - A8 vs a3: beat it in 7/13 walk-forward years, CAGR 6.8% vs 12.41% (needs +0.45), worst fall -18.44% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (Chaikin Money Flow above 0.15 (accumulation) with a new 20-day closing high) may time entries better than the current rule.
overrides: {"family": "cmf_breakout"}
```

```proposal
id: A9
status: rejected 2026-11-04 - A9 vs a3: beat it in 8/13 walk-forward years, CAGR 8.98% vs 12.41% (needs +0.45), worst fall -19.87% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (On-Balance Volume at a 50-day high while price is above its 50-day average) may time entries better than the current rule.
overrides: {"family": "obv_breakout"}
```

```proposal
id: A10
status: rejected 2026-11-04 - A10 vs a3: beat it in 6/13 walk-forward years, CAGR 7.92% vs 12.41% (needs +0.45), worst fall -17.2% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (Commodity Channel Index crosses above +100 (new strength)) may time entries better than the current rule.
overrides: {"family": "cci_breakout"}
```

```proposal
id: A11
status: rejected 2026-11-04 - A11 vs a3: beat it in 5/13 walk-forward years, CAGR 9.07% vs 12.41% (needs +0.45), worst fall -20.23% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (Williams %R crosses up through -80 (oversold turn) in a long-term uptrend) may time entries better than the current rule.
overrides: {"family": "williams_r"}
```

```proposal
id: A12
status: rejected 2026-11-04 - A12 vs a3: beat it in 7/13 walk-forward years, CAGR 9.64% vs 12.41% (needs +0.46), worst fall -13.13% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (weekly: top 10% by 20-day rate of change, above the 50-day average) may time entries better than the current rule.
overrides: {"family": "roc_leaders"}
```

```proposal
id: A13
status: rejected 2026-11-04 - A13 vs a3: beat it in 3/13 walk-forward years, CAGR 5.77% vs 12.41% (needs +0.46), worst fall -16.93% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (50-day average crosses above the 200-day average) may time entries better than the current rule.
overrides: {"family": "golden_cross"}
```

```proposal
id: A14
status: rejected 2026-11-04 - A14 vs a3: beat it in 5/13 walk-forward years, CAGR 8.17% vs 12.41% (needs +0.46), worst fall -15.74% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (close above the upper Keltner channel (20-day EMA + 2 ATR)) may time entries better than the current rule.
overrides: {"family": "keltner_breakout"}
```

```proposal
id: A15
status: rejected 2026-11-04 - A15 vs a3: beat it in 6/13 walk-forward years, CAGR 8.39% vs 12.41% (needs +0.46), worst fall -14.46% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (Heikin-Ashi candle turns green after 3+ red ones, in a long-term uptrend) may time entries better than the current rule.
overrides: {"family": "heikin_ashi_turn"}
```

```proposal
id: A16
status: rejected 2026-11-04 - A16 vs a3: beat it in 7/13 walk-forward years, CAGR 6.31% vs 12.41% (needs +0.47), worst fall -20.26% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (O'Neil/Kacher pocket pivot: up-day volume above every down-day volume of the prior 10 days, rising 50-day average) may time entries better than the current rule.
overrides: {"family": "pocket_pivot"}
```

```proposal
id: A17
status: rejected 2026-11-04 - A17 vs a3: beat it in 3/13 walk-forward years, CAGR 7.41% vs 12.41% (needs +0.47), worst fall -15.26% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (volume dried up (5-day average < 60% of normal) then a 20-day breakout on 1.5x volume) may time entries better than the current rule.
overrides: {"family": "volume_dryup_breakout"}
```

```proposal
id: A18
status: rejected 2026-11-04 - A18 vs a3: beat it in 6/13 walk-forward years, CAGR 6.24% vs 12.41% (needs +0.47), worst fall -23.34% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (Larry Williams volatility breakout: close above open + 0.6 x ATR at a 20-day high) may time entries better than the current rule.
overrides: {"family": "volatility_breakout"}
```

```proposal
id: A19
status: rejected 2026-11-04 - A19 vs a3: beat it in 6/13 walk-forward years, CAGR 7.32% vs 12.41% (needs +0.47), worst fall -13.9% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (bullish engulfing candle after a pullback near the 20-day EMA in an uptrend) may time entries better than the current rule.
overrides: {"family": "bullish_engulfing"}
```

```proposal
id: A20
status: rejected 2026-11-04 - A20 vs a3: beat it in 6/13 walk-forward years, CAGR 9.15% vs 12.41% (needs +0.47), worst fall -12.87% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (hammer candle (long lower shadow) after a 3-day decline in a long-term uptrend) may time entries better than the current rule.
overrides: {"family": "hammer"}
```

```proposal
id: A21
status: rejected 2026-11-04 - A21 vs a3: beat it in 5/13 walk-forward years, CAGR 5.95% vs 12.41% (needs +0.48), worst fall -12.0% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (morning-star three-candle reversal in a long-term uptrend) may time entries better than the current rule.
overrides: {"family": "morning_star"}
```

```proposal
id: A22
status: rejected 2026-11-04 - A22 vs a3: beat it in 7/13 walk-forward years, CAGR 4.54% vs 12.41% (needs +0.48), worst fall -16.83% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (three strong up candles in a row closing near their highs) may time entries better than the current rule.
overrides: {"family": "three_white_soldiers"}
```

```proposal
id: A23
status: rejected 2026-11-04 - A23 vs a3: beat it in 3/13 walk-forward years, CAGR 4.74% vs 12.41% (needs +0.48), worst fall -18.59% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (two similar lows 2-8 weeks apart, then a close above the high between them) may time entries better than the current rule.
overrides: {"family": "double_bottom"}
```

```proposal
id: A24
status: rejected 2026-11-04 - A24 vs a3: beat it in 3/13 walk-forward years, CAGR 4.19% vs 12.41% (needs +0.48), worst fall -16.13% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (flat highs with rising lows over ~6 weeks, then a close above the flat top) may time entries better than the current rule.
overrides: {"family": "ascending_triangle"}
```

```proposal
id: A25
status: rejected 2026-11-04 - A25 vs a3: beat it in 7/13 walk-forward years, CAGR 7.58% vs 12.41% (needs +0.48), worst fall -10.57% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (15%+ rise (pole), tight 5-day pause on lighter volume (flag), then a close above the flag) may time entries better than the current rule.
overrides: {"family": "bull_flag"}
```

```proposal
id: A26
status: rejected 2026-11-04 - A26 vs a3: beat it in 6/13 walk-forward years, CAGR 7.34% vs 12.41% (needs +0.48), worst fall -20.09% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (cup and handle: older high, 15%+ dip and recovery, then a close above that high) may time entries better than the current rule.
overrides: {"family": "cup_handle"}
```

```proposal
id: A27
status: rejected 2026-11-04 - A27 vs a3: beat it in 6/13 walk-forward years, CAGR 7.18% vs 12.41% (needs +0.48), worst fall -12.54% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a well-known setup (strong stock in an uptrend 5-10 days before its results date (pre-results run-up)) may time entries better than the current rule.
overrides: {"family": "pre_results_runup"}
```

```proposal
id: A28
status: rejected 2026-11-04 - A28 vs a3: beat it in 4/13 walk-forward years, CAGR 9.57% vs 12.41% (needs +0.49), worst fall -14.48% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a published method (Minervini trend template + volatility contraction breakout) may beat the current entry rule with the same exits.
overrides: {"family": "minervini_vcp"}
```

```proposal
id: A29
status: rejected 2026-11-04 - A29 vs a3: beat it in 5/13 walk-forward years, CAGR 5.42% vs 12.41% (needs +0.49), worst fall -10.69% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a published method (Weinstein stage-2 breakout above a rising 30-week average) may beat the current entry rule with the same exits.
overrides: {"family": "weinstein_stage2"}
```

```proposal
id: A30
status: rejected 2026-11-04 - A30 vs a3: beat it in 6/13 walk-forward years, CAGR 5.39% vs 12.41% (needs +0.49), worst fall -18.58% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a published method (Darvas box breakout near the 52-week high) may beat the current entry rule with the same exits.
overrides: {"family": "darvas_box"}
```

```proposal
id: A31
status: rejected 2026-11-04 - A31 vs a3: beat it in 4/13 walk-forward years, CAGR 6.65% vs 12.41% (needs +0.49), worst fall -10.84% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a published method (monthly 12-1 momentum leaders) may beat the current entry rule with the same exits.
overrides: {"family": "momentum_12_1"}
```

```proposal
id: A32
status: rejected 2026-11-04 - A32 vs a3: beat it in 5/13 walk-forward years, CAGR 5.64% vs 12.41% (needs +0.49), worst fall -15.98% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a published method (stocks closest to their 52-week high) may beat the current entry rule with the same exits.
overrides: {"family": "high52_rank"}
```

```proposal
id: A33
status: rejected 2026-11-04 - A33 vs a3: beat it in 9/13 walk-forward years, CAGR 8.69% vs 12.41% (needs +0.49), worst fall -6.84% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a published method (post-earnings drift after strong results gaps) may beat the current entry rule with the same exits.
overrides: {"family": "pead"}
```

```proposal
id: A34
status: rejected 2026-11-04 - A34 vs a3: beat it in 7/13 walk-forward years, CAGR 9.07% vs 12.41% (needs +0.49), worst fall -15.59% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a published method (leaders of the strongest sectors) may beat the current entry rule with the same exits.
overrides: {"family": "sector_rotation"}
```

```proposal
id: A35
status: rejected 2026-11-04 - A35 vs a3: beat it in 3/13 walk-forward years, CAGR 8.83% vs 12.41% (needs +0.50), worst fall -11.67% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: a published method (sharp dips below the lower Bollinger band in uptrends) may beat the current entry rule with the same exits.
overrides: {"family": "connors_pctb"}
```

```proposal
id: A36
status: rejected 2026-11-04 - A36 vs a3: beat it in 7/13 walk-forward years, CAGR 6.06% vs 12.41% (needs +0.50), worst fall -19.79% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "trend_pb_bo"}
```

```proposal
id: A37
status: rejected 2026-11-04 - A37 vs a3: beat it in 4/13 walk-forward years, CAGR 8.82% vs 12.41% (needs +0.50), worst fall -16.39% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "donchian"}
```

```proposal
id: A38
status: rejected 2026-11-04 - A38 vs a3: beat it in 6/13 walk-forward years, CAGR 9.31% vs 12.41% (needs +0.50), worst fall -21.31% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "high52"}
```

```proposal
id: A39
status: rejected 2026-11-04 - A39 vs a3: beat it in 4/13 walk-forward years, CAGR 9.99% vs 12.41% (needs +0.50), worst fall -12.44% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "mean_reversion"}
```

```proposal
id: A40
status: rejected 2026-11-04 - A40 vs a3: beat it in 6/13 walk-forward years, CAGR 8.43% vs 12.41% (needs +0.50), worst fall -12.56% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "momentum_leaders"}
```

```proposal
id: A41
status: rejected 2026-11-04 - A41 vs a3: beat it in 4/13 walk-forward years, CAGR 8.13% vs 12.41% (needs +0.50), worst fall -17.04% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "squeeze"}
```

```proposal
id: A42
status: rejected 2026-11-04 - A42 vs a3: beat it in 3/13 walk-forward years, CAGR 4.5% vs 12.55% (needs +0.50), worst fall -16.61% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "volume_surge"}
```

```proposal
id: A43
status: rejected 2026-11-04 - A43 vs a3: beat it in 4/13 walk-forward years, CAGR 6.19% vs 12.55% (needs +0.50), worst fall -13.08% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "nr7"}
```

```proposal
id: A44
status: rejected 2026-11-04 - A44 vs a3: beat it in 8/13 walk-forward years, CAGR 8.3% vs 12.55% (needs +0.51), worst fall -17.47% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "lowvol_momentum"}
```

```proposal
id: A45
status: rejected 2026-11-04 - A45 vs a3: beat it in 7/13 walk-forward years, CAGR 9.22% vs 12.55% (needs +0.51), worst fall -13.74% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "inside_day"}
```

```proposal
id: A46
status: rejected 2026-11-04 - A46 vs a3: beat it in 2/13 walk-forward years, CAGR 4.62% vs 12.55% (needs +0.51), worst fall -11.83% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "gap_go"}
```

```proposal
id: A47
status: rejected 2026-11-04 - A47 vs a3: beat it in 6/13 walk-forward years, CAGR 5.15% vs 12.55% (needs +0.51), worst fall -15.28% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "strong_close"}
```

```proposal
id: A48
status: rejected 2026-11-04 - A48 vs a3: beat it in 7/13 walk-forward years, CAGR 14.01% vs 12.55% (needs +0.51), worst fall -9.69% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "pullback_3d"}
```

```proposal
id: A49
status: rejected 2026-11-04 - A49 vs a3: beat it in 5/13 walk-forward years, CAGR 6.49% vs 12.55% (needs +0.51), worst fall -15.62% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Three Inside Up/Down pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdl3inside"}
```

```proposal
id: A50
status: rejected 2026-11-04 - A50 vs a3: beat it in 4/13 walk-forward years, CAGR 7.33% vs 12.55% (needs +0.51), worst fall -10.82% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Three-Line Strike pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdl3linestrike"}
```

```proposal
id: A51
status: rejected 2026-11-04 - A51 vs a3: beat it in 7/13 walk-forward years, CAGR 7.83% vs 12.55% (needs +0.51), worst fall -15.73% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Three Outside Up/Down pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdl3outside"}
```

```proposal
id: A52
status: rejected 2026-11-04 - A52 vs a3: beat it in 6/13 walk-forward years, CAGR 6.86% vs 12.55% (needs +0.51), worst fall -0.32% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Three Stars in the South pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdl3starsinsouth"}
```

```proposal
id: A53
status: rejected 2026-11-04 - A53 vs a3: beat it in 6/13 walk-forward years, CAGR 7.31% vs 12.55% (needs +0.51), worst fall -1.58% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Three Advancing White Soldiers pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdl3whitesoldiers"}
```

```proposal
id: A54
status: rejected 2026-11-04 - A54 vs a3: beat it in 6/13 walk-forward years, CAGR 7.04% vs 12.55% (needs +0.52), worst fall -0.61% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Abandoned Baby pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlabandonedbaby"}
```

```proposal
id: A55
status: rejected 2026-11-04 - A55 vs a3: beat it in 3/13 walk-forward years, CAGR 6.04% vs 12.55% (needs +0.52), worst fall -17.42% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Belt-hold pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlbelthold"}
```

```proposal
id: A56
status: rejected 2026-11-04 - A56 vs a3: beat it in 6/13 walk-forward years, CAGR 7.12% vs 12.55% (needs +0.52), worst fall -2.35% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Breakaway pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlbreakaway"}
```

```proposal
id: A57
status: rejected 2026-11-04 - A57 vs a3: beat it in 6/13 walk-forward years, CAGR 5.92% vs 12.55% (needs +0.52), worst fall -12.45% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Closing Marubozu pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlclosingmarubozu"}
```

```proposal
id: A58
status: rejected 2026-11-04 - A58 vs a3: beat it in 6/13 walk-forward years, CAGR 6.87% vs 12.55% (needs +0.52), worst fall -0.88% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Concealing Baby Swallow pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlconcealbabyswall"}
```

```proposal
id: A59
status: rejected 2026-11-04 - A59 vs a3: beat it in 5/13 walk-forward years, CAGR 5.86% vs 12.55% (needs +0.52), worst fall -9.4% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Counterattack pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlcounterattack"}
```

```proposal
id: A60
status: rejected 2026-11-04 - A60 vs a3: beat it in 6/13 walk-forward years, CAGR 10.13% vs 12.55% (needs +0.52), worst fall -18.37% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Doji pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdldoji"}
```

```proposal
id: A61
status: rejected 2026-11-04 - A61 vs a3: beat it in 5/13 walk-forward years, CAGR 6.05% vs 12.55% (needs +0.52), worst fall -17.71% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Doji Star pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdldojistar"}
```

```proposal
id: A62
status: rejected 2026-11-04 - A62 vs a3: beat it in 4/13 walk-forward years, CAGR 5.61% vs 12.55% (needs +0.52), worst fall -11.68% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Engulfing Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlengulfing"}
```

```proposal
id: A63
status: rejected 2026-11-04 - A63 vs a3: beat it in 5/13 walk-forward years, CAGR 6.47% vs 12.55% (needs +0.52), worst fall -11.62% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Up/Down-Gap Side-by-Side White Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlgapsidesidewhite"}
```

```proposal
id: A64
status: rejected 2026-11-04 - A64 vs a3: beat it in 6/13 walk-forward years, CAGR 5.18% vs 12.55% (needs +0.52), worst fall -22.34% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Harami Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlharami"}
```

```proposal
id: A65
status: rejected 2026-11-04 - A65 vs a3: beat it in 6/13 walk-forward years, CAGR 7.61% vs 12.55% (needs +0.52), worst fall -17.11% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Harami Cross Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlharamicross"}
```

```proposal
id: A66
status: rejected 2026-11-04 - A66 vs a3: beat it in 8/13 walk-forward years, CAGR 10.41% vs 12.55% (needs +0.52), worst fall -13.93% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the High-Wave Candle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlhighwave"}
```

```proposal
id: A67
status: rejected 2026-11-04 - A67 vs a3: beat it in 7/13 walk-forward years, CAGR 9.61% vs 12.55% (needs +0.53), worst fall -11.65% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Hikkake Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlhikkake"}
```

```proposal
id: A68
status: rejected 2026-11-04 - A68 vs a3: beat it in 6/13 walk-forward years, CAGR 9.06% vs 12.55% (needs +0.53), worst fall -12.77% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Modified Hikkake Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlhikkakemod"}
```

```proposal
id: A69
status: rejected 2026-11-04 - A69 vs a3: beat it in 7/13 walk-forward years, CAGR 7.04% vs 12.55% (needs +0.53), worst fall -15.56% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Homing Pigeon pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlhomingpigeon"}
```

```proposal
id: A70
status: rejected 2026-11-04 - A70 vs a3: beat it in 6/13 walk-forward years, CAGR 6.92% vs 12.55% (needs +0.53), worst fall -0.24% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Kicking pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlkicking"}
```

```proposal
id: A71
status: rejected 2026-11-04 - A71 vs a3: beat it in 6/13 walk-forward years, CAGR 6.92% vs 12.55% (needs +0.53), worst fall -0.24% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Kicking by Length pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlkickingbylength"}
```

```proposal
id: A72
status: rejected 2026-11-04 - A72 vs a3: beat it in 4/13 walk-forward years, CAGR 6.68% vs 12.55% (needs +0.53), worst fall -9.17% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Ladder Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlladderbottom"}
```

```proposal
id: A73
status: rejected 2026-11-04 - A73 vs a3: beat it in 8/13 walk-forward years, CAGR 10.09% vs 12.55% (needs +0.53), worst fall -15.84% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Long-Legged Doji pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdllongleggeddoji"}
```

```proposal
id: A74
status: rejected 2026-11-04 - A74 vs a3: beat it in 4/13 walk-forward years, CAGR 3.44% vs 12.55% (needs +0.53), worst fall -21.25% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Long Line Candle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdllongline"}
```

```proposal
id: A75
status: rejected 2026-11-04 - A75 vs a3: beat it in 5/13 walk-forward years, CAGR 5.92% vs 12.55% (needs +0.53), worst fall -11.78% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Marubozu pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlmarubozu"}
```

```proposal
id: A76
status: rejected 2026-11-04 - A76 vs a3: beat it in 7/13 walk-forward years, CAGR 8.57% vs 12.55% (needs +0.53), worst fall -10.69% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Matching Low pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlmatchinglow"}
```

```proposal
id: A77
status: rejected 2026-11-04 - A77 vs a3: beat it in 5/13 walk-forward years, CAGR 6.84% vs 12.55% (needs +0.53), worst fall -2.49% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Mat Hold pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlmathold"}
```

```proposal
id: A78
status: proposed
written: 2026-11-03
reason: (idea factory) For a1: the Morning Doji Star pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlmorningdojistar"}
```

```proposal
id: A79
status: proposed
written: 2026-11-03
reason: (idea factory) For a1: the Morning Star pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlmorningstar"}
```

```proposal
id: A80
status: proposed
written: 2026-11-03
reason: (idea factory) For a1: the Piercing Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlpiercing"}
```

```proposal
id: A81
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "ma_cross"}
```

```proposal
id: A82
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Rickshaw Man pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlrickshawman"}
```

```proposal
id: A83
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Rising/Falling Three Methods pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlrisefall3methods"}
```

```proposal
id: A84
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Separating Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlseparatinglines"}
```

```proposal
id: A85
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Short Line Candle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlshortline"}
```

```proposal
id: A86
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Spinning Top pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlspinningtop"}
```

```proposal
id: A87
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Stick Sandwich pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlsticksandwich"}
```

```proposal
id: A88
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Tasuki Gap pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdltasukigap"}
```

```proposal
id: A89
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Tristar pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdltristar"}
```

```proposal
id: A90
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Unique Three River pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlunique3river"}
```

```proposal
id: A91
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Upside/Downside Gap Three Methods pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlxsidegap3methods"}
```

```proposal
id: A92
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Tweezer Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_tweezer_bottom"}
```

```proposal
id: A93
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Railroad Tracks pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_railroad_tracks"}
```

```proposal
id: A94
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Belt Hold (generic variant) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_belt_hold"}
```

```proposal
id: A95
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Belt Hold pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_belt_hold_bullish"}
```

```proposal
id: A96
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Three-Bar Reversal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_three_bar_reversal"}
```

```proposal
id: A97
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Fakey / Failed Inside-Bar Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_fakey_inside_bar"}
```

```proposal
id: A98
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Fakey pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_fakey"}
```

```proposal
id: A99
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Long-Legged Doji pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_long_legged_doji"}
```

```proposal
id: A100
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Rickshaw Man pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_rickshaw_man"}
```

```proposal
id: A101
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Dragonfly Doji pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_dragonfly_doji"}
```

```proposal
id: A102
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Harami Cross pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_harami_cross"}
```

```proposal
id: A103
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Homing Pigeon pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_homing_pigeon"}
```

```proposal
id: A104
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Matching Low pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_matching_low"}
```

```proposal
id: A105
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Meeting Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_meeting_lines"}
```

```proposal
id: A106
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Separating Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_separating_lines"}
```

```proposal
id: A107
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Piercing Line (strict variant) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_piercing_line_variant"}
```

```proposal
id: A108
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Kicker pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_kicker"}
```

```proposal
id: A109
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Three-Line Strike pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_three_line_strike"}
```

```proposal
id: A110
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Three White Soldiers (strict variant) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_three_white_soldiers_strict"}
```

```proposal
id: A111
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Hammer (contextual strict) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_hammer_contextual"}
```

```proposal
id: A112
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Inverted Hammer (contextual strict) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_inverted_hammer_contextual"}
```

```proposal
id: A113
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Counterattack Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_counterattack"}
```

```proposal
id: A114
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Gap-Fill Reclaim Candle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_gap_fill_reclaim_candle"}
```

```proposal
id: A115
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Rising Three Methods pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_rising_three_methods"}
```

```proposal
id: A116
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Mat Hold pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_mat_hold"}
```

```proposal
id: A117
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Stick Sandwich pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_stick_sandwich"}
```

```proposal
id: A118
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Ladder Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_ladder_bottom"}
```

```proposal
id: A119
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Unique Three River Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_unique_three_river"}
```

```proposal
id: A120
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Abandoned Baby Bullish pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_abandoned_baby"}
```

```proposal
id: A121
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Upside Gap Side-by-Side White Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_gap_side_by_side_white_lines"}
```

```proposal
id: A122
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Downside Gap Three Methods pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bearish_downside_gap_three_methods"}
```

```proposal
id: A123
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Three Stars in the South pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bearish_three_star_south"}
```

```proposal
id: A124
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Concealing Baby Swallow pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_concealing_baby_swallow"}
```

```proposal
id: A125
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Double Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_double_bottom"}
```

```proposal
id: A126
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Triple Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_triple_bottom"}
```

```proposal
id: A127
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Inverse Head and Shoulders pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_inverse_head_and_shoulders"}
```

```proposal
id: A128
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Ascending Triangle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_ascending_triangle"}
```

```proposal
id: A129
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Rectangle / Trading Range pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_rectangle_range"}
```

```proposal
id: A130
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Falling Wedge pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_falling_wedge"}
```

```proposal
id: A131
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Broadening Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_broadening_bottom"}
```

```proposal
id: A132
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Measured Move Up / AB=CD Projection pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_measured_move_up"}
```

```proposal
id: A133
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Bull Pennant pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_bull_pennant"}
```

```proposal
id: A134
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Breakout and Retest pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_breakout_retest"}
```

```proposal
id: A135
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the False Breakout / Failed Auction pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_false_breakout"}
```

```proposal
id: A136
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Outside Bar / Engulfing Range Bar pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_outside_bar"}
```

```proposal
id: A137
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Pin Bar / Rejection Bar pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_pin_bar_rejection"}
```

```proposal
id: A138
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Breakaway Gap pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gap_breakaway"}
```

```proposal
id: A139
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Runaway / Measuring Gap pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gap_runaway"}
```

```proposal
id: A140
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Wyckoff Spring pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_wyckoff_spring"}
```

```proposal
id: A141
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Island Reversal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_island_reversal"}
```

```proposal
id: A142
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Inside Bar Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_inside_bar_breakout"}
```

```proposal
id: A143
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the NR4 Inside Day pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_nr4_inside_day"}
```

```proposal
id: A144
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the NR7 Inside Day pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_nr7_inside_day"}
```

```proposal
id: A145
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Darvas Box pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_darvas_box"}
```

```proposal
id: A146
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Flat Base pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_flat_base"}
```

```proposal
id: A147
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Volatility Contraction Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_vcp_volatility_contraction"}
```

```proposal
id: A148
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Key Reversal Up pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_key_reversal_up"}
```

```proposal
id: A149
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Turtle Soup False Break pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_turtle_soup"}
```

```proposal
id: A150
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Three Bar Play pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_three_bar_play"}
```

```proposal
id: A151
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Gap and Go pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gap_and_go"}
```

```proposal
id: A152
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Gap Fill Reversion pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gap_fill_reversion"}
```

```proposal
id: A153
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the First Pullback After Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_first_pullback_after_breakout"}
```

```proposal
id: A154
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Symmetrical Triangle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_symmetrical_triangle"}
```

```proposal
id: A155
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Ascending Channel pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_ascending_channel"}
```

```proposal
id: A156
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Cup Without Handle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_cup_without_handle"}
```

```proposal
id: A157
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the V Reversal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_v_reversal"}
```

```proposal
id: A158
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Selling Climax pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_selling_climax"}
```

```proposal
id: A159
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Liquidity Sweep Reversal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_liquidity_sweep_reversal"}
```

```proposal
id: A160
status: proposed
written: 2026-11-04
reason: (idea factory) For a3: the Compression Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_compression_breakout"}
```
