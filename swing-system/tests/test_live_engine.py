import pandas as pd

from swing import live_engine as le


def _bars(rows, start="2026-11-12 09:15"):
    idx = pd.date_range(start, periods=len(rows), freq="5min")
    return pd.DataFrame([{"open": o, "high": h, "low": l, "close": c, "volume": v} for o, h, l, c, v in rows], index=idx)


CTX = {"trend_long": 1.0, "trend_short": 0.2, "value_cr": 80.0, "patterns": 3, "bull_candles": 1, "bear_candles": 0}


def test_rank_rewards_quality_and_risk_follows_rank():
    good = {"setup": "ORB", "side": "buy", "entry": 100, "stop": 99, "targets": [101, 102, 103], "rel_vol": 3.0}
    stats = {"ORB": {"avg_net": 120, "allowed": True}}
    r_good, _ = le.rank(good, CTX, {"target": 60, "stop": 25}, stats)
    weak = dict(good, rel_vol=0.4)
    r_weak, _ = le.rank(weak, dict(CTX, trend_long=0.2, patterns=0, bull_candles=0, value_cr=5),
                        {"target": 20, "stop": 60}, {"ORB": {"avg_net": -50, "allowed": False}})
    assert r_good >= 8 and r_weak <= 4 and 1 <= r_weak <= 10
    assert le.risk_pct(9, "EQ") == 2.0 and le.risk_pct(6, "EQ") == 1.0 and le.risk_pct(9, "FNO") == 5.0


def test_formats_match_owner_samples():
    c = {"symbol": "RSYSTEMS", "side": "buy", "entry": 274, "stop": 272, "targets": [278, 282, 285], "setup": "ORB"}
    t = le.fmt_intraday(c, 8, 150)
    for part in ("Buy #RSYSTEMS at 274 👍", "STRICT STOPLOSS 272 ❗️❗️", "Target 278/282/285", "INTRADAY TRADE ONLYYY 📊",
                 "RANK - 8/10"):
        assert part in t
    n = le.fmt_normal({"symbol": "TEMPSENS", "entry": 540, "stop": 530, "targets": [560, 580]}, 9, 17, 2.0)
    assert "Bought #TEMPSENS at 540 📊" in n and "SL at 530 ❗️" in n and "2% Risk" in n and "RANK - 9/10" in n
    o = {"kind": "PE", "expiry": pd.Timestamp("2026-11-26"), "strike": 1120, "premium": 25, "premium_hi": 26,
         "targets": [35, 42, 50, 58], "spot_sl": 1150, "lot": 375, "loss": 1300}
    f = le.fmt_fno({"symbol": "VOLTAS"}, o, 8)
    for part in ("📉 VOLTAS", "🖲 NOV 1,120 PE 25-26".replace("1,120", "1,120"), "✅ Target-35-42-50-58+",
                 "⛔️ Stoploss-1,150 SPOT (75 Min CB)", "✨ Lot Size- 375", "RANK - 8/10"):
        assert part in f, part


def test_vwap_reclaim_on_last_bar_only():
    rows = [(100, 100.2, 99.0, 99.2, 1000)] + [(99.2, 99.4, 98.6, 98.8, 1000)] * 9 + [(98.8, 100.6, 98.7, 100.5, 5000)]
    b = _bars(rows)
    s = le.vwap_signal(b)
    assert s and s[0]["side"] == "buy" and s[0]["setup"] == "VWAP" and s[0]["stop"] < s[0]["entry"]
    now = b.index[-1] + pd.Timedelta(minutes=5)
    cands = le.intraday_candidates("X", b, 100.0, now)
    assert any(c["setup"] == "VWAP" for c in cands) and all(len(c["targets"]) == 3 for c in cands)


