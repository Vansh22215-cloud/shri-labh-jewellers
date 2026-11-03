"""Remaining daily-bar items of the owner's library (rule version cat-v3): Wyckoff phases, weekly-bar spikes,
point & figure and renko breakouts, gap/climax reversals, Gann levels, IPO base, and the remaining
market-structure (ICT/SMC-style) events, plus the last indicators and quant features.

All rules use completed bars only; every level that comes from an earlier event is carried forward from the bar
it became known. Long-side (bullish) variants only; neutral items are detector-only features.
"""
import numpy as np
import pandas as pd

from .catalog import _cross_above, pivots


def _df(B, x):
    c = B["c"]
    return pd.DataFrame(x, index=c.index, columns=c.columns)


def _ffill_event(level, event, limit):
    return level.where(event).ffill(limit=limit)


def _recent(event, lo, hi):
    """event happened between lo and hi bars ago (inclusive)."""
    e = event.fillna(False).astype(float)
    return e.shift(lo).rolling(hi - lo + 1, min_periods=1).max().fillna(0).astype(bool)


# ----------------------------------------------------------------------------- weekly bars (completed weeks only)
def weekly(B):
    if "_wk" in B:
        return B["_wk"]
    c, h, l, o = B["c"], B["h"], B["l"], B["o"]
    idx = c.index
    wk = pd.Series(idx.to_period("W").astype(str), index=idx)
    end = pd.Series(((idx + pd.offsets.BDay(1)).to_period("W").astype(str) != wk.values), index=idx)
    g = wk.values
    W = {"h": h.groupby(g).cummax(), "l": l.groupby(g).cummin(), "c": c,
         "o": o.groupby(g).transform("first")}
    W = {k: v.where(end, np.nan) for k, v in W.items()}          # a weekly bar exists only on its last day
    B["_wk"] = (W, end)
    return B["_wk"]


def _wshift(x, end, k):
    """Value of the weekly bar k weeks earlier, placed on week-end rows."""
    rows = x[end.values]
    return rows.shift(k).reindex(x.index)


