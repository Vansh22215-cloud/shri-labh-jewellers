import pandas as pd

from swing import brief

CAL = {"RCP": {"n": 4000, "win_pct": 45, "avg_pct": 4.4}, "Dip-buy A": {"n": 171, "win_pct": 80, "avg_pct": 3.34},
       "Breakout 90+": {"n": 800, "win_pct": 36, "avg_pct": 3.39}}
S = {"capital": 51000, "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25}}


def _b(setup, close, stop, tier="", score=0, **k):
    return {"setup": setup, "tier": tier, "score": score, "close": close, "stop": stop, **k}


def test_no_trade_day():
    t = brief.build("2026-11-20", [], pd.DataFrame(columns=["symbol", "setup", "why"]), pd.DataFrame(), S, CAL)
    assert "No trade today" in t and "don't justify the risk" in t


def test_ranked_by_evidence_per_rupee_risked_with_avoid_list():
    c = [("WIDE", _b("RCP", 100.0, 80.0), 100.0),                     # 4.4% avg / 20% risk = 0.22 per ₹1
         ("DIP", _b("Dip-buy", 100.0, 95.0, tier="A"), 100.0)]         # 3.34 / 5 = 0.67 per ₹1
    rej = pd.DataFrame([{"symbol": "SMALL", "setup": "RCP", "why": "outside the top 300"}])
    t = brief.build("2026-11-20", c, rej, pd.DataFrame(), S, CAL)
    assert t.index("DIP") < t.index("WIDE")
    assert "qty" in t and "max loss" in t and "Avoid today" in t and "SMALL" in t
    assert "no order that reliably adds profit" in t


def test_sent_once_and_kill_switch_says_no_trade(tmp_path, monkeypatch):
    from swing import telegram, vantage
    monkeypatch.setattr(brief, "SENT_F", tmp_path / "sent.txt")
    monkeypatch.setattr(vantage, "CALL_F", tmp_path / "calls.csv")
    out = []
    monkeypatch.setattr(telegram, "send_reliable", lambda s, text, label="": out.append(text))
    t = pd.Timestamp("2026-11-20 15:22")
    assert brief.maybe_send(t, t, [], dict(S, kill_switch=True), CAL)
    assert "No trade today" in out[0] and "safety stop" in out[0]
    assert not brief.maybe_send(t, t, [], S, CAL)                       # once a day
    assert not brief.maybe_send(pd.Timestamp("2026-11-21 15:10"), pd.Timestamp("2026-11-21 15:10"), [], S, CAL)
