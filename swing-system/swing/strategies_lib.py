"""STRATEGY LIBRARY for the search (owner 21 Nov: "start the strategy search; the ultimate goal is ₹10,000 profit a day").

Each strategy looks at ONE day of 5-minute candles (plus yesterday's close/high/low) and returns two True/False
arrays, `long` and `short`: True on a candle means "enter at the next candle's open". Every value uses only
candles up to and including that candle (no look-ahead), so the same function runs in the test (first True of
the day) and live (is the newest candle the first True?).

Stock strategies (intraday, top-100 most traded stocks):
  orb          opening-range breakout with volume and VWAP (the old rule, for comparison)
  gap_fade     gap of 1%+ at the open, first candle moves against the gap -> trade back towards yesterday's close
  gap_go       gap of 1%+ and the first candle continues beyond yesterday's high/low -> go with it
  vwap_revert  10:30-14:00, price 1.5% away from the day's VWAP -> trade back towards it
  trend_1015   at 10:15 the stock is 1%+ from its open, above/below VWAP, near its high/low -> follow the trend
  late_momo    at 2:00 pm the stock is 2%+ from its open and on the right side of VWAP -> ride into the close
  pdh_break    first break of yesterday's high/low after 9:30 with 1.5x volume -> follow
  rebound      after a 4%+ fall yesterday, a gap down whose first candle turns green -> buy the rebound
NIFTY strategies (weekly options, CALL for long / PUT for short):
  n_orb        9:15-9:30 range breakout with the 20-candle trend and the day's open (the current rule)
  n_gap_fade   NIFTY gaps 0.5%+ and the first candle moves against the gap
  n_trend_1015 at 10:15 NIFTY is 0.4%+ from its open and beyond its 20-candle average
  n_ema_cross  9/21-candle averages cross in the direction of the day (after 9:45)
  n_pdh_break  NIFTY breaks yesterday's high (CALL) or low (PUT)"""
import numpy as np


def ctx(o, h, l, c, v, end_m, prev_close=None, prev_high=None, prev_low=None, prev_change=None):
    """Arrays of one day (oldest first) + yesterday's values -> a dict every strategy reads."""
    v = np.asarray(v, float)
    cv = np.cumsum(v)
    vwap = np.where(cv > 0, np.cumsum(c * v) / np.maximum(cv, 1e-9), np.cumsum(c) / np.arange(1, len(c) + 1))
    idx = np.arange(len(c))
    prior = np.where(idx > 0, (cv - v) / np.maximum(idx, 1), np.nan)
    first = end_m <= 570                                     # candles ending by 9:30 (9:15, 9:20, 9:25)
    orh = np.maximum.accumulate(np.where(first, h, -np.inf)) if first.any() else np.full(len(c), np.nan)
    orl = np.minimum.accumulate(np.where(first, l, np.inf)) if first.any() else np.full(len(c), np.nan)
    orh = np.where(np.isinf(orh), np.nan, orh)
    orl = np.where(np.isinf(orl), np.nan, orl)
    ema = lambda x, n: _ema(x, n)
    return {"o": o, "h": h, "l": l, "c": c, "v": v, "end_m": end_m, "vwap": vwap,
            "strength": np.where(prior > 0, v / np.where(prior > 0, prior, 1), 0.0),
            "orh": orh, "orl": orl, "open0": o[0] if len(o) else np.nan,
            "run_hi": np.maximum.accumulate(h), "run_lo": np.minimum.accumulate(l),
            "ema9": ema(c, 9), "ema20": ema(c, 20), "ema21": ema(c, 21),
            "pc": prev_close, "ph": prev_high, "pl": prev_low, "pchg": prev_change}


def _ema(x, n):
    a = 2.0 / (n + 1)
    out = np.empty(len(x))
    s = np.nan
    for i, val in enumerate(x):
        s = val if i == 0 else a * val + (1 - a) * s
        out[i] = s
    return out


def _none(x):
    z = np.zeros(len(x["c"]), bool)
    return z, z.copy()


# ----------------------------------------------------------------------------- stocks
def orb(x):
    c, e = x["c"], x["end_m"]
    ok = (e >= 575) & (e <= 690) & (x["strength"] >= 1.5) & ~np.isnan(x["orh"])
    return ok & (c > x["orh"]) & (c > x["vwap"]), ok & (c < x["orl"]) & (c < x["vwap"])


