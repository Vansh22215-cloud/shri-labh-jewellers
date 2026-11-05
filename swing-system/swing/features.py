"""Indicator/feature calculators for the catalogue (ROADMAP M1 feature store groundwork).
TA-Lib canonical codes are computed with TA-Lib itself (exact parity); the non-TA-Lib items below are implemented
from their standard published formulas. All use only bars up to the current one."""
import numpy as np
import pandas as pd


def talib_feature(code, B, **params):
    """Run any TA-Lib function (by canonical code) per stock; returns the first output as a DataFrame."""
    from talib import abstract
    fn = abstract.Function(code)
    c = B["c"]
    out = pd.DataFrame(np.nan, index=c.index, columns=c.columns)
    for col in c.columns:
        d = pd.DataFrame({"open": B["o"][col], "high": B["h"][col], "low": B["l"][col], "close": c[col],
                          "volume": B["v"][col]}).dropna()
        if len(d) < 50:
            continue
        r = fn({k: d[k].values.astype(float) for k in d}, **params)
        r = r[0] if isinstance(r, list) else r
        out.loc[d.index, col] = r
    return out


def historical_volatility(B, n=20):
    return np.log(B["c"]).diff().rolling(n).std() * np.sqrt(252)


def parkinson_volatility(B, n=20):
    return np.sqrt((np.log(B["h"] / B["l"]) ** 2).rolling(n).mean() / (4 * np.log(2)) * 252)


def garman_klass_volatility(B, n=20):
    hl = 0.5 * np.log(B["h"] / B["l"]) ** 2
    co = (2 * np.log(2) - 1) * np.log(B["c"] / B["o"]) ** 2
    return np.sqrt((hl - co).rolling(n).mean() * 252)


def yang_zhang_volatility(B, n=20):
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]
    on = np.log(o / c.shift(1))
    oc = np.log(c / o)
    rs = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    return np.sqrt((on.rolling(n).var() + k * oc.rolling(n).var() + (1 - k) * rs.rolling(n).mean()) * 252)


def atr_percentile(B, n=250):
    ap = B["atr"] / B["c"]
    return ap.rolling(n, min_periods=100).rank(pct=True)


def pivot_points_classic(B):
    """Next-day floor pivots from the previous day's high/low/close (known before the next session)."""
    h, l, c = B["h"], B["l"], B["c"]
    pp = (h + l + c) / 3
    return {"pp": pp, "r1": 2 * pp - l, "s1": 2 * pp - h, "r2": pp + (h - l), "s2": pp - (h - l)}


def pivot_points_fibonacci(B):
    h, l, c = B["h"], B["l"], B["c"]
    pp, r = (h + l + c) / 3, (h - l)
    return {"pp": pp, "r1": pp + 0.382 * r, "r2": pp + 0.618 * r, "s1": pp - 0.382 * r, "s2": pp - 0.618 * r}


def pivot_points_camarilla(B):
    h, l, c = B["h"], B["l"], B["c"]
    r = h - l
    return {"r3": c + r * 1.1 / 4, "s3": c - r * 1.1 / 4, "r4": c + r * 1.1 / 2, "s4": c - r * 1.1 / 2}


def elder_impulse(B):
    """+1 green (EMA13 rising and MACD histogram rising), -1 red, 0 blue."""
    from .patterns import _ema
    c = B["c"]
    e13 = _ema(c, 13)
    macd = _ema(c, 12) - _ema(c, 26)
    hist = macd - macd.ewm(span=9, adjust=False).mean()
    up, dn = (e13 > e13.shift(1)) & (hist > hist.shift(1)), (e13 < e13.shift(1)) & (hist < hist.shift(1))
    return up.astype(int) - dn.astype(int)


def market_structure(B):
    """+1 higher-high & higher-low structure, -1 lower-high & lower-low, 0 mixed (from CONFIRMED pivots)."""
    from .catalog import pivots
    PLv, _, PHv, _ = pivots(B)
    hh, hl = PHv[:, :, -1] > PHv[:, :, -2], PLv[:, :, -1] > PLv[:, :, -2]
    lh, ll = PHv[:, :, -1] < PHv[:, :, -2], PLv[:, :, -1] < PLv[:, :, -2]
    v = np.where(hh & hl, 1, np.where(lh & ll, -1, 0))
    return pd.DataFrame(v, index=B["c"].index, columns=B["c"].columns)


def relative_strength_line(B, nifty):
    return B["c"].div(nifty.reindex(B["c"].index).ffill(), axis=0)


def anchored_vwap_daily(B, anchor_days=50):
    """Approximation on DAILY bars: volume-weighted typical price since `anchor_days` ago (true AVWAP needs intraday)."""
    tp = (B["h"] + B["l"] + B["c"]) / 3
    return (tp * B["v"]).rolling(anchor_days).sum() / B["v"].rolling(anchor_days).sum()


