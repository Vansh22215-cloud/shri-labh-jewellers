"""Intraday / market-profile items of the owner's library, computed from the 5-minute bars the lifelong store keeps
(swing/archive.py: data/archive/m5). Yahoo only serves ~60 days of 5-minute data, so this history did not exist
before; it now grows every trading day.

Per stock and day: VWAP, volume profile (POC, value area high/low at 70%, high/low-volume nodes), opening range
(first 15 min), initial balance (first 60 min), 30-minute TPO single prints, open-drive / open-test-drive, poor and
excess lows, lunch compression, double distribution, neutral day. Daily entry rules use only that day's completed
session (known at the close) and enter the next day.

READINESS: these entry rules join the idea factory automatically once MIN_DAYS of 5-minute history are stored
(a backtest on a few weeks would be meaningless). Until then they are 'implemented - collecting data'.
Rule version cat-v3.
"""
import numpy as np
import pandas as pd

MIN_DAYS = 250
SESSION_START = 9 * 60 + 15
NBINS = 24


def history_days():
    from .archive import days
    return len(days("m5"))


def ready():
    return history_days() >= MIN_DAYS


def day_profile(g):
    """g: one stock's 5-minute bars for one session (columns ts, open, high, low, close, volume)."""
    g = g.sort_values("ts")
    o, h, l, c, v = (g[x].to_numpy(dtype=float) for x in ("open", "high", "low", "close", "volume"))
    if len(c) < 20 or np.nansum(v) <= 0:
        return None
    ts = pd.to_datetime(g["ts"])
    mins = (ts.dt.hour * 60 + ts.dt.minute).to_numpy() - SESSION_START
    tp = (h + l + c) / 3
    vw = np.nansum(tp * v) / np.nansum(v)
    dev = np.sqrt(np.nansum(v * (tp - vw) ** 2) / np.nansum(v))
    lo, hi = np.nanmin(l), np.nanmax(h)
    rng = hi - lo
    if rng <= 0:
        return None
    edges = np.linspace(lo, hi, NBINS + 1)
    vol = np.zeros(NBINS)
    tpo = np.zeros(NBINS)
    period = mins // 30
    seen = [set() for _ in range(NBINS)]
    for i in range(len(c)):           # spread each bar's volume evenly over the bins it covers
        a = max(0, min(NBINS - 1, int((l[i] - lo) / rng * NBINS)))
        b = max(0, min(NBINS - 1, int((h[i] - lo) / rng * NBINS)))
        vol[a:b + 1] += v[i] / (b - a + 1)
        for k in range(a, b + 1):
            seen[k].add(period[i])
    tpo = np.array([len(s) for s in seen])
    mids = (edges[:-1] + edges[1:]) / 2
    poc_i = int(np.argmax(vol))
    # value area: grow around the POC until 70% of volume
    inc, lo_i, hi_i = vol[poc_i], poc_i, poc_i
    while inc < 0.7 * vol.sum() and (lo_i > 0 or hi_i < NBINS - 1):
        down = vol[lo_i - 1] if lo_i > 0 else -1
        up = vol[hi_i + 1] if hi_i < NBINS - 1 else -1
        if up >= down:
            hi_i += 1; inc += vol[hi_i]
        else:
            lo_i -= 1; inc += vol[lo_i]
    order = np.argsort(vol)[::-1]
    hvn2 = mids[order[1]] if len(order) > 1 else np.nan
    va_bins = np.arange(lo_i, hi_i + 1)
    lvn = mids[va_bins[np.argmin(vol[va_bins])]] if len(va_bins) > 2 else np.nan
    first = mins < 15
    ib = mins < 60
    or_hi, or_lo = np.nanmax(h[first]) if first.any() else np.nan, np.nanmin(l[first]) if first.any() else np.nan
    ib_hi, ib_lo = np.nanmax(h[ib]), np.nanmin(l[ib])
    open_ = o[0]
    after = mins >= 5
    lunch = (mins >= 165) & (mins < 255)          # 12:00 - 13:30
    morning = mins < 255
    half = NBINS // 2
    lower_poc = np.argmax(vol[:half]); upper_poc = half + np.argmax(vol[half:])
    gap = vol[lower_poc:upper_poc + 1].min() if upper_poc > lower_poc else np.nan
    am = mins < 180
    am_poc = mids[np.argmax(np.histogram(tp[am], bins=edges, weights=v[am])[0])] if am.any() else np.nan
    pm_poc = mids[np.argmax(np.histogram(tp[~am], bins=edges, weights=v[~am])[0])] if (~am).any() else np.nan
    day_low_bars = np.sum(l <= lo * 1.0005)
    tail_bins = 0
    while tail_bins < NBINS and tpo[tail_bins] <= 1:
        tail_bins += 1
    rets = np.diff(np.log(c))
    H = 3
    kern = lambda x: 1 - 6 * x ** 2 + 6 * x ** 3 if x <= .5 else 2 * (1 - x) ** 3      # Parzen
    rk = np.sum(rets ** 2) + 2 * sum(kern(k / (H + 1)) * np.sum(rets[k:] * rets[:-k]) for k in range(1, H + 1))
    return {
        "open": open_, "high": hi, "low": lo, "close": c[-1], "vwap": vw, "vwap_sd": dev,
        "poc": mids[poc_i], "vah": edges[hi_i + 1], "val": edges[lo_i], "hvn2": hvn2, "lvn": lvn,
        "or_hi": or_hi, "or_lo": or_lo, "ib_hi": ib_hi, "ib_lo": ib_lo,
        "single_prints": int((tpo == 1).sum()), "excess_low_frac": tail_bins / NBINS,
        "poor_low": float(day_low_bars >= 2),
        "open_drive_up": float(after.any() and np.nanmin(l[after & (mins < 30)]) > open_ and c[-1] > open_ + 0.5 * rng),
        "open_test_drive_up": float(first.any() and np.nanmin(l[mins < 10]) < open_ and c[-1] > or_hi and (c[-1] - lo) >= 0.7 * rng),
        "or_reversal_up": float(np.nanmin(l) < or_lo and c[-1] > or_hi),
        "or_low_sweep": float(np.nanmin(l[~first]) < or_lo and c[-1] > or_lo) if (~first).any() else 0.0,
        "lunch_compression": float(lunch.any() and (np.nanmax(h[lunch]) - np.nanmin(l[lunch])) <= 0.3 * rng),
        "pm_breakout": float(morning.any() and c[-1] > np.nanmax(h[morning])),
        "double_dist_up": float(upper_poc > lower_poc and gap < 0.3 * min(vol[lower_poc], vol[upper_poc]) and pm_poc > am_poc),
        "neutral_day": float(hi > ib_hi and lo < ib_lo and (lo + rng / 3) <= c[-1] <= (hi - rng / 3)),
        "vwap_reclaim": float((c[mins < 165] < vw).any() and c[-1] > vw and np.all(c[mins >= 315] > vw)) if (mins >= 315).any() else 0.0,
        "first_hour_volume": np.nansum(v[ib]), "realised_kernel_var": rk,
    }