def gap_fade(x):
    if not x["pc"]:
        return _none(x)
    gap = x["open0"] / x["pc"] - 1
    c, o, e = x["c"], x["o"], x["end_m"]
    ok = (e <= 575)                                        # decided in the first 4 candles
    return ok & (gap < -0.01) & (c > o) & (c > x["open0"]), ok & (gap > 0.01) & (c < o) & (c < x["open0"])


def gap_go(x):
    if not x["pc"] or not x["ph"]:
        return _none(x)
    gap = x["open0"] / x["pc"] - 1
    c, e = x["c"], x["end_m"]
    ok = (e <= 575)
    return ok & (gap > 0.01) & (c > x["ph"]) & (c > x["open0"]), ok & (gap < -0.01) & (c < x["pl"]) & (c < x["open0"])


def vwap_revert(x):
    c, e, w = x["c"], x["end_m"], x["vwap"]
    ok = (e >= 630) & (e <= 840)
    return ok & (c < w * 0.985), ok & (c > w * 1.015)


def trend_1015(x):
    c, e = x["c"], x["end_m"]
    m = c / x["open0"] - 1
    ok = (e == 615)
    return (ok & (m > 0.01) & (c > x["vwap"]) & (c >= x["run_hi"] * 0.995),
            ok & (m < -0.01) & (c < x["vwap"]) & (c <= x["run_lo"] * 1.005))


def late_momo(x):
    c, e = x["c"], x["end_m"]
    m = c / x["open0"] - 1
    ok = (e == 840)
    return ok & (m > 0.02) & (c > x["vwap"]), ok & (m < -0.02) & (c < x["vwap"])


def pdh_break(x):
    if not x["ph"]:
        return _none(x)
    c, e = x["c"], x["end_m"]
    ok = (e >= 575) & (e <= 840) & (x["strength"] >= 1.5)
    return ok & (c > x["ph"]), ok & (c < x["pl"])


def rebound(x):
    if x["pchg"] is None or not x["pc"]:
        return _none(x)
    c, o, e = x["c"], x["o"], x["end_m"]
    ok = (e <= 575) & (x["pchg"] < -0.04) & (x["open0"] < x["pc"])
    z = np.zeros(len(c), bool)
    return ok & (c > o), z


STOCK = {"orb": orb, "gap_fade": gap_fade, "gap_go": gap_go, "vwap_revert": vwap_revert, "trend_1015": trend_1015,
         "late_momo": late_momo, "pdh_break": pdh_break, "rebound": rebound}


# ----------------------------------------------------------------------------- NIFTY
def n_orb(x):
    c, e = x["c"], x["end_m"]
    ok = (e >= 575) & (e <= 870) & ~np.isnan(x["orh"])
    return (ok & (c > x["orh"]) & (c > x["ema20"]) & (c > x["open0"]),
            ok & (c < x["orl"]) & (c < x["ema20"]) & (c < x["open0"]))


def n_gap_fade(x):
    if not x["pc"]:
        return _none(x)
    gap = x["open0"] / x["pc"] - 1
    c, o, e = x["c"], x["o"], x["end_m"]
    ok = (e <= 575)
    return ok & (gap < -0.005) & (c > o), ok & (gap > 0.005) & (c < o)


def n_trend_1015(x):
    c, e = x["c"], x["end_m"]
    m = c / x["open0"] - 1
    ok = (e == 615)
    return ok & (m > 0.004) & (c > x["ema20"]), ok & (m < -0.004) & (c < x["ema20"])


def n_ema_cross(x):
    c, e, a, b = x["c"], x["end_m"], x["ema9"], x["ema21"]
    up = np.r_[False, (a[1:] > b[1:]) & (a[:-1] <= b[:-1])]
    dn = np.r_[False, (a[1:] < b[1:]) & (a[:-1] >= b[:-1])]
    ok = (e >= 585) & (e <= 870)
    return ok & up & (c > x["open0"]), ok & dn & (c < x["open0"])


def n_pdh_break(x):
    if not x["ph"]:
        return _none(x)
    c, e = x["c"], x["end_m"]
    ok = (e >= 575) & (e <= 870)
    return ok & (c > x["ph"]), ok & (c < x["pl"])


NIFTY = {"n_orb": n_orb, "n_gap_fade": n_gap_fade, "n_trend_1015": n_trend_1015, "n_ema_cross": n_ema_cross,
         "n_pdh_break": n_pdh_break}


def first_signal(fn, x):
    """-> (index, is_long) of the day's first signal, or None."""
    lg, sh = fn(x)
    hit = np.flatnonzero(lg | sh)
    if not len(hit):
        return None
    i = int(hit[0])
    return i, bool(lg[i])
