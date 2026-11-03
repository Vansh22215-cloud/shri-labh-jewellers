"""Library of strategy FAMILIES (different ways to pick stocks and time entries).

Every family uses only data up to the close of day t (no look-ahead); trades are
entered at the next open by the backtest. Shared indicators are computed once
(`base_indicators`) and each family is a cheap combination of them
(`family_signals`), so hundreds of variants can be searched quickly.

Families:
  trend_pb_bo      v1: uptrend + strong RS, breakout to 50-day high OR pullback-reversal to 20 EMA
  donchian         close above the highest close of the last N days (20 or 55), volume confirmation
  high52           within 2% of the 52-week high and a new 20-day high, strong RS
  mean_reversion   long-term uptrend but 2-day RSI < 10 (short-term oversold); exit on bounce
  momentum_leaders top 10% relative strength in a clean uptrend, entries on the first day of each week
  squeeze          Bollinger band width in the lowest 20% of 6 months, then a close above the upper band
  ma_cross         20-day EMA crosses above 50-day average while above the 200-day
  volume_surge     volume > 3x average with a strong up-close (institutional buying footprint)
  nr7              narrowest range of 7 days followed by a close above that day's high, in an uptrend
  lowvol_momentum  strong RS AND low volatility, bought near the 20-day EMA
  inside_day       yesterday's range inside the day before's; today closes above yesterday's high (uptrend)
  gap_go           opens >= 1% above yesterday's high and closes strong on 1.5x volume (gap-and-go)
  strong_close     up > 2% closing in the top 10% of the day's range, strong RS, above 50-day average
  pullback_3d      three lower closes in a row inside an uptrend (short dip), above the 50-day average
  --- strategy library (approximations of published methods, see ROADMAP S1-S9) ---
  minervini_vcp    Minervini trend template (price > 50 > 150 > 200-day avg, 200 rising, >= 30% above 52-week low,
                   within 25% of 52-week high, RS >= 70) + volatility contraction (10-day range < 50% of the
                   50-day range) + breakout above the 20-day high on 1.5x volume
  weinstein_stage2 Weinstein: close crosses above a RISING 30-week (150-day) average on 2x volume, RS >= 50
  darvas_box       Darvas: tight 20-day box (range <= 12% of price) within 10% of the 52-week high; close breaks
                   above the box top on 1.5x volume
  momentum_12_1    Jegadeesh-Titman/AQR: on the first trading day of each month buy the top 10% by 12-month
                   return skipping the last month, above the 200-day average
  high52_rank      George & Hwang: first trading day of each month, top 10% of stocks by closeness to the
                   52-week high, in an uptrend
  pead             Post-earnings drift: on the results reaction day the stock gaps up >= 3% and closes in the top
                   half of the day on 2x volume, above the 200-day average
  sector_rotation  Faber-style: first trading day of each week, leaders (RS >= 80) of the strongest industries
                   (industry rank >= 85%) in an uptrend
  connors_pctb     Connors %b: above the 200-day average and the close is below the lower Bollinger band
                   (%b < 0) - a sharp dip in an uptrend; exits via the exit rules
  delivery_breakout new 20-day closing high on 1.5x volume where the DELIVERY % is >= 1.3x its 20-day average
                   and >= 45% (genuine buying, not intraday churn), in an uptrend
"""
import numpy as np
import pandas as pd

FAMILIES = ["trend_pb_bo", "donchian", "high52", "mean_reversion", "momentum_leaders",
            "squeeze", "ma_cross", "volume_surge", "nr7", "lowvol_momentum"]
# Short-term (1-5 day) chart patterns, added 2026-11-03
SHORT_FAMILIES = ["inside_day", "gap_go", "strong_close", "pullback_3d"]
# Needs NSE delivery data (ROADMAP D1, added 2026-11-03)
DELIVERY_FAMILIES = ["delivery_breakout"]
# Strategy LIBRARY: well-known published methods (ROADMAP S1-S9, added 2026-11-03)
LIBRARY_FAMILIES = ["minervini_vcp", "weinstein_stage2", "darvas_box", "momentum_12_1", "high52_rank",
                    "pead", "sector_rotation", "connors_pctb"]


def sma(df, n):
    return df.rolling(n, min_periods=n).mean()


def ema(df, n):
    return df.ewm(span=n, adjust=False, min_periods=n).mean()


