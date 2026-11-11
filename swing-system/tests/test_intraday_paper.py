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
