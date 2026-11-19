import numpy as np
import pandas as pd

from swing import why_engine as we


def _hist(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.date_range("2013-01-01", "2026-06-01", periods=n)
    H = pd.DataFrame({"set": "top300", "setup": "RCP", "signal": d, "days": 40, "why": "Rolling Candle Profile SELL",
                      "ret_6m": rng.random(n), "from_52w_high": -rng.random(n) / 5, "mkt_trend": "rising",
                      "turnover_cr": rng.random(n) * 100, "net": rng.normal(0.03, 0.1, n)})
    H.loc[H["turnover_cr"] > 90, "net"] = -0.05            # the busiest 10% always lose (both periods)
    for c in we.NUM:
        if c not in H:
            H[c] = rng.random(n)
    H["exit_kind"] = H["why"].map(we.exit_kind)
    return H


def test_exit_kinds():
    assert we.exit_kind("Stop-loss (live)") == "stop-loss" and we.exit_kind("Target 2") == "target"
    assert we.exit_kind("Time exit (60 days)") == "time limit"
    assert we.exit_kind("Rolling Candle Profile SELL") == "sell signal"
    assert we.exit_kind("Closed above the 5-day average (dip-buy exit)") == "sell signal"


def test_loser_with_confirmed_pattern_becomes_lead(tmp_path, monkeypatch):
    monkeypatch.setattr(we, "LEADS_F", tmp_path / "leads.json")
    we._H["h"] = _hist()
    R = pd.DataFrame([{"source": "VANTAGE", "type": "VANTAGE Rolling Candle Profile", "symbol": "BIG", "date": "2026-11-20",
                       "status": "closed", "why": "Stop-loss", "result_pct": -6.0, "days": 12, "mistake": "slow_bleed",
                       "nifty_same_days_pct": 0.5, "vs_nifty_pct": -6.5, "results_week": "no", "market": "rising"}])
    x = {c: 0.5 for c in we.NUM} | {"turnover_cr": 99.0, "ret_6m": 0.5, "from_52w_high": -0.1}
    W = we.explain(R, facts=lambda r: x)
    assert W.iloc[0]["surprise"] == "lost, unknown cause"
    assert "turnover_cr high" in W.iloc[0]["lead"] and "confirmed: worse" in W.iloc[0]["history_answer"]
    assert we._leads()["leads"][0]["seen_in"] == ["BIG"]
    we._H.clear()


def test_winner_does_not_create_a_worse_lead(tmp_path, monkeypatch):
    monkeypatch.setattr(we, "LEADS_F", tmp_path / "leads.json")
    we._H["h"] = _hist()
    R = pd.DataFrame([{"source": "VANTAGE", "type": "VANTAGE Rolling Candle Profile", "symbol": "WIN", "date": "2026-11-20",
                       "status": "closed", "why": "Target 2", "result_pct": 60.0, "days": 30, "mistake": "",
                       "nifty_same_days_pct": 1.0, "vs_nifty_pct": 59.0, "results_week": "no", "market": "rising"}])
    x = {c: 0.5 for c in we.NUM} | {"turnover_cr": 99.0}
    W = we.explain(R, facts=lambda r: x)
    assert W.iloc[0]["surprise"].startswith("won") and W.iloc[0]["lead"] == ""
    assert we._leads()["leads"] == []
    we._H.clear()


def test_why_text():
    assert "market carried" in we.why_text({"result_pct": 8, "nifty_same_days_pct": 5})
    assert "results" in we.why_text({"result_pct": -9, "results_week": "yes"})
    assert "gap" in we.why_text({"result_pct": -9, "mistake": "gap_through_stop"})
