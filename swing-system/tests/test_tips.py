"""Live tips: quantity, one tip per stock, stop/target exits, kill switch, day strategies at 3:20 pm."""
from datetime import datetime

import pandas as pd
import pytest

from swing import live_feed as lf, strategy, tips
from swing.strategy import Strategy

S = {"capital": 51000, "stop_loss_pct": 1.0, "kill_switch": False, "live_strategies": ["toy"],
     "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25, "daily_loss_pct": 2}}


class Toy(Strategy):
    name, interval, kind = "toy", "5minute", "intraday"

    def entries(self, d):
        return d["close"] > d["open"]


class Feed:
    def __init__(self):
        self.builder = lf.CandleBuilder({1: "AAA"})


def tick(b, hh, mm, ss, ltp, vol):
    b.tick({"token": 1, "ltp": ltp, "volume": vol, "open": 100, "high": 110, "low": 90, "close": 99},
           datetime(2026, 11, 20, hh, mm, ss))


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(tips, "load_settings", lambda: S)
    monkeypatch.setattr(strategy, "load_all", lambda: {"toy": Toy()})
    monkeypatch.setattr(tips, "_HIST", {})
    from swing import candles
    prev = pd.DataFrame({"open": [99.0] * 3, "high": [100.0] * 3, "low": [98.0] * 3, "close": [99.5] * 3, "volume": [1e3] * 3},
                        index=pd.date_range("2026-11-19 15:10", periods=3, freq="5min"))
    monkeypatch.setattr(candles, "load", lambda *a, **k: prev)
    return Feed()


def test_quantity_rules():
    assert tips.quantity(100, 99, S) == 127               # 25% cap (12,750) binds before the 1% risk (510 shares)
    assert tips.quantity(100, 99, {**S, "capital": 0}) == 0


def test_tip_then_stop_exit(env, request):
    f = env
    for i in range(5):                                     # 9:15-9:19 rising: the 9:15 5-minute candle is green
        tick(f.builder, 9, 15 + i, 5, 100 + i * 0.2, 1000 * (i + 1))
    f.builder.close_minute(datetime(2026, 11, 20, 9, 20))
    sc = tips.Scanner(S)
    assert sc.on_close("5minute", datetime(2026, 11, 20, 9, 20), f, now=datetime(2026, 11, 20, 9, 20)) == 1
    T = tips.load_tips()
    assert len(T) == 1 and T.iloc[0]["stop"] == round(100.8 * 0.99, 2)
    assert sc.on_close("5minute", datetime(2026, 11, 20, 9, 20), f, now=datetime(2026, 11, 20, 9, 20)) == 0   # no repeat
    tick(f.builder, 9, 20, 10, 99.5, 6000)                 # falls below the 1% stop
    f.builder.close_minute(datetime(2026, 11, 20, 9, 21))
    sc.on_close("minute", datetime(2026, 11, 20, 9, 21), f, now=datetime(2026, 11, 20, 9, 21))
    T = tips.load_tips()
    assert T.iloc[0]["why"] == "stop-loss" and T.iloc[0]["net_pct"] < -1
    labels = [l for l, _ in request.node.sent]
    assert labels.count("trade tip") == 1 and labels.count("exit alert") == 1


def test_kill_switch_blocks_new_tips_only(env, monkeypatch):
    monkeypatch.setattr(tips, "load_settings", lambda: {**S, "kill_switch": True})
    f = env
    for i in range(5):
        tick(f.builder, 9, 15 + i, 5, 100 + i * 0.2, 1000 * (i + 1))
    f.builder.close_minute(datetime(2026, 11, 20, 9, 20))
    assert tips.Scanner(S).on_close("5minute", datetime(2026, 11, 20, 9, 20), f, now=datetime(2026, 11, 20, 9, 20)) == 0


def test_only_approved_strategies_send(env):
    assert tips.Scanner({**S, "live_strategies": []}).strategies == {}