def atr(high, low, close, n):
    prev = close.shift(1)
    tr = np.maximum(high - low, np.maximum((high - prev).abs(), (low - prev).abs()))
    tr = tr.where(~(high.isna() | low.isna()))
    return tr.rolling(n, min_periods=n).mean()


def rsi(close, n):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def xs_rank(df, mask):
    return df.where(mask).rank(axis=1, pct=True)


def base_indicators(P, nifty_close, member_mask, industry, p, results_soon=None):
    """All shared indicators (expensive part, computed once)."""
    o, h, l, c, v, raw = P["open"], P["high"], P["low"], P["close"], P["volume"], P["raw_close"]
    nifty = nifty_close.reindex(c.index).ffill()
    B = {"c": c, "h": h, "l": l, "v": v, "o": o}
    B["sma50"], B["sma200"] = sma(c, p["trend_fast_sma"]), sma(c, p["trend_slow_sma"])
    B["ema20"] = ema(c, p["pullback_ema"])
    B["atr"] = a = atr(h, l, c, p["atr_period"])
    bars = c.notna().cumsum()
    traded_value = (raw * v).rolling(p["liquidity_lookback"], min_periods=20).median()
    member = member_mask.reindex(index=c.index, columns=c.columns).fillna(False).astype(bool)
    member &= (bars >= p["min_history_days"]) & (raw >= p["min_price"]) & c.notna()
    B["member"] = member

    sk = p["mom_skip"]
    rs_l = (c.shift(sk) / c.shift(p["mom_long"]) - 1).sub(nifty.shift(sk) / nifty.shift(p["mom_long"]) - 1, axis=0)
    rs_s = (c.shift(sk) / c.shift(p["mom_short"]) - 1).sub(nifty.shift(sk) / nifty.shift(p["mom_short"]) - 1, axis=0)
    B["rs_rank"] = rank_rs_l = xs_rank(rs_l, member)
    rank_rs_s = xs_rank(rs_s, member)

    sector_rank = pd.DataFrame(0.5, index=c.index, columns=c.columns)
    ind = pd.Series({s: industry.get(s) for s in c.columns}).dropna()
    if len(ind):
        groups = {g: list(cols) for g, cols in ind.groupby(ind).groups.items()}
        rs_m = rs_l.where(member)
        ind_mean = pd.DataFrame({g: rs_m[cols].mean(axis=1) for g, cols in groups.items()})
        ind_rank = ind_mean.rank(axis=1, pct=True)
        for g, cols in groups.items():
            sector_rank[cols] = np.repeat(ind_rank[[g]].values, len(cols), axis=1)
        sector_rank = sector_rank.fillna(0.5)
    B["sector_rank"] = sector_rank
    B["industry"] = {s_: industry.get(s_) for s_ in c.columns}

    B["up_trend"] = (c > B["sma50"]) & (B["sma50"] > B["sma200"]) & (B["sma200"] > B["sma200"].shift(p["slope_lookback"]))
    B["above200"] = c > B["sma200"]
    B["not_extended"] = (c / B["sma50"] - 1) * 100 <= p["max_extension_above_50dma_pct"]
    pct_above = (c > B["sma50"]).astype(float).where(B["sma50"].notna()).rolling(63, min_periods=40).mean()
    atr_pct = a / c
    B["lowvol_rank"] = xs_rank(-atr_pct, member)
    trend_q = 0.5 * xs_rank(pct_above, member) + 0.5 * B["lowvol_rank"]
    liq = xs_rank(traded_value, member)
    w = p["score_weights"]
    B["score"] = (w["rs_long"] * rank_rs_l + w["rs_short"] * rank_rs_s + w["sector_rs"] * sector_rank
                  + w["trend_quality"] * trend_q + w["liquidity"] * liq) * 100

    B["avg_vol"] = v.shift(1).rolling(50, min_periods=30).mean()
    rng = (h - l)
    B["close_pos"] = (c - l) / rng.replace(0, np.nan)
    B["hi50"] = c.shift(1).rolling(50, min_periods=50).max()
    B["hi20"] = c.shift(1).rolling(20, min_periods=20).max()
    B["hi55"] = c.shift(1).rolling(55, min_periods=55).max()
    B["hi252"] = h.rolling(252, min_periods=200).max()
    B["lo252"] = l.rolling(252, min_periods=200).min()
    B["sma150"] = sma(c, 150)
    rng10 = h.rolling(10, min_periods=10).max() - l.rolling(10, min_periods=10).min()
    rng50 = h.rolling(50, min_periods=50).max() - l.rolling(50, min_periods=50).min()
    B["contraction"] = (rng10 / rng50.replace(0, np.nan)).shift(1)        # up to yesterday
    hb20, lb20 = h.shift(1).rolling(20, min_periods=20).max(), l.shift(1).rolling(20, min_periods=20).min()
    B["box_top"], B["box_width"] = hb20, (hb20 - lb20) / c
    B["mom_12_1_rank"] = xs_rank(c.shift(21) / c.shift(252) - 1, member)
    B["near_high_rank"] = xs_rank(c / B["hi252"], member)
    B["bb_lower"] = None   # set below
    B["low5_min"] = l.rolling(5, min_periods=5).min()
    B["prev_high"] = h.shift(1)
    B["inside_prev"] = ((h.shift(1) < h.shift(2)) & (l.shift(1) > l.shift(2)))
    B["down3"] = (c < c.shift(1)) & (c.shift(1) < c.shift(2)) & (c.shift(2) < c.shift(3))
    B["rsi2"] = rsi(c, 2)
    mid, sd = sma(c, 20), c.rolling(20, min_periods=20).std()
    B["bb_upper"] = mid + 2 * sd
    B["bb_lower"] = mid - 2 * sd
    bw = (4 * sd / mid)
    bw_lo, bw_hi = bw.rolling(126, min_periods=100).min(), bw.rolling(126, min_periods=100).max()
    B["bw_pct"] = ((bw - bw_lo) / (bw_hi - bw_lo).replace(0, np.nan)).shift(1)
    nr = rng.rolling(7, min_periods=7).min()
    B["nr7_prev"] = (rng == nr).shift(1).fillna(False).astype(bool)
    B["ret1"] = c / c.shift(1) - 1
    B["ema20_prev_below"] = (B["ema20"].shift(1) <= B["sma50"].shift(1))
    idx = c.index
    _m = pd.Series(idx.month, index=idx)
    B["month_start"] = _m.ne(_m.shift(1))
    B["week_start"] = pd.Series(np.asarray(idx.isocalendar().week, dtype=float), index=idx).diff().fillna(1).ne(0)

    breadth = ((c > B["sma50"]) & member).sum(axis=1) / member.sum(axis=1).replace(0, np.nan) * 100
    B["breadth"] = breadth
    B["regime_ok"] = (nifty > nifty.rolling(p["regime_sma"], min_periods=p["regime_sma"]).mean()) & \
                     (breadth >= p["breadth_min_pct_above_50dma"])
    dv = P.get("deliv")
    if dv is not None:
        dv = dv.reindex(index=c.index, columns=c.columns)
        B["deliv"] = dv
        B["deliv_avg"] = dv.shift(1).rolling(20, min_periods=10).mean()   # past 20 days only
    else:
        B["deliv"] = B["deliv_avg"] = None
    rd = P.get("results_day")
    B["results_day"] = rd.reindex(index=c.index, columns=c.columns).fillna(False).astype(bool) if rd is not None else None
    B["results_soon"] = None if results_soon is None else \
        results_soon.reindex(index=c.index, columns=c.columns).fillna(False).astype(bool)
    return B


