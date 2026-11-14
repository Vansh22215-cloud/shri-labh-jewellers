import numpy as np
import pandas as pd

from swing import positional as pos


def _trend(n=400, seed=1):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(0.002 + 0.01 * rng.standard_normal(n)))
    o = np.r_[c[0], c[:-1]]
    d = pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.005, "low": np.minimum(o, c) * 0.995, "close": c,
                      "volume": 1e5}, index=pd.bdate_range("2024-01-01", periods=n))
    d["raw_close"] = d["close"]
    return d


def test_signal_only_on_a_buy_bar_near_the_high(monkeypatch):
    a = _trend()
    from swing import rolling_profile
    s = rolling_profile.signals(a[["open", "high", "low", "close", "volume"]].tail(400), "price")
    buys = np.where(s["buy"].values)[0]
    assert len(buys)                                         # an uptrend gives BUY signals
    k = buys[-1]
    sg = pos.signal(a.iloc[:k + 1])
    c = a["close"].iloc[:k + 1]
    if c.iloc[-1] >= 0.9 * c.tail(250).max():
        assert sg and sg["stop"] < sg["close"] and 7 <= sg["bands"] <= 12
    assert pos.signal(a.iloc[:k]) is None or s["buy"].values[k - 1]


def test_send_evening_respects_room_and_format(monkeypatch, tmp_path):
    from swing import live_engine as le
    monkeypatch.setattr(le, "TIPS_F", tmp_path / "tips.csv")
    sent = []
    monkeypatch.setattr(le, "send", lambda text, label="trade tip": sent.append(text))
    sigs = [{"symbol": f"S{i}", "close": 100.0, "stop": 90.0, "anchor": 97.0, "bands": 9, "from_high_pct": -2.0}
            for i in range(5)]
    n = pos.send_evening("2026-11-14", {"capital": 45000, "positional_max_new": 2, "positional_max_open": 4}, sigs)
    assert n == 2 and len(sent) == 2
    assert "Positional trade" in sent[0] and "RANK - 6/10" in sent[0] and "SELL signal" in sent[0]
    n2 = pos.send_evening("2026-11-15", {"capital": 45000, "positional_max_new": 5, "positional_max_open": 4}, sigs[2:])
    assert n2 == 2                                            # 4 open at most
