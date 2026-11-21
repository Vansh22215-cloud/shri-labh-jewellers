"""Practice account: fills, charges, stop/target, day limits, both strategies on hand-made minute candles,
replay over days, dashboard picture."""
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from swing import autotrader, costs, dashboard, paper
from swing.replay import Market

DAY = pd.Timestamp("2026-11-18")


def minutes(day, path, vol=1000.0):
    """1-minute candles 9:15-15:29 following `path` (one close per minute, extended flat)."""
    idx = pd.date_range(day + timedelta(hours=9, minutes=15), day + timedelta(hours=15, minutes=29), freq="1min")
    c = np.interp(np.arange(len(idx)), np.linspace(0, len(idx) - 1, len(path)), path)
    o = np.r_[c[0], c[:-1]]
    v = np.full(len(idx), vol)
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.05, "low": np.minimum(o, c) - 0.05, "close": c,
                         "volume": v}, index=idx)


NFO = pd.DataFrame({"instrument_token": [1, 2], "tradingsymbol": ["NIFTY26NOV24000CE", "NIFTY26NOV24000PE"],
                    "expiry": pd.to_datetime(["2026-11-24", "2026-11-24"]), "strike": [24000, 24000],
                    "instrument_type": ["CE", "PE"], "lot_size": [65, 65]})


def test_option_charges_match_zerodha_formula():
    ch = costs.option_cost(6500, 8000)          # ₹40 brokerage, 0.1% STT on 8,000, exchange, SEBI, stamp, GST
    assert 58 < ch < 64            # 40 + 8 + 5.08 + 0.01 + 0.20 + GST 8.12 = 61.4


def test_broker_fills_and_money(tmp_path):
    b = paper.Broker(tmp_path / "a.json", start=50800)
    p = b.open_position("k", "NIFTY X CALL", "NFO:X", "OPT", "LONG", 130, 100, 70, 160, "NIFTY options", DAY)
    assert p.avg == 100.3 and round(b.available(), 2) == round(50800 - 130 * 100.3, 2)
    c = b.close_position("k", 160, DAY + timedelta(hours=11), "target")
    assert c["pnl"] == round(130 * (160 - 0.48) - 130 * 100.3, 2) and c["net"] < c["pnl"]
    assert paper.Broker(tmp_path / "a.json").acc.cash == b.acc.cash            # kept across restarts
    assert b.open_position("big", "X", "X", "OPT", "LONG", 10_000, 100, 70, 160, "s", DAY) is None   # no money


def run_day(data, extra=None, params=None):
    b = paper.Broker(None, start=50800)
    m = Market(data, NFO, lambda s: (extra or {}).get(s))
    m.set_day(DAY)
    msgs = []
    e = autotrader.Engine(b, m, params=params, notify=lambda k, t: msgs.append((k, t)))
    t = DAY + timedelta(hours=9, minutes=16)
    while t <= DAY + timedelta(hours=15, minutes=30):
        e.on_minute(t)
        t += timedelta(minutes=1)
    return b, msgs


def test_nifty_breakout_buys_call_and_hits_target():
    nifty = minutes(DAY, [24000, 24010, 23995, 24005, 24060, 24150, 24200, 24220])
    opt = minutes(DAY, [100, 101, 99, 100, 112, 150, 170, 175])
    data = {"NIFTY50": nifty, "NFO:NIFTY26NOV24000CE": opt}
    b, msgs = run_day(data, {"NFO:NIFTY26NOV24000CE": opt})
    c = [x for x in b.day_closed(DAY) if x["kind"] == "OPT"]
    assert c and c[0]["name"] == "NIFTY 24 NOV 24000 CALL" and c[0]["why"] == "target" and c[0]["qty"] % 65 == 0
    assert any(k == "entry" for k, _ in msgs) and any(k == "exit" for k, _ in msgs)


def test_stock_breakout_with_volume_and_one_percent_stop():
    day = minutes(DAY, [500, 501, 499.5, 500.5, 500, 507, 498, 494, 494], vol=1000.0)
    day.loc[day.index[25:30], "volume"] = 9000.0                # strong volume on the breakout candle 9:40
    data = {"NIFTY50": minutes(DAY, [24000] * 8), "AAA": day}
    b, msgs = run_day(data, params={"stk_max_trades": 3})       # stocks are paused by default (21 Nov long test)
    c = [x for x in b.day_closed(DAY) if x["symbol"] == "AAA"]
    assert c and c[0]["side"] == "LONG"
    assert c[0]["why"] in ("stop-loss", "stop at entry", "target", "square-off 3:15 pm")


def test_day_loss_limit_stops_new_trades():
    b = paper.Broker(None, start=50800)
    b.acc.closed.append({"exit_time": str(DAY + timedelta(hours=10)), "net": -8000, "pnl": -8000, "strategy": "stocks",
                         "symbol": "Z", "name": "Z", "charges": 0})
    m = Market({"NIFTY50": minutes(DAY, [24000, 24300])}, NFO, lambda s: None)
    m.set_day(DAY)
    e = autotrader.Engine(b, m)
    e.on_minute(DAY + timedelta(hours=10, minutes=5))
    assert e.locked == "loss limit"


def test_dashboard_picture(tmp_path):
    rows = [{"name": "NIFTY 24 NOV 24000 CALL", "qty": 130, "buy_avg": 100.3, "sell_avg": 160, "ltp": 120, "pnl": 7761}]
    f = dashboard.render(rows, tmp_path / "d.png", DAY, balance=58500, start=50800, charges=60, net=7701)
    assert f.exists() and f.stat().st_size > 10_000


def test_full_replay_sends_five_dashboards_then_summary(tmp_path, monkeypatch, request):
    from swing import replay, fno, telegram
    days = [DAY + timedelta(days=i) for i in range(5)]
    days = [d for d in pd.bdate_range(DAY, periods=5)]
    data = {"NIFTY50": pd.concat([minutes(d, [24000, 24010, 23995, 24005, 24060, 24150, 24200]) for d in days]),
            "AAA": pd.concat([minutes(d, [500, 501, 499, 500, 506, 510, 512]) for d in days])}
    opt = pd.concat([minutes(d, [100, 101, 99, 100, 112, 150, 170]) for d in days])
    monkeypatch.setattr(replay, "load_data", lambda n: (data, days))
    monkeypatch.setattr(replay, "fetch", lambda *a, **k: opt)
    monkeypatch.setattr(fno, "nfo", lambda: NFO)
    monkeypatch.setattr(replay, "PRIVATE", tmp_path)
    monkeypatch.setattr(replay, "DATA", tmp_path)
    monkeypatch.setattr(replay, "REPORT", tmp_path / "r.md")
    photos = []
    monkeypatch.setattr(telegram, "send_photo", lambda s, p, caption="", label="dashboard": photos.append(caption) or "photo sent")
    out = replay.run(5, send=True)
    assert len(out) == 5 and len(photos) == 5 and photos[0].startswith("📊 Practice day 1 of 5")
    assert any(l == "test result" and "Practice replay" in t for l, t in request.node.sent)
    assert "Kite Connect historical 1-minute candles only" in (tmp_path / "r.md").read_text()