NON_TALIB_IMPL = {
    "historical_volatility": "swing/features.py:historical_volatility",
    "parkinson_volatility": "swing/features.py:parkinson_volatility",
    "garman_klass_volatility": "swing/features.py:garman_klass_volatility",
    "yang_zhang_volatility": "swing/features.py:yang_zhang_volatility",
    "atr_percentile": "swing/features.py:atr_percentile",
    "pivot_points_classic": "swing/features.py:pivot_points_classic",
    "pivot_points_fibonacci": "swing/features.py:pivot_points_fibonacci",
    "pivot_points_camarilla": "swing/features.py:pivot_points_camarilla",
    "elder_impulse_system": "swing/features.py:elder_impulse",
    "market_structure_hh_hl": "swing/features.py:market_structure (confirmed pivots)",
    "relative_strength_line": "swing/features.py:relative_strength_line",
    "anchored_vwap": "swing/features.py:anchored_vwap_daily (daily-bar approximation)",
    "heikin_ashi_trend": "swing/patterns.py:heikin_ashi_turn",
    "supertrend_multi": "swing/patterns.py:_supertrend_up (single 10/3 setting; multi-setting not yet)",
    "volatility_squeeze": "swing/families.py:squeeze (Bollinger width percentile)",
}
BLOCKED = {"volume_profile": "needs intraday volume-at-price data",
           "cumulative_volume_delta": "needs tick/aggressor-side data (OHLCV cannot give true delta)",
           "volume_delta": "needs tick/aggressor-side data (OHLCV cannot give true delta)",
           "vwap_deviation_bands": "needs intraday bars (session VWAP)"}


# ----------------------------------------------------------------------------- quant research features (library v2)
def quant_feature(fid, B):
    """Daily-bar versions of the v2 catalogue's OHLCV quant features (all use completed bars only)."""
    c, h, l, o, v, A = B["c"], B["h"], B["l"], B["o"], B["v"], B["atr"]
    r = c.pct_change()
    rng = (h - l).replace(0, np.nan)
    ema = lambda n: c.ewm(span=n, adjust=False).mean()
    f = {
        "log_return": lambda: np.log(c / c.shift(1)),
        "simple_return": lambda: r,
        "overnight_return": lambda: o / c.shift(1) - 1,
        "intraday_return": lambda: c / o - 1,
        "close_to_close_return_5": lambda: c / c.shift(5) - 1,
        "close_to_close_return_20": lambda: c / c.shift(20) - 1,
        "close_to_close_return_60": lambda: c / c.shift(60) - 1,
        "rolling_return_volatility": lambda: r.rolling(20).std() * np.sqrt(252),
        "downside_return_volatility": lambda: r.where(r < 0, 0).rolling(20).std() * np.sqrt(252),
        "upside_return_volatility": lambda: r.where(r > 0, 0).rolling(20).std() * np.sqrt(252),
        "return_skewness": lambda: r.rolling(60).skew(),
        "return_excess_kurtosis": lambda: r.rolling(60).kurt(),
        "gap_size_atr": lambda: (o - c.shift(1)) / A.shift(1),
        "true_range_atr": lambda: pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()]).groupby(level=0).max() / A.shift(1),
        "bar_range_percent": lambda: (h - l) / c * 100,
        "body_atr": lambda: (c - o).abs() / A,
        "upper_wick_atr": lambda: (h - np.maximum(o, c)) / A,
        "lower_wick_atr": lambda: (np.minimum(o, c) - l) / A,
        "close_location_value": lambda: ((c - l) - (h - c)) / rng,
        "bar_overlap_ratio": lambda: (np.minimum(h, h.shift(1)) - np.maximum(l, l.shift(1))).clip(lower=0) / rng,
        "inside_bar_flag": lambda: ((h < h.shift(1)) & (l > l.shift(1))).astype(float),
        "outside_bar_flag": lambda: ((h > h.shift(1)) & (l < l.shift(1))).astype(float),
        "consecutive_up_bars": lambda: _streak(c > c.shift(1)),
        "consecutive_down_bars": lambda: _streak(c < c.shift(1)),
        "close_above_prior_high": lambda: (c > h.shift(1)).astype(float),
        "close_below_prior_low": lambda: (c < l.shift(1)).astype(float),
        "distance_from_rolling_high": lambda: c / h.rolling(252, min_periods=60).max() - 1,
        "distance_from_rolling_low": lambda: c / l.rolling(252, min_periods=60).min() - 1,
        "distance_from_prior_day_high": lambda: (c - h.shift(1)) / A,
        "distance_from_prior_day_low": lambda: (c - l.shift(1)) / A,
        "relative_volume_20": lambda: v / v.shift(1).rolling(20).mean(),
        "relative_volume_median_20": lambda: v / v.shift(1).rolling(20).median(),
        "volume_zscore_60": lambda: (v - v.rolling(60).mean()) / v.rolling(60).std(),
        "dollar_volume": lambda: c * v,
        "amihud_20": lambda: (r.abs() / (c * v).replace(0, np.nan)).rolling(20).mean() * 1e7,
        "weekday": lambda: pd.DataFrame(np.repeat(c.index.weekday.values[:, None], c.shape[1], 1), index=c.index, columns=c.columns),
        "month": lambda: pd.DataFrame(np.repeat(c.index.month.values[:, None], c.shape[1], 1), index=c.index, columns=c.columns),
        "benchmark_return": lambda: B["nifty_ret"] if "nifty_ret" in B else None,
        "market_return_dispersion": lambda: pd.DataFrame(np.repeat(r.std(axis=1).values[:, None], c.shape[1], 1), index=c.index, columns=c.columns),
        "breadth_above_20dma": lambda: _breadth(c > c.rolling(20).mean(), B),
        "breadth_above_50dma": lambda: _breadth(c > c.rolling(50).mean(), B),
        "breadth_above_200dma": lambda: _breadth(c > c.rolling(200).mean(), B),
        "new_52w_high_count": lambda: _breadth(h >= h.rolling(252, min_periods=200).max(), B, count=True),
        "new_52w_low_count": lambda: _breadth(l <= l.rolling(252, min_periods=200).min(), B, count=True),
        "sector_strength_rank": lambda: B.get("sector_rank"),
        "stock_strength_rank": lambda: B.get("rs_rank"),
        "trend_slope_atr": lambda: (ema(20) - ema(20).shift(10)) / 10 / A,
        "distance_from_ema20_atr": lambda: (c - ema(20)) / A,
        "distance_from_ema50_atr": lambda: (c - ema(50)) / A,
        "distance_from_ema200_atr": lambda: (c - ema(200)) / A,
        "multi_timeframe_trend_score": lambda: (c > ema(20)).astype(float) + (c > ema(50)) + (c > ema(200)),
        "multi_timeframe_momentum_score": lambda: np.sign(c / c.shift(5) - 1) + np.sign(c / c.shift(20) - 1) + np.sign(c / c.shift(60) - 1),
        "earnings_event_flag": lambda: B.get("results_day"),
        "fvg_size_atr": lambda: ((l - h.shift(2)).clip(lower=0)) / A,
    }
    if fid not in f:
        raise KeyError(fid)
    return f[fid]()


