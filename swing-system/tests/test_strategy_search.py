"""Strategy search: no strategy peeks at later candles; the whole search runs; the live trader uses the winner."""
import json
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from swing import candles, strategies_lib as SL, strategy_search as ss


def day_arrays(seed, n=75, base=100.0):
    rng = np.random.default_rng(seed)
    c = base * np.exp(np.cumsum(rng.normal(0, 0.006, n)))
    o = np.r_[base * (1 + rng.normal(0, 0.02)), c[:-1]]
    h, l = np.maximum(o, c) * 1.002, np.minimum(o, c) * 0.998
    v = rng.integers(1e3, 5e4, n).astype(float)
    end_m = 560 + 5 * np.arange(n)
    return o, h, l, c, v, end_m


@pytest.mark.parametrize("name", list(SL.STOCK) + list(SL.NIFTY))
def test_no_strategy_looks_ahead(name):
    fn = {**SL.STOCK, **SL.NIFTY}[name]
    for seed in range(15):
        o, h, l, c, v, e = day_arrays(seed)
        full_l, full_s = fn(SL.ctx(o, h, l, c, v, e, 100.0, 101.0, 99.0, -0.05))
        for i in range(2, len(c), 7):
            pl, ps = fn(SL.ctx(o[:i + 1], h[:i + 1], l[:i + 1], c[:i + 1], v[:i + 1], e[:i + 1], 100.0, 101.0, 99.0, -0.05))
            assert pl[-1] == full_l[i] and ps[-1] == full_s[i], (name, seed, i)


def test_gap_fade_signal():
    o = np.array([102.0, 101.0, 100.5]); c = np.array([101.0, 100.6, 100.4])
    x = SL.ctx(o, o + 0.2, c - 0.2, c, np.ones(3), np.array([560, 565, 570]), 100.0, 101.0, 99.0, 0.0)
    assert SL.first_signal(SL.gap_fade, x) == (0, False)          # 2% gap up, red first candle -> short


def test_search_runs_end_to_end(monkeypatch):
    from swing import longtest as lt
    days = pd.bdate_range("2023-06-01", periods=25).append(pd.bdate_range("2024-06-03", periods=25))
    rng = np.random.default_rng(2)
    for sym in ["AAA", "BBB", "NIFTY50"]:
        rows = []
        for d in days:
            idx = pd.date_range(d + pd.Timedelta(hours=9, minutes=15), periods=75, freq="5min")
            c = (24000 if sym == "NIFTY50" else 100) * np.exp(np.cumsum(rng.normal(0.0003, 0.005, 75)))
            o = np.r_[c[0] * (1 + rng.normal(0, 0.015)), c[:-1]]
            rows.append(pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.002, "low": np.minimum(o, c) * 0.998,
                                      "close": c, "volume": rng.integers(1e3, 5e4, 75).astype(float)}, index=idx))
        candles.store("5minute", sym, pd.concat(rows))
    monkeypatch.setattr(candles, "symbols", lambda iv="day": ["NIFTY50", "AAA", "BBB"])
    monkeypatch.setattr(ss, "REPORT", candles.BASE / "ss.md")
    monkeypatch.setattr(ss, "DATA", candles.BASE)
    srows, nrows, rec = ss.run(send=False, workers=1)
    assert len(srows) == len(SL.STOCK) * len(ss.S_EXITS) and len(nrows) == len(SL.NIFTY) * len(ss.N_EXITS)
    assert "goal ₹10,000" in ss.REPORT.read_text()
    p = json.loads((candles.BASE / "practice_params.json").read_text())
    assert "stk_max_trades" in p and "opt_max_trades" in p
    txt = ss.REPORT.read_text()
    assert "Every stock strategy by market condition" in txt


def _gap_day():
    from swing.replay import Market
    DAY = pd.Timestamp("2026-11-18")
    idx = pd.date_range(DAY + timedelta(hours=9, minutes=15), DAY + timedelta(hours=15, minutes=29), freq="1min")
    c = np.r_[np.linspace(102, 100.5, 10), np.full(len(idx) - 10, 100.4)]
    o = np.r_[102.0, c[:-1]]
    stock = pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.05, "low": np.minimum(o, c) - 0.05, "close": c,
                          "volume": 1000.0}, index=idx)
    prev = pd.DataFrame({"open": 99.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000.0},
                        index=pd.date_range(DAY - timedelta(days=1) + timedelta(hours=9, minutes=15), periods=375, freq="1min"))
    m = Market({"NIFTY50": stock * 240, "AAA": pd.concat([prev, stock])}, None, lambda s: None)
    m.set_day(DAY)
    return DAY, m


