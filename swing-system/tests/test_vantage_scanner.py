"""VANTAGE INDICATOR scanner (owner 17 Nov): exact indicator logic on every NSE stock -> Telegram."""
import json

import numpy as np
import pandas as pd
import pytest

from swing import vantage


def _stock(seed=7, n=900):
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0009, 0.02, n)
    c = 100 * np.exp(np.cumsum(r))
    o = c * (1 + rng.normal(0, 0.005, n))
    h = np.maximum(o, c) * (1 + abs(rng.normal(0, 0.008, n)))
    l = np.minimum(o, c) * (1 - abs(rng.normal(0, 0.008, n)))
    v = rng.integers(50_000, 200_000, n).astype(float)
    idx = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, index=idx)


def test_todays_signal_equals_the_backtest_signal_for_that_day():
    rep = vantage._replica()
    d = _stock()
    bench = pd.Series(np.linspace(18000, 24000, len(d)), index=d.index)
    full = pd.DataFrame(rep.run(d, bench))
    assert len(full) > 0
    checked = 0
    for _, tr in full.iterrows():
        k = d.index.get_loc(tr["signal"])
        st = {}
        rep.run(d.iloc[:k + 1], bench, state=st)                  # the scan on the evening of the signal day
        assert st["buy"] and st["buy"]["setup"] == tr["setup"]
        checked += 1
        if tr["why"] in ("Stop-loss", "Target 2"):
            e = d.index.get_loc(tr["exit_date"])
            st2 = {}
            rep.run(d.iloc[:e + 1], bench, state=st2)
            assert st2["sell"] and st2["sell"]["why"] == tr["why"] and st2["sell"]["signal"] == tr["signal"]
    assert checked == len(full)


@pytest.fixture
def env(monkeypatch, tmp_path):
    sent = []
    from swing import telegram, health
    monkeypatch.setattr(vantage, "SIGNALS_F", tmp_path / "sig.csv")
    monkeypatch.setattr(vantage, "LAST_F", tmp_path / "last.json")
    monkeypatch.setattr(vantage, "symbols", lambda: ["TITAN", "ABC"])
    monkeypatch.setattr(health, "traded_today", lambda now=None: True)
    monkeypatch.setattr(telegram, "send_reliable", lambda s, text, label="": sent.append((label, text)))
    from swing import data_prices
    monkeypatch.setattr(data_prices, "update", lambda syms: None)
    monkeypatch.setattr(vantage, "today_bars", lambda syms, day: {"TITAN": {}})
    monkeypatch.setattr(vantage, "calibration", lambda: {"Dip-buy A": {"win_pct": 80, "n": 171}})
    monkeypatch.setattr(vantage, "_last_close", lambda sym, day: 105.0)
    return sent


def _buy(day):
    return {"setup": "Dip-buy", "tier": "A", "score": 41, "close": 100.0, "stop": 92.0, "t1": float("nan"),
            "t2": float("nan"), "signal": pd.Timestamp(day)}


def test_buy_message_format_once_and_sell_only_for_sent_buys(env, monkeypatch):
    day = "2026-11-17"
    monkeypatch.setattr(vantage, "scan", lambda d, bars: [("TITAN", {"buy": _buy(day), "in_position": True}, 5e8),
                                                          ("ABC", {"sell": {"why": "Stop-loss", "price": 9.0, "intrabar": True},
                                                                   "in_position": False}, 5e8)])
    r = vantage.run(day)
    assert r["buys"] == 1 and r["sells"] == 0                                   # ABC: no BUY was ever sent -> no SELL
    label, text = env[0]
    assert label == "vantage indicator"
    assert text.startswith("#VANTAGE INDICATOR\n\n#TITAN\n\n🟢 BUY · Dip-buy A · likely win 80%")
    assert "Stop-loss ₹92.00" in text
    assert vantage.run(day)["buys"] == 0                                         # re-run: never sent twice
    sell = {"why": "Closed above the 5-day average (dip-buy exit)", "price": 104.0, "intrabar": False}
    monkeypatch.setattr(vantage, "scan", lambda d, bars: [("TITAN", {"sell": sell, "in_position": True}, 5e8)])
    assert vantage.run("2026-11-19")["sells"] == 1
    assert env[-1][1].startswith("#VANTAGE INDICATOR\n\n#TITAN\n\n🔴 SELL (exit)") and "+4.0%" in env[-1][1]
    assert vantage.run("2026-11-19")["sells"] == 0                               # closed: no repeat