def _streak(cond):
    cond = cond.fillna(False).astype(int)
    grp = (cond == 0).cumsum()
    return cond.groupby(grp).cumsum() if isinstance(cond, pd.Series) else cond.apply(lambda s: s.groupby((s == 0).cumsum()).cumsum())


def _breadth(cond, B, count=False):
    m = B["member"]
    x = (cond & m).sum(axis=1)
    if not count:
        x = x / m.sum(axis=1).replace(0, np.nan)
    return pd.DataFrame(np.repeat(x.values[:, None], cond.shape[1], 1), index=cond.index, columns=cond.columns)


QUANT_IMPL = ["log_return", "simple_return", "overnight_return", "intraday_return", "close_to_close_return_5",
              "close_to_close_return_20", "close_to_close_return_60", "rolling_return_volatility",
              "downside_return_volatility", "upside_return_volatility", "return_skewness", "return_excess_kurtosis",
              "gap_size_atr", "true_range_atr", "bar_range_percent", "body_atr", "upper_wick_atr", "lower_wick_atr",
              "close_location_value", "bar_overlap_ratio", "inside_bar_flag", "outside_bar_flag",
              "consecutive_up_bars", "consecutive_down_bars", "close_above_prior_high", "close_below_prior_low",
              "distance_from_rolling_high", "distance_from_rolling_low", "distance_from_prior_day_high",
              "distance_from_prior_day_low", "relative_volume_20", "relative_volume_median_20", "volume_zscore_60",
              "dollar_volume", "amihud_20", "weekday", "month", "market_return_dispersion", "breadth_above_20dma",
              "breadth_above_50dma", "breadth_above_200dma", "new_52w_high_count", "new_52w_low_count",
              "sector_strength_rank", "stock_strength_rank", "trend_slope_atr", "distance_from_ema20_atr",
              "distance_from_ema50_atr", "distance_from_ema200_atr", "multi_timeframe_trend_score",
              "multi_timeframe_momentum_score", "earnings_event_flag", "fvg_size_atr"]
QUANT_ELSEWHERE = {"expiry_week_flag": "swing/intel_events.py (monthly F&O expiry calendar)",
                   "distance_to_earnings": "swing/fundamentals.py:next_results_date",
                   "distance_to_expiry": "swing/intel_events.py", "put_call_oi_ratio": "swing/intel_fno.py (index PCR)",
                   "open_interest_delta": "swing/intel_fno.py / intel_positioning.py (participant OI)",
                   "estimated_slippage_bps": "swing/backtest cost model (fixed 15 bps)",
                   "regime_trend_probability": "swing/families.py regime filter (NIFTY trend, rule-based not a probability)"}
