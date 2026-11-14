import numpy as np
import pandas as pd

from swing import high_prob as hp


def _stock(n=260, drop=True):
    idx = pd.bdate_range("2025-01-01", periods=n)
    c = 100 * np.exp(np.linspace(0, 0.9, n))                 # strong uptrend
    if drop:
        c[-3:] = c[-4] * np.array([0.97, 0.94, 0.91])         # sharp 3-day dip
    d = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "adj_close": c, "volume": 1e6}, index=idx)
    return d


def test_signal_needs_strong_stock_and_sharp_dip():
    sg = hp.signal(_stock())
    assert sg and sg["rsi2"] < 2 and sg["stop"] < sg["close"] and sg["sma5"] > sg["close"]
    assert hp.signal(_stock(drop=False)) is None


def test_market_filter():
    idx = pd.bdate_range("2025-01-01", periods=260)
    c = np.linspace(100, 150, 260)
    c[-2:] = [c[-3] * 0.98, c[-3] * 0.96]
    ok, up, r = hp.market_ok(pd.DataFrame({"close": c}, index=idx))
    assert ok and up and r < 20
    ok2, up2, _ = hp.market_ok(pd.DataFrame({"close": c[::-1].copy()}, index=idx))
    assert not ok2 and not up2


def test_evening_sends_format_and_exits(monkeypatch, tmp_path):
    from swing import live_engine as le
    monkeypatch.setattr(le, "TIPS_F", tmp_path / "t.csv")
    sent = []
    monkeypatch.setattr(le, "send", lambda text, label="trade tip": sent.append((label, text)))
    sg = dict(hp.signal(_stock()), symbol="TEMPSENS")
    monkeypatch.setattr(hp, "scan", lambda day=None: ([sg], "dip day"))
    day0 = str(_stock().index[-1].date())
    assert hp.send_evening(day0, {"capital": 45000}) == 1
    lab, txt = sent[0]
    for part in ("Buy #TEMPSENS tomorrow at open", "SL at", "2% Risk", "RANK - ", "5-day average", "tradingview.com"):
        assert part in txt, part
    t = le.load_tips()
    assert t["setup"].iloc[0] == "HP" and t["status"].iloc[0] == "open"
    # bounce: close back above the 5-day average -> sell alert
    up = _stock()
    nxt = up.index[-1] + pd.offsets.BDay(1)
    up.loc[nxt] = [up["close"].iloc[-4]] * 4 + [up["close"].iloc[-4], 1e6]
    monkeypatch.setattr("swing.data_prices.load", lambda s: up)
    msgs = hp.evening_exits(str(nxt.date()))
    assert msgs and "SELL at tomorrow's open" in msgs[0] and le.load_tips()["status"].iloc[0] == "done"


def test_rank_10_only_at_an_order_block():
    from swing import high_prob as hp
    assert hp.rank({"rsi2": 0.1, "ob": None}) == 9
    assert hp.rank({"rsi2": 1.5, "ob": (95.0, 99.0)}) == 10
