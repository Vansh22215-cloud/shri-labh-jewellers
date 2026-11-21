"""A whole live practice day, end to end, with fake Kite ticks: feed -> candles -> practice trader -> Telegram
messages -> 3:30 pm dashboard. Catches wiring bugs the unit tests cannot."""
from datetime import datetime, timedelta

import pytest

from swing import fno, kite, live_feed as lf, practice_live, telegram


class Feed:
    def __init__(self):
        self.builder = lf.CandleBuilder({1: "NIFTY50", 2: "AAA"})


def test_full_live_day(tmp_path, monkeypatch):
    sent, photos = [], []
    monkeypatch.setattr(telegram, "send_reliable", lambda s, text, html=False, label="": sent.append((label, text)) or True)
    monkeypatch.setattr(telegram, "send_photo", lambda s, p, caption="", label="": photos.append(caption) or "photo sent")
    monkeypatch.setattr(practice_live, "ACCOUNT_F", tmp_path / "paper.json")
    monkeypatch.setattr(practice_live, "DATA", tmp_path)
    monkeypatch.setattr(practice_live, "load_settings", lambda: {"kill_switch": False, "paper_capital": 50800})
    monkeypatch.setattr(practice_live, "practice_params", lambda: {})
    opt_px = {"v": 100.0}
    monkeypatch.setattr(kite, "quotes", lambda syms: {s: {"last": opt_px["v"]} for s in syms})
    monkeypatch.setattr(kite, "mis_ratio", lambda *a, **k: 0.2)
    monkeypatch.setattr(fno, "pick", lambda spot, side, t, table=None: {
        "symbol": "NFO:NIFTY26NOV24000CE", "token": 9, "lot": 65, "expiry": "2026-11-23", "strike": 24000,
        "side": side, "name": "NIFTY 23 NOV 24000 CALL"})
    monkeypatch.setattr(practice_live.LiveMarket, "poll_options", lambda self, broker: None)
    feed = Feed()
    pl = practice_live.PracticeLive()
    day = datetime(2026, 11, 23)
    nifty, stock, vol = 24000.0, 500.0, 0.0
    for i in range(376):                                    # 9:15 ... 15:30
        t = day + timedelta(hours=9, minutes=15 + i)
        if i < 375:
            nifty += 1.5 if 15 <= i < 120 else 0.0                         # breaks out after 9:30, trends up
            stock += 0.5 if 20 <= i < 40 else 0.0
            vol += 8000 if 20 <= i < 25 else 1000
            opt_px["v"] = 100 + max(0.0, nifty - 24030) * 0.5
            for tok, px, v in ((1, nifty, None), (2, stock, vol)):
                feed.builder.tick({"token": tok, "ltp": px, "volume": v, "open": 24000 if tok == 1 else 500,
                                   "high": px + 5, "low": 23990 if tok == 1 else 499, "close": 23990 if tok == 1 else 498},
                                  t + timedelta(seconds=30))
        end = t + timedelta(minutes=1)
        feed.builder.close_minute(end)
        if pl.market is not None:                           # what the 2-second option poller would have seen
            for p in pl.broker.acc.open.values():
                if p.kind == "OPT":
                    b = pl.market.opt.setdefault(p.symbol, [opt_px["v"]] * 4)
                    b[1], b[2], b[3] = max(b[1], opt_px["v"]), min(b[2], opt_px["v"]), opt_px["v"]
        for iv in lf.closed_intervals(t):
            pl.on_close(iv, end, feed)
    labels = [l for l, _ in sent]
    assert "trade tip" in labels and "exit alert" in labels, sent
    assert any("NIFTY 23 NOV 24000 CALL" in txt for _, txt in sent)
    assert not pl.broker.acc.open                          # nothing carried overnight
    assert len(photos) == 1 and photos[0].startswith("📊 Today")
    assert all(c["exit_time"] <= "2026-11-23 15:30" for c in pl.broker.acc.closed)


def test_dashboard_backup_when_feed_was_down(tmp_path, monkeypatch):
    from swing import paper
    photos = []
    monkeypatch.setattr(telegram, "send_photo", lambda s, p, caption="", label="": photos.append(caption) or "photo sent")
    monkeypatch.setattr(practice_live, "ACCOUNT_F", tmp_path / "paper.json")
    monkeypatch.setattr(practice_live, "DATA", tmp_path)
    monkeypatch.setattr(practice_live, "DASH_F", tmp_path / "sent.txt")
    b = paper.Broker(tmp_path / "paper.json")
    b.open_position("k", "AAA", "AAA", "EQ", "LONG", 10, 100, 99, 102, "stocks", datetime(2026, 11, 23, 10, 0))
    assert practice_live.fallback_dashboard("2026-11-23") and len(photos) == 1
    assert not paper.Broker(tmp_path / "paper.json").acc.open           # squared off
    assert not practice_live.fallback_dashboard("2026-11-23")          # only once
