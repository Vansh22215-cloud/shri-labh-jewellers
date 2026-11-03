"""Registry for the owner's Market Pattern & Technical Indicator Reference Library (library/market_pattern_library,
v2.0.0: 148 chart patterns, 130 candlestick patterns, 324 indicators, 85 market-structure events,
104 quant research features = 791 records) and the detectors built from it.

Rules followed (from the library's README / CLAUDE_CODE_HANDOFF):
  * the JSON is the single source of truth; nothing is re-typed here except the mapping to code
  * TA-Lib canonical implementations are used for every item with a TA-Lib code (exact parity)
  * chart patterns use a SWING-PIVOT ENGINE with right-side confirmation: a pivot at bar t with r confirmation
    bars is only known at bar t + r; signals are stamped on the bar they became knowable (no back-dating)
  * every catalogue item gets an audit status: implemented / implemented_detector_only / not_applicable_to_strategy /
    blocked_by_data / not_yet_implemented, with a reason (library/IMPLEMENTATION_AUDIT.md)
  * a detector is NOT a profitable strategy: entries are tested by the idea factory with costs and walk-forward.
Rule version: "cat-v1" for v1 detectors, "cat-v2" for the market-structure events added with library v2.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT

LIB = ROOT / "library" / "market_pattern_library"
RULE_VERSION = "cat-v1"
RULE_VERSION_MS = "cat-v2"


def load():
    out = {}
    for kind, fn in (("chart_pattern", "chart_patterns.json"), ("candlestick", "candlestick_patterns.json"),
                     ("indicator", "indicators.json"), ("market_structure", "market_structure_events.json"),
                     ("quant_feature", "quant_research_features.json")):
        if not (LIB / fn).exists():
            continue
        for it in json.loads((LIB / fn).read_text())["items"]:
            out[f"{kind}/{it['id']}"] = dict(it, _type=kind)     # keyed by type: some ids exist in two files
    return out


def get(kind, item_id):
    return load()[f"{kind}/{item_id}"]


def validate(cat=None):
    cat = cat or load()
    need = {"chart_pattern": ["id", "name", "deterministic_detection_outline", "confirmation_rule", "invalidation_rule"],
            "candlestick": ["id", "name", "typical_direction", "definition"],
            "indicator": ["id", "name", "category", "calculation_basis"],
            "market_structure": ["id", "name", "definition", "detection_outline"],
            "quant_feature": ["id", "name", "definition"]}
    problems = [f"{k}: missing {f}" for k, v in cat.items() for f in need[v["_type"]] if not v.get(f)]
    return problems


def aliases():
    """Shorthand/name -> (catalogue type, canonical id), from aliases.json (v2)."""
    f = LIB / "aliases.json"
    if not f.exists():
        return {}
    kind = {"chart_pattern": "chart_pattern", "candlestick": "candlestick", "indicator": "indicator",
            "market_structure": "market_structure", "quant_feature": "quant_feature"}
    return {k: (kind.get(v.get("catalogue"), v.get("catalogue")), v["canonical_id"])
            for k, v in json.loads(f.read_text())["aliases"].items()}


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


# ----------------------------------------------------------------------------- non-TA-Lib candles (library v2 variants)
def candle_x(cid, B):
    """Configurable heuristics for the v2 candles that have no TA-Lib code. Body/range thresholds are adaptive
    (relative to the stock's own 20-day average body and ATR), as the catalogue requires."""
    c, h, l, o = B["c"], B["h"], B["l"], B["o"]
    A = B["atr"]
    body = (c - o).abs()
    ab = body.shift(1).rolling(20, min_periods=10).mean()
    rng = (h - l).replace(0, np.nan)
    up, dn = c > o, c < o
    big = body >= 1.3 * ab
    small = body <= 0.5 * ab
    doji = body <= 0.1 * rng
    tol = 0.1 * A
    S = lambda x, k=1: x.shift(k)
    top, bot = np.maximum(o, c), np.minimum(o, c)
    decline = c.shift(1) < c.shift(6)                       # short-term down move into the pattern
    with np.errstate(invalid="ignore"):
        r = {
            "tweezer_bottom": lambda: ((l - S(l)).abs() <= tol) & S(dn) & up & decline,
            "bullish_tweezer_bottom": lambda: ((l - S(l)).abs() <= tol) & S(dn) & up & decline,
            "railroad_tracks": lambda: S(dn) & S(big) & up & big & ((body - S(body)).abs() <= 0.25 * S(body)) & decline,
            "bullish_railroad_tracks": lambda: S(dn) & S(big) & up & big & ((body - S(body)).abs() <= 0.25 * S(body)) & decline,
            "belt_hold": lambda: up & big & ((o - l) <= 0.05 * rng) & decline,
            "belt_hold_bullish": lambda: up & big & ((o - l) <= 0.05 * rng) & ((h - c) <= 0.15 * rng),
            "three_bar_reversal": lambda: (S(l) < S(l, 2)) & (S(l) < l) & (c > S(h)) & up,
            "fakey_inside_bar": lambda: (S(h, 1) < S(h, 2)) & (S(l, 1) > S(l, 2)) & (l < S(l)) & (c > S(h)),
            "bullish_fakey": lambda: (S(h, 2) < S(h, 3)) & (S(l, 2) > S(l, 3)) & (S(l) < S(l, 2)) & (c > S(h, 3)),
            "long_legged_doji": lambda: doji & ((h - top) >= 0.35 * rng) & ((bot - l) >= 0.35 * rng) & decline,
            "rickshaw_man": lambda: doji & ((((o + c) / 2) - (h + l) / 2).abs() <= 0.1 * rng) & (rng >= A) & decline,
            "dragonfly_doji": lambda: doji & ((h - top) <= 0.1 * rng) & ((bot - l) >= 0.6 * rng) & decline,
            "bullish_harami_cross": lambda: S(dn) & S(big) & doji & (top <= S(o)) & (bot >= S(c)),
            "bullish_homing_pigeon": lambda: S(dn) & S(big) & dn & (o < S(o)) & (c > S(c)) & decline,
            "bullish_matching_low": lambda: S(dn) & dn & ((c - S(c)).abs() <= tol) & decline,
            "bullish_meeting_lines": lambda: S(dn) & S(big) & up & big & ((c - S(c)).abs() <= tol),
            "bullish_separating_lines": lambda: S(dn) & up & big & ((o - S(o)).abs() <= tol) & (c > S(o)),
            "piercing_line_variant": lambda: S(dn) & S(big) & (o < S(l)) & (c > (S(o) + S(c)) / 2) & (c < S(o)),
            "bullish_kicker": lambda: S(dn) & S(big) & up & big & (o > S(o)) & (l > S(c)),
            "bullish_three_line_strike": lambda: S(dn, 1) & S(dn, 2) & S(dn, 3) & (S(c, 1) < S(c, 2)) & (S(c, 2) < S(c, 3))
                                                  & up & (o <= S(c)) & (c > S(o, 3)),
            "bullish_three_white_soldiers_strict": lambda: up & S(up) & S(up, 2) & (c > S(c)) & (S(c) > S(c, 2))
                                                  & ((h - c) <= 0.15 * rng) & (o > S(o)) & (o < S(c)) & big & S(big) & S(big, 2),
            "bullish_hammer_contextual": lambda: ((bot - l) >= 2 * body) & ((h - top) <= 0.1 * rng) & (l <= l.shift(1).rolling(20).min())
                                                  & (rng >= 0.8 * A),
            "bullish_inverted_hammer_contextual": lambda: ((h - top) >= 2 * body) & ((bot - l) <= 0.1 * rng)
                                                  & (l <= l.shift(1).rolling(20).min()),
            "bullish_counterattack": lambda: S(dn) & S(big) & up & big & (o < S(l)) & ((c - S(c)).abs() <= tol),
            "bullish_gap_fill_reclaim_candle": lambda: (o < S(l)) & (c > S(c)) & up,
            "bullish_rising_three_methods": lambda: S(up, 4) & S(big, 4) & S(small, 3) & S(small, 2) & S(small, 1)
                                                  & (S(h, 1).rolling(3).max() <= S(h, 4)) & (S(l, 1).rolling(3).min() >= S(l, 4))
                                                  & up & big & (c > S(c, 4)),
            "bullish_mat_hold": lambda: S(up, 4) & S(big, 4) & (S(l, 1).rolling(3).min() > S(o, 4) + 0.5 * S(body, 4))
                                                  & up & (c > S(h, 4)),
            "bullish_stick_sandwich": lambda: S(dn, 2) & S(up, 1) & dn & ((c - S(c, 2)).abs() <= tol) & decline,
            "bullish_ladder_bottom": lambda: S(dn, 4) & S(dn, 3) & S(dn, 2) & S(dn, 1) & (S(c, 1) < S(c, 4)) & up & (o > S(o)),
            "bullish_unique_three_river": lambda: S(dn, 2) & S(big, 2) & S(dn, 1) & (S(l, 1) < S(l, 2)) & S(small, 1)
                                                  & up & small & (c < S(c, 1)),
            "bullish_abandoned_baby": lambda: S(dn, 2) & S(doji, 1) & (S(h, 1) < S(l, 2)) & up & (l > S(h, 1)),
            "bullish_concealing_baby_swallow": lambda: S(dn, 3) & S(dn, 2) & S(dn, 1) & dn & (o > S(h)) & (c < S(l)) & False,
            "bullish_gap_side_by_side_white_lines": lambda: S(up, 1) & up & (S(l, 1) > S(h, 2)) & ((o - S(o)).abs() <= tol),
            "bullish_gapping_side_by_side_white_lines": lambda: S(up, 1) & up & (S(l, 1) > S(h, 2)) & ((o - S(o)).abs() <= tol),
            "bearish_downside_gap_three_methods": lambda: S(dn, 2) & S(dn, 1) & (S(h, 1) < S(l, 2)) & up & (o > S(c)) & (c >= S(l, 2)),
            "bearish_three_star_south": lambda: S(dn, 2) & S(dn, 1) & dn & (S(body, 1) < S(body, 2)) & (body < S(body, 1))
                                                & ((h - l) < S(h - l, 1)) & (S(h - l, 1) < S(h - l, 2)) & (l >= S(l, 1)) & decline,
            "bullish_concealing_baby_swallow": lambda: cdl_panel("CDLCONCEALBABYSWALL", B) > 0,
            "four_price_doji": lambda: ((h - l) <= 0.0005 * c),      # data-quality flag (detector-only)
        }
    if cid not in r:
        raise KeyError(cid)
    return r[cid]().fillna(False).astype(bool)


# v2 names whose rule is identical to another detector (merged so they are not tested twice)
DUPLICATE_OF = {"candlestick/bullish_tweezer_bottom": "cdx_tweezer_bottom",
                "candlestick/bullish_railroad_tracks": "cdx_railroad_tracks",
                "candlestick/bullish_gapping_side_by_side_white_lines": "cdx_bullish_gap_side_by_side_white_lines",
                "chart_pattern/rounding_bottom": "cp_cup_without_handle",
                "chart_pattern/cypher_bullish": "cp_harmonic_cypher", "chart_pattern/deep_crab_bullish": "cp_harmonic_deep_crab",
                "chart_pattern/shark_bullish": "cp_harmonic_shark", "chart_pattern/abcd_bullish": "cp_harmonic_ab_cd",
                "chart_pattern/elliott_impulse_wave": "cp_elliott_impulse", "chart_pattern/gap_exhaustion": "cp_exhaustion_gap",
                "market_structure/session_open_drive": "cp_market_profile_open_drive"}
CANDLE_X = ["tweezer_bottom", "railroad_tracks", "belt_hold",
            "belt_hold_bullish", "three_bar_reversal", "fakey_inside_bar", "bullish_fakey", "long_legged_doji",
            "rickshaw_man", "dragonfly_doji", "bullish_harami_cross", "bullish_homing_pigeon", "bullish_matching_low",
            "bullish_meeting_lines", "bullish_separating_lines", "piercing_line_variant", "bullish_kicker",
            "bullish_three_line_strike", "bullish_three_white_soldiers_strict", "bullish_hammer_contextual",
            "bullish_inverted_hammer_contextual", "bullish_counterattack", "bullish_gap_fill_reclaim_candle",
            "bullish_rising_three_methods", "bullish_mat_hold", "bullish_stick_sandwich", "bullish_ladder_bottom",
            "bullish_unique_three_river", "bullish_abandoned_baby", "bullish_gap_side_by_side_white_lines",
            "bearish_downside_gap_three_methods", "bearish_three_star_south", "bullish_concealing_baby_swallow"]
CANDLE_DETECTOR_ONLY = ["four_price_doji"]


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
    elif pid == "inside_bar_breakout":
        ib = (h.shift(1) < h.shift(2)) & (l.shift(1) > l.shift(2))
        e = ib & (c > h.shift(2))
    elif pid in ("nr4_inside_day", "nr7_inside_day"):
        n = 4 if pid == "nr4_inside_day" else 7
        r_ = (h - l)
        nr = (r_ == r_.rolling(n).min()) & (h < h.shift(1)) & (l > l.shift(1))
        e = nr.shift(1) & (c > h.shift(1))
    elif pid == "darvas_box":
        top_ = h.shift(1).rolling(20).max()
        flat = (h.shift(1).rolling(10).max() <= top_) & (h.shift(11).rolling(10).max() >= top_ * 0.999)
        e = flat & (c > top_) & (c >= h.rolling(252, min_periods=120).max() * 0.9)
    elif pid == "flat_base":
        hi25, lo25 = h.shift(1).rolling(25).max(), l.shift(1).rolling(25).min()
        e = ((hi25 / lo25 - 1) <= 0.15) & (c > hi25) & B["above200"]
    elif pid == "vcp_volatility_contraction":
        r10 = (h.rolling(10).max() / l.rolling(10).min() - 1)
        e = (r10.shift(1) < r10.shift(11)) & (r10.shift(11) < r10.shift(21)) & (v.shift(1).rolling(5).mean() < B["avg_vol"]) \
            & (c > h.shift(1).rolling(10).max()) & B["up_trend"]
    elif pid == "key_reversal_up":
        e = (l < l.shift(1)) & (l <= l.shift(1).rolling(20).min()) & (c > h.shift(1))
    elif pid == "turtle_soup":
        e = (l < lo20) & (lo20 < lo20.shift(4)) & (c > lo20) & (c > o)
    elif pid == "three_bar_play":
        ign = ((c.shift(2) - o.shift(2)) >= 1.5 * B["atr"].shift(2))
        rest = ((h.shift(1) - l.shift(1)) <= 0.5 * (h.shift(2) - l.shift(2))) & (l.shift(1) > (o.shift(2) + c.shift(2)) / 2)
        e = ign & rest & (c > h.shift(2))
    elif pid == "gap_and_go":
        e = (o > h.shift(1)) & (c > o) & (c >= h - 0.2 * (h - l)) & (v > 1.5 * B["avg_vol"])
    elif pid == "gap_fill_reversion":
        e = (o < l.shift(1) - 0.5 * B["atr"].shift(1)) & (c > o) & B["above200"]
    elif pid == "first_pullback_after_breakout":
        brk = (c > c.shift(1).rolling(50).max()).rolling(15).max().astype(bool)
        e = brk & (l <= B["ema20"]) & (c > B["ema20"]) & (c > o) & (c.shift(1) < c.shift(2))
    elif pid == "symmetrical_triangle":
        PLv, PLi, PHv, PHi = pivots(B)
        dfm = lambda x: pd.DataFrame(x, index=c.index, columns=c.columns)
        ok = dfm((PHv[:, :, 2] < PHv[:, :, 1]) & (PLv[:, :, 2] > PLv[:, :, 1]))
        e = ok & _cross_above(c, dfm(PHv[:, :, 2]) + 0.1 * B["atr"]) & B["above200"]
    elif pid == "ascending_channel":
        PLv, PLi, PHv, PHi = pivots(B)
        dfm = lambda x: pd.DataFrame(x, index=c.index, columns=c.columns)
        ok = dfm((PHv[:, :, 2] > PHv[:, :, 1]) & (PLv[:, :, 2] > PLv[:, :, 1]))
        e = ok & (l <= dfm(PLv[:, :, 2]) + 0.5 * B["atr"]) & (c > o) & (c > dfm(PLv[:, :, 2]))
    elif pid in ("cup_without_handle", "rounding_bottom"):
        hi = h.shift(1).rolling(120, min_periods=80).max()
        lo = l.shift(1).rolling(120, min_periods=80).min()
        depth = 1 - lo / hi
        e = (depth >= 0.12) & (depth <= 0.40) & (c >= hi * 0.97) & (c.shift(60) < hi * 0.85) & (c > B["sma50"])
    elif pid == "v_reversal":
        drop = c.shift(5) / c.shift(15) - 1
        e = (drop <= -0.12) & (c / c.shift(5) - 1 >= 0.08) & (v > B["avg_vol"])
    elif pid == "selling_climax":
        e = (v.shift(1) > 3 * B["avg_vol"].shift(1)) & (c.shift(1) < c.shift(20) * 0.85) & (c > h.shift(1))
    elif pid == "liquidity_sweep_reversal":
        lo50 = l.shift(1).rolling(50).min()
        e = (l < lo50) & (c > lo50) & ((c - l) >= 0.6 * (h - l))
    elif pid == "compression_breakout":
        bw = (c.rolling(20).std() * 4) / c.rolling(20).mean()
        e = (bw.shift(1) <= bw.shift(1).rolling(120, min_periods=60).quantile(0.15)) & (c > h.shift(1).rolling(20).max())
    elif pid == "heikin_ashi_trend_run":
        hc = (o + h + l + c) / 4
        hcv = hc.to_numpy(copy=True)
        hov = np.full_like(hcv, np.nan)
        hov[0] = (o.values[0] + c.values[0]) / 2
        for t in range(1, len(hov)):
            hov[t] = np.where(np.isnan(hov[t - 1]), (o.values[t] + c.values[t]) / 2, (hov[t - 1] + hcv[t - 1]) / 2)
        ho = pd.DataFrame(hov, index=c.index, columns=c.columns)
        green = (hc > ho) & (np.minimum(ho, hc) <= l + 1e-9 + 0.02 * (h - l))      # green, no lower wick
        e = green & green.shift(1) & green.shift(2) & ~green.shift(3).fillna(False).astype(bool)
    elif pid == "stair_step_trend":
        e = B["up_trend"] & (l.rolling(20).min() > l.shift(20).rolling(20).min()) & (c > h.shift(1).rolling(20).max())
    elif pid == "wyckoff_spring_test":
        lo60 = l.shift(5).rolling(60).min()
        spring = ((l < lo60) & (c > lo60)).shift(1).rolling(5).max().astype(bool)
        e = spring & (l > lo60) & (v < B["avg_vol"]) & (c > o)
    elif pid == "trendline_break_retest":
        PLv, PLi, PHv, PHi = pivots(B)
        dfm = lambda x: pd.DataFrame(x, index=c.index, columns=c.columns)
        lh = dfm(np.where(PHv[:, :, 2] < PHv[:, :, 1], PHv[:, :, 2], np.nan))
        broke = (c > lh).rolling(10).max().astype(bool)
        e = broke & (l <= lh + 0.3 * B["atr"]) & (c > lh) & (c > o)
    else:   # library v2 remainder: swing geometry, Wyckoff/weekly/P&F/renko, intraday profile
        from . import advanced, profile, zigzag
        if pid in zigzag.DETECTORS:
            return zigzag.signal(pid, B, p)
        if pid in advanced.CHART:
            return advanced.chart(pid, B, p)
        if pid in profile.ENTRIES["chart_pattern"]:
            return profile.signal(pid, B, p)
        raise ValueError(f"no detector for chart pattern {pid}")
    return (e & B["member"]).fillna(False)


CHART_DETECTORS = ["double_bottom", "triple_bottom", "inverse_head_and_shoulders", "ascending_triangle",
                   "rectangle_range", "falling_wedge", "broadening_bottom", "measured_move_up", "bull_pennant",
                   "breakout_retest", "false_breakout", "outside_bar", "pin_bar_rejection", "gap_breakaway",
                   "gap_runaway", "wyckoff_spring", "island_reversal",
                   # library v2 additions
                   "inside_bar_breakout", "nr4_inside_day", "nr7_inside_day", "darvas_box", "flat_base",
                   "vcp_volatility_contraction", "key_reversal_up", "turtle_soup", "three_bar_play", "gap_and_go",
                   "gap_fill_reversion", "first_pullback_after_breakout", "symmetrical_triangle", "ascending_channel",
                   "cup_without_handle", "v_reversal", "selling_climax", "liquidity_sweep_reversal",
                   "compression_breakout", "heikin_ashi_trend_run", "stair_step_trend", "wyckoff_spring_test",
                   "trendline_break_retest"]
# ----------------------------------------------------------------------------- market-structure events (v2 library)
def _period_ref(B, freq):
    """Previous completed week's / month's low and high, and the current period's open (all known at the bar)."""
    c, h, l, o = B["c"], B["h"], B["l"], B["o"]
    idx = c.index
    key = idx.to_period(freq)
    g = pd.Series(key, index=idx)
    newp = g.ne(g.shift(1))
    pid = newp.cumsum().values
    op = o.where(pd.Series(newp.values, index=idx), np.nan).ffill()
    # previous period's full range: shift the per-period aggregates by one period
    plo = l.groupby(pid).min().shift(1)
    phi = h.groupby(pid).max().shift(1)
    prev_lo = pd.DataFrame(plo.loc[pid].values, index=idx, columns=c.columns)
    prev_hi = pd.DataFrame(phi.loc[pid].values, index=idx, columns=c.columns)
    return prev_lo, prev_hi, op


def ms_signal(mid, B, p):
    """Bullish market-structure events from the v2 catalogue, on completed daily bars, confirmed pivots only."""
    c, h, l, o, v = B["c"], B["h"], B["l"], B["o"], B["v"]
    A = B["atr"]
    T, N = c.shape
    df = lambda x: pd.DataFrame(x, index=c.index, columns=c.columns)
    PLv, PLi, PHv, PHi = pivots(B)
    l2, l3, h2, h3 = df(PLv[:, :, 1]), df(PLv[:, :, 2]), df(PHv[:, :, 1]), df(PHv[:, :, 2])
    i3 = df(PLi[:, :, 2])
    tpos = df(np.repeat(np.arange(T)[:, None], N, axis=1).astype(float))
    body = (c - o)
    with np.errstate(invalid="ignore"):
        if mid == "break_of_structure_bullish":          # uptrend structure (higher low) and close breaks last swing high
            e = (l3 > l2) & _cross_above(c, h3)
        elif mid == "change_of_character_bullish":       # downtrend (LH + LL) and close breaks the last lower high
            e = (h3 < h2) & (l3 < l2) & _cross_above(c, h3)
        elif mid == "market_structure_shift_bullish":    # CHoCH with displacement (big body, volume)
            e = (h3 < h2) & (l3 < l2) & _cross_above(c, h3) & (body >= 1.0 * A) & (v > 1.3 * B["avg_vol"])
        elif mid == "higher_low":                        # a higher pivot low just got confirmed (knowable today), uptrend
            e = (i3 == tpos - 3) & (l3 > l2) & B["above200"]
        elif mid == "sell_side_liquidity_sweep":         # trade below last swing low, close back above it
            e = (l < l3) & (c > l3) & (c > o)
        elif mid == "equal_lows_liquidity_pool":         # two equal swing lows (resting stops) swept and reclaimed
            e = ((l3 - l2).abs() <= 0.25 * A) & (l < np.fmin(l2, l3)) & (c > np.fmax(l2, l3))
        elif mid == "fair_value_gap_bullish":            # 3-bar gap: today's low above the high two bars ago, trend up
            e = (l > h.shift(2)) & ((l - h.shift(2)) >= 0.25 * A) & (c > B["sma50"])
        elif mid == "inverse_fair_value_gap_bullish":    # a bearish gap (high < low two bars earlier) gets closed through
            top = l.shift(2).where(h < l.shift(2)).ffill(limit=10)
            e = _cross_above(c, top)
        elif mid == "displacement_bullish":
            e = (body >= 2.0 * A) & ((c - l) >= 0.8 * (h - l)) & (v > 1.5 * B["avg_vol"])
        elif mid == "order_block_bullish":               # last down candle before a displacement that breaks structure
            disp = (body >= 1.5 * A) & (c > h3)
            e = disp & (c.shift(1) < o.shift(1))
        elif mid == "range_acceptance_above":            # two closes above the prior 20-day range
            hi = h.shift(2).rolling(20).max()
            e = (c > hi) & (c.shift(1) > hi) & (c.shift(2) <= hi)
        elif mid == "range_rejection_below":             # dip below the 20-day range, close in the top half of the bar
            lo = l.shift(1).rolling(20).min()
            e = (l < lo) & (c > lo) & ((c - l) >= 0.5 * (h - l))
        elif mid == "discount_zone":                     # uptrend pullback into the lower half of the last swing range
            mid_ = (h3 + l3) / 2
            e = B["up_trend"] & (c < mid_) & (c > l3) & (c > o) & (c.shift(1) <= o.shift(1))
        elif mid in ("prior_week_low_sweep", "weekly_open_reclaim"):
            plo, _, op = _period_ref(B, "W")
            e = ((l < plo) & (c > plo)) if mid == "prior_week_low_sweep" else (_cross_above(c, op) & B["above200"])
        elif mid == "monthly_open_reclaim":
            _, _, op = _period_ref(B, "M")
            e = _cross_above(c, op) & B["above200"]
        elif mid == "prior_day_low_sweep":
            e = (l < l.shift(1)) & (c > l.shift(1)) & (c > o) & B["above200"]
        elif mid == "squeeze_release":                   # Bollinger inside Keltner, then release upward
            m20 = c.rolling(20).mean(); sd = c.rolling(20).std()
            inside = (m20 + 2 * sd) < (m20 + 1.5 * A)
            e = inside.shift(1) & ~inside & (c > m20 + 2 * sd)
        elif mid == "parabolic_sar_flip":
            tl = _talib()
            sar = pd.DataFrame(np.nan, index=c.index, columns=c.columns)
            for col in c.columns:
                ok = h[col].notna() & l[col].notna()
                if ok.sum() > 30:
                    ix = ok[ok].index
                    sar.loc[ix, col] = tl.SAR(h[col][ix].values.astype(float), l[col][ix].values.astype(float))
            e = _cross_above(c, sar)
        elif mid == "atr_trailing_stop_flip":            # chandelier (short side) flipped: close above lowest low + 3 ATR
            lvl = l.rolling(22).min() + 3 * A
            e = _cross_above(c, lvl.shift(1))
        elif mid == "trend_day_up":                      # opens near low, closes near high, wide range
            rng = (h - l)
            e = ((o - l) <= 0.2 * rng) & ((h - c) <= 0.1 * rng) & (rng >= 1.5 * A)
        else:
            from . import advanced, profile
            if mid in advanced.MS or mid in advanced.MS_DETECTOR_ONLY:
                return advanced.ms(mid, B, p)
            if mid in profile.ENTRIES["market_structure"] or mid in profile.DETECTOR_ONLY["market_structure"]:
                return profile.signal(mid, B, p)
            raise ValueError(f"no detector for market-structure event {mid}")
    return (e.fillna(False).astype(bool) & B["member"]).fillna(False)


MS_DETECTORS = ["break_of_structure_bullish", "change_of_character_bullish", "market_structure_shift_bullish",
                "higher_low", "sell_side_liquidity_sweep", "equal_lows_liquidity_pool", "fair_value_gap_bullish",
                "inverse_fair_value_gap_bullish", "displacement_bullish", "order_block_bullish",
                "range_acceptance_above", "range_rejection_below", "discount_zone", "prior_week_low_sweep",
                "weekly_open_reclaim", "monthly_open_reclaim", "prior_day_low_sweep", "squeeze_release",
                "parabolic_sar_flip", "atr_trailing_stop_flip", "trend_day_up"]


# catalogue items covered by earlier families (swing/families.py, swing/patterns.py)
CHART_MAPPED = {"bull_flag": "bull_flag", "cup_and_handle": "cup_handle", "inside_bar": "inside_day",
                "engulfing_price_action": "bullish_engulfing", "price_channel": "donchian",
                # v2 names that are the same rule as an existing detector
                "breakaway_gap": "cp_gap_breakaway", "runaway_gap": "cp_gap_runaway", "throwback": "cp_breakout_retest",
                "failed_breakdown_trap": "cp_false_breakout", "island_reversal_bottom": "cp_island_reversal",
                "outside_bar_reversal_structure": "cp_outside_bar", "compression_to_expansion": "cp_compression_breakout",
                "volatility_contraction_triangle": "cp_vcp_volatility_contraction", "equal_highs_equal_lows": "cp_rectangle_range",
                "horizontal_channel": "cp_rectangle_range", "saucer_with_handle": "cup_handle",
                "adam_eve_double_bottom": "cp_double_bottom", "opening_range_breakout": "intraday ORB (swing/intraday.py)"}


def families():
    """Entry families created from the catalogue: TA-Lib bullish candles (cdl_*) and chart detectors (cp_*)."""
    cat = load()
    out = []
    for k, it in cat.items():
        if it["_type"] == "candlestick" and it.get("canonical_code") and it.get("typical_direction") in ("bullish", "both", "neutral"):
            out.append(f"cdl_{it['id']}")
    have_c = {it["id"] for it in cat.values() if it["_type"] == "candlestick"}
    out += [f"cdx_{x}" for x in CANDLE_X if x in have_c]
    out += [f"cp_{x}" for x in CHART_DETECTORS]
    have = {it["id"] for it in cat.values() if it["_type"] == "market_structure"}
    out += [f"ms_{x}" for x in MS_DETECTORS if x in have]
    from . import advanced, profile, zigzag
    have_cp = {it["id"] for it in cat.values() if it["_type"] == "chart_pattern"}
    out += [f"cp_{x}" for x in zigzag.DETECTORS + advanced.CHART if x in have_cp]
    out += [f"ms_{x}" for x in advanced.MS if x in have]
    try:   # intraday-profile entries join automatically once a year of 5-minute history has been stored
        if profile.ready():
            out += [f"cp_{x}" for x in profile.ENTRIES["chart_pattern"] if x in have_cp]
            out += [f"ms_{x}" for x in profile.ENTRIES["market_structure"] if x in have]
    except Exception:
        pass
    return out


def signals(fam, B, p):
    if fam.startswith("cdl_"):
        it = get("candlestick", fam[4:])
        out = cdl_panel(it["canonical_code"], B)
        e = (out > 0) & B["above200"] & B["member"]       # bullish reading, long-term uptrend context
        return e.fillna(False), f"{it['name']} candle (TA-Lib {it['canonical_code']}) in an uptrend"
    if fam.startswith("cdx_"):
        it = get("candlestick", fam[4:])
        e = candle_x(fam[4:], B) & B["member"]
        return e.fillna(False), f"{it['name']} candle (library v2 rule)"
    if fam.startswith("cp_"):
        pid = fam[3:]
        it = get("chart_pattern", pid)
        return chart_signal(pid, B, p), f"{it['name']} breakout (confirmed close)"
    if fam.startswith("ms_"):
        it = get("market_structure", fam[3:])
        return ms_signal(fam[3:], B, p), f"{it['name']} (market structure, completed bar)"
    raise ValueError(fam)
