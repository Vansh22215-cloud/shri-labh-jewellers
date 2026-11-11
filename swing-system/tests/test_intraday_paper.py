import pandas as pd

from swing import intraday_paper as ip


def _day(prices, start="2026-11-11 09:15"):
    idx = pd.date_range(start, periods=len(prices), freq="5min")
    rows = []
    for o, h, l, c in prices:
        rows.append({"open": o, "high": h, "low": l, "close": c, "volume": 1000})
    return pd.DataFrame(rows, index=idx)


def test_orb_long_trigger_and_levels():
    b = _day([(100, 101, 99, 100.5), (100.5, 101.5, 100, 101), (101, 101.8, 100.6, 101.2),   # range 99-101.8
              (101.2, 102.4, 101.1, 102.2)])                                               # 09:30 close above
    s = [x for x in ip.signals(b) if x["setup"] == "ORB"][0]
    assert s["side"] == "buy" and s["entry"] == 102.2 and s["stop"] == 100.4 and abs(s["target"] - 104.0) < 1e-9


def test_paper_trade_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setattr(ip, "TRADES_F", tmp_path / "p.csv")
    monkeypatch.setattr(ip, "_charges", lambda e, x, q: 20.0)
    b = _day([(100, 101, 99, 100.5), (100.5, 101.5, 100, 101), (101, 101.8, 100.6, 101.2),
              (101.2, 102.4, 101.1, 102.2)])
    now = pd.Timestamp("2026-11-11 09:40")
    tr = ip.step(now=now, symbols=["X"], bars={"X": b})
    assert len(tr) == 1 and tr.iloc[0]["status"] == "open" and tr.iloc[0]["qty"] == 250        # 450 / 1.8
    b2 = pd.concat([b, _day([(102.2, 104.5, 102, 104.2)], start="2026-11-11 09:35")])
    tr = ip.step(now=pd.Timestamp("2026-11-11 09:45"), symbols=["X"], bars={"X": b2})
    r = tr.iloc[0]
    assert r["status"] == "target" and abs(r["pnl"] - 450) < 1 and abs(r["net"] - 430) < 1
    tr = ip.step(now=pd.Timestamp("2026-11-11 09:50"), symbols=["X"], bars={"X": b2})
    assert len(tr) == 1                                                       # one trade per setup per day
    assert "1 trades this week, 1 won" in ip.week_line("2026-11-12")


def test_live_tips_respect_settings_time_cap_and_allowed(monkeypatch, tmp_path):
    monkeypatch.setattr(ip, "TRADES_F", tmp_path / "p.csv")
    monkeypatch.setattr(ip, "SETUPS_F", tmp_path / "setups.json")
    sent = []
    monkeypatch.setattr("swing.telegram.send", lambda s, text, html=False, label="": sent.append(text) or "Telegram message sent")
    monkeypatch.setattr("swing.kite.historical", lambda *a, **k: None)
    monkeypatch.setattr("swing.risk.new_ticket", lambda *a, **k: {"status": "BLOCKED"})
    monkeypatch.setattr("swing.bot.send_ticket", lambda *a, **k: None)
    new = [dict(symbol=f"S{i}", setup="ORB", side="buy", entry=100.0, stop=99.0, target=101.0) for i in range(3)]
    s = {"intraday_tips": True, "intraday_max_tips": 2}
    now = pd.Timestamp("2026-11-12 10:05")
    assert ip.send_tips(new, now, settings=dict(s, intraday_tips=False)) == set()
    assert ip.send_tips(new, pd.Timestamp("2026-11-12 14:45"), settings=s) == set()      # too late in the day
    out = ip.send_tips(new, now, settings=s)
    assert len(out) == 2 and "INTRADAY TIP" in sent[0] and "not yet validated" in sent[0]  # cap 2, labelled
    import json
    ip.SETUPS_F.write_text(json.dumps({"allowed": ["FLAG"]}))
    sent.clear()
    assert ip.send_tips(new, now, settings=s) == set()                                     # ORB failed the test


def test_backtest_rule_needs_profit_in_both_halves(monkeypatch, tmp_path):
    from swing import intraday_backtest as bt
    monkeypatch.setattr(ip, "SETUPS_F", tmp_path / "setups.json")
    days = [f"2026-06-{d:02d}" for d in range(1, 31)]
    rows = [{"day": days[i % 30], "setup": "ORB", "net": 50.0} for i in range(60)]           # good in both halves
    rows += [{"day": days[i % 30], "setup": "FLAG", "net": (300.0 if days[i % 30] < days[15] else -100.0)}
             for i in range(60)]                                                         # good only early
    rows += [{"day": days[i % 30], "setup": "BOUNCE", "net": 80.0} for i in range(10)]     # too few trades
    txt = bt.decide(pd.DataFrame(rows), 5)
    import json
    d = json.loads(ip.SETUPS_F.read_text())
    assert d["allowed"] == ["ORB"] and "From tomorrow" in txt
    assert ip.allowed_setups() == ({"ORB"}, True)


def test_simulate_day_exits():
    from swing import intraday_backtest as bt
    b = _day([(100, 101, 99, 100.5), (100.5, 101.5, 100, 101), (101, 101.8, 100.6, 101.2),
              (101.2, 102.4, 101.1, 102.2), (102.2, 104.5, 102, 104.2)])
    t = bt.simulate_day(b, None)
    assert t and t[0]["setup"] == "ORB" and t[0]["how"] == "target"