def test_option_trade_picks_liquid_strike_within_risk(monkeypatch):
    from swing import kite
    ins = pd.DataFrame([{"tradingsymbol": f"VOLTAS26NOV{k}PE", "name": "VOLTAS", "expiry": pd.Timestamp("2026-11-26"),
                         "strike": float(k), "lot_size": 375, "instrument_type": "PE"} for k in (1100, 1120, 1140, 1160)])
    monkeypatch.setattr(le, "nfo", lambda: ins)

    class Q:
        def __init__(self, ts):
            self.ts = ts

        def json(self):
            return {"data": {f"NFO:{self.ts}": {"last_price": 25.0, "oi": 10000,
                                                "depth": {"buy": [{"price": 24.9}], "sell": [{"price": 25.1}]}}}}
    monkeypatch.setattr(kite, "_get", lambda path, params=None, timeout=20: Q(params[0][1].split(":")[1]))
    wide = {"symbol": "VOLTAS", "side": "sell", "entry": 1130.0, "stop": 1150.0, "targets": [1110.0, 1090.0, 1070.0]}
    now = pd.Timestamp("2026-11-12 10:30")
    assert le.option_trade(wide, 8, 1130.0, now, 45000) is None                    # loss at SL above the rank's limit
    c = {"symbol": "VOLTAS", "side": "sell", "entry": 1130.0, "stop": 1134.0, "targets": [1122.0, 1114.0, 1106.0]}
    o = le.option_trade(c, 8, 1130.0, now, 45000)
    assert o and o["kind"] == "PE" and o["lot"] == 375 and o["loss"] <= 45000 * 0.03 and len(o["targets"]) >= 2
    assert le.option_trade(c, 6, 1130.0, now, 4000) is None                       # too small capital: skipped


def test_exit_alerts_once_each(monkeypatch, tmp_path):
    monkeypatch.setattr(le, "TIPS_F", tmp_path / "t.csv")
    sent = []
    monkeypatch.setattr(le, "send", lambda text, label="trade tip": sent.append((label, text)))
    le.save_tip({"time": "2026-11-12 10:00", "type": "INTRADAY", "symbol": "RSYSTEMS", "side": "buy", "entry": 274, "stop": 272,
                 "targets": "278/282/285", "rank": 8, "qty": 10, "status": "open", "hit": 0, "day": "2026-11-12"})
    now = pd.Timestamp("2026-11-12 11:00")
    le.exits({"RSYSTEMS": {"last": 282.5, "high": 283, "low": 273}}, now)
    assert [l for l, _ in sent] == ["exit alert", "exit alert"] and "Target 2 hit" in sent[-1][1]
    sent.clear()
    le.exits({"RSYSTEMS": {"last": 282.5, "high": 283, "low": 273}}, now)
    assert sent == []                                                             # nothing repeated
    le.exits({"RSYSTEMS": {"last": 271, "high": 283, "low": 270}}, now)
    assert "stop-loss" in sent[-1][1] and le.load_tips()["status"].iloc[0] == "stop"


def test_quality_gates():
    c = {"setup": "ORB", "side": "buy", "entry": 100, "stop": 99, "targets": [101, 102], "rel_vol": 2.0}
    assert le.gates(c, CTX, {"target": 55, "stop": 40}, {})[0] is True
    assert le.gates(c, dict(CTX, trend_long=0.2), None, {})[0] is False                     # against the trend
    assert le.gates(dict(c, rel_vol=1.0), CTX, None, {})[0] is False                        # no volume
    assert le.gates(c, CTX, {"target": 30, "stop": 50}, {})[0] is False                     # stop comes first
    assert le.gates(c, CTX, None, {"ORB": {"allowed": False}})[0] is False                  # failed the history test


