"""D118 breakout tips: the live rule is EXACTLY the rule that passed the pre-registered 13-year test."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "validation")
from swing import breakout  # noqa: E402


def _bars(seed=3, n=700):
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0008, 0.018, n)
    r[400:440] = rng.normal(0, 0.004, 40)          # a quiet base ...
    r[440] = 0.06                                  # ... then a breakout
    c = 100 * np.exp(np.cumsum(r))
    o = c * (1 + rng.normal(0, 0.004, n))
    h = np.maximum(o, c) * (1 + abs(rng.normal(0, 0.006, n)))
    l = np.minimum(o, c) * (1 - abs(rng.normal(0, 0.006, n)))
    v = rng.integers(80_000, 120_000, n).astype(float)
    v[440] = 400_000
    idx = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v, "raw_close": c}, index=idx)


def test_live_signal_equals_research_rule_without_lookahead():
    import new_strategies_research as nr
    a = _bars()
    m = np.ones(len(a), bool)
    want = np.asarray(nr.s_brk52("X", a, m)[0], bool) | np.asarray(nr.s_vcp("X", a, m)[0], bool)
    got = np.array([breakout.signal(a.iloc[:k + 1]) is not None for k in range(len(a))])
    assert want[260:].sum() > 0                                  # the test series really contains breakouts
    assert (got[260:] == want[260:]).all()                       # same days, using only data up to each day


def test_breakout_tip_message_and_sizing(monkeypatch):
    from swing import live_engine as le
    sent = []
    monkeypatch.setattr(le, "send", lambda text, label="trade tip": sent.append(text))
    s = {"capital": 45000, "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25}}
    sg = {"symbol": "ABC", "close": 500.0, "stop": 470.0, "why": "52-week-high breakout on volume", "both": False,
          "vol_x": 2.3, "exit_level": 455.0}
    assert breakout.send_evening("2026-11-17", s, [sg]) == 1
    msg = sent[0]
    assert "Breakout trade" in msg and "Buy #ABC" in msg and "50-day average" in msg and "/bought ABC" in msg
    t = le.load_tips()
    assert t["setup"].iloc[0] == "BRK" and int(t["qty"].iloc[0]) == 15     # 1% of 45,000 / 30 = 15 (order 7,500)
    assert breakout.send_evening("2026-11-18", s, [sg]) == 0               # never twice while open