# ----------------------------------------------------------------------------- chart patterns
def chart(pid, B, p=None):
    c, h, l, o, v, A = B["c"], B["h"], B["l"], B["o"], B["v"], B["atr"]
    av = B["avg_vol"]
    up = c > o
    with np.errstate(invalid="ignore", divide="ignore"):
        sc = (v >= 3 * av) & (l <= l.shift(1).rolling(60).min()) & (c <= 0.8 * c.shift(60))   # selling climax
        rng_hi = h.shift(1).rolling(40).max()
        rng_lo = l.shift(1).rolling(60).min()
        tight = (rng_hi / rng_lo - 1) <= 0.35
        mid = (rng_hi + rng_lo) / 2
        if pid == "wyckoff_accumulation":                      # SC 30-120 bars ago, range, SOS breakout on volume
            e = _recent(sc, 30, 120) & tight & _cross_above(c, rng_hi) & (v >= 1.5 * av)
        elif pid == "creek_breakout":                          # jump across the creek: tested resistance broken
            touches = (h >= 0.98 * rng_hi).astype(float).rolling(40).sum()
            e = ((rng_hi / l.shift(1).rolling(40).min() - 1) <= 0.25) & (touches >= 3) & _cross_above(c, rng_hi) & (v >= 1.3 * av)
        elif pid == "wyckoff_sign_of_strength":
            spring = (l < rng_lo) & (c > rng_lo)
            e = ((h - l) >= 1.5 * A) & ((c - l) >= 0.75 * (h - l)) & (v >= 1.5 * av) & (c > mid) & \
                (_recent(spring, 1, 30) | _recent(sc, 5, 60))
        elif pid == "wyckoff_last_point_of_support":
            sos = ((h - l) >= 1.5 * A) & ((c - l) >= 0.75 * (h - l)) & (v >= 1.5 * av) & (c > mid)
            e = _recent(sos, 3, 20) & (l > mid) & (c.shift(1) < c.shift(3)) & (v < av) & up
        elif pid == "wyckoff_backup_to_edge":
            brk = _cross_above(c, rng_hi)
            lvl = _ffill_event(rng_hi, brk, 20).shift(1)
            e = _recent(brk, 3, 20) & (l <= lvl + 0.5 * A) & (c > lvl) & up
        elif pid == "secondary_test_wyckoff":
            sc_low, sc_vol = _ffill_event(l, sc, 40).shift(5), _ffill_event(v, sc, 40).shift(5)
            e = (l <= sc_low * 1.03) & (l >= sc_low * 0.98) & (v < 0.7 * sc_vol) & up
        elif pid in ("pipe_bottom", "horn_bottom"):
            W, end = weekly(B)
            wl, wh, wo, wc = W["l"], W["h"], W["o"], W["c"]
            wr = (wh - wl)
            spike = ((np.minimum(wo, wc) - wl) >= 0.5 * wr)
            k = 1 if pid == "pipe_bottom" else 2
            s0, sk = spike, _wshift(spike.astype(float), end, k) > 0
            l0, lk = wl, _wshift(wl, end, k)
            before = pd.concat([_wshift(wl, end, j) for j in range(k + 1, k + 4)]).groupby(level=0).min()
            cond = s0 & sk & ((l0 / lk - 1).abs() <= 0.01) & (np.minimum(l0, lk) < before)
            if pid == "horn_bottom":
                cond &= _wshift(wl, end, 1) > np.maximum(l0, lk)          # the bar between is shallower
            e = cond.fillna(False) & end.values[:, None]
        elif pid == "point_figure_breakout":
            e = _df(B, _pnf_double_top(c.to_numpy(dtype=float)))
        elif pid == "renko_breakout":
            e = _df(B, _renko_reversal(c.to_numpy(dtype=float)))
        elif pid in ("exhaustion_gap", "gap_exhaustion"):
            gd = (o < l.shift(1)) & (v >= 2 * av) & (c.shift(1) <= 0.85 * c.shift(30))
            lvl = _ffill_event(l.shift(1), gd, 3)
            e = _cross_above(c, lvl) & _recent(gd, 1, 3)
        elif pid == "trend_exhaustion_climax":
            e = (c <= 0.7 * c.shift(60)) & ((h - l) >= 2.5 * A) & (v >= 3 * av) & ((c - l) >= 0.5 * (h - l))
        elif pid == "gann_square_of_nine_level":
            PLv, PLi, PHv, PHi = pivots(B, L=5, R=5)
            base = _df(B, np.fmin(PLv[:, :, 0], np.fmin(PLv[:, :, 1], PLv[:, :, 2])))      # recent major low
            sq = np.sqrt(base)
            m = np.floor((np.sqrt(l.clip(lower=0)) - sq) / 0.25 + 0.5)
            lvl = (sq + 0.25 * m) ** 2
            e = (m >= 1) & ((l - lvl).abs() <= 0.1 * A) & (c > lvl) & up & B["above200"] & (l < l.shift(1))
        elif pid == "ipo_base":
            first = c.apply(lambda s: s.first_valid_index())
            start = c.index[5]
            age = pd.DataFrame({col: (c.index >= first[col]).cumsum() if first[col] is not None else 0
                                for col in c.columns}, index=c.index)
            new_listing = pd.Series({col: first[col] is not None and first[col] > start for col in c.columns})
            hi = h.expanding().max().shift(1)
            lo = l.expanding().min()
            # second-year base: the universe only admits stocks first seen >= 365 days earlier (data quality)
            e = (age >= 250) & (age <= 500) & ((lo / hi) >= 0.6) & _cross_above(c, hi) & new_listing.values[None, :]
        else:
            raise ValueError(f"no detector for chart pattern {pid}")
    return (e.fillna(False).astype(bool) & B["member"]).fillna(False)


