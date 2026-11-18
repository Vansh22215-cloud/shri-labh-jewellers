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


def test_mistake_diagnosis():
    idx = pd.bdate_range("2026-11-02", periods=30)
    flat = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1e6}, index=idx)
    fall = flat.copy(); fall["close"] = np.linspace(100, 85, 30)
    load = lambda s: fall if s == "NIFTY50" else flat
    base = {"symbol": "X", "source": "VANTAGE", "date": "2026-11-02", "entry_date": "2026-11-03", "exit_date": "2026-11-20"}
    assert learning.diagnose(dict(base, status="closed", result_pct=-6, best_pct=7.0), lambda s: flat)[0] == "gave_back"
    assert learning.diagnose(dict(base, status="closed", result_pct=-6, best_pct=0.5), lambda s: flat)[0] == "never_worked"
    assert learning.diagnose(dict(base, status="closed", result_pct=-6, best_pct=2.0), load)[0] == "market_fell"
    assert learning.diagnose(dict(base, status="closed", result_pct=-9, why="stop-loss", stop=90.0, exit=85.0,
                                  best_pct=1.0), lambda s: flat)[0] == "gap_through_stop"
    assert learning.diagnose(dict(base, status="closed", result_pct=4, best_pct=6), lambda s: flat) == ("", "")
    assert learning.diagnose(dict(base, status="open", result_pct=-1, best_pct=2), lambda s: flat) == ("", "")


def test_repeats_and_mistake_lessons():
    R = pd.DataFrame({"source": ["hourly scan", "strategy tip", "strategy tip"], "symbol": ["CYIENT"] * 3,
                      "result_pct": [-1.0, -2.0, -0.5]})
    assert learning.repeats(R).iloc[0]["times"] == 3
    M = pd.DataFrame({"source": "strategy tip", "code": ["never_worked"] * 6 + ["slow_bleed"] * 4, "result_pct": -3.0})
    L = learning.mistake_lessons(M)
    assert len(L) == 1 and "6 of 10" in L[0]["lesson"]


def test_live_stop_label_and_vantage_best_point():
    idx = pd.bdate_range("2026-11-02", periods=6)
    flat = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1e6}, index=idx)
    r = {"symbol": "X", "source": "VANTAGE", "date": "2026-11-02", "entry_date": "2026-11-02", "exit_date": "2026-11-04",
         "status": "closed", "result_pct": -9, "why": "Stop-loss (live)", "stop": 90.0, "exit": 85.0, "best_pct": 1.0}
    assert learning.diagnose(r, lambda s: flat)[0] == "gap_through_stop"
    hot = flat.copy()
    hot.loc[idx[0], "high"] = 130.0                       # the signal day's own high must not count for VANTAGE
    R = pd.DataFrame([dict(r, status="open", entry=100.0, exit=100.0, result_pct=0.0, exit_date="nan")])
    E = learning.enrich(R, lambda s: hot if s != "NIFTY50" else None)
    assert E.iloc[0]["best_pct"] == 1.0
