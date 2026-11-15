import numpy as np
import pandas as pd

from swing import oneoff_picks as op


def test_table_and_quantities(monkeypatch):
    rng = np.random.default_rng(5)
    def hist(sym, interval="day", days=730):
        c = 100 * np.exp(np.cumsum(0.003 + 0.01 * rng.standard_normal(500)))
        o = np.r_[c[0], c[:-1]]
        return pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.01, "low": np.minimum(o, c) * 0.99, "close": c,
                             "volume": 5e6}, index=pd.bdate_range("2024-11-01", periods=500))
    import swing.kite as k
    monkeypatch.setattr(k, "historical", hist)
    monkeypatch.setattr(k, "quotes", lambda s: {})
    monkeypatch.setattr("swing.high_prob.universe", lambda: [f"S{i}" for i in range(30)])
    monkeypatch.setattr("swing.tipcheck.equity_list", lambda: pd.DataFrame({"SYMBOL": [f"S{i}" for i in range(30)]}))
    monkeypatch.setattr("swing.orderflow.sectors", lambda syms: {s: f"G{i}" for i, s in enumerate(syms)})
    req = {"capital": 15000, "n": 5, "sl_pct": 10}
    out, n, bar = op.pick(req)
    assert n == 30 and len(out) <= 5
    assert sum(o["qty"] * o["last"] for o in out) <= 15000 + 1e-6
    t = op.table(out, req, n, bar)
    assert "SL (-10%)" in t and "Kite data" in t
