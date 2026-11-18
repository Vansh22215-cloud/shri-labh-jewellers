"""VANTAGE live scorecard: every tip scored, open and closed, against the test; no owner data."""
import numpy as np
import pandas as pd

from swing import scorecard, vantage


def test_scores_open_and_closed_tips(monkeypatch, tmp_path):
    monkeypatch.setattr(vantage, "SIGNALS_F", tmp_path / "sig.csv")
    monkeypatch.setattr(scorecard, "CSV", tmp_path / "sc.csv")
    monkeypatch.setattr(scorecard, "MD", tmp_path / "sc.md")
    monkeypatch.setattr(vantage, "calibration", lambda: {"RCP": {"win_pct": 46, "avg_pct": 4.0}})
    pd.DataFrame([
        {"sym": "AAA", "signal": "2026-11-17", "setup": "RCP", "tier": "", "score": "1", "close": "100", "stop": "84",
         "likely": "46", "status": "open", "sent_at": "x", "exit_date": "", "exit_why": "", "exit_price": "", "limit_test": "99"},
        {"sym": "BBB", "signal": "2026-11-17", "setup": "RCP", "tier": "", "score": "1", "close": "200", "stop": "170",
         "likely": "46", "status": "closed", "sent_at": "x", "exit_date": "2026-11-18", "exit_why": "Stop-loss (live)",
         "exit_price": "170", "limit_test": ""}]).to_csv(vantage.SIGNALS_F, index=False)
    idx = pd.bdate_range("2026-11-17", periods=3)
    d = pd.DataFrame({"open": 100.0, "high": 112.0, "low": [98.0, 98.5, 105.0], "close": [100.0, 105.0, 110.0],
                      "volume": 1e6}, index=idx)
    S = scorecard.build(load=lambda s: d, today="20 Nov 2026")
    a, b = S[S.sym == "AAA"].iloc[0], S[S.sym == "BBB"].iloc[0]
    assert a["status"] == "open" and a["result_pct"] == 10.0 and a["trading_days"] == 2 and a["limit_test_fill"] == "yes"
    assert b["status"] == "closed" and b["result_pct"] == -15.35
    md = (tmp_path / "sc.md").read_text()
    assert "Tips sent: **2**" in md and "won 0 of 1" in md and "46% / 4.0%" in md
    assert "capital" not in md.lower() and "bought" not in md.lower()