@pytest.mark.parametrize("align,expect", [(1, True), (-1, False)])
def test_live_trader_uses_a_strategy_only_in_its_market_condition(align, expect):
    from swing import autotrader, paper
    DAY, m = _gap_day()
    b = paper.Broker(None, start=50800)
    e = autotrader.Engine(b, m, params={"stk_strategy": "rules", "stk_rules": [["gap_fade", 0.02, align, 1]],
                                        "stk_max_trades": 3, "opt_max_trades": 0})
    t = DAY + timedelta(hours=9, minutes=16)
    while t <= DAY + timedelta(hours=10):
        e.on_minute(t)
        t += timedelta(minutes=1)
    trades = list(b.acc.open.values()) + b.acc.closed
    assert bool(trades) == expect                # the gap-fade short goes WITH a falling NIFTY: only align +1 fits
    if expect:
        p = trades[0]
        side = p.side if hasattr(p, "side") else p["side"]
        assert side == "SHORT"


def test_live_trader_takes_a_library_strategy_signal():
    from swing import autotrader, paper
    from swing.replay import Market
    DAY = pd.Timestamp("2026-11-18")
    idx = pd.date_range(DAY + timedelta(hours=9, minutes=15), DAY + timedelta(hours=15, minutes=29), freq="1min")
    c = np.r_[np.linspace(102, 100.5, 10), np.full(len(idx) - 10, 100.4)]
    o = np.r_[102.0, c[:-1]]
    stock = pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.05, "low": np.minimum(o, c) - 0.05, "close": c,
                          "volume": 1000.0}, index=idx)
    prev = pd.DataFrame({"open": 99.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000.0},
                        index=pd.date_range(DAY - timedelta(days=1) + timedelta(hours=9, minutes=15), periods=375, freq="1min"))
    data = {"NIFTY50": stock * 240, "AAA": pd.concat([prev, stock])}
    b = paper.Broker(None, start=50800)
    m = Market(data, None, lambda s: None)
    m.set_day(DAY)
    e = autotrader.Engine(b, m, params={"stk_strategy": "gap_fade", "stk_max_trades": 3, "opt_max_trades": 0})
    t = DAY + timedelta(hours=9, minutes=16)
    while t <= DAY + timedelta(hours=10):
        e.on_minute(t)
        t += timedelta(minutes=1)
    trades = [p for p in list(b.acc.open.values())] + b.acc.closed
    assert trades and (trades[0].side if hasattr(trades[0], "side") else trades[0]["side"]) == "SHORT"


def test_owner_rules_one_percent_stop_and_manual_trade_messages():
    from swing import autotrader, paper
    from swing.replay import Market
    e = autotrader.Engine(paper.Broker(None, start=50800), Market({}, None, lambda s: None), params={"stk_stop": 0.015})
    assert e.p["stk_stop"] == 0.01
    r = lambda strat, stop, d, rc: {"strategy": strat, "stop": stop, "target": 0.02, "dev": {"avg_day": d},
                                    "recent": {"avg_day": rc}}
    assert not ss._usable(r("gap_fade", 0.015, 500, 500), True)        # not the owner's 1% stop
    assert not ss._usable(r("gap_fade", 0.01, 206, 11), True)          # +₹11 a day is break-even noise
    assert ss._usable(r("gap_fade", 0.01, 206, 150), True)

    class Pos:
        side, name, symbol, kind, qty, lots, avg, stop, target, note, t1 = ("LONG", "NIFTY 24200 CE", "NFO:NIFTY26N2424200CE",
                                                                         "OPT", 65, 1, 120.0, 96.0, 240.0, "x", None)
    txt = autotrader.Engine.entry_text(Pos)
    assert "NIFTY26N2424200CE" in txt and "SL order at ₹96.00" in txt and "₹132.00" in txt


def test_capital_protection_caps_win_over_test_settings():
    from swing import autotrader, paper
    from swing.replay import Market
    b = paper.Broker(None, start=50800)
    e = autotrader.Engine(b, Market({}, None, lambda s: None),
                          params={"opt_risk": 6240, "stk_risk": 2400, "day_max_loss": 12500, "day_target": 10000})
    assert (e.p["opt_risk"], e.p["stk_risk"], e.p["day_max_loss"]) == (2500, 1000, 3000)
    assert e.p["day_target"] == float("inf")
    e.day = pd.Timestamp("2026-11-23")
    assert e._room() == 3000