def test_missed_exit_day_is_caught_and_kill_switch_blocks_buys(env, monkeypatch):
    day = "2026-11-17"
    monkeypatch.setattr(vantage, "scan", lambda d, bars: [("TITAN", {"buy": _buy(day), "in_position": True}, 5e8)])
    vantage.run(day)
    monkeypatch.setattr(vantage, "scan", lambda d, bars: [("TITAN", {"in_position": False}, 5e8)])
    assert vantage.run("2026-11-24")["sells"] == 1 and "could not be scanned" in env[-1][1]
    from swing import config
    real = config.load_settings
    monkeypatch.setattr(vantage, "load_settings", lambda: dict(real(), kill_switch=True))
    monkeypatch.setattr(vantage, "scan", lambda d, bars: [("NEW", {"buy": _buy("2026-11-25"), "in_position": True}, 5e8)])
    assert vantage.run("2026-11-25")["buys"] == 0


def test_kite_scan_without_login_leaves_the_evening_retry_due(env, monkeypatch):
    monkeypatch.setattr(vantage, "today_bars", lambda syms, day: {})
    r = vantage.run("2026-11-17", source="kite")
    assert not r["ok"] and vantage.due_evening("2026-11-17")


def test_schedule(monkeypatch, tmp_path):
    from swing import daemon
    monkeypatch.setattr(daemon, "_load", lambda: {})
    assert "vantage" in daemon.due(pd.Timestamp("2026-11-17 15:41"))
    assert "vantage" not in daemon.due(pd.Timestamp("2026-11-17 15:20"))
    assert "vantage" not in daemon.due(pd.Timestamp("2026-11-21 15:41"))     # Saturday


def test_prefilter_never_drops_a_real_signal():
    """Every BUY the full logic finds must pass the live pre-filter (it only skips stocks that cannot signal)."""
    rep = vantage._replica()
    misses = checked = 0
    for seed in range(6):
        d = _stock(seed)
        bench = pd.Series(np.linspace(18000, 24000, len(d)), index=d.index)
        for _, tr in pd.DataFrame(rep.run(d, bench)).iterrows():
            k = d.index.get_loc(tr["signal"])
            hist, today = d.iloc[:k], d.iloc[k]
            c = hist["close"]
            dip, rcp, brk = 1.10 * 0.97 * c.tail(200).mean(), 0.9 * c.tail(249).max(), hist["high"].tail(50).max()
            checked += 1
            misses += not (today["close"] >= min(dip, rcp) or today["close"] > brk)
    assert checked > 5 and misses == 0


def test_live_alert_once_then_confirmed_or_cancelled(env, monkeypatch, tmp_path):
    monkeypatch.setattr(vantage, "LIVE_F", tmp_path / "live.csv")
    monkeypatch.setattr(vantage, "SNAP_F", tmp_path / "snap.json")
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    vantage.write_snapshot({"TITAN": {"open": 100, "high": 103, "low": 99, "last": 101, "volume": 5e5},
                            "NIFTY50": {"open": 1, "high": 1, "low": 1, "last": 1, "volume": 1}})

    class Sc:
        day = now.normalize()

        def cycle(self):
            return now, [("TITAN", {"buy": dict(_buy(now), close=101.0)}, 5e8), ("ABC", {"buy": _buy(now)}, 5e8)]
    r = vantage.live_step(Sc())
    assert r["live_buys"] == 2
    assert env[0][1].startswith("#VANTAGE INDICATOR\n\n#TITAN\n\n⚡ LIVE BUY signal · Dip-buy A")
    assert "Price now ₹101.00" in env[0][1] and "confirm ✅ or cancel ❌" in env[0][1]
    assert vantage.live_step(Sc())["live_buys"] == 0                   # once per stock per day
    # close: TITAN held (normal BUY carries ✅ CONFIRMED), ABC did not (❌ CANCELLED)
    monkeypatch.setattr(vantage, "scan", lambda d, bars: [("TITAN", {"buy": _buy(now), "in_position": True}, 5e8)])
    vantage.run(str(now.date()))
    texts = [t for _, t in env[2:]]
    assert any(t.startswith("#VANTAGE INDICATOR\n\n#ABC\n\n❌ CANCELLED") for t in texts)
    assert any("#TITAN\n\n✅ CONFIRMED at the close" in t and "🟢 BUY" in t for t in texts)