QUANT_BLOCKED_CATS = {"microstructure": "needs order-book / tick data (not available free)",
                      "profile_location": "needs intraday volume-at-price data",
                      "execution": "needs live quotes / spreads", "options": "needs option-chain history (IV)",
                      "derivatives": "needs futures/basis history"}


# ----------------------------------------------------------------------------- v2 indicators without a TA-Lib code
def _roll_apply(df, n, fn):
    return df.rolling(n, min_periods=n).apply(fn, raw=True)


def _wma(x, n):
    w = np.arange(1, n + 1, dtype=float)
    return _roll_apply(x, n, lambda a: (a * w).sum() / w.sum())


def _rsi(x, n=14):
    d = x.diff()
    up, dn = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(), (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def indicator_v2(iid, B):
    """Daily implementations of the v2 indicators that have no TA-Lib function. Completed bars only."""
    c, h, l, o, v, A = B["c"], B["h"], B["l"], B["o"], B["v"], B["atr"]
    r = c.pct_change()
    lr = np.log(c / c.shift(1))
    rng = (h - l).replace(0, np.nan)
    ema = lambda x, n: x.ewm(span=n, adjust=False).mean()
    sma = lambda x, n: x.rolling(n).mean()
    mfm = ((c - l) - (h - c)) / rng
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()]).groupby(level=0).max()
    bench = B.get("nifty")
    br = bench.pct_change() if isinstance(bench, pd.Series) else None
    def per_col_bench(fn):
        if br is None:
            return None
        return c.apply(lambda s: fn(s.pct_change(), br))
    def chop(n=14):
        return 100 * np.log10(tr.rolling(n).sum() / (h.rolling(n).max() - l.rolling(n).min())) / np.log10(n)
    def er(n=10):
        return (c - c.shift(n)).abs() / c.diff().abs().rolling(n).sum()
    def slope(n=20):
        x = np.arange(n, dtype=float); xm = x - x.mean()
        return _roll_apply(c, n, lambda a: (xm * (a - a.mean())).sum() / (xm ** 2).sum())
    def r2(n=20):
        x = np.arange(n, dtype=float)
        return _roll_apply(c, n, lambda a: np.corrcoef(x, a)[0, 1] ** 2)
    def vpt():
        return (r * v).cumsum()
    def nvi(neg=True):
        cond = (v < v.shift(1)) if neg else (v > v.shift(1))
        return (1 + r.where(cond, 0).fillna(0)).cumprod() * 1000
    def rvi(n=10):
        num = ((c - o) + 2 * (c.shift(1) - o.shift(1)) + 2 * (c.shift(2) - o.shift(2)) + (c.shift(3) - o.shift(3))) / 6
        den = ((h - l) + 2 * (h.shift(1) - l.shift(1)) + 2 * (h.shift(2) - l.shift(2)) + (h.shift(3) - l.shift(3))) / 6
        return num.rolling(n).sum() / den.rolling(n).sum()
    def vortex(n=14):
        vp = (h - l.shift(1)).abs().rolling(n).sum() / tr.rolling(n).sum()
        vm = (l - h.shift(1)).abs().rolling(n).sum() / tr.rolling(n).sum()
        return vp - vm
    def stc():
        m = ema(c, 23) - ema(c, 50)
        k = 100 * (m - m.rolling(10).min()) / (m.rolling(10).max() - m.rolling(10).min()).replace(0, np.nan)
        d = ema(k, 3)
        k2 = 100 * (d - d.rolling(10).min()) / (d.rolling(10).max() - d.rolling(10).min()).replace(0, np.nan)
        return ema(k2, 3)
    def fisher(n=10):
        mid = (h + l) / 2
        x = 2 * ((mid - mid.rolling(n).min()) / (mid.rolling(n).max() - mid.rolling(n).min()).replace(0, np.nan) - 0.5)
        x = ema(x.clip(-0.999, 0.999), 5).clip(-0.999, 0.999)
        return 0.5 * np.log((1 + x) / (1 - x))
    def connors():
        streak = np.sign(c.diff()).fillna(0)
        st = streak.copy()
        sv = st.to_numpy(copy=True); s0 = streak.to_numpy()
        for t in range(1, len(sv)):
            sv[t] = np.where(s0[t] == 0, 0, np.where(np.sign(sv[t - 1]) == s0[t], sv[t - 1] + s0[t], s0[t]))
        st = pd.DataFrame(sv, index=c.index, columns=c.columns)
        pr = r.rolling(100).rank(pct=True) * 100
        return (_rsi(c, 3) + _rsi(st, 2) + pr) / 3
    def mcginley(n=14):
        cv = c.to_numpy(); md = np.full_like(cv, np.nan)
        md[0] = cv[0]
        for t in range(1, len(cv)):
            prev = np.where(np.isnan(md[t - 1]), cv[t], md[t - 1])
            md[t] = prev + (cv[t] - prev) / (n * (cv[t] / prev) ** 4)
        return pd.DataFrame(md, index=c.index, columns=c.columns)
    def hurst(n=100):
        def hh(a):
            lags = range(2, 20)
            tau = [np.std(a[lag:] - a[:-lag]) for lag in lags]
            return np.polyfit(np.log(list(lags)), np.log(np.maximum(tau, 1e-12)), 1)[0]
        return _roll_apply(np.log(c), n, hh)
    def mdd(n=252):
        return c / c.rolling(n, min_periods=20).max() - 1
    def ulcer(n=14):
        dd = 100 * (c / c.rolling(n).max() - 1)
        return np.sqrt((dd ** 2).rolling(n).mean())
    def zz(k=3.0):          # last confirmed ATR zigzag direction (+1 up leg, -1 down leg); a pivot is known only once price
        cv, av = c.to_numpy(), A.to_numpy()       # has moved k ATR away from it
        out = np.full_like(cv, np.nan)
        d = np.zeros(cv.shape[1]); ext = cv[0].copy()
        for t in range(1, len(cv)):
            x, a = cv[t], av[t]
            up_new = (d >= 0) & (x > ext); dn_new = (d <= 0) & (x < ext)
            ext = np.where(up_new | dn_new, x, ext)
            flip_dn = (d >= 0) & (x < ext - k * a); flip_up = (d <= 0) & (x > ext + k * a)
            d = np.where(flip_dn, -1, np.where(flip_up, 1, d)); ext = np.where(flip_dn | flip_up, x, ext)
            out[t] = d
        return pd.DataFrame(out, index=c.index, columns=c.columns)
    def divergence(osc):    # bullish divergence: price lower confirmed low, oscillator higher at those lows
        from .catalog import pivots
        PLv, PLi, _, _ = pivots(B)
        T, N = c.shape
        ov = osc.to_numpy()
        i2, i3 = PLi[:, :, 1], PLi[:, :, 2]
        o2 = np.full((T, N), np.nan); o3 = np.full((T, N), np.nan)
        for j in range(N):
            ok2, ok3 = ~np.isnan(i2[:, j]), ~np.isnan(i3[:, j])
            o2[ok2, j] = ov[i2[ok2, j].astype(int), j]; o3[ok3, j] = ov[i3[ok3, j].astype(int), j]
        return pd.DataFrame(((PLv[:, :, 2] < PLv[:, :, 1]) & (o3 > o2)).astype(float), index=c.index, columns=c.columns)
    macd = ema(c, 12) - ema(c, 26)
    F = {
        "amihud_illiquidity": lambda: (r.abs() / (c * v).replace(0, np.nan)).rolling(20).mean() * 1e7,
        "aroon_oscillator": lambda: 100 * (_roll_apply(h, 26, np.argmax) - _roll_apply(l, 26, np.argmin)) / 25,
        "bollinger_bandwidth_percentile": lambda: ((4 * c.rolling(20).std()) / sma(c, 20)).rolling(252, min_periods=60).rank(pct=True),
        "buying_pressure": lambda: (c - np.minimum(l, c.shift(1))) / rng,
        "selling_pressure": lambda: (np.maximum(h, c.shift(1)) - c) / rng,
        "candle_body_pct": lambda: (c - o).abs() / rng,
        "upper_shadow_pct": lambda: (h - np.maximum(o, c)) / rng,
        "lower_shadow_pct": lambda: (np.minimum(o, c) - l) / rng,
        "close_location_in_range": lambda: (c - l) / rng,
        "close_location_value": lambda: mfm,
        "ce": lambda: h.rolling(22).max() - 3 * A,
        "chaikin_money_flow": lambda: (mfm * v).rolling(20).sum() / v.rolling(20).sum(),
        "chaikin_oscillator": lambda: ema((mfm * v).cumsum(), 3) - ema((mfm * v).cumsum(), 10),
        "chande_momentum_oscillator": lambda: 100 * (c.diff().clip(lower=0).rolling(14).sum() - (-c.diff().clip(upper=0)).rolling(14).sum())
                                              / c.diff().abs().rolling(14).sum(),
        "choppiness_index": chop,
        "choppiness_adaptive_threshold": lambda: chop() - chop().rolling(252, min_periods=60).median(),
        "connors_rsi": connors,
        "coppock_curve": lambda: _wma((c / c.shift(14) - 1) + (c / c.shift(11) - 1), 10) * 100,
        "cusum_change_detector": lambda: ((r - r.rolling(60).mean()) / r.rolling(60).std()).clip(-5, 5).rolling(20).sum(),
        "day_of_week_effect": lambda: pd.DataFrame(np.repeat(c.index.weekday.values[:, None], c.shape[1], 1), index=c.index, columns=c.columns),
        "month_end_effect": lambda: pd.DataFrame(np.repeat(((c.index + pd.offsets.BDay(1)).month != c.index.month)[:, None],
                                                           c.shape[1], 1), index=c.index, columns=c.columns),   # calendar known ahead
        "demand_index": lambda: ema(r * v, 10) / ema(v, 10),
        "detrended_price_oscillator": lambda: c.shift(11) - sma(c, 20),     # shifted-close form (no centred average)
        "donchian_width": lambda: (h.rolling(20).max() - l.rolling(20).min()) / c,
        "ease_of_movement": lambda: sma(((h + l) / 2).diff() / (v / 1e6 / rng), 14),
        "efficiency_ratio": er,
        "kama_efficiency_ratio": er,
        "elder_force_index": lambda: ema(c.diff() * v, 13),
        "epma": lambda: c.rolling(20).apply(lambda a: np.polyval(np.polyfit(np.arange(20), a, 1), 20), raw=True),
        "lsma": lambda: c.rolling(25).apply(lambda a: np.polyval(np.polyfit(np.arange(25), a, 1), 24), raw=True),
        "ewma_volatility": lambda: np.sqrt((lr ** 2).ewm(alpha=0.06, adjust=False).mean() * 252),
        "fisher_transform": fisher,
        "gap_to_prior_range": lambda: (o - c.shift(1)) / (h.shift(1) - l.shift(1)).replace(0, np.nan),
        "overnight_gap_percent": lambda: (o / c.shift(1) - 1) * 100,
        "hurst_exponent": hurst,
        "intraday_intensity_index": lambda: (2 * c - h - l) / rng * v,
        "inverse_fisher_rsi": lambda: (np.exp(2 * 0.1 * (_rsi(c) - 50)) - 1) / (np.exp(2 * 0.1 * (_rsi(c) - 50)) + 1),
        "keltner_channel_width": lambda: 4 * A / ema(c, 20),
        "ma_ribbon_width": lambda: (pd.concat([ema(c, n) for n in (10, 20, 30, 40, 50, 60)]).groupby(level=0).max()
                                    - pd.concat([ema(c, n) for n in (10, 20, 30, 40, 50, 60)]).groupby(level=0).min()) / c,
        "ma_spread": lambda: (sma(c, 50) - sma(c, 200)) / sma(c, 200),
        "price_ma_distance": lambda: (c - sma(c, 50)) / A,
        "macd_histogram_slope": lambda: (macd - ema(macd, 9)).diff(),
        "macd_normalised": lambda: macd / A,
        "macdv": lambda: macd / A * 100,
        "macd_divergence": lambda: divergence(macd),
        "rsi_divergence": lambda: divergence(_rsi(c)),
        "rsi_divergence_score": lambda: divergence(_rsi(c)),
        "stoch_divergence": lambda: divergence(100 * (c - l.rolling(14).min()) / (h.rolling(14).max() - l.rolling(14).min()).replace(0, np.nan)),
        "mass_index": lambda: (ema(h - l, 9) / ema(ema(h - l, 9), 9)).rolling(25).sum(),
        "mcginley_dynamic": mcginley,
        "negative_volume_index": lambda: nvi(True),
        "positive_volume_index": lambda: nvi(False),
        "relative_range": lambda: (h - l) / A,
        "relative_strength_rank": lambda: B.get("rs_rank"),
        "relative_strength_vs_benchmark": lambda: c.div(bench, axis=0) if isinstance(bench, pd.Series) else None,
        "sector_relative_strength": lambda: B.get("sector_rank"),
        "relative_vigor_index": rvi,
        "smoothed_rvi": lambda: _wma(rvi(), 4),
        "relative_volatility_index": lambda: _rsi(c.rolling(10).std(), 14),
        "robust_mad_zscore": lambda: (c - c.rolling(60).median()) / (1.4826 * (c - c.rolling(60).median()).abs().rolling(60).median()),
        "rolling_zscore": lambda: (c - sma(c, 20)) / c.rolling(20).std(),
        "rolling_percentile_rank": lambda: c.rolling(252, min_periods=60).rank(pct=True),
        "rogers_satchell_volatility": lambda: np.sqrt((np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)).rolling(20).mean() * 252),
        "realised_volatility": lambda: lr.rolling(20).std() * np.sqrt(252),
        "roll_spread_estimator": lambda: 2 * np.sqrt((-(c.diff().rolling(20).cov(c.diff().shift(1)))).clip(lower=0)),
        "rolling_autocorrelation": lambda: r.rolling(60).corr(r.shift(1)),
        "rolling_beta": lambda: per_col_bench(lambda s, b: s.rolling(120).cov(b) / b.rolling(120).var()),
        "rolling_correlation": lambda: per_col_bench(lambda s, b: s.rolling(60).corr(b)),
        "rolling_calmar": lambda: (c / c.shift(252) - 1) / (-mdd(252)).replace(0, np.nan),
        "rolling_drawdown": lambda: mdd(252),
        "rolling_max_drawdown": lambda: mdd(252).rolling(252, min_periods=20).min(),
        "rolling_expected_shortfall": lambda: _roll_apply(r, 250, lambda a: a[a <= np.quantile(a, 0.05)].mean()),
        "rolling_var": lambda: r.rolling(250).quantile(0.05),
        "rolling_kurtosis": lambda: r.rolling(60).kurt(),
        "rolling_skewness": lambda: r.rolling(60).skew(),
        "rolling_linear_regression_slope": slope,
        "rolling_linear_regression_r2": r2,
        "rolling_omega": lambda: r.clip(lower=0).rolling(120).sum() / (-r.clip(upper=0)).rolling(120).sum(),
        "rolling_sharpe": lambda: r.rolling(120).mean() / r.rolling(120).std() * np.sqrt(252),
        "rolling_sortino": lambda: r.rolling(120).mean() / r.where(r < 0, 0).rolling(120).std() * np.sqrt(252),
        "rolling_tail_ratio": lambda: r.rolling(250).quantile(0.95) / (-r.rolling(250).quantile(0.05)),
        "rolling_vwap": lambda: ((h + l + c) / 3 * v).rolling(20).sum() / v.rolling(20).sum(),
        "rsi_of_ema": lambda: _rsi(ema(c, 10)),
        "schaff_trend_cycle": stc,
        "smma": lambda: c.ewm(alpha=1 / 14, adjust=False).mean(),
        "swma": lambda: _wma(c, 4),
        "t3_average": lambda: (lambda e1: (lambda e2: (lambda e3: (lambda e4: (lambda e5: (lambda e6:
                               -0.343 * e6 + 1.785 * e5 - 3.304 * e4 + 2.519 * e3)(ema(e5, 5)))(ema(e4, 5)))(ema(e3, 5)))(ema(e2, 5)))(ema(e1, 5)))(ema(c, 5)),
        "jma": lambda: ema(ema(c, 7), 3),                       # simplified (true JMA is proprietary)
        "tema_slope": lambda: (lambda e1: (3 * e1 - 3 * ema(e1, 20) + ema(ema(e1, 20), 20)).diff())(ema(c, 20)),
        "trend_direction_force_index": lambda: (lambda m: (m - ema(m, 13)) * (m.diff() - ema(m, 13).diff()) ** 3)(ema(c, 13)),
        "trend_intensity_index": lambda: 100 * (c > sma(c, 60)).rolling(30).sum() / 30,
        "ulcer_index": ulcer,
        "ulcer_performance_index": lambda: (c / c.shift(252) - 1) * 100 / ulcer(252).replace(0, np.nan),
        "ultimate_oscillator": lambda: (lambda bp, trr: 100 * (4 * bp.rolling(7).sum() / trr.rolling(7).sum() + 2 * bp.rolling(14).sum()
                                         / trr.rolling(14).sum() + bp.rolling(28).sum() / trr.rolling(28).sum()) / 7)(
                                         c - np.minimum(l, c.shift(1)), tr),
        "vertical_horizontal_filter": lambda: (c.rolling(28).max() - c.rolling(28).min()) / c.diff().abs().rolling(28).sum(),
        "volatility_of_volatility": lambda: (A / c).rolling(60).std(),
        "volume_price_trend": vpt,
        "volume_weighted_macd": lambda: (c * v).ewm(span=12).mean() / v.ewm(span=12).mean() - (c * v).ewm(span=26).mean() / v.ewm(span=26).mean(),
        "volume_zone_oscillator": lambda: 100 * ema(np.sign(c.diff()) * v, 14) / ema(v, 14),
        "vortex_indicator": vortex,
        "zigzag_atr": zz,
        "swing_distance_atr": lambda: (c - B["l"].rolling(20).min()) / A,
        "bos_choch": lambda: None,   # implemented as events in catalog.ms_signal
        "market_breadth_percent_above_ma": lambda: quant_feature("breadth_above_50dma", B),
        "market_breadth_new_high_new_low": lambda: quant_feature("new_52w_high_count", B) - quant_feature("new_52w_low_count", B),
        "earnings_proximity": lambda: B.get("results_day"),
        "egarch_volatility": lambda: np.sqrt((lr ** 2).ewm(alpha=0.06, adjust=False).mean() * 252),   # EWMA stand-in
        "garch_11_volatility": lambda: np.sqrt((lr ** 2).ewm(alpha=0.06, adjust=False).mean() * 252),  # EWMA stand-in
        "realised_bipower_variation": lambda: (np.pi / 2 * (lr.abs() * lr.abs().shift(1)).rolling(20).mean() * 252) ** 0.5,
        "permutation_entropy": lambda: _roll_apply(c, 60, lambda a: _perm_entropy(a)),
        "market_meanness_index": lambda: _roll_apply(c, 50, lambda a: 100 * np.mean(((a[2:] > np.median(a)) & (a[1:-1] > a[2:]))
                                                                                 | ((a[2:] < np.median(a)) & (a[1:-1] < a[2:])))),
        "detrended_fluctuation": lambda: None,
    }
    if iid not in F:
        raise KeyError(iid)
    return F[iid]()


