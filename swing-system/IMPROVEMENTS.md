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
status: rejected 2026-11-04 - A78 vs a3: beat it in 2/13 walk-forward years, CAGR 3.87% vs 12.55% (needs +0.53), worst fall -13.53% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Morning Doji Star pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlmorningdojistar"}
```

```proposal
id: A79
status: rejected 2026-11-04 - A79 vs a3: beat it in 5/13 walk-forward years, CAGR 6.4% vs 12.55% (needs +0.53), worst fall -11.81% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Morning Star pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlmorningstar"}
```

```proposal
id: A80
status: rejected 2026-11-04 - A80 vs a3: beat it in 3/13 walk-forward years, CAGR 7.3% vs 12.55% (needs +0.53), worst fall -13.17% vs -10.71%, gate FAIL
written: 2026-11-03
reason: (idea factory) For a1: the Piercing Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlpiercing"}
```

```proposal
id: A81
status: rejected 2026-11-05 - A81 vs a3: beat it in 4/13 walk-forward years, CAGR 9.28% vs 12.55% (needs +0.53), worst fall -9.92% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: an alternative core entry rule may beat the current one with the same exits.
overrides: {"family": "ma_cross"}
```

```proposal
id: A82
status: rejected 2026-11-05 - A82 vs a3: beat it in 8/13 walk-forward years, CAGR 9.86% vs 12.55% (needs +0.54), worst fall -15.06% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Rickshaw Man pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlrickshawman"}
```

```proposal
id: A83
status: rejected 2026-11-05 - A83 vs a3: beat it in 6/13 walk-forward years, CAGR 6.65% vs 12.55% (needs +0.54), worst fall -5.78% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Rising/Falling Three Methods pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlrisefall3methods"}
```

```proposal
id: A84
status: rejected 2026-11-05 - A84 vs a3: beat it in 7/13 walk-forward years, CAGR 7.66% vs 12.55% (needs +0.54), worst fall -10.33% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Separating Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlseparatinglines"}
```

```proposal
id: A85
status: rejected 2026-11-05 - A85 vs a3: beat it in 7/13 walk-forward years, CAGR 9.46% vs 12.55% (needs +0.54), worst fall -12.47% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Short Line Candle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlshortline"}
```

```proposal
id: A86
status: rejected 2026-11-05 - A86 vs a3: beat it in 7/13 walk-forward years, CAGR 6.38% vs 12.55% (needs +0.54), worst fall -19.25% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Spinning Top pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlspinningtop"}
```

```proposal
id: A87
status: rejected 2026-11-05 - A87 vs a3: beat it in 4/13 walk-forward years, CAGR 6.5% vs 12.55% (needs +0.54), worst fall -10.28% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Stick Sandwich pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlsticksandwich"}
```

```proposal
id: A88
status: rejected 2026-11-05 - A88 vs a3: beat it in 8/13 walk-forward years, CAGR 9.01% vs 12.55% (needs +0.54), worst fall -13.77% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Tasuki Gap pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdltasukigap"}
```

```proposal
id: A89
status: rejected 2026-11-05 - A89 vs a3: beat it in 8/13 walk-forward years, CAGR 7.41% vs 12.55% (needs +0.54), worst fall -10.52% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Tristar pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdltristar"}
```

```proposal
id: A90
status: rejected 2026-11-05 - A90 vs a3: beat it in 6/13 walk-forward years, CAGR 6.37% vs 12.55% (needs +0.54), worst fall -10.2% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Unique Three River pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlunique3river"}
```

```proposal
id: A91
status: rejected 2026-11-05 - A91 vs a3: beat it in 3/13 walk-forward years, CAGR 7.61% vs 12.55% (needs +0.54), worst fall -11.25% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Upside/Downside Gap Three Methods pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdl_cdlxsidegap3methods"}
```

```proposal
id: A92
status: rejected 2026-11-05 - A92 vs a3: beat it in 6/13 walk-forward years, CAGR 8.79% vs 12.55% (needs +0.54), worst fall -16.54% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Tweezer Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_tweezer_bottom"}
```

```proposal
id: A93
status: rejected 2026-11-05 - A93 vs a3: beat it in 7/13 walk-forward years, CAGR 6.11% vs 12.55% (needs +0.54), worst fall -14.41% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Railroad Tracks pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_railroad_tracks"}
```

```proposal
id: A94
status: rejected 2026-11-05 - A94 vs a3: beat it in 7/13 walk-forward years, CAGR 6.94% vs 12.55% (needs +0.54), worst fall -16.6% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Belt Hold (generic variant) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_belt_hold"}
```

```proposal
id: A95
status: rejected 2026-11-05 - A95 vs a3: beat it in 6/13 walk-forward years, CAGR 7.62% vs 12.55% (needs +0.54), worst fall -19.59% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Belt Hold pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_belt_hold_bullish"}
```

```proposal
id: A96
status: rejected 2026-11-05 - A96 vs a3: beat it in 8/13 walk-forward years, CAGR 11.08% vs 12.55% (needs +0.54), worst fall -12.54% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Three-Bar Reversal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_three_bar_reversal"}
```

```proposal
id: A97
status: rejected 2026-11-05 - A97 vs a3: beat it in 4/13 walk-forward years, CAGR 3.68% vs 12.55% (needs +0.54), worst fall -17.37% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Fakey / Failed Inside-Bar Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_fakey_inside_bar"}
```

```proposal
id: A98
status: rejected 2026-11-05 - A98 vs a3: beat it in 5/13 walk-forward years, CAGR 5.78% vs 12.55% (needs +0.54), worst fall -13.92% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Fakey pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_fakey"}
```

```proposal
id: A99
status: rejected 2026-11-05 - A99 vs a3: beat it in 6/13 walk-forward years, CAGR 8.33% vs 12.55% (needs +0.54), worst fall -13.25% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Long-Legged Doji pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_long_legged_doji"}
```

```proposal
id: A100
status: rejected 2026-11-05 - A100 vs a3: beat it in 4/13 walk-forward years, CAGR 4.79% vs 12.55% (needs +0.55), worst fall -18.95% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Rickshaw Man pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_rickshaw_man"}
```

```proposal
id: A101
status: rejected 2026-11-05 - A101 vs a3: beat it in 3/13 walk-forward years, CAGR 5.49% vs 12.55% (needs +0.55), worst fall -18.19% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Dragonfly Doji pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_dragonfly_doji"}
```

```proposal
id: A102
status: rejected 2026-11-05 - A102 vs a3: beat it in 5/13 walk-forward years, CAGR 7.75% vs 12.55% (needs +0.55), worst fall -15.58% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Harami Cross pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_harami_cross"}
```

```proposal
id: A103
status: rejected 2026-11-05 - A103 vs a3: beat it in 7/13 walk-forward years, CAGR 6.9% vs 12.55% (needs +0.55), worst fall -16.63% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Homing Pigeon pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_homing_pigeon"}
```

```proposal
id: A104
status: rejected 2026-11-05 - A104 vs a3: beat it in 8/13 walk-forward years, CAGR 11.16% vs 12.55% (needs +0.55), worst fall -12.09% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Matching Low pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_matching_low"}
```

```proposal
id: A105
status: rejected 2026-11-05 - A105 vs a3: beat it in 3/13 walk-forward years, CAGR 4.46% vs 12.55% (needs +0.55), worst fall -11.2% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Meeting Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_meeting_lines"}
```

```proposal
id: A106
status: rejected 2026-11-05 - A106 vs a3: beat it in 5/13 walk-forward years, CAGR 9.45% vs 12.55% (needs +0.55), worst fall -12.0% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Separating Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_separating_lines"}
```

```proposal
id: A107
status: rejected 2026-11-05 - A107 vs a3: beat it in 3/13 walk-forward years, CAGR 5.94% vs 12.55% (needs +0.55), worst fall -11.32% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Piercing Line (strict variant) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_piercing_line_variant"}
```

```proposal
id: A108
status: rejected 2026-11-05 - A108 vs a3: beat it in 5/13 walk-forward years, CAGR 7.11% vs 12.55% (needs +0.55), worst fall -6.85% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Kicker pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_kicker"}
```

```proposal
id: A109
status: rejected 2026-11-05 - A109 vs a3: beat it in 3/13 walk-forward years, CAGR 5.99% vs 12.55% (needs +0.55), worst fall -17.68% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Three-Line Strike pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_three_line_strike"}
```

```proposal
id: A110
status: rejected 2026-11-05 - A110 vs a3: beat it in 7/13 walk-forward years, CAGR 8.16% vs 12.55% (needs +0.55), worst fall -8.13% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Three White Soldiers (strict variant) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_three_white_soldiers_strict"}
```

```proposal
id: A111
status: rejected 2026-11-05 - A111 vs a3: beat it in 6/13 walk-forward years, CAGR 9.27% vs 12.55% (needs +0.55), worst fall -11.71% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Hammer (contextual strict) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_hammer_contextual"}
```

```proposal
id: A112
status: rejected 2026-11-05 - A112 vs a3: beat it in 3/13 walk-forward years, CAGR 4.93% vs 12.55% (needs +0.55), worst fall -13.56% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Inverted Hammer (contextual strict) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_inverted_hammer_contextual"}
```

```proposal
id: A113
status: rejected 2026-11-05 - A113 vs a3: beat it in 3/13 walk-forward years, CAGR 3.6% vs 12.55% (needs +0.55), worst fall -12.83% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bullish Counterattack Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_counterattack"}
```

```proposal
id: A114
status: rejected 2026-11-05 - A114 vs a3: beat it in 4/13 walk-forward years, CAGR 5.59% vs 12.55% (needs +0.55), worst fall -23.5% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Gap-Fill Reclaim Candle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_gap_fill_reclaim_candle"}
```

```proposal
id: A115
status: rejected 2026-11-05 - A115 vs a3: beat it in 5/13 walk-forward years, CAGR 6.52% vs 12.55% (needs +0.55), worst fall -2.65% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Rising Three Methods pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_rising_three_methods"}
```

```proposal
id: A116
status: rejected 2026-11-05 - A116 vs a3: beat it in 5/13 walk-forward years, CAGR 7.25% vs 12.55% (needs +0.55), worst fall -19.97% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Mat Hold pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_mat_hold"}
```

```proposal
id: A117
status: rejected 2026-11-05 - A117 vs a3: beat it in 4/13 walk-forward years, CAGR 8.19% vs 12.55% (needs +0.55), worst fall -12.38% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Stick Sandwich pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_stick_sandwich"}
```

```proposal
id: A118
status: rejected 2026-11-05 - A118 vs a3: beat it in 5/13 walk-forward years, CAGR 8.68% vs 12.55% (needs +0.55), worst fall -15.52% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Ladder Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_ladder_bottom"}
```

```proposal
id: A119
status: rejected 2026-11-05 - A119 vs a3: beat it in 4/13 walk-forward years, CAGR 6.18% vs 12.55% (needs +0.55), worst fall -10.33% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Unique Three River Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_unique_three_river"}
```

```proposal
id: A120
status: rejected 2026-11-05 - A120 vs a3: beat it in 5/13 walk-forward years, CAGR 6.8% vs 12.55% (needs +0.55), worst fall -2.11% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Abandoned Baby Bullish pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_abandoned_baby"}
```

```proposal
id: A121
status: rejected 2026-11-05 - A121 vs a3: beat it in 5/13 walk-forward years, CAGR 7.79% vs 12.55% (needs +0.55), worst fall -4.55% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Upside Gap Side-by-Side White Lines pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_gap_side_by_side_white_lines"}
```

```proposal
id: A122
status: rejected 2026-11-05 - A122 vs a3: beat it in 7/13 walk-forward years, CAGR 8.21% vs 12.55% (needs +0.55), worst fall -10.06% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Downside Gap Three Methods pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bearish_downside_gap_three_methods"}
```

```proposal
id: A123
status: rejected 2026-11-05 - A123 vs a3: beat it in 6/13 walk-forward years, CAGR 6.95% vs 12.55% (needs +0.56), worst fall -12.21% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Three Stars in the South pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bearish_three_star_south"}
```

```proposal
id: A124
status: rejected 2026-11-05 - A124 vs a3: beat it in 6/13 walk-forward years, CAGR 7.11% vs 12.55% (needs +0.56), worst fall -0.88% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Concealing Baby Swallow pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cdx_bullish_concealing_baby_swallow"}
```

```proposal
id: A125
status: rejected 2026-11-05 - A125 vs a3: beat it in 3/13 walk-forward years, CAGR 2.94% vs 12.55% (needs +0.56), worst fall -15.91% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Double Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_double_bottom"}
```

```proposal
id: A126
status: rejected 2026-11-05 - A126 vs a3: beat it in 3/13 walk-forward years, CAGR 5.83% vs 12.55% (needs +0.56), worst fall -13.15% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Triple Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_triple_bottom"}
```

```proposal
id: A127
status: rejected 2026-11-05 - A127 vs a3: beat it in 4/13 walk-forward years, CAGR 8.25% vs 12.55% (needs +0.56), worst fall -6.54% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Inverse Head and Shoulders pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_inverse_head_and_shoulders"}
```

```proposal
id: A128
status: rejected 2026-11-05 - A128 vs a3: beat it in 5/13 walk-forward years, CAGR 4.13% vs 12.55% (needs +0.56), worst fall -18.49% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Ascending Triangle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_ascending_triangle"}
```

```proposal
id: A129
status: rejected 2026-11-05 - A129 vs a3: beat it in 5/13 walk-forward years, CAGR 4.91% vs 12.55% (needs +0.56), worst fall -15.11% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Rectangle / Trading Range pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_rectangle_range"}
```

```proposal
id: A130
status: rejected 2026-11-05 - A130 vs a3: beat it in 7/13 walk-forward years, CAGR 7.16% vs 12.55% (needs +0.56), worst fall -16.32% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Falling Wedge pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_falling_wedge"}
```

```proposal
id: A131
status: rejected 2026-11-05 - A131 vs a3: beat it in 4/13 walk-forward years, CAGR 5.13% vs 12.55% (needs +0.56), worst fall -16.02% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Broadening Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_broadening_bottom"}
```

```proposal
id: A132
status: rejected 2026-11-05 - A132 vs a3: beat it in 5/13 walk-forward years, CAGR 8.51% vs 12.55% (needs +0.56), worst fall -20.29% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Measured Move Up / AB=CD Projection pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_measured_move_up"}
```

```proposal
id: A133
status: rejected 2026-11-05 - A133 vs a3: beat it in 3/13 walk-forward years, CAGR 6.06% vs 12.55% (needs +0.56), worst fall -4.72% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Bull Pennant pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_bull_pennant"}
```

```proposal
id: A134
status: rejected 2026-11-05 - A134 vs a3: beat it in 6/13 walk-forward years, CAGR 3.93% vs 12.55% (needs +0.56), worst fall -28.26% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Breakout and Retest pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_breakout_retest"}
```

```proposal
id: A135
status: rejected 2026-11-05 - A135 vs a3: beat it in 5/13 walk-forward years, CAGR 5.41% vs 12.55% (needs +0.56), worst fall -18.15% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the False Breakout / Failed Auction pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_false_breakout"}
```

```proposal
id: A136
status: rejected 2026-11-05 - A136 vs a3: beat it in 5/13 walk-forward years, CAGR 8.64% vs 12.55% (needs +0.56), worst fall -18.42% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Outside Bar / Engulfing Range Bar pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_outside_bar"}
```

```proposal
id: A137
status: rejected 2026-11-05 - A137 vs a3: beat it in 3/13 walk-forward years, CAGR 6.55% vs 12.55% (needs +0.56), worst fall -15.82% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Pin Bar / Rejection Bar pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_pin_bar_rejection"}
```

```proposal
id: A138
status: rejected 2026-11-05 - A138 vs a3: beat it in 5/13 walk-forward years, CAGR 5.68% vs 12.55% (needs +0.56), worst fall -17.35% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Breakaway Gap pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gap_breakaway"}
```

```proposal
id: A139
status: rejected 2026-11-05 - A139 vs a3: beat it in 5/13 walk-forward years, CAGR 9.99% vs 12.55% (needs +0.56), worst fall -9.7% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Runaway / Measuring Gap pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gap_runaway"}
```

```proposal
id: A140
status: rejected 2026-11-05 - A140 vs a3: beat it in 4/13 walk-forward years, CAGR 8.85% vs 12.55% (needs +0.56), worst fall -12.83% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Wyckoff Spring pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_wyckoff_spring"}
```

```proposal
id: A141
status: rejected 2026-11-05 - A141 vs a3: beat it in 7/13 walk-forward years, CAGR 7.37% vs 12.55% (needs +0.56), worst fall -7.83% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Island Reversal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_island_reversal"}
```

```proposal
id: A142
status: rejected 2026-11-05 - A142 vs a3: beat it in 5/13 walk-forward years, CAGR 7.47% vs 12.55% (needs +0.56), worst fall -13.04% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Inside Bar Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_inside_bar_breakout"}
```

```proposal
id: A143
status: rejected 2026-11-05 - A143 vs a3: beat it in 7/13 walk-forward years, CAGR 8.12% vs 12.55% (needs +0.56), worst fall -12.51% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the NR4 Inside Day pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_nr4_inside_day"}
```

```proposal
id: A144
status: rejected 2026-11-05 - A144 vs a3: beat it in 6/13 walk-forward years, CAGR 8.32% vs 12.55% (needs +0.56), worst fall -11.9% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the NR7 Inside Day pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_nr7_inside_day"}
```

```proposal
id: A145
status: rejected 2026-11-05 - A145 vs a3: beat it in 3/13 walk-forward years, CAGR 7.3% vs 12.55% (needs +0.56), worst fall -16.46% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Darvas Box pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_darvas_box"}
```

```proposal
id: A146
status: rejected 2026-11-05 - A146 vs a3: beat it in 5/13 walk-forward years, CAGR 8.28% vs 12.55% (needs +0.56), worst fall -19.87% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Flat Base pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_flat_base"}
```

```proposal
id: A147
status: rejected 2026-11-05 - A147 vs a3: beat it in 6/13 walk-forward years, CAGR 7.26% vs 12.55% (needs +0.56), worst fall -14.5% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Volatility Contraction Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_vcp_volatility_contraction"}
```

```proposal
id: A148
status: rejected 2026-11-05 - A148 vs a3: beat it in 3/13 walk-forward years, CAGR 5.3% vs 12.55% (needs +0.56), worst fall -17.71% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Key Reversal Up pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_key_reversal_up"}
```

```proposal
id: A149
status: rejected 2026-11-05 - A149 vs a3: beat it in 6/13 walk-forward years, CAGR 4.37% vs 12.55% (needs +0.56), worst fall -14.16% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Turtle Soup False Break pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_turtle_soup"}
```

```proposal
id: A150
status: rejected 2026-11-05 - A150 vs a3: beat it in 6/13 walk-forward years, CAGR 9.25% vs 12.55% (needs +0.57), worst fall -9.6% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Three Bar Play pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_three_bar_play"}
```

```proposal
id: A151
status: rejected 2026-11-05 - A151 vs a3: beat it in 6/13 walk-forward years, CAGR 7.34% vs 12.55% (needs +0.57), worst fall -11.09% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Gap and Go pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gap_and_go"}
```

```proposal
id: A152
status: rejected 2026-11-05 - A152 vs a3: beat it in 3/13 walk-forward years, CAGR 5.5% vs 12.55% (needs +0.57), worst fall -16.27% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Gap Fill Reversion pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gap_fill_reversion"}
```

```proposal
id: A153
status: rejected 2026-11-05 - A153 vs a3: beat it in 5/13 walk-forward years, CAGR 8.45% vs 12.55% (needs +0.57), worst fall -11.07% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the First Pullback After Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_first_pullback_after_breakout"}
```

```proposal
id: A154
status: rejected 2026-11-05 - A154 vs a3: beat it in 6/13 walk-forward years, CAGR 7.76% vs 12.55% (needs +0.57), worst fall -22.66% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Symmetrical Triangle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_symmetrical_triangle"}
```

```proposal
id: A155
status: rejected 2026-11-05 - A155 vs a3: beat it in 5/13 walk-forward years, CAGR 6.87% vs 12.55% (needs +0.57), worst fall -13.34% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Ascending Channel pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_ascending_channel"}
```

```proposal
id: A156
status: rejected 2026-11-05 - A156 vs a3: beat it in 5/13 walk-forward years, CAGR 8.71% vs 12.55% (needs +0.57), worst fall -23.3% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Cup Without Handle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_cup_without_handle"}
```

```proposal
id: A157
status: rejected 2026-11-05 - A157 vs a3: beat it in 2/13 walk-forward years, CAGR 2.06% vs 12.55% (needs +0.57), worst fall -16.46% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the V Reversal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_v_reversal"}
```

```proposal
id: A158
status: rejected 2026-11-05 - A158 vs a3: beat it in 5/13 walk-forward years, CAGR 4.32% vs 12.55% (needs +0.57), worst fall -10.72% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Selling Climax pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_selling_climax"}
```

```proposal
id: A159
status: rejected 2026-11-05 - A159 vs a3: beat it in 7/13 walk-forward years, CAGR 9.01% vs 12.55% (needs +0.57), worst fall -13.84% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Liquidity Sweep Reversal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_liquidity_sweep_reversal"}
```

```proposal
id: A160
status: rejected 2026-11-05 - A160 vs a3: beat it in 4/13 walk-forward years, CAGR 8.71% vs 12.55% (needs +0.57), worst fall -16.15% vs -10.71%, gate FAIL
written: 2026-11-04
reason: (idea factory) For a3: the Compression Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_compression_breakout"}
```

```proposal
id: A161
status: rejected 2026-11-06 - A161 vs a3: beat it in 6/13 walk-forward years, CAGR 8.3% vs 12.55% (needs +0.57), worst fall -20.89% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Heikin Ashi Trend Run pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_heikin_ashi_trend_run"}
```

```proposal
id: A162
status: rejected 2026-11-06 - A162 vs a3: beat it in 5/13 walk-forward years, CAGR 8.16% vs 12.55% (needs +0.57), worst fall -14.48% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Stair-Step Trend pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_stair_step_trend"}
```

```proposal
id: A163
status: rejected 2026-11-06 - A163 vs a3: beat it in 7/13 walk-forward years, CAGR 7.7% vs 12.55% (needs +0.57), worst fall -19.75% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Wyckoff Spring Test pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_wyckoff_spring_test"}
```

```proposal
id: A164
status: rejected 2026-11-06 - A164 vs a3: beat it in 3/13 walk-forward years, CAGR 4.88% vs 12.55% (needs +0.57), worst fall -16.19% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Trendline Break and Retest pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_trendline_break_retest"}
```

```proposal
id: A165
status: rejected 2026-11-06 - A165 vs a3: beat it in 6/13 walk-forward years, CAGR 8.32% vs 12.55% (needs +0.57), worst fall -18.3% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Break of Structure (BOS) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_break_of_structure_bullish"}
```

```proposal
id: A166
status: rejected 2026-11-06 - A166 vs a3: beat it in 5/13 walk-forward years, CAGR 7.37% vs 12.55% (needs +0.57), worst fall -10.64% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Change of Character (CHoCH) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_change_of_character_bullish"}
```

```proposal
id: A167
status: rejected 2026-11-06 - A167 vs a3: beat it in 4/13 walk-forward years, CAGR 6.33% vs 12.55% (needs +0.57), worst fall -15.83% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Market Structure Shift (MSS) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_market_structure_shift_bullish"}
```

```proposal
id: A168
status: rejected 2026-11-06 - A168 vs a3: beat it in 7/13 walk-forward years, CAGR 10.47% vs 12.55% (needs +0.57), worst fall -13.55% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Higher Low (HL) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_higher_low"}
```

```proposal
id: A169
status: rejected 2026-11-06 - A169 vs a3: beat it in 6/13 walk-forward years, CAGR 12.66% vs 12.55% (needs +0.57), worst fall -11.7% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Sell-Side Liquidity Sweep pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_sell_side_liquidity_sweep"}
```

```proposal
id: A170
status: rejected 2026-11-06 - A170 vs a3: beat it in 3/13 walk-forward years, CAGR 4.26% vs 12.55% (needs +0.57), worst fall -18.37% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Equal Lows Liquidity Pool pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_equal_lows_liquidity_pool"}
```

```proposal
id: A171
status: rejected 2026-11-06 - A171 vs a3: beat it in 5/13 walk-forward years, CAGR 8.65% vs 12.55% (needs +0.57), worst fall -19.09% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Fair Value Gap (FVG) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_fair_value_gap_bullish"}
```

```proposal
id: A172
status: rejected 2026-11-06 - A172 vs a3: beat it in 5/13 walk-forward years, CAGR 6.23% vs 12.55% (needs +0.57), worst fall -16.61% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Inverse FVG (IFVG) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_inverse_fair_value_gap_bullish"}
```

```proposal
id: A173
status: rejected 2026-11-06 - A173 vs a3: beat it in 4/13 walk-forward years, CAGR 6.76% vs 12.55% (needs +0.57), worst fall -17.51% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Displacement pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_displacement_bullish"}
```

```proposal
id: A174
status: rejected 2026-11-06 - A174 vs a3: beat it in 4/13 walk-forward years, CAGR 4.57% vs 12.55% (needs +0.57), worst fall -19.04% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Order Block (heuristic) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_order_block_bullish"}
```

```proposal
id: A175
status: rejected 2026-11-06 - A175 vs a3: beat it in 3/13 walk-forward years, CAGR 9.86% vs 12.55% (needs +0.57), worst fall -14.06% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Acceptance Above Range pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_range_acceptance_above"}
```

```proposal
id: A176
status: rejected 2026-11-06 - A176 vs a3: beat it in 6/13 walk-forward years, CAGR 9.01% vs 12.55% (needs +0.57), worst fall -14.8% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Rejection Below Range pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_range_rejection_below"}
```

```proposal
id: A177
status: rejected 2026-11-06 - A177 vs a3: beat it in 6/13 walk-forward years, CAGR 8.32% vs 12.55% (needs +0.57), worst fall -10.04% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Discount Zone pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_discount_zone"}
```

```proposal
id: A178
status: rejected 2026-11-06 - A178 vs a3: beat it in 7/13 walk-forward years, CAGR 8.85% vs 12.55% (needs +0.57), worst fall -16.68% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Prior Week Low Sweep pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_prior_week_low_sweep"}
```

```proposal
id: A179
status: rejected 2026-11-06 - A179 vs a3: beat it in 4/13 walk-forward years, CAGR 6.72% vs 12.55% (needs +0.57), worst fall -17.92% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Weekly Open Reclaim pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_weekly_open_reclaim"}
```

```proposal
id: A180
status: rejected 2026-11-06 - A180 vs a3: beat it in 7/13 walk-forward years, CAGR 6.85% vs 12.55% (needs +0.57), worst fall -17.87% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Monthly Open Reclaim pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_monthly_open_reclaim"}
```

```proposal
id: A181
status: rejected 2026-11-06 - A181 vs a3: beat it in 4/13 walk-forward years, CAGR 9.14% vs 12.55% (needs +0.57), worst fall -16.93% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Prior Day Low Sweep pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_prior_day_low_sweep"}
```

```proposal
id: A182
status: rejected 2026-11-06 - A182 vs a3: beat it in 1/13 walk-forward years, CAGR 6.78% vs 12.55% (needs +0.57), worst fall -17.01% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Volatility Squeeze Release pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_squeeze_release"}
```

```proposal
id: A183
status: rejected 2026-11-06 - A183 vs a3: beat it in 5/13 walk-forward years, CAGR 8.11% vs 12.55% (needs +0.58), worst fall -16.9% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Parabolic SAR State Flip pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_parabolic_sar_flip"}
```

```proposal
id: A184
status: rejected 2026-11-06 - A184 vs a3: beat it in 5/13 walk-forward years, CAGR 7.06% vs 12.55% (needs +0.58), worst fall -17.98% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the ATR Trailing Stop Flip pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_atr_trailing_stop_flip"}
```

```proposal
id: A185
status: rejected 2026-11-06 - A185 vs a3: beat it in 8/13 walk-forward years, CAGR 9.42% vs 12.55% (needs +0.58), worst fall -24.56% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Up Trend Day pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_trend_day_up"}
```

```proposal
id: A186
status: rejected 2026-11-06 - A186 vs a3: beat it in 4/13 walk-forward years, CAGR 7.17% vs 12.55% (needs +0.58), worst fall -4.81% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Gartley (XABCD) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_harmonic_gartley"}
```

```proposal
id: A187
status: rejected 2026-11-06 - A187 vs a3: beat it in 5/13 walk-forward years, CAGR 6.26% vs 12.55% (needs +0.58), worst fall -2.44% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bat (XABCD) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_harmonic_bat"}
```

```proposal
id: A188
status: rejected 2026-11-06 - A188 vs a3: beat it in 6/13 walk-forward years, CAGR 6.79% vs 12.55% (needs +0.58), worst fall -1.03% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Alternate Bat Bullish pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_alternate_bat_bullish"}
```

```proposal
id: A189
status: rejected 2026-11-06 - A189 vs a3: beat it in 6/13 walk-forward years, CAGR 7.03% vs 12.55% (needs +0.58), worst fall -3.29% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Butterfly (XABCD) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_harmonic_butterfly"}
```

```proposal
id: A190
status: rejected 2026-11-06 - A190 vs a3: beat it in 7/13 walk-forward years, CAGR 7.25% vs 12.55% (needs +0.58), worst fall -0.54% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Crab (XABCD) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_harmonic_crab"}
```

```proposal
id: A191
status: rejected 2026-11-06 - A191 vs a3: beat it in 7/13 walk-forward years, CAGR 7.8% vs 12.55% (needs +0.58), worst fall -2.79% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Deep Crab (XABCD) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_harmonic_deep_crab"}
```

```proposal
id: A192
status: rejected 2026-11-06 - A192 vs a3: beat it in 5/13 walk-forward years, CAGR 7.47% vs 12.55% (needs +0.58), worst fall -2.27% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Cypher (XABCD) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_harmonic_cypher"}
```

```proposal
id: A193
status: rejected 2026-11-06 - A193 vs a3: beat it in 4/13 walk-forward years, CAGR 6.39% vs 12.55% (needs +0.58), worst fall -11.22% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Shark (0XABC) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_harmonic_shark"}
```

```proposal
id: A194
status: rejected 2026-11-06 - A194 vs a3: beat it in 8/13 walk-forward years, CAGR 8.96% vs 12.55% (needs +0.58), worst fall -5.03% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the 5-0 Bullish pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_5_0_bullish"}
```

```proposal
id: A195
status: rejected 2026-11-06 - A195 vs a3: beat it in 3/13 walk-forward years, CAGR 4.78% vs 12.55% (needs +0.58), worst fall -10.37% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the AB=CD Harmonic Pattern pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_harmonic_ab_cd"}
```

```proposal
id: A196
status: rejected 2026-11-06 - A196 vs a3: beat it in 4/13 walk-forward years, CAGR 4.93% vs 12.55% (needs +0.58), worst fall -11.68% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Three Drives Pattern Bullish pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_three_drives_bullish"}
```

```proposal
id: A197
status: rejected 2026-11-06 - A197 vs a3: beat it in 6/13 walk-forward years, CAGR 8.63% vs 12.55% (needs +0.58), worst fall -13.31% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Elliott Impulse Wave (1–5) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_elliott_impulse"}
```

```proposal
id: A198
status: rejected 2026-11-06 - A198 vs a3: beat it in 4/13 walk-forward years, CAGR 6.68% vs 12.55% (needs +0.58), worst fall -12.72% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Elliott ABC Correction pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_elliott_abc_correction"}
```

```proposal
id: A199
status: rejected 2026-11-06 - A199 vs a3: beat it in 3/13 walk-forward years, CAGR 5.86% vs 12.55% (needs +0.58), worst fall -7.5% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Elliott Zigzag Correction pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_elliott_zigzag"}
```

```proposal
id: A200
status: rejected 2026-11-06 - A200 vs a3: beat it in 6/13 walk-forward years, CAGR 8.74% vs 12.55% (needs +0.58), worst fall -11.24% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Elliott Flat Correction pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_elliott_flat_correction"}
```

```proposal
id: A201
status: rejected 2026-11-06 - A201 vs a3: beat it in 4/13 walk-forward years, CAGR 4.88% vs 12.55% (needs +0.58), worst fall -9.49% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Elliott Triangle pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_elliott_triangle"}
```

```proposal
id: A202
status: rejected 2026-11-06 - A202 vs a3: beat it in 3/13 walk-forward years, CAGR 4.66% vs 12.55% (needs +0.58), worst fall -10.77% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Elliott Diagonal pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_elliott_diagonal"}
```

```proposal
id: A203
status: rejected 2026-11-06 - A203 vs a3: beat it in 5/13 walk-forward years, CAGR 5.32% vs 12.55% (needs +0.58), worst fall -7.8% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Diamond Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_diamond_bottom"}
```

```proposal
id: A204
status: rejected 2026-11-06 - A204 vs a3: beat it in 7/13 walk-forward years, CAGR 7.8% vs 12.55% (needs +0.58), worst fall -1.52% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Megaphone Formation pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_megaphone_formation"}
```

```proposal
id: A205
status: rejected 2026-11-06 - A205 vs a3: beat it in 5/13 walk-forward years, CAGR 7.03% vs 12.55% (needs +0.58), worst fall -13.16% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Andrews Pitchfork pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_andrews_pitchfork"}
```

```proposal
id: A206
status: rejected 2026-11-06 - A206 vs a3: beat it in 5/13 walk-forward years, CAGR 8.18% vs 12.55% (needs +0.58), worst fall -15.53% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Schiff Pitchfork pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_schiff_pitchfork"}
```

```proposal
id: A207
status: rejected 2026-11-06 - A207 vs a3: beat it in 6/13 walk-forward years, CAGR 8.5% vs 12.55% (needs +0.58), worst fall -11.95% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Modified Schiff Pitchfork pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_modified_schiff_pitchfork"}
```

```proposal
id: A208
status: rejected 2026-11-06 - A208 vs a3: beat it in 5/13 walk-forward years, CAGR 6.63% vs 12.55% (needs +0.58), worst fall -10.48% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Fibonacci Cluster pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_fibonacci_cluster"}
```

```proposal
id: A209
status: rejected 2026-11-06 - A209 vs a3: beat it in 6/13 walk-forward years, CAGR 8.28% vs 12.55% (needs +0.58), worst fall -14.62% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Fibonacci Time Zone pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_fibonacci_time_zone"}
```

```proposal
id: A210
status: rejected 2026-11-06 - A210 vs a3: beat it in 3/13 walk-forward years, CAGR 3.42% vs 12.55% (needs +0.58), worst fall -14.91% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Wyckoff Accumulation Schematic pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_wyckoff_accumulation"}
```

```proposal
id: A211
status: rejected 2026-11-06 - A211 vs a3: beat it in 2/13 walk-forward years, CAGR 2.75% vs 12.55% (needs +0.58), worst fall -26.94% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Wyckoff Creek Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_creek_breakout"}
```

```proposal
id: A212
status: rejected 2026-11-06 - A212 vs a3: beat it in 3/13 walk-forward years, CAGR 1.74% vs 12.55% (needs +0.58), worst fall -19.77% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Wyckoff Sign of Strength pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_wyckoff_sign_of_strength"}
```

```proposal
id: A213
status: rejected 2026-11-06 - A213 vs a3: beat it in 8/13 walk-forward years, CAGR 5.72% vs 12.55% (needs +0.58), worst fall -13.7% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Wyckoff Last Point of Support pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_wyckoff_last_point_of_support"}
```

```proposal
id: A214
status: rejected 2026-11-06 - A214 vs a3: beat it in 6/13 walk-forward years, CAGR 4.35% vs 12.55% (needs +0.58), worst fall -17.95% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Wyckoff Backup to Edge of Creek pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_wyckoff_backup_to_edge"}
```

```proposal
id: A215
status: rejected 2026-11-06 - A215 vs a3: beat it in 3/13 walk-forward years, CAGR 4.6% vs 12.55% (needs +0.58), worst fall -14.0% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Wyckoff Secondary Test pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_secondary_test_wyckoff"}
```

```proposal
id: A216
status: rejected 2026-11-06 - A216 vs a3: beat it in 6/13 walk-forward years, CAGR 6.34% vs 12.55% (needs +0.58), worst fall -13.95% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Pipe Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_pipe_bottom"}
```

```proposal
id: A217
status: rejected 2026-11-06 - A217 vs a3: beat it in 4/13 walk-forward years, CAGR 5.39% vs 12.55% (needs +0.58), worst fall -6.58% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Horn Bottom pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_horn_bottom"}
```

```proposal
id: A218
status: rejected 2026-11-06 - A218 vs a3: beat it in 2/13 walk-forward years, CAGR 7.13% vs 12.55% (needs +0.58), worst fall -18.41% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Point and Figure Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_point_figure_breakout"}
```

```proposal
id: A219
status: rejected 2026-11-06 - A219 vs a3: beat it in 2/13 walk-forward years, CAGR 4.99% vs 12.55% (needs +0.58), worst fall -17.61% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Renko Breakout pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_renko_breakout"}
```

```proposal
id: A220
status: rejected 2026-11-06 - A220 vs a3: beat it in 7/13 walk-forward years, CAGR 6.69% vs 12.55% (needs +0.58), worst fall -8.24% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Exhaustion Gap pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_exhaustion_gap"}
```

```proposal
id: A221
status: rejected 2026-11-06 - A221 vs a3: beat it in 6/13 walk-forward years, CAGR 6.9% vs 12.55% (needs +0.58), worst fall -4.22% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Trend Exhaustion Climax pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_trend_exhaustion_climax"}
```

```proposal
id: A222
status: rejected 2026-11-06 - A222 vs a3: beat it in 4/13 walk-forward years, CAGR 5.16% vs 12.55% (needs +0.58), worst fall -17.78% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Gann Square of Nine Level Confluence pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_gann_square_of_nine_level"}
```

```proposal
id: A223
status: rejected 2026-11-06 - A223 vs a3: beat it in 6/13 walk-forward years, CAGR 7.53% vs 12.55% (needs +0.59), worst fall -1.54% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the IPO Base pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "cp_ipo_base"}
```

```proposal
id: A224
status: rejected 2026-11-06 - A224 vs a3: beat it in 4/13 walk-forward years, CAGR 5.5% vs 12.55% (needs +0.59), worst fall -12.77% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Breaker Block pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_breaker_block_bullish"}
```

```proposal
id: A225
status: rejected 2026-11-06 - A225 vs a3: beat it in 3/13 walk-forward years, CAGR 6.67% vs 12.55% (needs +0.59), worst fall -18.61% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Breaker Retest pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_breaker_retest"}
```

```proposal
id: A226
status: rejected 2026-11-06 - A226 vs a3: beat it in 7/13 walk-forward years, CAGR 9.01% vs 12.55% (needs +0.59), worst fall -15.54% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Mitigation Block pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_mitigation_block_bullish"}
```

```proposal
id: A227
status: rejected 2026-11-06 - A227 vs a3: beat it in 3/13 walk-forward years, CAGR 8.12% vs 12.55% (needs +0.59), worst fall -15.51% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Rejection Block pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_rejection_block_bullish"}
```

```proposal
id: A228
status: rejected 2026-11-06 - A228 vs a3: beat it in 4/13 walk-forward years, CAGR 5.09% vs 12.55% (needs +0.59), worst fall -24.91% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Consequent Encroachment (CE) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_consequent_encroachment"}
```

```proposal
id: A229
status: rejected 2026-11-06 - A229 vs a3: beat it in 3/13 walk-forward years, CAGR 7.34% vs 12.55% (needs +0.59), worst fall -10.89% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Equal Highs Liquidity Pool pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_equal_highs_liquidity_pool"}
```

```proposal
id: A230
status: rejected 2026-11-06 - A230 vs a3: beat it in 6/13 walk-forward years, CAGR 7.47% vs 12.55% (needs +0.59), worst fall -14.43% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Equilibrium (50%) pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_equilibrium_level"}
```

```proposal
id: A231
status: rejected 2026-11-06 - A231 vs a3: beat it in 4/13 walk-forward years, CAGR 5.89% vs 12.55% (needs +0.59), worst fall -10.44% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the External Liquidity Sweep pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_external_liquidity_sweep"}
```

```proposal
id: A232
status: rejected 2026-11-06 - A232 vs a3: beat it in 5/13 walk-forward years, CAGR 13.25% vs 12.55% (needs +0.59), worst fall -11.48% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Internal Liquidity Sweep pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_internal_liquidity_sweep"}
```

```proposal
id: A233
status: rejected 2026-11-06 - A233 vs a3: beat it in 4/13 walk-forward years, CAGR 5.7% vs 12.55% (needs +0.59), worst fall -20.21% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Internal Structure Break pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_internal_structure_break"}
```

```proposal
id: A234
status: rejected 2026-11-06 - A234 vs a3: beat it in 5/13 walk-forward years, CAGR 9.15% vs 12.55% (needs +0.59), worst fall -16.58% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the External Structure Break pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_external_structure_break"}
```

```proposal
id: A235
status: rejected 2026-11-06 - A235 vs a3: beat it in 8/13 walk-forward years, CAGR 8.47% vs 12.55% (needs +0.59), worst fall -8.67% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Liquidity Void pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_liquidity_void"}
```

```proposal
id: A236
status: rejected 2026-11-06 - A236 vs a3: beat it in 7/13 walk-forward years, CAGR 10.16% vs 12.55% (needs +0.59), worst fall -13.36% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Multi-Timeframe Alignment pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_multi_timeframe_alignment"}
```

```proposal
id: A237
status: rejected 2026-11-06 - A237 vs a3: beat it in 6/13 walk-forward years, CAGR 9.07% vs 12.55% (needs +0.59), worst fall -13.06% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Optimal Trade Entry (OTE) Zone pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_optimal_trade_entry_zone"}
```

```proposal
id: A238
status: rejected 2026-11-06 - A238 vs a3: beat it in 5/13 walk-forward years, CAGR 6.94% vs 12.55% (needs +0.59), worst fall -16.55% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Anchored VWAP Reclaim pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_anchored_vwap_reclaim"}
```

```proposal
id: A239
status: rejected 2026-11-06 - A239 vs a3: beat it in 9/13 walk-forward years, CAGR 7.07% vs 12.55% (needs +0.59), worst fall -20.82% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: the Bullish Volume Imbalance pattern from the owner's pattern library may time entries better than the current rule.
overrides: {"family": "ms_volume_imbalance_bullish"}
```

```proposal
id: A240
status: rejected 2026-11-06 - A240 vs a3: beat it in 6/13 walk-forward years, CAGR 8.42% vs 12.55% (needs +0.59), worst fall -13.57% vs -10.71%, gate FAIL
written: 2026-11-05
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise.
overrides: {"stop_atr_mult": 2.5}
```

```proposal
id: A241
status: rejected 2026-11-09 - A241 vs a3: beat it in 6/13 walk-forward years, CAGR 8.95% vs 12.55% (needs +0.59), worst fall -12.26% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility.
overrides: {"stop_atr_mult": 3.5}
```

```proposal
id: A242
status: rejected 2026-11-09 - A242 vs a3: beat it in 4/13 walk-forward years, CAGR 4.94% vs 12.55% (needs +0.59), worst fall -18.27% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly.
overrides: {"max_hold_days": 15}
```

```proposal
id: A243
status: rejected 2026-11-09 - A243 vs a3: beat it in 5/13 walk-forward years, CAGR 7.64% vs 12.55% (needs +0.59), worst fall -14.19% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets.
overrides: {"max_hold_days": 35}
```

```proposal
id: A244
status: rejected 2026-11-09 - A244 vs a3: beat it in 5/13 walk-forward years, CAGR 11.78% vs 12.55% (needs +0.59), worst fall -11.78% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a nearer first target banks partial profit more often.
overrides: {"target1_r": 1.5}
```

```proposal
id: A245
status: rejected 2026-11-09 - A245 vs a3: beat it in 2/13 walk-forward years, CAGR 8.91% vs 12.55% (needs +0.59), worst fall -19.06% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit.
overrides: {"target2_r": 3.0}
```

```proposal
id: A246
status: rejected 2026-11-09 - A246 vs a3: beat it in 6/13 walk-forward years, CAGR 6.48% vs 12.55% (needs +0.59), worst fall -13.32% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them.
overrides: {"exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A247
status: rejected 2026-11-09 - A247 vs a3: beat it in 4/13 walk-forward years, CAGR 10.02% vs 12.55% (needs +0.59), worst fall -11.37% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders.
overrides: {"min_rs_filter": 50}
```

```proposal
id: A248
status: rejected 2026-11-09 - A248 vs a3: beat it in 7/13 walk-forward years, CAGR 8.0% vs 12.55% (needs +0.59), worst fall -13.47% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners.
overrides: {"min_mom12_rank": 0.5}
```

```proposal
id: A249
status: rejected 2026-11-09 - A249 vs a3: beat it in 6/13 walk-forward years, CAGR 11.71% vs 12.55% (needs +0.59), worst fall -11.38% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops.
overrides: {"max_atr_pct": 5.0}
```

```proposal
id: A250
status: rejected 2026-11-09 - A250 vs a3: beat it in 5/13 walk-forward years, CAGR 9.41% vs 12.55% (needs +0.59), worst fall -15.29% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves.
overrides: {"min_volume_mult": 1.0}
```

```proposal
id: A251
status: rejected 2026-11-09 - A251 vs a3: beat it in 5/13 walk-forward years, CAGR 8.83% vs 12.55% (needs +0.59), worst fall -6.39% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses.
overrides: {"use_regime_filter": true}
```

```proposal
id: A252
status: rejected 2026-11-09 - A252 vs a3: beat it in 7/13 walk-forward years, CAGR 10.39% vs 12.55% (needs +0.59), worst fall -10.52% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals.
overrides: {"max_open_positions": 3}
```

```proposal
id: A253
status: rejected 2026-11-09 - A253 vs a3: beat it in 6/13 walk-forward years, CAGR 13.27% vs 12.55% (needs +0.59), worst fall -14.52% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: one more position spreads risk across more independent trades.
overrides: {"max_open_positions": 5}
```

```proposal
id: A254
status: rejected 2026-11-09 - A254 vs a3: beat it in 3/13 walk-forward years, CAGR 11.36% vs 12.55% (needs +0.59), worst fall -12.69% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns.
overrides: {"max_per_industry": 2}
```

```proposal
id: A255
status: rejected 2026-11-09 - A255 vs a3: beat it in 6/13 walk-forward years, CAGR 12.31% vs 12.55% (needs +0.59), worst fall -13.61% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens.
overrides: {"skip_if_us_drop_pct": 2.0}
```

```proposal
id: A256
status: rejected 2026-11-09 - A256 vs a3: beat it in 6/13 walk-forward years, CAGR 6.92% vs 12.55% (needs +0.59), worst fall -0.24% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets.
overrides: {"min_fii_long_pct": 25}
```

```proposal
id: A257
status: rejected 2026-11-09 - A257 vs a3: beat it in 4/13 walk-forward years, CAGR 6.97% vs 12.55% (needs +0.59), worst fall -15.43% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "stop_atr_mult": 2.5}
```

```proposal
id: A258
status: rejected 2026-11-09 - A258 vs a3: beat it in 3/13 walk-forward years, CAGR 7.87% vs 12.55% (needs +0.59), worst fall -12.82% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "stop_atr_mult": 3.5}
```

```proposal
id: A259
status: rejected 2026-11-09 - A259 vs a3: beat it in 4/13 walk-forward years, CAGR 4.68% vs 12.55% (needs +0.59), worst fall -20.41% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "max_hold_days": 15}
```

```proposal
id: A260
status: rejected 2026-11-09 - A260 vs a3: beat it in 4/13 walk-forward years, CAGR 7.97% vs 12.55% (needs +0.59), worst fall -14.81% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "max_hold_days": 35}
```

```proposal
id: A261
status: rejected 2026-11-09 - A261 vs a3: beat it in 3/13 walk-forward years, CAGR 6.13% vs 12.55% (needs +0.59), worst fall -15.36% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "target1_r": 1.5}
```

```proposal
id: A262
status: rejected 2026-11-09 - A262 vs a3: beat it in 5/13 walk-forward years, CAGR 8.94% vs 12.55% (needs +0.59), worst fall -12.31% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "target2_r": 3.0}
```

```proposal
id: A263
status: rejected 2026-11-09 - A263 vs a3: beat it in 4/13 walk-forward years, CAGR 6.21% vs 12.55% (needs +0.59), worst fall -14.25% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A264
status: rejected 2026-11-09 - A264 vs a3: beat it in 4/13 walk-forward years, CAGR 8.71% vs 12.55% (needs +0.59), worst fall -12.51% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "min_rs_filter": 50}
```

```proposal
id: A265
status: rejected 2026-11-09 - A265 vs a3: beat it in 2/13 walk-forward years, CAGR 7.41% vs 12.55% (needs +0.59), worst fall -18.37% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "min_mom12_rank": 0.5}
```

```proposal
id: A266
status: rejected 2026-11-09 - A266 vs a3: beat it in 3/13 walk-forward years, CAGR 6.7% vs 12.55% (needs +0.59), worst fall -12.15% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "max_atr_pct": 5.0}
```

```proposal
id: A267
status: rejected 2026-11-09 - A267 vs a3: beat it in 5/13 walk-forward years, CAGR 9.24% vs 12.55% (needs +0.59), worst fall -12.44% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "min_volume_mult": 1.0}
```

```proposal
id: A268
status: rejected 2026-11-09 - A268 vs a3: beat it in 6/13 walk-forward years, CAGR 6.13% vs 12.55% (needs +0.59), worst fall -18.11% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "use_regime_filter": true}
```

```proposal
id: A269
status: rejected 2026-11-09 - A269 vs a3: beat it in 4/13 walk-forward years, CAGR 5.25% vs 12.55% (needs +0.59), worst fall -12.13% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "max_open_positions": 3}
```

```proposal
id: A270
status: rejected 2026-11-09 - A270 vs a3: beat it in 3/13 walk-forward years, CAGR 4.59% vs 12.55% (needs +0.59), worst fall -20.69% vs -10.71%, gate FAIL
written: 2026-11-06
reason: (idea factory) For a3: one more position spreads risk across more independent trades - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "max_open_positions": 5}
```

```proposal
id: A271
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "max_per_industry": 2}
```

```proposal
id: A272
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "skip_if_us_drop_pct": 2.0}
```

```proposal
id: A273
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets - applied to the macd_cross entry rule.
overrides: {"family": "macd_cross", "min_fii_long_pct": 25}
```

```proposal
id: A274
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "stop_atr_mult": 2.5}
```

```proposal
id: A275
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "stop_atr_mult": 3.5}
```

```proposal
id: A276
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "max_hold_days": 15}
```

```proposal
id: A277
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "max_hold_days": 35}
```

```proposal
id: A278
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "target1_r": 1.5}
```

```proposal
id: A279
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "target2_r": 3.0}
```

```proposal
id: A280
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A281
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "min_rs_filter": 50}
```

```proposal
id: A282
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "min_mom12_rank": 0.5}
```

```proposal
id: A283
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "max_atr_pct": 5.0}
```

```proposal
id: A284
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "min_volume_mult": 1.0}
```

```proposal
id: A285
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "use_regime_filter": true}
```

```proposal
id: A286
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "max_open_positions": 3}
```

```proposal
id: A287
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: one more position spreads risk across more independent trades - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "max_open_positions": 5}
```

```proposal
id: A288
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "max_per_industry": 2}
```

```proposal
id: A289
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "skip_if_us_drop_pct": 2.0}
```

```proposal
id: A290
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets - applied to the rsi50_cross entry rule.
overrides: {"family": "rsi50_cross", "min_fii_long_pct": 25}
```

```proposal
id: A291
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "stop_atr_mult": 3.5}
```

```proposal
id: A292
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "max_hold_days": 15}
```

```proposal
id: A293
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "max_hold_days": 35}
```

```proposal
id: A294
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "target1_r": 1.5}
```

```proposal
id: A295
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "target2_r": 3.0}
```

```proposal
id: A296
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A297
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "min_rs_filter": 50}
```

```proposal
id: A298
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "min_mom12_rank": 0.5}
```

```proposal
id: A299
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "max_atr_pct": 5.0}
```

```proposal
id: A300
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "min_volume_mult": 1.0}
```

```proposal
id: A301
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "use_regime_filter": true}
```

```proposal
id: A302
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "max_open_positions": 3}
```

```proposal
id: A303
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: one more position spreads risk across more independent trades - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "max_open_positions": 5}
```

```proposal
id: A304
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "max_per_industry": 2}
```

```proposal
id: A305
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "skip_if_us_drop_pct": 2.0}
```

```proposal
id: A306
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets - applied to the stoch_cross entry rule.
overrides: {"family": "stoch_cross", "min_fii_long_pct": 25}
```

```proposal
id: A307
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "stop_atr_mult": 2.5}
```

```proposal
id: A308
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "stop_atr_mult": 3.5}
```

```proposal
id: A309
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "max_hold_days": 15}
```

```proposal
id: A310
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "max_hold_days": 35}
```

```proposal
id: A311
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "target1_r": 1.5}
```

```proposal
id: A312
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "target2_r": 3.0}
```

```proposal
id: A313
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A314
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "min_rs_filter": 50}
```

```proposal
id: A315
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "min_mom12_rank": 0.5}
```

```proposal
id: A316
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "max_atr_pct": 5.0}
```

```proposal
id: A317
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "min_volume_mult": 1.0}
```

```proposal
id: A318
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "use_regime_filter": true}
```

```proposal
id: A319
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "max_open_positions": 3}
```

```proposal
id: A320
status: proposed
written: 2026-11-06
reason: (idea factory) For a3: one more position spreads risk across more independent trades - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "max_open_positions": 5}
```

```proposal
id: A321
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "max_per_industry": 2}
```

```proposal
id: A322
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "skip_if_us_drop_pct": 2.0}
```

```proposal
id: A323
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets - applied to the adx_dmi entry rule.
overrides: {"family": "adx_dmi", "min_fii_long_pct": 25}
```

```proposal
id: A324
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "stop_atr_mult": 2.5}
```

```proposal
id: A325
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "stop_atr_mult": 3.5}
```

```proposal
id: A326
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "max_hold_days": 15}
```

```proposal
id: A327
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "max_hold_days": 35}
```

```proposal
id: A328
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "target1_r": 1.5}
```

```proposal
id: A329
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "target2_r": 3.0}
```

```proposal
id: A330
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A331
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "min_rs_filter": 50}
```

```proposal
id: A332
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "min_mom12_rank": 0.5}
```

```proposal
id: A333
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "max_atr_pct": 5.0}
```

```proposal
id: A334
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "min_volume_mult": 1.0}
```

```proposal
id: A335
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "use_regime_filter": true}
```

```proposal
id: A336
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "max_open_positions": 3}
```

```proposal
id: A337
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: one more position spreads risk across more independent trades - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "max_open_positions": 5}
```

```proposal
id: A338
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "max_per_industry": 2}
```

```proposal
id: A339
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "skip_if_us_drop_pct": 2.0}
```

```proposal
id: A340
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets - applied to the supertrend_flip entry rule.
overrides: {"family": "supertrend_flip", "min_fii_long_pct": 25}
```

```proposal
id: A341
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "stop_atr_mult": 2.5}
```

```proposal
id: A342
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "stop_atr_mult": 3.5}
```

```proposal
id: A343
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "max_hold_days": 15}
```

```proposal
id: A344
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "max_hold_days": 35}
```

```proposal
id: A345
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "target1_r": 1.5}
```

```proposal
id: A346
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "target2_r": 3.0}
```

```proposal
id: A347
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A348
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "min_rs_filter": 50}
```

```proposal
id: A349
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "min_mom12_rank": 0.5}
```

```proposal
id: A350
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "max_atr_pct": 5.0}
```

```proposal
id: A351
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "min_volume_mult": 1.0}
```

```proposal
id: A352
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "use_regime_filter": true}
```

```proposal
id: A353
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "max_open_positions": 3}
```

```proposal
id: A354
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: one more position spreads risk across more independent trades - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "max_open_positions": 5}
```

```proposal
id: A355
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "max_per_industry": 2}
```

```proposal
id: A356
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "skip_if_us_drop_pct": 2.0}
```

```proposal
id: A357
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets - applied to the ichimoku_breakout entry rule.
overrides: {"family": "ichimoku_breakout", "min_fii_long_pct": 25}
```

```proposal
id: A358
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "stop_atr_mult": 2.5}
```

```proposal
id: A359
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "stop_atr_mult": 3.5}
```

```proposal
id: A360
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "max_hold_days": 15}
```

```proposal
id: A361
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "max_hold_days": 35}
```

```proposal
id: A362
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "target1_r": 1.5}
```

```proposal
id: A363
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "target2_r": 3.0}
```

```proposal
id: A364
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A365
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "min_rs_filter": 50}
```

```proposal
id: A366
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "min_mom12_rank": 0.5}
```

```proposal
id: A367
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "max_atr_pct": 5.0}
```

```proposal
id: A368
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "min_volume_mult": 1.0}
```

```proposal
id: A369
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "use_regime_filter": true}
```

```proposal
id: A370
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "max_open_positions": 3}
```

```proposal
id: A371
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: one more position spreads risk across more independent trades - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "max_open_positions": 5}
```

```proposal
id: A372
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "max_per_industry": 2}
```

```proposal
id: A373
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "skip_if_us_drop_pct": 2.0}
```

```proposal
id: A374
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets - applied to the mfi_reversal entry rule.
overrides: {"family": "mfi_reversal", "min_fii_long_pct": 25}
```

```proposal
id: A375
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "stop_atr_mult": 2.5}
```

```proposal
id: A376
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "stop_atr_mult": 3.5}
```

```proposal
id: A377
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "max_hold_days": 15}
```

```proposal
id: A378
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "max_hold_days": 35}
```

```proposal
id: A379
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "target1_r": 1.5}
```

```proposal
id: A380
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "target2_r": 3.0}
```

```proposal
id: A381
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A382
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "min_rs_filter": 50}
```

```proposal
id: A383
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "min_mom12_rank": 0.5}
```

```proposal
id: A384
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping the most volatile stocks reduces gap losses through stops - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "max_atr_pct": 5.0}
```

```proposal
id: A385
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring at least average volume on the signal day filters thin moves - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "min_volume_mult": 1.0}
```

```proposal
id: A386
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: avoiding new trades when the market is below its 200-day average cuts bear-market losses - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "use_regime_filter": true}
```

```proposal
id: A387
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: fewer, best-ranked positions concentrate on the strongest signals - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "max_open_positions": 3}
```

```proposal
id: A388
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: one more position spreads risk across more independent trades - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "max_open_positions": 5}
```

```proposal
id: A389
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: at most two trades per industry limits sector-wide drawdowns - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "max_per_industry": 2}
```

```proposal
id: A390
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries after a >2% overnight US fall avoids buying into global risk-off opens - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "skip_if_us_drop_pct": 2.0}
```

```proposal
id: A391
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: skipping entries when FIIs are extremely short in index futures avoids hostile markets - applied to the cmf_breakout entry rule.
overrides: {"family": "cmf_breakout", "min_fii_long_pct": 25}
```

```proposal
id: A392
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly tighter stop cuts the size of losing trades while staying outside daily noise - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "stop_atr_mult": 2.5}
```

```proposal
id: A393
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a slightly wider stop avoids being shaken out of trends by normal volatility - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "stop_atr_mult": 3.5}
```

```proposal
id: A394
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: shorter holds free capital faster for fresh signals when trends fade quickly - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "max_hold_days": 15}
```

```proposal
id: A395
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: longer holds give drifting trends more time to reach targets - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "max_hold_days": 35}
```

```proposal
id: A396
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer first target banks partial profit more often - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "target1_r": 1.5}
```

```proposal
id: A397
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a nearer final target converts more winners before the time limit - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "target2_r": 3.0}
```

```proposal
id: A398
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: a trailing stop lets the few big trends run instead of capping them - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "exit_style": "trail", "trail_atr_mult": 3.0}
```

```proposal
id: A399
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: buying only stocks stronger than the average stock favours leaders - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "min_rs_filter": 50}
```

```proposal
id: A400
status: proposed
written: 2026-11-09
reason: (idea factory) For a3: requiring above-average 12-month momentum favours long-term winners - applied to the obv_breakout entry rule.
overrides: {"family": "obv_breakout", "min_mom12_rank": 0.5}
```
