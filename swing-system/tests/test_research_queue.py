import pandas as pd

from swing import research_queue as rq


def test_family_rates_smoothed_and_skips_explorations():
    X = [{"family": "exit", "verdict": "fail"}, {"family": "exit", "verdict": "PASS - live"},
         {"family": "money", "verdict": "near miss"}, {"family": "x", "verdict": "no fix needed / not worth a test"}]
    r = rq.family_rates(X)
    assert r["exit"] == (2, 1.0, 0.5) and r["money"][1] == 0.5 and "x" not in r


def test_rank_puts_broken_belief_first_and_pushes_down_retests(tmp_path, monkeypatch):
    monkeypatch.setattr(rq, "OUT", tmp_path / "q.md")
    checks = [("B2", "3:20 pm beats next open", "proven", "broken", "next open +0.5%", "x"),
              ("B1", "stock choice", "proven", "holding", "", "y")]
    q = pd.DataFrame([{"situation": "market_mood", "lesson": "calm better", "evidence": "strong", "status": "to research"},
                      {"situation": "weekday", "lesson": "Fri better", "evidence": "strong", "status": "to research"},
                      {"situation": "weekday", "lesson": "old", "evidence": "strong", "status": "tested"}])
    rates = {"adversarial": (3, 2, 0.6), "filter": (7, 0, 0.11)}
    C = rq.rank(rq.candidates(checks, q, missed_n=5), rates)
    assert C[0]["kind"] == "belief" and len(C) == 3
    mood = next(c for c in C if "calm" in c["idea"]); fri = next(c for c in C if "Fri" in c["idea"])
    assert mood["tested"] and mood["score"] < fri["score"]
    L = rq.write(C, rates, today="19 Nov 2026")
    assert "THIS WEEK" in L[-3] and "later" in L[-1] and (tmp_path / "q.md").exists()


def test_missed_only_when_many():
    assert not rq.candidates(missed_n=5)
    assert rq.candidates(missed_n=12)[0]["kind"] == "missed"


def test_portfolio_risk_sizes_live_channels_only(monkeypatch):
    from swing import learning, safety
    monkeypatch.setattr(safety, "configured", lambda s: (True, ""))
    R = pd.DataFrame([
        {"source": "VANTAGE", "sent": "sent", "status": "open", "entry": 100, "stop": 90, "exit": 110},
        {"source": "live engine", "sent": "sent", "status": "open", "entry": 200, "stop": 180, "exit": 200},
        {"source": "hourly scan", "sent": "sent", "status": "open", "entry": 100, "stop": 90, "exit": 100},
        {"source": "VANTAGE", "sent": "sent", "status": "closed", "entry": 100, "stop": 90, "exit": 120}])
    s = {"capital": 51000, "risk_limits": {"risk_per_trade_pct": 1.0, "max_order_pct": 25.0}}
    L = learning.portfolio_risk(R, s)
    assert "2 positions" in L[0]
    # 51 shares x 100 + 25 shares x 200 = 10,100 needed; at stops: 51 x 20 + 25 x 20 = 1,520
    assert "10,100" in L[0] and "1,520" in L[1]


def test_portfolio_risk_needs_capital():
    from swing import learning
    R = pd.DataFrame([{"source": "VANTAGE", "sent": "sent", "status": "open", "entry": 100, "stop": 90, "exit": 110}])
    assert learning.portfolio_risk(R, {}) == []


def test_registry_stages_complete():
    import json
    from swing.config import ROOT
    doc = json.loads((ROOT / "strategies" / "registry.json").read_text())
    assert [x["n"] for x in doc["stages"]] == list(range(1, 8))
    assert all(isinstance(s.get("stage"), int) and 0 <= s["stage"] <= 7 for s in doc["strategies"])
