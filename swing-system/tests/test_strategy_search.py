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


def test_expiry_day_option_with_no_move_is_closed_and_market_read_is_sent():
    from swing import autotrader, paper
    DAY, m = _gap_day()
    idx = pd.date_range(DAY + timedelta(hours=9, minutes=15), DAY + timedelta(hours=15, minutes=29), freq="1min")
    m.data["NFO:NIFTYTEST"] = pd.DataFrame({"open": 99.0, "high": 100.5, "low": 98.5, "close": 99.0, "volume": 1.0}, index=idx)
    b = paper.Broker(None, start=50800)
    sent = []
    e = autotrader.Engine(b, m, params={"stk_max_trades": 0, "opt_max_trades": 0}, notify=lambda k, x: sent.append(x))
    t0 = DAY + timedelta(hours=9, minutes=40)
    pos = b.open_position("OPT-T", "NIFTY TEST CALL", "NFO:NIFTYTEST", "OPT", "LONG", 65, 100.0, 70.0, 160.0,
                          "NIFTY options", t0, lots=1)
    pos.expiry = str(DAY.date())
    t = t0
    while t <= DAY + timedelta(hours=10, minutes=20):
        e.on_minute(t)
        t += timedelta(minutes=1)
    assert not b.acc.open and "time decay" in b.acc.closed[0]["why"]
    assert any("Market at 09:45" in x and "not a trade signal" in x for x in sent)


def test_five_day_stock_rule_runs_small_when_no_stock_strategy_passed(monkeypatch, tmp_path):
    from swing import practice_live as pl
    monkeypatch.setattr(pl, "DATA", tmp_path)
    (tmp_path / "practice_params.json").write_text('{"stk_max_trades": 0, "opt_strategy": "n_pdh_break"}')
    p = pl.practice_params()
    assert p["stk_max_trades"] == 3 and p["stk_risk"] == 500 and p["stk_strategy"] is None
    assert p["opt_strategy"] == "n_pdh_break"
    (tmp_path / "practice_params.json").write_text('{"stk_rules": [["gap_fade", 0.02, 1, 1]], "stk_strategy": "rules"}')
    assert pl.practice_params()["stk_strategy"] == "rules"


def test_option_exit_modes_on_a_tip_like_trend_day():
    # like the owner's 9:26 tip: +1R quickly, back to the entry once, then a big run
    path = np.r_[np.linspace(100, 125, 5), np.linspace(125, 100.5, 4), np.linspace(101, 300, 30), [300] * 20]
    o = np.r_[100.0, path[:-1]]
    h, l, c = np.maximum(o, path) + 0.5, np.minimum(o, path) - 0.5, path
    ends = np.array([f"{(555 + 5 * i) // 60:02d}:{(555 + 5 * i) % 60:02d}" for i in range(len(path))])
    cost = ss.sim_opt(o, h, l, c, ends, 1, 100.0, 0.2, 2.0, "cost")
    keep = ss.sim_opt(o, h, l, c, ends, 1, 100.0, 0.2, 2.0, "keep")
    trail = ss.sim_opt(o, h, l, c, ends, 1, 100.0, 0.2, 2.0, "trail")
    assert cost[1] == "stop" and cost[0] == 100.0                  # shaken out at the entry
    assert keep[1] == "target" and keep[0] == 300.0                # held to +200%
    assert trail[0] >= cost[0]                                     # a 1R trail is never worse than cost here
    p2 = np.r_[np.linspace(100, 125, 5), np.linspace(124, 112, 4), np.linspace(113, 300, 30), [300] * 20]
    o2 = np.r_[100.0, p2[:-1]]                                     # a shallower dip: the trail survives it
    t2 = ss.sim_opt(o2, np.maximum(o2, p2) + 0.5, np.minimum(o2, p2) - 0.5, p2, ends, 1, 100.0, 0.2, 5.0, "trail")
    assert t2[0] > 200


def test_new_strategies_from_the_tips_fire_and_never_peek():
    for name, fn in (("rs_divergence", SL.rs_divergence), ("trend_pullback", SL.trend_pullback),
                     ("n_trend_pullback", SL.n_trend_pullback)):
        for seed in range(10):
            o, h, l, c, v, e = day_arrays(seed)
            nif = (24000.0, {int(x): 24000 * (1 + 0.004 * (k % 3 - 1)) for k, x in enumerate(e)})
            full = fn(SL.ctx(o, h, l, c, v, e, 100.0, 101.0, 99.0, 0.0, nifty=nif))
            for i in range(2, len(c), 9):
                part = fn(SL.ctx(o[:i + 1], h[:i + 1], l[:i + 1], c[:i + 1], v[:i + 1], e[:i + 1], 100.0, 101.0, 99.0,
                                 0.0, nifty=nif))
                assert part[0][-1] == full[0][i] and part[1][-1] == full[1][i], (name, seed, i)
    # a stock 2% down at 10:30 while NIFTY is up 0.5%, at its low, below VWAP -> short
    c = np.r_[np.linspace(100, 98, 16)]
    o = np.r_[100.0, c[:-1]]
    e = 560 + 5 * np.arange(16)
    nif = (24000.0, {int(x): 24120.0 for x in e})
    lg, sh = SL.rs_divergence(SL.ctx(o, o + 0.05, c - 0.05, c, np.ones(16), e, 100.0, 101.0, 99.0, 0.0, nifty=nif))
    assert sh[-1] and not lg.any()


def test_live_trailing_stop_follows_the_best_price():
    from swing import autotrader, paper
    from swing.replay import Market
    b = paper.Broker(None, start=50800)
    e = autotrader.Engine(b, Market({}, None, lambda s: None))
    pos = b.open_position("OPT-T", "NIFTY X CALL", "NFO:X", "OPT", "LONG", 65, 100.0, 80.0, 300.0, "NIFTY options",
                          pd.Timestamp("2026-11-23 09:40"), lots=1)
    pos.exit_mode, pos.r_frac = "trail", 0.2
    a = pos.avg
    e._opt_exit_rule(pos, a * 1.1)
    assert pos.stop < a                                            # not yet +1R
    e._opt_exit_rule(pos, a * 1.5)
    assert pos.stop == round(a * 1.5 * 0.8, 2)                    # trails 1R below the best
    e._opt_exit_rule(pos, a * 1.3)
    assert pos.stop == round(a * 1.5 * 0.8, 2)                    # never moves down
