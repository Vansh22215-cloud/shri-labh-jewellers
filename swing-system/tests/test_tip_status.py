import pandas as pd

from swing import tip_status as ts, tipcheck


def test_judge_plain_answers():
    assert ts.judge("buy", 95, 100, 96, 120)[1] == "stop-loss hit"
    assert ts.judge("buy", 110, 100, 90, 120, hi=121, lo=105)[1] == "target reached"       # touched today
    assert "close to the stop" in ts.judge("buy", 97, 100, 96, 120)[1]
    assert ts.judge("buy", 105, 100, 90, 120)[2].startswith("Hold")
    assert ts.judge("sell", 90, 100, 105, 80)[1] == "in profit"
    assert "Don't chase" in ts.judge("buy", 112, None, None, None, waiting=True, zone=(100, 105))[2]
    assert "Can be bought" in ts.judge("buy", 102, None, None, None, waiting=True, zone=(100, 105))[2]


def test_update_lists_every_tip_and_no_nifty_pulse(monkeypatch, tmp_path):
    monkeypatch.setattr(tipcheck, "TIPS_F", tmp_path / "ft.csv")
    monkeypatch.setattr(ts, "SIGNALS_F", tmp_path / "sig.csv")
    tipcheck.save({"symbol": "TATASTEEL", "side": "buy", "raw": "x"}, "RISKY", {"entry": 178, "stop": 170, "target": 195},
                  "Dark Horse")
    ts.record_signals("2026-11-06", [{"symbol": "AJANTPHARM", "entry_low": 3240, "entry_high": 3290, "stop": 3020,
                                      "target1": 3600, "qty": 1}])
    tips = pd.DataFrame([{"date": "2026-11-03", "symbol": "ICICIBANK", "kind": "tip", "status": "open",
                          "entry_low": 1410, "entry_high": 1438, "stop": 1340, "target1": 1594, "qty": 5,
                          "entry_price": 1424.5}])
    snap = {k: pd.Series({"TATASTEEL": 185.0, "AJANTPHARM": 3312.0, "ICICIBANK": 1550.0}) for k in ("close", "high", "low")}
    t = ts.message(snap, tips, pd.Timestamp("2026-11-06 13:20"), today=pd.Timestamp("2026-11-06").date())
    for part in ("TIPS UPDATE", "System tips", "ICICIBANK", "₹+628 on 5", "scan signals", "AJANTPHARM",
                 "Forwarded from Dark Horse", "TATASTEEL", "If you took it", "3 tip(s) followed"):
        assert part in t, part
    assert "Nifty" not in t
    assert set(ts.symbols_needed()) >= {"TATASTEEL", "AJANTPHARM"}


def test_no_tips_message():
    t = ts.message({k: pd.Series(dtype=float) for k in ("close", "high", "low")},
                   pd.DataFrame(columns=["kind", "status", "symbol", "date"]), pd.Timestamp("2026-11-06 10:20"))
    assert "No open tips" in t
