"""The Learner: expectation bands, situation buckets, lessons -> research only, alerts once."""
import numpy as np
import pandas as pd

from swing import learning

PROF = {"RCP": {"win_pct": 43, "avg_pct": 3.3, "sd_pct": 19.8, "mae_p90": -16.7}}


def tips(n, res, status="closed", worst=-5.0):
    return pd.DataFrame({"source": "VANTAGE", "type": "VANTAGE Rolling Candle Profile", "status": status,
                         "result_pct": res[:n] if isinstance(res, list) else [res] * n, "worst_pct": worst,
                         "date": "2026-11-17", "exit_date": "2026-11-20"})


def test_expectation_bands():
    assert learning.expectation(tips(5, 2.0), PROF)[0][1] == "too early"
    assert learning.expectation(tips(40, [-8.0] * 30 + [10.0] * 10), PROF)[0][1] == "below expected"
    assert learning.expectation(tips(40, [-5.0] * 22 + [12.0] * 18), PROF)[0][1] == "on track"
    assert learning.expectation(tips(12, 0.0, "open", worst=-20.0), PROF)[0][1] == "early warning"


def test_buckets_and_lessons_go_to_research_only():
    R = pd.DataFrame({"source": "VANTAGE", "status": "closed", "result_pct": [6.0] * 12 + [-2.0] * 12,
                      "market": ["rising"] * 12 + ["falling"] * 12})
    W = learning.when_it_works(R)
    L = learning.lessons(W)
    assert len(L) == 1 and "rising" in L[0]["lesson"] and L[0]["status"].startswith("to research")


def test_alert_once(monkeypatch, tmp_path):
    from swing import telegram
    sent = []
    monkeypatch.setattr(telegram, "send_reliable", lambda s, t, label="": sent.append(label))
    monkeypatch.setattr(learning, "STATE", tmp_path / "st.json")
    E = [("VANTAGE Rolling Candle Profile", "below expected", "x")]
    assert learning.alerts(E, s={}) == 1 and learning.alerts(E, s={}) == 0 and sent == ["system problem"]
