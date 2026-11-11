"""Intraday setup library (D96) - ONE place for every setup, used by the live engine (on the bar that just closed) and
by the weekly Kite-history test (whole days), so what is tested is exactly what is sent. The same rules are drawn
on TradingView by tradingview/swing_system_setups.pine.

Each function takes ONE stock's 5-minute bars of ONE day (index = bar start, IST) and returns the FIRST trigger of
each direction: {setup, side, entry_time, entry, stop, target}. A trigger only uses bars up to and including its
own bar (no look-ahead). All levels are on completed bars.

  ORB      opening-range breakout (09:15-09:30 range), stop = range middle, target 1R      (intraday_paper)
  FLAG     bull flag after a 1.5% opening run, stop = flag low, target 2R                     (intraday_paper)
  BOUNCE   2.5% down + RSI(14) < 25, first bar closing above the previous high; target 1R     (intraday_paper)
  VWAP     close crosses VWAP after >= 6 of 7 bars on the other side, volume above average; target 1.5R
  RANGE    close beyond the last 12 bars' high/low on 1.5x volume, after 10:00; stop = range middle; target 2R
  EMAPB    trend pullback: EMA9 > EMA21 and price above VWAP, a bar dips to EMA21 and closes back above it, bullish
           bar; stop = bar low; target 2R (mirror for shorts)
  INSIDE   inside bar, then a close beyond the mother bar; stop = other side of the mother bar; target 1.5R
  GAPGO    gap of 1%+ at the open, first bar in the gap's direction, first close beyond the first bar; stop = other
           side of the first bar; target 2R
"""
import numpy as np
import pandas as pd


def _vwap(b):
    tp = (b["high"] + b["low"] + b["close"]) / 3
    return (tp * b["volume"]).cumsum() / b["volume"].replace(0, np.nan).cumsum()


def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def _first(out, setup, side, ts, entry, stop, r_mult):
    if any(o["setup"] == setup and o["side"] == side for o in out):
        return
    risk = (entry - stop) if side == "buy" else (stop - entry)
    if risk <= 0 or risk / entry < 0.002:
        return
    tgt = entry + r_mult * risk if side == "buy" else entry - r_mult * risk
    out.append({"setup": setup, "side": side, "entry_time": ts, "entry": float(entry), "stop": float(stop),
                "target": float(tgt)})


def vwap_cross(b):
    out = []
    if len(b) < 10:
        return out
    vw = _vwap(b)
    av = b["volume"].rolling(20, min_periods=5).mean().shift(1)
    c = b["close"]
    for i in range(8, len(b)):
        below = (c.iloc[i - 7:i] < vw.iloc[i - 7:i]).sum() >= 6
        above = (c.iloc[i - 7:i] > vw.iloc[i - 7:i]).sum() >= 6
        vol_ok = b["volume"].iloc[i] > (av.iloc[i] or 0)
        if below and c.iloc[i - 1] < vw.iloc[i - 1] and c.iloc[i] > vw.iloc[i] and vol_ok:
            _first(out, "VWAP", "buy", b.index[i], c.iloc[i], b["low"].iloc[i - 5:i + 1].min(), 1.5)
        if above and c.iloc[i - 1] > vw.iloc[i - 1] and c.iloc[i] < vw.iloc[i] and vol_ok:
            _first(out, "VWAP", "sell", b.index[i], c.iloc[i], b["high"].iloc[i - 5:i + 1].max(), 1.5)
    return out


def range_break(b, n=12):
    out = []
    if len(b) < n + 2:
        return out
    av = b["volume"].rolling(20, min_periods=5).mean().shift(1)
    for i in range(n, len(b)):
        ts = b.index[i]
        if ts.hour * 60 + ts.minute < 10 * 60:
            continue
        hi, lo = b["high"].iloc[i - n:i].max(), b["low"].iloc[i - n:i].min()
        mid = (hi + lo) / 2
        c, v = b["close"].iloc[i], b["volume"].iloc[i]
        if v < 1.5 * (av.iloc[i] or np.inf):
            continue
        if c > hi:
            _first(out, "RANGE", "buy", ts, c, mid, 2.0)
        elif c < lo:
            _first(out, "RANGE", "sell", ts, c, mid, 2.0)
    return out


def ema_pullback(b):
    out = []
    if len(b) < 25:
        return out
    e9, e21, vw = _ema(b["close"], 9), _ema(b["close"], 21), _vwap(b)
    for i in range(22, len(b)):
        o, h, l, c = (b[k].iloc[i] for k in ("open", "high", "low", "close"))
        if e9.iloc[i] > e21.iloc[i] and c > vw.iloc[i] and l <= e21.iloc[i] < c and c > o:
            _first(out, "EMAPB", "buy", b.index[i], c, l, 2.0)
        if e9.iloc[i] < e21.iloc[i] and c < vw.iloc[i] and h >= e21.iloc[i] > c and c < o:
            _first(out, "EMAPB", "sell", b.index[i], c, h, 2.0)
    return out


def inside_break(b):
    out = []
    for i in range(3, len(b)):
        mh, ml = b["high"].iloc[i - 2], b["low"].iloc[i - 2]
        if b["high"].iloc[i - 1] < mh and b["low"].iloc[i - 1] > ml:     # bar i-1 inside bar i-2
            c = b["close"].iloc[i]
            if c > mh:
                _first(out, "INSIDE", "buy", b.index[i], c, ml, 1.5)
            elif c < ml:
                _first(out, "INSIDE", "sell", b.index[i], c, mh, 1.5)
    return out


def gap_go(b, prev_close):
    out = []
    if not prev_close or len(b) < 2:
        return out
    o1, h1, l1, c1 = (b[k].iloc[0] for k in ("open", "high", "low", "close"))
    gap = o1 / prev_close - 1
    for i in range(1, min(len(b), 12)):
        c = b["close"].iloc[i]
        if gap >= 0.01 and c1 > o1 and c > h1:
            _first(out, "GAPGO", "buy", b.index[i], c, l1, 2.0)
            break
        if gap <= -0.01 and c1 < o1 and c < l1:
            _first(out, "GAPGO", "sell", b.index[i], c, h1, 2.0)
            break
    return out


def all_signals(b, prev_close=None):
    """Every setup's first trigger(s) on one stock-day."""
    from .intraday_paper import signals
    out = signals(b, prev_close)
    for fn in (vwap_cross, range_break, ema_pullback, inside_break):
        try:
            out += fn(b)
        except Exception:
            pass
    try:
        out += gap_go(b, prev_close)
    except Exception:
        pass
    return out


WORDS = {"ORB": "opening-range breakout", "FLAG": "flag breakout", "BOUNCE": "oversold bounce",
         "VWAP": "VWAP reclaim", "RANGE": "range breakout", "EMAPB": "trend pullback to EMA",
         "INSIDE": "inside-bar breakout", "GAPGO": "gap and go", "SWING": "swing setup"}