def _pnf_double_top(c, box=0.02, rev=3):
    """Point & figure (log boxes of 2%, 3-box reversal) on closes: True on the day an X column exceeds the
    previous X column's top (double-top buy)."""
    T, N = c.shape
    lb = np.log1p(box)
    out = np.zeros((T, N), bool)
    d = np.zeros(N)
    top, bot, prev_xtop = np.full(N, np.nan), np.full(N, np.nan), np.full(N, np.nan)
    fired = np.zeros(N, bool)
    for t in range(T):
        x = np.log(c[t])
        ok = ~np.isnan(x)
        new = ok & np.isnan(top)
        top[new], bot[new] = x[new], x[new]
        upc = ok & (d >= 0)
        rise = upc & (x >= top + lb)
        top[rise] = x[rise]
        if t:
            brk = rise & (d > 0) & ~fired & ~np.isnan(prev_xtop) & (top > prev_xtop + 1e-12)
            out[t] = brk
            fired |= brk
        rev_dn = upc & (x <= top - rev * lb)
        dnc = ok & (d <= 0) & ~rev_dn
        fall = dnc & (x <= bot - lb)
        bot[fall] = x[fall]
        rev_up = dnc & (x >= bot + rev * lb)
        # switch columns
        prev_xtop[rev_dn & (d > 0)] = top[rev_dn & (d > 0)]
        bot[rev_dn] = x[rev_dn]; d[rev_dn] = -1
        top[rev_up] = x[rev_up]; d[rev_up] = 1; fired[rev_up] = False
        d[ok & (d == 0) & rise] = 1
    return out


def _renko_reversal(c, brick=0.02, min_down=3):
    """Renko bricks (2% log): True when the second up brick forms after a run of >= 3 down bricks."""
    T, N = c.shape
    lb = np.log1p(brick)
    out = np.zeros((T, N), bool)
    lvl = np.full(N, np.nan)
    run = np.zeros(N)          # +n up bricks / -n down bricks in the current run
    last_down = np.zeros(N)
    for t in range(T):
        x = np.log(c[t])
        ok = ~np.isnan(x)
        new = ok & np.isnan(lvl)
        lvl[new] = x[new]
        nu = np.where(ok, np.floor((x - lvl) / lb), 0)
        nd = np.where(ok, np.floor((lvl - x) / lb), 0)
        upm = ok & (nu >= 1)
        dnm = ok & (nd >= 1) & ~upm
        was_down = run < 0
        last_down[upm & was_down] = -run[upm & was_down]
        run[upm] = np.where(run[upm] > 0, run[upm] + nu[upm], nu[upm])
        lvl[upm] += nu[upm] * lb
        run[dnm] = np.where(run[dnm] < 0, run[dnm] - nd[dnm], -nd[dnm])
        lvl[dnm] -= nd[dnm] * lb
        out[t] = upm & (run >= 2) & (run - nu < 2) & (last_down >= min_down)
    return out


CHART = ["wyckoff_accumulation", "creek_breakout", "wyckoff_sign_of_strength", "wyckoff_last_point_of_support",
         "wyckoff_backup_to_edge", "secondary_test_wyckoff", "pipe_bottom", "horn_bottom", "point_figure_breakout",
         "renko_breakout", "exhaustion_gap", "trend_exhaustion_climax", "gann_square_of_nine_level", "ipo_base"]


