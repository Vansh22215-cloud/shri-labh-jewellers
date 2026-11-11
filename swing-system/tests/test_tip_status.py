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
                 "Forwarded from Dark Horse", "TATASTEEL", "If you took it", "3 tip(s) listed"):
        assert part in t, part
    assert "Nifty" not in t
    assert set(ts.symbols_needed()) >= {"TATASTEEL", "AJANTPHARM"}


def test_no_tips_message(monkeypatch, tmp_path):
    monkeypatch.setattr(tipcheck, "TIPS_F", tmp_path / "none.csv")
    monkeypatch.setattr(ts, "SIGNALS_F", tmp_path / "none2.csv")
    t = ts.message({k: pd.Series(dtype=float) for k in ("close", "high", "low")},
                   pd.DataFrame(columns=["kind", "status", "symbol", "date"]), pd.Timestamp("2026-11-06 10:20"))
    assert "No tips yet" in t


def test_every_forwarded_tip_is_listed_and_new_ones_marked(monkeypatch, tmp_path):
    monkeypatch.setattr(tipcheck, "TIPS_F", tmp_path / "ft.csv")
    monkeypatch.setattr(ts, "SIGNALS_F", tmp_path / "sig.csv")
    sv = tipcheck.save
    sv({"symbol": "RELIANCE", "side": "1500 CE", "raw": "x"}, "AVOID", {"entry": 25, "stop": 15, "target": 40, "ltp": 1312},
       "G", outcome="n/a (option - outcome not tracked yet)")
    sv({"symbol": None, "raw": "big move coming"}, "UNKNOWN", {}, "G")
    sv({"symbol": "FEDERALBNK", "side": "buy", "raw": "x"}, "GOOD", {"entry": 330, "stop": 320, "target": 338, "ltp": 330},
       "H", outcome="target")
    since = pd.Timestamp.now() + pd.Timedelta(minutes=1)
    sv({"symbol": "ICICIBANK", "side": "buy", "raw": "x"}, "AVOID", {"ltp": 1550}, "H", outcome="n/a")
    df = pd.read_csv(tipcheck.TIPS_F)
    df.loc[df["symbol"] == "ICICIBANK", "checked"] = str((since + pd.Timedelta(minutes=5)).round("s"))
    df.to_csv(tipcheck.TIPS_F, index=False)
    snap = {k: pd.Series({"RELIANCE": 1313.8, "FEDERALBNK": 339.9, "ICICIBANK": 1550.5}) for k in ("close", "high", "low")}
    t = ts.message(snap, pd.DataFrame(columns=["kind", "status", "symbol", "date"]), pd.Timestamp.now(), since=since)
    for part in ("RELIANCE 1500 CE", "option tip", "couldn't read", "RIGHT - reached the target", "FEDERALBNK",
                 "🆕 📌 <b>ICICIBANK", "4 tip(s) listed", "1 new since the last update"):
        assert part in t, part


def test_weekly_summary_scorecards_and_every_tip(monkeypatch, tmp_path):
    monkeypatch.setattr(tipcheck, "TIPS_F", tmp_path / "ft.csv")
    sv = tipcheck.save
    sv({"symbol": "TATASTEEL", "side": "buy", "raw": "x"}, "RISKY", {"entry": 178, "stop": 170, "target": 195, "ltp": 178}, "DH")
    sv({"symbol": "FEDERALBNK", "side": "buy", "raw": "x"}, "GOOD", {"entry": 330, "stop": 320, "target": 338}, "SG",
       outcome="target")
    sv({"symbol": "SBIN", "side": "buy", "raw": "x"}, "RISKY", {"entry": 800, "stop": 780, "target": 850}, "SG", outcome="stop")
    from swing import journal
    monkeypatch.setattr(journal, "load_tips", lambda: pd.DataFrame([
        {"date": str(pd.Timestamp.today().date()), "symbol": "ICICIBANK", "kind": "tip", "status": "open",
         "entry_low": 1410, "entry_high": 1438, "stop": 1340, "target1": 1594, "qty": 5, "entry_price": 1400.0}]))
    monkeypatch.setattr(ts, "daily_snap", lambda syms: {k: pd.Series({"TATASTEEL": 185.0, "ICICIBANK": 1450.0,
                                                                       "FEDERALBNK": 340.0, "SBIN": 790.0})
                                                         for k in ("close", "high", "low")})
    t = ts.weekly_summary()
    for part in ("WEEKLY SUMMARY", "4 tip(s) this week", "1 ✅ right", "1 ❌ wrong", "2 🟢 open in profit",
                 "Channel scorecards", "SG: 1 of 2 finished calls were right", "ICICIBANK", "₹+250 on 5",
                 "closed - target reached", "closed - stop hit"):
        assert part in t, part