def panel(B):
    """Daily profile features aligned to B (date x stock). NaN where no 5-minute history."""
    if "_profile" in B:
        return B["_profile"]
    from .archive import m5_bars
    c = B["c"]
    m5 = m5_bars(start=c.index[0], end=c.index[-1], symbols=list(c.columns))
    out = {}
    if len(m5):
        m5["day"] = m5["ts"].dt.normalize()
        rows = []
        for (d, s), g in m5.groupby(["day", "symbol"]):
            r = day_profile(g)
            if r:
                rows.append({"date": d, "symbol": s, **r})
        if rows:
            df = pd.DataFrame(rows)
            for k in df.columns.drop(["date", "symbol"]):
                out[k] = df.pivot(index="date", columns="symbol", values=k).reindex(index=c.index, columns=c.columns)
    B["_profile"] = out
    return out


def signal(pid, B, p=None):
    P = panel(B)
    c = B["c"]
    if not P:
        return pd.DataFrame(False, index=c.index, columns=c.columns)
    sh = lambda k: P[k].shift(1)
    with np.errstate(invalid="ignore"):
        if pid in ("market_profile_open_drive", "session_open_drive"):
            e = P["open_drive_up"] > 0
        elif pid == "market_profile_open_test_drive":
            e = P["open_test_drive_up"] > 0
        elif pid == "opening_range_reversal":
            e = P["or_reversal_up"] > 0
        elif pid == "opening_range_low_sweep":
            e = P["or_low_sweep"] > 0
        elif pid == "lunch_session_compression":
            e = (P["lunch_compression"] > 0) & (P["pm_breakout"] > 0)
        elif pid == "double_distribution_day":
            e = P["double_dist_up"] > 0
        elif pid == "value_area_migration_up":
            e = (P["val"] > sh("val")) & (P["vah"] > sh("vah")) & (P["poc"] > sh("vah")) & (P["close"] > P["vah"])
        elif pid == "market_profile_balance_area":
            vah5, val5 = P["vah"].shift(1).rolling(5).min(), P["val"].shift(1).rolling(5).max()
            bal = val5 < vah5
            e = bal & (P["close"] > P["vah"].shift(1).rolling(5).max())
        elif pid == "failed_auction":
            e = (P["low"] < sh("val")) & (P["close"] > sh("val"))
        elif pid == "poor_low":
            e = (P["poor_low"] > 0) & ((P["close"] - P["low"]) >= 0.5 * (P["high"] - P["low"]))
        elif pid == "excess_low":
            e = (P["excess_low_frac"] >= 0.1) & (P["close"] > P["vwap"])
        elif pid == "vwap_reclaim":
            e = P["vwap_reclaim"] > 0
        # detector-only (neutral) items
        elif pid == "neutral_day":
            e = P["neutral_day"] > 0
        elif pid == "single_print_zone":
            e = P["single_prints"] >= 3
        else:
            raise ValueError(f"no profile detector for {pid}")
    return (e.fillna(False).astype(bool) & B["member"]).fillna(False)