# ----------------------------------------------------------------------------- market structure (remaining)
def ms(mid, B, p=None):
    c, h, l, o, v, A = B["c"], B["h"], B["l"], B["o"], B["v"], B["atr"]
    av = B["avg_vol"]
    up = c > o
    body = c - o
    PLv, PLi, PHv, PHi = pivots(B)
    l2, l3, h2, h3 = (_df(B, x) for x in (PLv[:, :, 1], PLv[:, :, 2], PHv[:, :, 1], PHv[:, :, 2]))
    with np.errstate(invalid="ignore", divide="ignore"):
        if mid in ("breaker_block_bullish", "breaker_retest"):
            disp_dn = (body <= -1.5 * A)
            ob_hi = _ffill_event(h.shift(1), disp_dn & (c.shift(1) > o.shift(1)), 40)    # last up candle's high
            brk = _cross_above(c, ob_hi)
            if mid == "breaker_block_bullish":
                e = brk
            else:
                lvl = _ffill_event(ob_hi, brk, 15).shift(1)
                e = _recent(brk, 2, 15) & (l <= lvl + 0.3 * A) & (c > lvl) & up
        elif mid == "mitigation_block_bullish":     # higher low, then the last lower high is broken
            e = (l3 > l2) & (h3 < h2) & _cross_above(c, h3)
        elif mid == "rejection_block_bullish":
            wick = (np.minimum(o, c) - l) >= 2 * body.abs()
            zone_top = _ffill_event(np.minimum(o, c), wick & (l <= l.shift(1).rolling(20).min()), 30)
            zone_low = _ffill_event(l, wick & (l <= l.shift(1).rolling(20).min()), 30)
            e = (l <= zone_top.shift(1)) & (l >= zone_low.shift(1)) & up & (c > zone_top.shift(1))
        elif mid == "consequent_encroachment":
            fvg = (l > h.shift(2)) & ((l - h.shift(2)) >= 0.25 * A)
            ce = _ffill_event((l + h.shift(2)) / 2, fvg, 20).shift(1)
            e = (l <= ce) & (c > ce) & up
        elif mid == "equal_highs_liquidity_pool":    # equal highs taken out and accepted above
            eq = (h3 - h2).abs() <= 0.25 * A
            top = np.fmax(h2, h3)
            e = eq & (c > top) & (c.shift(1) > top) & (c.shift(2) <= top)
        elif mid == "equilibrium_level":
            eqm = (h3 + l3) / 2
            e = B["up_trend"] & _cross_above(c, eqm)
        elif mid == "external_liquidity_sweep":
            lo = l.shift(1).rolling(60).min()
            e = (l < lo) & (c > lo) & up
        elif mid == "internal_liquidity_sweep":
            lo = l.shift(1).rolling(60).min()
            e = (l3 > lo + 0.5 * A) & (l < l3) & (c > l3) & up
        elif mid in ("internal_structure_break", "external_structure_break"):
            Lr = (2, 2) if mid == "internal_structure_break" else (8, 8)
            a, ai, b, bi = pivots(B, L=Lr[0], R=Lr[1])
            hh, ll2, ll3 = _df(B, b[:, :, 2]), _df(B, a[:, :, 1]), _df(B, a[:, :, 2])
            e = (ll3 > ll2) & _cross_above(c, hh)
        elif mid == "liquidity_void":               # three non-overlapping up bars (one-sided trade)
            e = (l > h.shift(1)) & (l.shift(1) > h.shift(2)) & (c > o) & (c.shift(1) > o.shift(1))
        elif mid == "multi_timeframe_alignment":
            wk = c.rolling(50).mean()                # ~10-week average
            mo = c.rolling(200).mean()               # ~10-month average
            al = B["up_trend"] & (c > wk) & (c > mo) & (c / c.shift(20) > 1)
            e = al & ~al.shift(1).fillna(False).astype(bool)
        elif mid == "optimal_trade_entry_zone":     # 62-79% retracement of the last up swing
            i3l, i3h = _df(B, PLi[:, :, 2]), _df(B, PHi[:, :, 2])
            leg = (i3h > i3l) & (h3 > l3)
            z_hi, z_lo = h3 - 0.62 * (h3 - l3), h3 - 0.79 * (h3 - l3)
            e = leg & (l <= z_hi) & (l >= z_lo) & up & B["above200"]
        elif mid == "anchored_vwap_reclaim":        # VWAP anchored at the last confirmed swing high
            tp = (h + l + c) / 3
            cum_pv, cum_v = (tp * v).fillna(0).cumsum(), v.fillna(0).cumsum()
            anc = _df(B, PHi[:, :, 2])
            T = len(c)
            ai = anc.fillna(-1).astype(int).clip(lower=0).to_numpy()
            cpv, cv = cum_pv.to_numpy(), cum_v.to_numpy()
            cols = np.arange(c.shape[1])[None, :]
            base_pv = np.where(ai > 0, cpv[np.maximum(ai - 1, 0), cols], 0)
            base_v = np.where(ai > 0, cv[np.maximum(ai - 1, 0), cols], 0)
            avwap = _df(B, (cpv - base_pv) / np.where(cv - base_v > 0, cv - base_v, np.nan))
            avwap = avwap.where(anc.notna())
            e = _cross_above(c, avwap) & (c < h3)
        elif mid == "volume_imbalance_bullish":     # body gap: open above prior close, wicks overlap
            e = (o > c.shift(1)) & (l <= h.shift(1)) & up & (c.shift(1) > o.shift(1))
        # ---- neutral structure items: detector-only (features, not entries)
        elif mid == "consolidation_range":
            e = ((h.rolling(20).max() - l.rolling(20).min()) <= 3 * A)
        elif mid == "parabolic_run":
            roc = c / c.shift(10) - 1
            e = (roc > roc.shift(5)) & (roc.shift(5) > roc.shift(10)) & (c > 1.3 * B["sma50"])
        elif mid == "climax_volume_spike":
            e = ((v - v.rolling(60).mean()) / v.rolling(60).std()) > 4
        elif mid == "stop_run_inference":
            lo = l.shift(1).rolling(20).min()
            e = (l < lo - 0.5 * A) & ((h - l) >= 2 * A)
        elif mid == "multi_timeframe_conflict":
            e = (c > c.rolling(20).mean()) != (c > c.rolling(200).mean())
        else:
            raise ValueError(f"no detector for market-structure event {mid}")
    return (e.fillna(False).astype(bool) & B["member"]).fillna(False)