def test_stale_snapshot_is_never_used(monkeypatch, tmp_path):
    monkeypatch.setattr(vantage, "SNAP_F", tmp_path / "snap.json")
    old = (pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None) - pd.Timedelta(minutes=10))
    (tmp_path / "snap.json").write_text(json.dumps({"time": str(old)[:19], "q": {"X": [1, 1, 1, 1, 1]}}))
    assert vantage.read_snapshot() == (None, {})


def test_live_stop_loss_alert_for_a_sent_buy(env, monkeypatch, tmp_path):
    monkeypatch.setattr(vantage, "LIVE_F", tmp_path / "live.csv")
    monkeypatch.setattr(vantage, "SNAP_F", tmp_path / "snap.json")
    monkeypatch.setattr(vantage, "scan", lambda d, bars: [("TITAN", {"buy": _buy("2026-11-16"), "in_position": True}, 5e8)])
    vantage.run("2026-11-16")                                         # BUY sent yesterday, stop 92
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    vantage.write_snapshot({"TITAN": {"open": 95, "high": 96, "low": 91.5, "last": 92.5, "volume": 5e5}})

    class Sc:
        day = pd.Timestamp("2026-11-17")

        def cycle(self):
            return now, []
    r = vantage.live_step(Sc())
    assert r["stops"] == 1 and "Stop-loss hit (live)" in env[-1][1]
    assert vantage.live_step(Sc())["stops"] == 0                       # only once


def test_index_without_volume_is_kept_in_the_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(vantage, "SNAP_F", tmp_path / "snap.json")
    vantage.write_snapshot({"NIFTY50": {"open": 24000, "high": 24100, "low": 23900, "last": 24050, "volume": 0},
                            "DEAD": {"open": 10, "high": 10, "low": 10, "last": 10, "volume": 0}})
    t, bars = vantage.read_snapshot()
    assert "NIFTY50" in bars and "DEAD" not in bars


def test_buy_messages_carry_the_quantity():
    from swing import safety
    s = {"capital": 45000, "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25}}
    assert "📦 Qty: 3 shares ≈ ₹4,272 · max loss ≈ ₹423 (1% of ₹45,000)" in vantage.qty_line(1424.0, 1283.0, s)
    assert "Qty: 0" in vantage.qty_line(30000.0, 29000.0, s)            # one share > 25% of capital
    b = {"setup": "RCP", "tier": "", "score": 80, "close": 1424.0, "stop": 1283.0, "t2": float("nan")}
    assert "📦 Qty:" in vantage.buy_message("ICICIBANK", b, 46, 5510, False)
    assert "📦 Qty:" in vantage.live_buy_message("ICICIBANK", b, 46, 5510, 1424.0, pd.Timestamp("2026-11-18 11:42"), False)
    assert safety.size(1424.0, 1283.0, s) == 3


def test_thin_stocks_get_no_buy(env, monkeypatch):
    day = "2026-11-17"
    monkeypatch.setattr(vantage, "scan", lambda d, bars: [("THIN", {"buy": _buy(day), "in_position": True}, 1.5e7),
                                                          ("LIQUID", {"buy": _buy(day), "in_position": True}, 2.5e7)])
    r = vantage.run(day)
    assert r["buys"] == 1 and "#LIQUID" in env[-1][1]                  # Rs 1.5 cr/day skipped, Rs 2.5 cr/day sent