ENTRIES = {"chart_pattern": ["market_profile_open_drive", "market_profile_open_test_drive", "opening_range_reversal",
                             "market_profile_balance_area", "failed_auction"],
           "market_structure": ["opening_range_low_sweep", "lunch_session_compression",
                                "double_distribution_day", "value_area_migration_up", "poor_low", "excess_low",
                                "vwap_reclaim"]}
DETECTOR_ONLY = {"market_structure": ["neutral_day", "single_print_zone"]}


def feature(fid, B):
    """Daily intraday-derived features (indicators / quant items needing 5-minute data)."""
    P = panel(B)
    if not P:
        return None
    A = B["atr"]
    F = {
        "volume_profile": lambda: P["poc"], "volume_profile_poc": lambda: P["poc"],
        "volume_profile_value_area": lambda: P["vah"] - P["val"],
        "volume_profile_high_volume_nodes": lambda: P["hvn2"], "volume_profile_low_volume_nodes": lambda: P["lvn"],
        "vwap_deviation_bands": lambda: (P["close"] - P["vwap"]) / P["vwap_sd"],
        "volume_weighted_average_price_bands": lambda: (P["close"] - P["vwap"]) / P["vwap_sd"],
        "intraday_vwap_distance": lambda: (P["close"] - P["vwap"]) / A,
        "relative_volume_time_of_day": lambda: P["first_hour_volume"] / P["first_hour_volume"].shift(1).rolling(20, min_periods=5).mean(),
        "realised_kernel_volatility": lambda: np.sqrt(P["realised_kernel_var"].clip(lower=0) * 252),
        "distance_from_poc": lambda: (P["close"] - P["poc"]) / A,
        "distance_from_vah": lambda: (P["close"] - P["vah"]) / A,
        "distance_from_val": lambda: (P["close"] - P["val"]) / A,
        "profile_value_overlap": lambda: ((np.minimum(P["vah"], P["vah"].shift(1)) - np.maximum(P["val"], P["val"].shift(1))).clip(lower=0)
                                          / (P["vah"] - P["val"]).replace(0, np.nan)),
    }
    if fid not in F:
        raise KeyError(fid)
    return F[fid]()


FEATURES = ["volume_profile", "volume_profile_poc", "volume_profile_value_area", "volume_profile_high_volume_nodes",
            "volume_profile_low_volume_nodes", "vwap_deviation_bands", "volume_weighted_average_price_bands",
            "intraday_vwap_distance", "relative_volume_time_of_day", "realised_kernel_volatility",
            "distance_from_poc", "distance_from_vah", "distance_from_val", "profile_value_overlap"]


def bar_features(m5):
    """Per-5-minute-bar session-time features (quant catalogue)."""
    ts = pd.to_datetime(m5["ts"])
    mins = ts.dt.hour * 60 + ts.dt.minute - SESSION_START
    return pd.DataFrame({"minutes_since_open": mins, "minutes_to_close": 375 - mins,
                         "is_first_15_minutes": (mins < 15).astype(float), "is_last_30_minutes": (mins >= 345).astype(float),
                         "time_of_day_bucket": (mins // 75).clip(0, 4)}, index=m5.index)


BAR_FEATURES = ["minutes_since_open", "minutes_to_close", "is_first_15_minutes", "is_last_30_minutes", "time_of_day_bucket"]