MS = ["breaker_block_bullish", "breaker_retest", "mitigation_block_bullish", "rejection_block_bullish",
      "consequent_encroachment", "equal_highs_liquidity_pool", "equilibrium_level", "external_liquidity_sweep",
      "internal_liquidity_sweep", "internal_structure_break", "external_structure_break", "liquidity_void",
      "multi_timeframe_alignment", "optimal_trade_entry_zone", "anchored_vwap_reclaim", "volume_imbalance_bullish"]
MS_DETECTOR_ONLY = ["consolidation_range", "parabolic_run", "climax_volume_spike", "stop_run_inference",
                    "multi_timeframe_conflict"]


# ----------------------------------------------------------------------------- last indicators / quant features
def feature(fid, B):
    c, h, l, o, v, A = B["c"], B["h"], B["l"], B["o"], B["v"], B["atr"]
    r = c.pct_change()
    nifty = B.get("nifty")
    import talib as tl

    def per_col(fn):
        out = pd.DataFrame(np.nan, index=c.index, columns=c.columns)
        for col in c.columns:
            s = c[col]
            ok = s.notna()
            if ok.sum() > 64:
                out.loc[ok, col] = fn(s[ok].to_numpy(dtype=float))
        return out

    def acf_period(x, w=64):
        out = np.full(len(x), np.nan)
        for t in range(w, len(x)):
            a = np.diff(np.log(x[t - w:t + 1]))
            a = a - a.mean()
            den = (a * a).sum()
            if den == 0:
                continue
            ac = [(a[k:] * a[:-k]).sum() / den for k in range(8, 49)]
            out[t] = 8 + int(np.argmax(ac))
        return out

    def sampen(x, m=2, w=60, step=5):
        """Sample entropy of the last w returns, refreshed every `step` bars (carried forward in between)."""
        out = np.full(len(x), np.nan)
        for t in range(w, len(x), step):
            a = np.diff(np.log(x[t - w:t + 1]))
            rr = 0.2 * a.std()
            if rr == 0:
                continue
            def phi(mm):
                X = np.array([a[i:i + mm] for i in range(len(a) - mm)])
                d = np.max(np.abs(X[:, None, :] - X[None, :, :]), axis=2)
                return ((d <= rr).sum() - len(X)) / 2
            b, aa = phi(m), phi(m + 1)
            out[t] = -np.log(aa / b) if aa > 0 and b > 0 else np.nan
        return pd.Series(out).ffill(limit=step - 1).to_numpy()

    lc = np.log(c)
    ln = np.log(nifty) if isinstance(nifty, pd.Series) else None
    divs = _from_price_files(B, "dividends")
    F = {
        "autocorrelation_periodogram": lambda: per_col(acf_period),
        "hilbert_dominant_cycle": lambda: per_col(tl.HT_DCPERIOD),
        "ehlers_mama": lambda: per_col(lambda x: tl.MAMA(x)[0]),
        "fisher_cycle_indicator": lambda: (lambda cyc: 0.5 * np.log((1 + cyc) / (1 - cyc)))(
            (2 * (c - c.rolling(10).min()) / (c.rolling(10).max() - c.rolling(10).min()).replace(0, np.nan) - 1).clip(-.999, .999)
            .ewm(span=3).mean().clip(-.999, .999)),
        "skew": lambda: r.rolling(60).skew(),
        "sample_entropy": lambda: per_col(sampen),
        "rolling_cointegration_residual": lambda: None if ln is None else lc.apply(
            lambda s: s - (s.rolling(120).cov(ln) / ln.rolling(120).var()) * ln - (s.rolling(120).mean() - (s.rolling(120).cov(ln) / ln.rolling(120).var()) * ln.rolling(120).mean())),
        "spread_zscore": lambda: None if ln is None else (lambda s: (s - s.rolling(60).mean()) / s.rolling(60).std())(lc.sub(ln, axis=0)),
        "dividend_event_proximity": lambda: _days_since(divs) if divs is not None else None,
        "days_to_dividend": lambda: (365 - _days_since(divs)).clip(lower=0) if divs is not None else None,   # yearly payers: estimate
        "corporate_action_flag": lambda: ((divs.fillna(0) > 0) | (_from_price_files(B, "splits").fillna(0) > 0)).astype(float),
        "benchmark_return": lambda: None if nifty is None else pd.DataFrame(np.repeat(nifty.pct_change().to_numpy()[:, None], c.shape[1], 1), index=c.index, columns=c.columns),
        "market_correlation": lambda: None if nifty is None else r.rolling(60).corr(nifty.pct_change()),
        "distance_from_prior_week_high": lambda: (c - _prior_week(B, "h")) / A,
        "distance_from_prior_week_low": lambda: (c - _prior_week(B, "l")) / A,
        "quarter_end_flag": lambda: pd.DataFrame(np.repeat((((c.index + pd.offsets.BDay(1)).quarter != c.index.quarter))[:, None], c.shape[1], 1), index=c.index, columns=c.columns),
        "sector_return": lambda: _sector_return(B),
        "swing_prominence_atr": lambda: (lambda P: (_df(B, P[2][:, :, 2]) - _df(B, np.fmax(P[0][:, :, 1], P[0][:, :, 2]))) / A)(pivots(B)),
        "order_block_size_atr": lambda: ((h.shift(1) - l.shift(1)) / A.shift(1)).where(((c - o) >= 1.5 * A) & (c.shift(1) < o.shift(1))).ffill(limit=40),
        "regime_high_vol_probability": lambda: (A / c).rolling(500, min_periods=100).rank(pct=True),
        "regime_mean_reversion_probability": lambda: 1 - ((c - c.shift(10)).abs() / c.diff().abs().rolling(10).sum()).rolling(60).mean(),
        "regime_trend_probability": lambda: ((c - c.shift(10)).abs() / c.diff().abs().rolling(10).sum()).rolling(60).mean(),
        "regime_liquidity_stress": lambda: (r.abs() / (c * v).replace(0, np.nan)).rolling(20).mean().rolling(500, min_periods=100).rank(pct=True),
        "turnover_ratio": lambda: v / _shares(B),
        "market_cap_bucket": lambda: (lambda m: (m > 5e9).astype(float) + (m > 2e10) + (m > 1e11) + 1)(c * _shares(B)).where((c * _shares(B)).notna()),
        "macro_event_flag": lambda: _macro_flag(B),
        "free_float_market_cap": lambda: c * _float_shares(B),
    }
    if fid not in F:
        raise KeyError(fid)
    return F[fid]()