def test_tips_carry_tradingview_link_and_all_setups_exist():
    c = {"symbol": "RSYSTEMS", "side": "buy", "entry": 274, "stop": 272, "targets": [278, 282, 285], "setup": "RANGE"}
    assert "tradingview.com/chart/?symbol=NSE:RSYSTEMS&interval=5" in le.fmt_intraday(c, 8, 10)
    assert "symbol=NSE:NIFTY&" in le.tv_link("NIFTY50")
    from swing import setups
    rows = [(100, 100.5, 99.5, 100.2, 1000)] * 14 + [(100.2, 102.5, 100.1, 102.4, 6000)]
    idx = pd.date_range("2026-11-12 09:15", periods=len(rows), freq="5min")
    b = pd.DataFrame([dict(open=o, high=h, low=l, close=c_, volume=v) for o, h, l, c_, v in rows], index=idx)
    got = {(x["setup"], x["side"]) for x in setups.all_signals(b, 99.0)}
    assert ("RANGE", "buy") in got
    for x in setups.all_signals(b, 99.0):                    # never a trigger from a future bar
        assert x["entry_time"] <= b.index[-1]


def test_exit_ignores_prices_from_before_the_tip(monkeypatch, tmp_path):
    """Regression (12 Nov): a dip BEFORE the tip was sent must not count as a stop-loss hit."""
    monkeypatch.setattr(le, "TIPS_F", tmp_path / "t.csv")
    sent = []
    monkeypatch.setattr(le, "send", lambda text, label="trade tip": sent.append(text))
    le.save_tip({"time": "2026-11-12 11:00", "type": "INTRADAY", "symbol": "X", "side": "buy", "entry": 100, "stop": 99,
                 "targets": "101/102/103", "rank": 8, "qty": 10, "status": "open", "hit": 0, "day": "2026-11-12"})
    idx = pd.date_range("2026-11-12 09:15", "2026-11-12 11:10", freq="5min")
    b = pd.DataFrame({"open": 100.0, "high": 100.2, "low": 99.8, "close": 100.0, "volume": 1}, index=idx)
    b.loc[pd.Timestamp("2026-11-12 09:30"), "low"] = 97.0                          # the morning dip, before the tip
    q = {"X": {"last": 100.1, "high": 100.5, "low": 97.0}}                          # day's low includes that dip
    le.exits(q, pd.Timestamp("2026-11-12 11:12"), candles={"X": b})
    assert sent == [] and le.load_tips()["status"].iloc[0] == "open"


def test_noise_proof_stop_follow_through_and_market():
    from swing import setups
    sg = {"setup": "ORB", "side": "buy", "entry": 100.0, "stop": 99.9, "target": 100.1}
    n = setups.noise_proof(sg, 0.5)
    assert n["stop"] == 99.5 and n["targets"] == [100.5, 101.0, 101.5]               # widened to 1 ATR
    assert setups.noise_proof(dict(sg, stop=97.0), 0.5) is None                     # wider than 3 ATR: skipped
    c = {"side": "buy", "entry": 100.0, "stop": 99.0}
    assert le.follow_through(c, {"last": 100.2})[0] and not le.follow_through(c, {"last": 100.5})[0]
    assert not le.follow_through(c, {"last": 99.8})[0]                              # breakout already failed
    assert le.market_agrees(c, {"last": 101, "open": 100}) and not le.market_agrees(c, {"last": 99, "open": 100})


def test_learning_pauses_a_losing_setup(monkeypatch, tmp_path):
    monkeypatch.setattr(le, "SHADOW_F", tmp_path / "s.csv")
    pd.DataFrame([{"setup": "RANGE", "status": "closed", "result_r": -1.0}] * 10 +
                 [{"setup": "RANGE", "status": "closed", "result_r": 1.0}] * 3 +
                 [{"setup": "VWAP", "status": "closed", "result_r": 2.0}] * 12).to_csv(le.SHADOW_F, index=False)
    rec = le.live_record()
    assert rec["RANGE"]["paused"] and not rec["VWAP"]["paused"]
    st = le.learned_stats()
    assert st["RANGE"]["allowed"] is False and st["VWAP"]["avg_net"] > 0
