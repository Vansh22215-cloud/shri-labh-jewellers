"""Stress: splits / bonuses while a tip is open (82 NSE stocks in 12 months) - no false stop alerts, applied once."""
import pandas as pd

from swing import corp_actions as ca, vantage


def prices(split_day=None, ratio=2.0, n=10):
    idx = pd.bdate_range("2026-11-02", periods=n)
    c = [1000.0] * n
    sp = [0.0] * n
    if split_day is not None:
        k = list(idx).index(pd.Timestamp(split_day))
        c = c[:k] + [x / ratio for x in c[k:]]
        sp[k] = ratio
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1e6, "splits": sp}, index=idx)


def test_split_factor_and_guard():
    d = prices("2026-11-06")
    assert ca.split_factor(d, "2026-11-03") == 2.0 and ca.split_factor(d, "2026-11-06") == 1.0
    assert ca.looks_like_split(500, 1000) and not ca.looks_like_split(800, 1000)   # a real 20% fall still counts


def test_open_vantage_tip_restated_once(monkeypatch, tmp_path):
    monkeypatch.setattr(vantage, "SIGNALS_F", tmp_path / "sig.csv")
    pd.DataFrame([{"sym": "ABC", "signal": "2026-11-03", "setup": "RCP", "tier": "", "score": "1", "close": "1000.00",
                   "stop": "840.00", "likely": "46", "status": "open", "sent_at": "x", "exit_date": "", "exit_why": "",
                   "exit_price": "", "limit_test": "990.00"}]).to_csv(vantage.SIGNALS_F, index=False)
    import swing.live_engine as le
    monkeypatch.setattr(le, "load_tips", lambda: pd.DataFrame())
    d = prices("2026-11-06")
    assert ca.rescale_open_tips(load=lambda s: d) == 1
    S = vantage._load_signals()
    assert float(S.iloc[0]["close"]) == 500.0 and float(S.iloc[0]["stop"]) == 420.0 and float(S.iloc[0]["limit_test"]) == 495.0
    assert ca.rescale_open_tips(load=lambda s: d) == 0                              # never applied twice
