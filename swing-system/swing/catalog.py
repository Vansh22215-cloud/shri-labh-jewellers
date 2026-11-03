"""Registry for the owner's Market Pattern & Technical Indicator Reference Library (library/market_pattern_library,
v1.0.0: 52 chart patterns, 69 candlestick patterns, 176 indicators) and the detectors built from it.

Rules followed (from the library's README / CLAUDE_CODE_HANDOFF):
  * the JSON is the single source of truth; nothing is re-typed here except the mapping to code
  * TA-Lib canonical implementations are used for every item with a TA-Lib code (exact parity)
  * chart patterns use a SWING-PIVOT ENGINE with right-side confirmation: a pivot at bar t with r confirmation
    bars is only known at bar t + r; signals are stamped on the bar they became knowable (no back-dating)
  * every catalogue item gets an audit status: implemented / implemented_detector_only / not_applicable_to_strategy /
    blocked_by_data / not_yet_implemented, with a reason (library/IMPLEMENTATION_AUDIT.md)
  * a detector is NOT a profitable strategy: entries are tested by the idea factory with costs and walk-forward.
Rule version of every detector here: "cat-v1".
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT

LIB = ROOT / "library" / "market_pattern_library"
RULE_VERSION = "cat-v1"


def load():
    out = {}
    for kind, fn in (("chart_pattern", "chart_patterns.json"), ("candlestick", "candlestick_patterns.json"),
                     ("indicator", "indicators.json")):
        for it in json.loads((LIB / fn).read_text())["items"]:
            out[f"{kind}/{it['id']}"] = dict(it, _type=kind)     # keyed by type: some ids exist in two files
    return out


def get(kind, item_id):
    return load()[f"{kind}/{item_id}"]


def validate(cat=None):
    cat = cat or load()
    need = {"chart_pattern": ["id", "name", "deterministic_detection_outline", "confirmation_rule", "invalidation_rule"],
            "candlestick": ["id", "name", "typical_direction", "definition"],
            "indicator": ["id", "name", "category", "calculation_basis"]}
    problems = [f"{k}: missing {f}" for k, v in cat.items() for f in need[v["_type"]] if not v.get(f)]
    return problems


def query(category=None, kind=None):
    return [v for v in load().values() if (category is None or v.get("category") == category)
            and (kind is None or v["_type"] == kind)]


# ----------------------------------------------------------------------------- TA-Lib candlesticks
def _talib():
    import talib
    return talib


def cdl_panel(code, B):
    """TA-Lib candlestick output (+100 bullish / -100 bearish / 0) for every stock; per-column on valid bars only."""
    key = "_cdl_" + code
    if key in B:
        return B[key]
    tl = _talib()
    fn = getattr(tl, code)
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]
    out = pd.DataFrame(0.0, index=c.index, columns=c.columns)
    for col in c.columns:
        ok = o[col].notna() & h[col].notna() & l[col].notna() & c[col].notna()
        if ok.sum() < 20:
            continue
        idx = ok[ok].index
        r = fn(o[col][idx].values.astype(float), h[col][idx].values.astype(float),
               l[col][idx].values.astype(float), c[col][idx].values.astype(float))
        out.loc[idx, col] = r
    B[key] = out
    return out


# ----------------------------------------------------------------------------- swing pivots (no look-ahead)
def pivots(B, L=3, R=3, k=3):
    """Confirmed swing pivots. At bar t we know a pivot low at t-R if low[t-R] is the minimum of
    low[t-R-L .. t] (L bars left, R bars right, all closed). Returns, for every bar, the values and bar positions of
    the last k confirmed pivot lows and highs (arrays T x N x k; NaN = none yet)."""
    key = f"_piv_{L}_{R}_{k}"
    if key in B:
        return B[key]
    h, l = B["h"], B["l"]
    w = L + R + 1
    pl = (l.shift(R) == l.rolling(w, min_periods=w).min()) & l.shift(R).notna()
    ph = (h.shift(R) == h.rolling(w, min_periods=w).max()) & h.shift(R).notna()
    lv, hv = l.shift(R).values, h.shift(R).values
    T, N = l.shape
    PLv, PLi = np.full((T, N, k), np.nan), np.full((T, N, k), np.nan)
    PHv, PHi = np.full((T, N, k), np.nan), np.full((T, N, k), np.nan)
    curLv, curLi = np.full((N, k), np.nan), np.full((N, k), np.nan)
    curHv, curHi = np.full((N, k), np.nan), np.full((N, k), np.nan)
    plv, phv = pl.values, ph.values
    for t in range(T):
        m = plv[t]
        if m.any():
            curLv[m] = np.roll(curLv[m], -1, axis=1); curLi[m] = np.roll(curLi[m], -1, axis=1)
            curLv[m, -1], curLi[m, -1] = lv[t][m], t - R
        m = phv[t]
        if m.any():
            curHv[m] = np.roll(curHv[m], -1, axis=1); curHi[m] = np.roll(curHi[m], -1, axis=1)
            curHv[m, -1], curHi[m, -1] = hv[t][m], t - R
        PLv[t], PLi[t], PHv[t], PHi[t] = curLv, curLi, curHv, curHi
    B[key] = (PLv, PLi, PHv, PHi)
    return B[key]


def _cross_above(c, level):
    lv = pd.DataFrame(level, index=c.index, columns=c.columns) if isinstance(level, np.ndarray) else level
    return (c > lv) & (c.shift(1) <= lv.shift(1))


def chart_signal(pid, B, p):
    """Bullish chart-pattern detectors (long-only system). Confirmation = close crosses the trigger level."""
    c, h, l, o, v = B["c"], B["h"], B["l"], B["o"], B["v"]
    a = B["atr"].values
    T, N = c.shape
    idx = np.arange(T)[:, None]
    PLv, PLi, PHv, PHi = pivots(B)
    df = lambda x: pd.DataFrame(x, index=c.index, columns=c.columns)
    l1, l2, l3 = PLv[:, :, 0], PLv[:, :, 1], PLv[:, :, 2]          # oldest .. newest pivot low
    i1, i2, i3 = PLi[:, :, 0], PLi[:, :, 1], PLi[:, :, 2]
    h1, h2, h3 = PHv[:, :, 0], PHv[:, :, 1], PHv[:, :, 2]
    j1, j2, j3 = PHi[:, :, 0], PHi[:, :, 1], PHi[:, :, 2]
    tol, buf = 0.5 * a, 0.1 * a
    with np.errstate(invalid="ignore"):
        if pid == "double_bottom":
            ok = (np.abs(l3 - l2) <= tol) & (i3 - i2 >= 5) & (j3 > i2) & (j3 < i3) & (idx - i3 <= 60)
            trig = np.where(ok, h3 + buf, np.nan)
        elif pid == "triple_bottom":
            ok = (np.abs(l3 - l2) <= tol) & (np.abs(l2 - l1) <= tol) & (i2 - i1 >= 5) & (i3 - i2 >= 5) & (j3 > i2)
            trig = np.where(ok, np.fmax(h3, h2) + buf, np.nan)
        elif pid == "inverse_head_and_shoulders":
            ok = (l2 < l1 - tol) & (l2 < l3 - tol) & (np.abs(l3 - l1) <= 2 * tol) & (j3 > i2) & (j2 > i1) & (j2 < i2)
            trig = np.where(ok, np.fmax(h3, h2) + buf, np.nan)
        elif pid == "ascending_triangle":
            ok = (np.abs(h3 - h2) <= tol) & (l3 > l2 + tol) & (j3 - j2 >= 5)
            trig = np.where(ok, np.fmax(h3, h2) + buf, np.nan)
        elif pid == "rectangle_range":
            ok = (np.abs(h3 - h2) <= tol) & (np.abs(l3 - l2) <= tol) & ((h3 - l3) >= 2 * a)
            trig = np.where(ok, np.fmax(h3, h2) + buf, np.nan)
        elif pid == "falling_wedge":
            sh = (h3 - h2) / np.maximum(j3 - j2, 1)
            sl = (l3 - l2) / np.maximum(i3 - i2, 1)
            ok = (h3 < h2) & (l3 < l2) & (sh < sl) & (sh < 0)
            trig = np.where(ok, h3 + buf, np.nan)
        elif pid == "broadening_bottom":
            ok = (h3 > h2) & (l3 < l2) & (j3 > j2) & (i3 > i2)
            trig = np.where(ok, h3 + buf, np.nan)
        elif pid == "measured_move_up":
            leg1 = h2 - l2
            ok = (j2 > i2) & (i3 > j2) & (l3 > l2) & (leg1 > 3 * a) & ((h2 - l3) <= 0.62 * leg1)
            trig = np.where(ok, h2 + buf, np.nan)
        elif pid == "bull_pennant":
            pole = (c.shift(5) / c.shift(15) - 1).values
            ok = (pole >= 0.12) & (h3 < h2) & (l3 > l2) & (idx - j3 <= 15)
            trig = np.where(ok, h3 + buf, np.nan)
        else:
            trig = None
        if trig is not None:
            return (_cross_above(c, trig) & B["member"]).fillna(False)
    # non-pivot price-action detectors (single/two-bar or rolling-window definitions)
    hi20, lo20 = h.shift(1).rolling(20).max(), l.shift(1).rolling(20).min()
    if pid == "breakout_retest":
        lvl = c.shift(1).rolling(50).max().shift(10)                 # level broken during the last 10 bars
        broke = (c.rolling(10).max() > lvl)
        e = broke & (l <= lvl + 0.5 * B["atr"]) & (c > lvl) & (c > o)
    elif pid == "false_breakout":
        e = (l.shift(1) < lo20.shift(1)) & (c > lo20.shift(1)) & (c > o)      # bear trap: breakdown fails
    elif pid == "outside_bar":
        e = (h > h.shift(1)) & (l < l.shift(1)) & ((c - l) >= 0.75 * (h - l))
    elif pid == "pin_bar_rejection":
        rng = (h - l).replace(0, np.nan)
        e = ((np.minimum(o, c) - l) >= 0.66 * rng) & (l <= lo20 * 1.01)
    elif pid == "gap_breakaway":
        e = (o > hi20) & (l > h.shift(1)) & (v > 1.5 * B["avg_vol"]) & (c > o)
    elif pid == "gap_runaway":
        e = (l > h.shift(1)) & (c > B["sma50"]) & (B["sma50"] > B["sma50"].shift(10)) & (v > 1.2 * B["avg_vol"])
    elif pid == "wyckoff_spring":
        lo60, hi60 = l.shift(1).rolling(60).min(), h.shift(1).rolling(60).max()
        rangey = (hi60 / lo60 - 1) < 0.25
        e = rangey & (l < lo60) & (c > lo60) & (v > B["avg_vol"])
    elif pid == "island_reversal":
        gap_dn = (h.shift(1) < l.shift(2))                           # yesterday gapped below the day before
        e = gap_dn & (l > h.shift(1))                                # today gaps back above: a one-day island
    else:
        raise ValueError(f"no detector for chart pattern {pid}")
    return (e & B["member"]).fillna(False)


CHART_DETECTORS = ["double_bottom", "triple_bottom", "inverse_head_and_shoulders", "ascending_triangle",
                   "rectangle_range", "falling_wedge", "broadening_bottom", "measured_move_up", "bull_pennant",
                   "breakout_retest", "false_breakout", "outside_bar", "pin_bar_rejection", "gap_breakaway",
                   "gap_runaway", "wyckoff_spring", "island_reversal"]
# catalogue items covered by earlier families (swing/families.py, swing/patterns.py)
CHART_MAPPED = {"bull_flag": "bull_flag", "cup_and_handle": "cup_handle", "inside_bar": "inside_day",
                "engulfing_price_action": "bullish_engulfing", "price_channel": "donchian"}


def families():
    """Entry families created from the catalogue: TA-Lib bullish candles (cdl_*) and chart detectors (cp_*)."""
    cat = load()
    out = []
    for k, it in cat.items():
        if it["_type"] == "candlestick" and it.get("canonical_code") and it.get("typical_direction") in ("bullish", "both", "neutral"):
            out.append(f"cdl_{it['id']}")
    out += [f"cp_{x}" for x in CHART_DETECTORS]
    return out


def signals(fam, B, p):
    if fam.startswith("cdl_"):
        it = get("candlestick", fam[4:])
        out = cdl_panel(it["canonical_code"], B)
        e = (out > 0) & B["above200"] & B["member"]       # bullish reading, long-term uptrend context
        return e.fillna(False), f"{it['name']} candle (TA-Lib {it['canonical_code']}) in an uptrend"
    if fam.startswith("cp_"):
        pid = fam[3:]
        it = get("chart_pattern", pid)
        return chart_signal(pid, B, p), f"{it['name']} breakout (confirmed close)"
    raise ValueError(fam)