def _days_since(event_amount):
    e = (event_amount.fillna(0) > 0)
    pos = pd.DataFrame(np.repeat(np.arange(len(e))[:, None], e.shape[1], 1), index=e.index, columns=e.columns).astype(float)
    last = pos.where(e).ffill()
    return (pos - last) * 365 / 252


def _prior_week(B, col):
    W, end = weekly(B)
    x = W[col]
    rows = x[end.values]
    return rows.shift(0).reindex(x.index).ffill().shift(1)


def _sector_return(B):
    """Equal-weight daily return of each stock's industry within the universe."""
    ind = B.get("industry") or {}
    c = B["c"]
    r = c.pct_change().where(B["member"])
    out = pd.DataFrame(np.nan, index=c.index, columns=c.columns)
    groups = pd.Series(ind).reindex(c.columns).dropna()
    for g, cols in groups.groupby(groups).groups.items():
        m = r[list(cols)].mean(axis=1)
        out[list(cols)] = np.repeat(m.to_numpy()[:, None], len(cols), 1)
    return out


def _from_price_files(B, col):
    """Dividends / splits columns from the stored Yahoo files (0 where unknown)."""
    key = f"_pf_{col}"
    if key in B:
        return B[key]
    from .data_prices import load
    c = B["c"]
    out = pd.DataFrame(0.0, index=c.index, columns=c.columns)
    for s in c.columns:
        try:
            df = load(s)
        except Exception:
            df = None
        if df is not None and col in df:
            out[s] = df[col].reindex(c.index).fillna(0.0)
    B[key] = out
    return out


