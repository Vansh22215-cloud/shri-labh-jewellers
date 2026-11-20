"""Tester (1% stop, targets, gaps, square-off, costs, context) and Learner on hand-made candles."""
import pandas as pd
import pytest

from swing import backtest, candles, learner, strategy
from swing.strategy import Strategy

S = {"capital": 51000, "stop_loss_pct": 1.0, "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25}}


class Toy(Strategy):
    name, interval, kind, targets_r = "toy", "15minute", "intraday", (2.0,)
    description = "buy every candle whose close is above its open"

    def entries(self, d):
        return d["close"] > d["open"]


def bars(rows, start="2026-11-20 09:15", freq="15min"):
    idx = pd.date_range(start, periods=len(rows), freq=freq)
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=idx).astype(float)


def test_stop_is_one_percent_and_gap_is_not_hidden():
    t = Toy()
    d = bars([[99, 100.5, 99, 100, 10], [100, 100.2, 98.9, 99.5, 10], [99.5, 99.6, 99.4, 99.5, 10]])
    tr = backtest.simulate("A", d, t, S)
    assert tr[0]["stop"] == 99.0 and tr[0]["why"] == "stop-loss" and tr[0]["exit"] == 99.0
    d = bars([[99, 100.5, 99, 100, 10], [97, 97.5, 96, 97, 10], [97, 97, 97, 97, 10]])
    tr = backtest.simulate("A", d, t, S)
    assert tr[0]["exit"] == 97.0                           # opened below the stop: sold at the open, not at 99


def test_target_and_stop_in_one_candle_assumes_stop():
    d = bars([[99, 100.5, 99, 100, 10], [100, 102.5, 98.5, 101, 10], [101, 101, 101, 101, 10]])
    assert backtest.simulate("A", d, Toy(), S)[0]["why"] == "stop-loss"
    d = bars([[99, 100.5, 99, 100, 10], [100, 102.5, 99.5, 101, 10], [101, 101, 101, 101, 10]])
    tr = backtest.simulate("A", d, Toy(), S)
    assert tr[0]["why"] == "target" and tr[0]["exit"] == 102.0 and tr[0]["gross_pct"] == 2.0


def test_intraday_square_off_and_costs():
    rows = [[99, 100.5, 99, 100, 10]] + [[100, 100.3, 99.8, 100.1, 10]] * 30
    d = bars(rows, start="2026-11-20 13:00", freq="5min")
    tr = backtest.simulate("A", d, Toy(), S)[0]
    assert tr["why"] == "square-off 3:20 pm" and tr["exit_time"].strftime("%H:%M") == "15:20"
    assert tr["net_pct"] < tr["gross_pct"] and 0.3 < tr["cost_pct"] < 0.5      # intraday charges + 2 x 0.15% slippage


def test_no_entries_after_310():
    d = bars([[99, 100.5, 99, 100, 10]] * 3, start="2026-11-20 15:15", freq="5min")
    assert backtest.simulate("A", d, Toy(), S) == []


def test_run_on_library_reports_kite_only(monkeypatch):
    rows = []
    for k in range(60):
        rows += [[99, 100.5, 99, 100, 10], [100, 102.5, 99.5, 101, 10], [101, 101.2, 100.9, 101, 10]]
    d = bars(rows, freq="15min")
    d.index = pd.date_range("2026-01-01 09:15", periods=len(d), freq="15min")
    candles.store("15minute", "AAA", d)
    monkeypatch.setattr(strategy, "load_all", lambda: {"toy": Toy()})
    T, data = backtest.run("toy", symbols=["AAA", "MISSING"], workers=1)
    assert len(T) and data["stocks_tested"] == 1 and data["stocks_without_kite_candles"] == 1
    txt = (backtest.OUT / "toy.md").read_text()
    assert "Kite Connect historical candles" in txt and "Yahoo: not used" in txt
    assert {"time_of_day", "weekday", "rel_volume"} <= set(T.columns)


def test_learner_reasons_groups_and_ideas():
    rows = []
    for i in range(200):
        bad = i % 4 == 0
        rows.append({"sym": "A", "entry": 100, "stop": 99, "exit": 99 if bad else 102, "why": "stop-loss" if bad else "target",
                     "bars": 1 if bad else 5, "net_pct": -1.3 if bad else 1.7, "best_pct": 0.1 if bad else 2.0,
                     "worst_pct": -1.0, "vix": "> 25" if bad else "13-18", "weekday": "Mon"})
    T = pd.DataFrame(rows)
    a = learner.analyse("toy", T, live=pd.DataFrame())
    assert a["test"]["trades"] == 200
    r = {x["reason"]: x["trades"] for x in a["reasons"]}
    assert r["lost: wrong from the start"] == 50 and r["won: reached the target"] == 150
    worse = [g for g in a["groups"] if g["worse"]]
    assert worse and worse[0]["context"] == "vix" and worse[0]["value"] == "> 25"
    assert any("VIX" in i or "vix" in i for i in a["ideas"])
    learner.report("toy", T)
    assert "Where it works" in (learner.OUT / "toy.md").read_text()


def test_loss_reasons():
    base = {"entry": 100, "stop": 99, "bars": 5, "best_pct": 0.1}
    assert learner.loss_reason({**base, "exit": 98, "why": "stop-loss", "net_pct": -2.3}) == "lost: gap through the stop"
    assert learner.loss_reason({**base, "exit": 99, "why": "stop-loss", "net_pct": -1.3, "best_pct": 1.2}) == \
        "lost: was right, gave it back"
    assert learner.loss_reason({**base, "exit": 99.6, "why": "square-off 3:20 pm", "net_pct": -0.7}) == \
        "lost: slow bleed (no stop, no target)"
