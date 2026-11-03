import numpy as np
import pandas as pd

from swing import intraday


def _cube(bars):
    """bars: list of days, each a list of 7 (o,h,l,c) tuples for ONE stock."""
    D = len(bars)
    cube = {k: np.full((D, 1, 7), np.nan) for k in "ohlcv"}
    for d, day in enumerate(bars):
        for k, (o, h, l, c) in enumerate(day):
            cube["o"][d, 0, k], cube["h"][d, 0, k], cube["l"][d, 0, k], cube["c"][d, 0, k] = o, h, l, c
            cube["v"][d, 0, k] = 1000
    days = pd.bdate_range("2025-01-01", periods=D)
    ctx = {"prev_close": np.vstack([[[np.nan]], cube["c"][:-1, :, 6]]), "up": np.ones((D, 1), bool),
           "dn": np.zeros((D, 1), bool), "rvol": np.ones((D, 1))}
    return days, ["A"], cube, ctx


flat = [(100, 100.5, 99.5, 100)] * 7


def test_mis_costs_small():
    c = intraday.mis_costs(20000, 20000)
    assert 5 < c < 30          # ~Rs 17 for a Rs 20k intraday round trip


def test_orb_enters_next_bar_and_stops_first():
    # first hour range 99-101; bar 1 closes 101.5 (> high) -> entry at bar 2 open 101.6;
    # bar 2 touches both stop 99 and target -> stop assumed first
    day = [(100, 101, 99, 100.5), (100.5, 101.6, 100.4, 101.5), (101.6, 105, 98.5, 100)] + [(100, 100.2, 99.8, 100)] * 4
    days, syms, cube, ctx = _cube([flat, day])
    v = {"strategy": "orb_long", "target_r": 1.0, "stop": "range", "trend_filter": True, "max_trades": 1, "name": "x"}
    eq, tr = intraday.run(days, syms, cube, ctx, v)
    t = tr.iloc[0]
    assert abs(t["entry"] - 101.6 * (1 + intraday.SLIP)) < 0.01
    assert t["reason"] == "stop" and t["pnl"] < 0


def test_squareoff_at_1515_open():
    day = [(100, 101, 99, 100.5), (100.5, 101.6, 100.4, 101.5)] + [(101.6, 101.8, 101.0, 101.7)] * 4 + [(102, 102, 101.9, 102)]
    days, syms, cube, ctx = _cube([flat, day])
    v = {"strategy": "orb_long", "target_r": None, "stop": "range", "trend_filter": False, "max_trades": 1, "name": "x"}
    _, tr = intraday.run(days, syms, cube, ctx, v)
    assert tr.iloc[0]["reason"] == "squareoff"
    assert abs(tr.iloc[0]["exit"] - 102 * (1 - intraday.SLIP)) < 0.01


def test_signal_uses_only_closed_bars():
    # breakout happens only in the LAST tradable bar (13:15 close) -> entry at 14:15, never earlier
    day = [(100, 101, 99, 100)] + [(100, 100.8, 99.5, 100)] * 3 + [(100, 101.4, 100, 101.3), (101.3, 101.5, 101, 101.2), (101.2, 101.3, 101, 101.1)]
    days, syms, cube, ctx = _cube([flat, day])
    d, es, st = intraday.signals(cube, ctx, {"strategy": "orb_long", "stop": "range", "trend_filter": False})
    assert d[1, 0] == 1 and es[1, 0] == 5