def _shares(B):
    """Latest known share count per stock (from statement snapshots), as a constant row."""
    import json
    from .config import FUND
    c = B["c"]
    sh = {}
    for s in c.columns:
        f = FUND / f"{s}.json"
        if f.exists():
            try:
                ann = json.loads(f.read_text()).get("annual") or {}
                vals = [ann[k].get("shares") for k in sorted(ann) if ann[k].get("shares")]
                if vals:
                    sh[s] = float(vals[-1])
            except Exception:
                pass
    return pd.DataFrame(np.repeat(pd.Series(sh).reindex(c.columns).to_numpy()[None, :], len(c), 0),
                        index=c.index, columns=c.columns)


def _float_shares(B):
    """Free-float shares: Yahoo's floatShares when known, else total shares x (1 - insider/promoter holding)."""
    import json
    from .config import FUND
    c = B["c"]
    fl = {}
    for s in c.columns:
        f = FUND / f"{s}.json"
        if not f.exists():
            continue
        try:
            snap = json.loads(f.read_text())
        except Exception:
            continue
        if snap.get("float_shares"):
            fl[s] = float(snap["float_shares"])
        else:
            ann = snap.get("annual") or {}
            vals = [ann[k].get("shares") for k in sorted(ann) if ann[k].get("shares")]
            if vals and snap.get("insider_pct") is not None:
                fl[s] = float(vals[-1]) * (1 - float(snap["insider_pct"]))
    return pd.DataFrame(np.repeat(pd.Series(fl).reindex(c.columns).to_numpy()[None, :], len(c), 0),
                        index=c.index, columns=c.columns)


def _macro_flag(B):
    try:
        from .intel_events import calendar
        cal = calendar("2000-01-01")
        dates = set(pd.to_datetime(cal[cal["event"] != "Monthly F&O expiry"]["date"]).dt.normalize())
    except Exception:
        return None
    c = B["c"]
    m = np.array([d in dates for d in c.index])
    return pd.DataFrame(np.repeat(m[:, None], c.shape[1], 1), index=c.index, columns=c.columns)


FEATURES = ["autocorrelation_periodogram", "hilbert_dominant_cycle", "ehlers_mama", "fisher_cycle_indicator", "skew",
            "sample_entropy", "rolling_cointegration_residual", "spread_zscore", "dividend_event_proximity",
            "days_to_dividend", "corporate_action_flag", "benchmark_return", "market_correlation",
            "distance_from_prior_week_high", "distance_from_prior_week_low", "quarter_end_flag", "sector_return",
            "swing_prominence_atr", "order_block_size_atr", "regime_high_vol_probability",
            "regime_mean_reversion_probability", "regime_liquidity_stress", "turnover_ratio", "market_cap_bucket",
            "macro_event_flag", "free_float_market_cap"]
CHART_NOTES = {"ipo_base": "second-year base only: the universe admits stocks a year after listing",
               "gann_square_of_nine_level": "square-of-nine steps of 45 degrees from the last major low; very definition-sensitive"}
FEATURE_NOTES = {"days_to_dividend": "estimated from the last ex-date (+1 year); exact future ex-dates are not in free data",
                 "regime_high_vol_probability": "percentile rank score (0-1), not a calibrated probability",
                 "regime_mean_reversion_probability": "1 - efficiency ratio, rank-style score, not a calibrated probability",
                 "regime_liquidity_stress": "percentile rank of Amihud illiquidity, not a calibrated probability",
                 "turnover_ratio": "needs share count (from statements); total shares, not free float",
                 "market_cap_bucket": "total shares x price (free-float data is not free)",
                 "sector_return": "equal-weight industry return of the universe (when the engine provides it)",
                 "macro_event_flag": "Budget/election (+ hand-added RBI/Fed) dates from the event calendar",
                 "free_float_market_cap": "Yahoo floatShares (collected from now on), else shares x (1 - promoter holding)"}