def _perm_entropy(a, m=3):
    from math import factorial
    pats = {}
    for i in range(len(a) - m + 1):
        k = tuple(np.argsort(a[i:i + m]))
        pats[k] = pats.get(k, 0) + 1
    p = np.array(list(pats.values()), dtype=float); p /= p.sum()
    return -(p * np.log(p)).sum() / np.log(factorial(m))


INDICATOR_V2_APPROX = {"egarch_volatility": "EWMA stand-in (no fitted GARCH yet)",
                       "garch_11_volatility": "EWMA stand-in (no fitted GARCH yet)",
                       "jma": "simplified (true Jurik MA is proprietary)",
                       "detrended_price_oscillator": "shifted-close form, no centred average (avoids look-ahead)",
                       "kama_efficiency_ratio": "Kaufman efficiency ratio (same as efficiency_ratio)"}

INDICATOR_V2 = ['amihud_illiquidity',
                'aroon_oscillator',
                'bollinger_bandwidth_percentile',
                'buying_pressure',
                'selling_pressure',
                'candle_body_pct',
                'upper_shadow_pct',
                'lower_shadow_pct',
                'close_location_in_range',
                'close_location_value',
                'ce',
                'chaikin_money_flow',
                'chaikin_oscillator',
                'chande_momentum_oscillator',
                'choppiness_index',
                'choppiness_adaptive_threshold',
                'connors_rsi',
                'coppock_curve',
                'cusum_change_detector',
                'day_of_week_effect',
                'month_end_effect',
                'demand_index',
                'detrended_price_oscillator',
                'donchian_width',
                'ease_of_movement',
                'efficiency_ratio',
                'kama_efficiency_ratio',
                'elder_force_index',
                'epma',
                'lsma',
                'ewma_volatility',
                'fisher_transform',
                'gap_to_prior_range',
                'overnight_gap_percent',
                'hurst_exponent',
                'intraday_intensity_index',
                'inverse_fisher_rsi',
                'keltner_channel_width',
                'ma_ribbon_width',
                'ma_spread',
                'price_ma_distance',
                'macd_histogram_slope',
                'macd_normalised',
                'macdv',
                'macd_divergence',
                'rsi_divergence',
                'rsi_divergence_score',
                'stoch_divergence',
                'mass_index',
                'mcginley_dynamic',
                'negative_volume_index',
                'positive_volume_index',
                'relative_range',
                'relative_strength_rank',
                'relative_strength_vs_benchmark',
                'sector_relative_strength',
                'relative_vigor_index',
                'smoothed_rvi',
                'relative_volatility_index',
                'robust_mad_zscore',
                'rolling_zscore',
                'rolling_percentile_rank',
                'rogers_satchell_volatility',
                'realised_volatility',
                'roll_spread_estimator',
                'rolling_autocorrelation',
                'rolling_beta',
                'rolling_correlation',
                'rolling_calmar',
                'rolling_drawdown',
                'rolling_max_drawdown',
                'rolling_expected_shortfall',
                'rolling_var',
                'rolling_kurtosis',
                'rolling_skewness',
                'rolling_linear_regression_slope',
                'rolling_linear_regression_r2',
                'rolling_omega',
                'rolling_sharpe',
                'rolling_sortino',
                'rolling_tail_ratio',
                'rolling_vwap',
                'rsi_of_ema',
                'schaff_trend_cycle',
                'smma',
                'swma',
                't3_average',
                'jma',
                'tema_slope',
                'trend_direction_force_index',
                'trend_intensity_index',
                'ulcer_index',
                'ulcer_performance_index',
                'ultimate_oscillator',
                'vertical_horizontal_filter',
                'volatility_of_volatility',
                'volume_price_trend',
                'volume_weighted_macd',
                'volume_zone_oscillator',
                'vortex_indicator',
                'zigzag_atr',
                'swing_distance_atr',
                'market_breadth_percent_above_ma',
                'market_breadth_new_high_new_low',
                'earnings_proximity',
                'egarch_volatility',
                'garch_11_volatility',
                'realised_bipower_variation',
                'permutation_entropy',
                'market_meanness_index']