P_FII = {"series": None}   # set by engine.build from the participant-OI panel (FII index-futures long %)


def family_signals(B, p):
    """Entry mask, setup label and ranking score for the family named in p['family']."""
    fam = p.get("family", "trend_pb_bo")
    c, v = B["c"], B["v"]
    rs_ok = B["rs_rank"] * 100 >= p["min_rs_percentile"]
    if fam == "trend_pb_bo":
        breakout = (c > B["hi50"]) & (v > p["breakout_volume_mult"] * B["avg_vol"]) & (B["close_pos"] >= 0.5)
        touched = B["low5_min"] <= B["ema20"] * (1 + p["pullback_band_pct"] / 100)
        pullback = touched & (c > B["ema20"]) & (c > B["prev_high"]) & ~breakout
        entry = B["up_trend"] & B["not_extended"] & rs_ok & (breakout | pullback)
        setup = np.where(breakout, "breakout", np.where(pullback, "pullback", ""))
    elif fam == "donchian":
        hi = B["hi20"] if p.get("donchian_n", 55) == 20 else B["hi55"]
        entry = B["above200"] & (c > hi) & (v > 1.2 * B["avg_vol"])
        setup = "donchian breakout"
    elif fam == "high52":
        entry = (c >= 0.98 * B["hi252"]) & (c > B["hi20"]) & rs_ok & B["above200"]
        setup = "near 52-week high"
    elif fam == "mean_reversion":
        entry = B["above200"] & (B["rsi2"] < 10) & (c > B["sma50"] * 0.95)
        setup = "oversold dip in uptrend"
    elif fam == "momentum_leaders":
        ws = pd.DataFrame(np.repeat(B["week_start"].to_numpy(dtype=bool)[:, None], c.shape[1], axis=1),
                          index=c.index, columns=c.columns)
        entry = ws & (B["rs_rank"] >= 0.9) & B["up_trend"] & B["not_extended"]
        setup = "momentum leader"
    elif fam == "squeeze":
        entry = (B["bw_pct"] <= 0.2) & (c > B["bb_upper"]) & B["above200"]
        setup = "volatility squeeze breakout"
    elif fam == "ma_cross":
        entry = B["ema20_prev_below"] & (B["ema20"] > B["sma50"]) & B["above200"]
        setup = "20/50 average crossover"
    elif fam == "volume_surge":
        entry = (v > 3 * B["avg_vol"]) & (B["ret1"] > 0.04) & (B["close_pos"] >= 0.75) & (c > B["sma50"])
        setup = "volume surge"
    elif fam == "nr7":
        entry = B["nr7_prev"] & (c > B["prev_high"]) & B["up_trend"]
        setup = "NR7 breakout"
    elif fam == "lowvol_momentum":
        entry = rs_ok & (B["lowvol_rank"] >= 0.7) & (c > B["sma50"]) & (c <= B["ema20"] * 1.02) & (c > B["prev_high"])
        setup = "low-volatility leader on pullback"
    elif fam == "inside_day":
        entry = B["inside_prev"] & (c > B["prev_high"]) & B["up_trend"]
        setup = "inside-day breakout"
    elif fam == "gap_go":
        entry = (B["o"] >= B["prev_high"] * 1.01) & (c > B["o"]) & (B["close_pos"] >= 0.7) & \
                (v > 1.5 * B["avg_vol"]) & (c > B["sma50"])
        setup = "gap-and-go"
    elif fam == "strong_close":
        entry = (B["ret1"] > 0.02) & (B["close_pos"] >= 0.9) & rs_ok & (c > B["sma50"])
        setup = "strong close"
    elif fam == "minervini_vcp":
        tt = (c > B["sma50"]) & (B["sma50"] > B["sma150"]) & (B["sma150"] > B["sma200"]) & \
             (B["sma200"] > B["sma200"].shift(21)) & (c >= 1.3 * B["lo252"]) & (c >= 0.75 * B["hi252"]) & \
             (B["rs_rank"] >= 0.7)
        entry = tt & (B["contraction"] < 0.5) & (c > B["hi20"]) & (v > 1.5 * B["avg_vol"])
        setup = "Minervini trend template + VCP breakout"
    elif fam == "weinstein_stage2":
        entry = (c > B["sma150"]) & (c.shift(1) <= B["sma150"].shift(1)) & (B["sma150"] > B["sma150"].shift(20)) & \
                (v > 2 * B["avg_vol"]) & (B["rs_rank"] >= 0.5)
        setup = "Weinstein stage-2 breakout"
    elif fam == "darvas_box":
        entry = (B["box_width"] <= 0.12) & (c >= 0.9 * B["hi252"]) & (c > B["box_top"]) & (v > 1.5 * B["avg_vol"])
        setup = "Darvas box breakout"
    elif fam == "momentum_12_1":
        ms = pd.DataFrame(np.repeat(B["month_start"].to_numpy(dtype=bool)[:, None], c.shape[1], axis=1),
                          index=c.index, columns=c.columns)
        entry = ms & (B["mom_12_1_rank"] >= 0.9) & B["above200"]
        setup = "12-month momentum leader (monthly)"
    elif fam == "high52_rank":
        ms = pd.DataFrame(np.repeat(B["month_start"].to_numpy(dtype=bool)[:, None], c.shape[1], axis=1),
                          index=c.index, columns=c.columns)
        entry = ms & (B["near_high_rank"] >= 0.9) & B["up_trend"]
        setup = "closest to 52-week high (monthly)"
    elif fam == "pead":
        if B.get("results_day") is None:
            raise ValueError("results dates not available")
        entry = B["results_day"] & (B["o"] >= c.shift(1) * 1.03) & (B["close_pos"] >= 0.5) & \
                (v > 2 * B["avg_vol"]) & B["above200"]
        setup = "strong results reaction (earnings drift)"
    elif fam == "sector_rotation":
        ws = pd.DataFrame(np.repeat(B["week_start"].to_numpy(dtype=bool)[:, None], c.shape[1], axis=1),
                          index=c.index, columns=c.columns)
        entry = ws & (B["sector_rank"] >= 0.85) & (B["rs_rank"] >= 0.8) & B["up_trend"]
        setup = "leader of a top sector"
    elif fam == "connors_pctb":
        entry = B["above200"] & (c < B["bb_lower"])
        setup = "sharp dip below lower band in uptrend"
    elif fam == "delivery_breakout":
        if B.get("deliv") is None:
            raise ValueError("delivery data not available")
        entry = (c > B["hi20"]) & (v > 1.5 * B["avg_vol"]) & (B["deliv"] >= 1.3 * B["deliv_avg"]) & \
                (B["deliv"] >= 45) & B["up_trend"]
        setup = "high-delivery breakout"
    elif fam == "pullback_3d":
        entry = B["down3"] & B["up_trend"] & (c > B["sma50"])
        setup = "3-day pullback in uptrend"
    else:
        raise ValueError(f"unknown family {fam}")
    eligible = B["member"] & entry & B["atr"].notna()
    # optional filters used by research proposals (IMPROVEMENTS.md)
    if p.get("min_sector_rank"):
        eligible &= B["sector_rank"] >= p["min_sector_rank"]
    if p.get("min_volume_mult"):
        eligible &= v >= p["min_volume_mult"] * B["avg_vol"]
    if p.get("min_rs_filter"):
        eligible &= B["rs_rank"] * 100 >= p["min_rs_filter"]
    if p.get("min_delivery_ratio") and B.get("deliv") is not None:
        eligible &= B["deliv"] >= p["min_delivery_ratio"] * B["deliv_avg"]
    if p.get("min_mom12_rank"):   # 12-1 month momentum rank filter (cross-sectional, 0..1)
        eligible &= B["mom_12_1_rank"] >= p["min_mom12_rank"]
    if p.get("max_atr_pct"):
        eligible &= (B["atr"] / c * 100) <= p["max_atr_pct"]
    if B.get("results_soon") is not None and p.get("results_rule") == "exclude":
        eligible &= ~B["results_soon"]
    setup = pd.DataFrame(setup if isinstance(setup, np.ndarray) else np.full(c.shape, setup),
                         index=c.index, columns=c.columns)
    score = B["score"]
    if fam == "mean_reversion":
        score = 100 - B["rsi2"]      # most oversold first
    regime = B["regime_ok"] if p.get("use_regime_filter", True) else pd.Series(True, index=c.index)
    if p.get("min_fii_long_pct") and P_FII.get("series") is not None:   # FII positioning filter (ROADMAP I1)
        fl = P_FII["series"].reindex(c.index).ffill()
        regime = regime & (fl >= p["min_fii_long_pct"]).fillna(True)
    entry_block = None
    if p.get("skip_if_us_drop_pct"):   # skip next-open entries after a big overnight US fall (ROADMAP I3)
        from .intel_global import us_return_before
        entry_block = (us_return_before(c.index) * 100 < -p["skip_if_us_drop_pct"]).fillna(False)
    return {"entry_block": entry_block,
            "score": score, "eligible": eligible, "setup": setup, "atr": B["atr"], "regime_ok": regime,
            "market_regime_ok": B["regime_ok"], "breadth": B["breadth"], "rs_rank": B["rs_rank"],
            "sector_rank": B["sector_rank"], "sma50": B["sma50"], "sma200": B["sma200"], "ema20": B["ema20"],
            "member": B["member"], "industry": B.get("industry", {})}
