import pandas as pd

from swing import abnormal


def test_daily_loss_limit(monkeypatch):
    monkeypatch.setattr(abnormal.data_prices, "load", lambda s: None)
    tips = pd.DataFrame({"status": ["closed", "closed"], "exit_date": ["2026-11-03", "2026-11-03"], "pnl": [-600, -400]})
    assert any("Daily loss" in r for r in abnormal.check(45000, tips, "2026-11-03"))
    assert abnormal.check(45000, tips, "2026-11-04") == []


def test_vix_spike(monkeypatch):
    idx = pd.bdate_range("2026-01-01", periods=3)
    vix = pd.DataFrame({"close": [14, 14, 18]}, index=idx)
    monkeypatch.setattr(abnormal.data_prices, "load", lambda s: vix if s == "INDIAVIX" else None)
    assert any("VIX" in r for r in abnormal.check(45000))
