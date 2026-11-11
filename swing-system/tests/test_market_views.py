from datetime import datetime, timezone

import numpy as np
import pandas as pd

from swing import market_views as mv, tipcheck

DARK_HORSE = "#Nifty Shows Trend Continuation On 60 Min TF ✅\n\nWeakness Only Sustaining Below 24290 ✅"


def _bars(prices, start="2026-11-06 04:00"):
    idx = pd.date_range(start, periods=len(prices), freq="h", tz="UTC")
    p = np.array(prices, float)
    return pd.DataFrame({"open": p, "high": p * 1.001, "low": p * 0.999, "close": p}, index=idx)


def test_parses_index_view_forex_gold_crypto():
    v = mv.parse(DARK_HORSE)
    assert v["ticker"] == "^NSEI" and v["side"] == "buy" and v["wrong_if"] == ("below", 24290.0)
    assert v["type"] == "view" and v["timeframe"] == "60 min"
    g = mv.parse("XAUUSD BUY NOW 2650 SL 2640 TP1 2670 TP2 2690")
    assert (g["ticker"], g["entry"], g["stop"], g["targets"], g["type"]) == ("GC=F", 2650, 2640, [2670, 2690], "setup")
    f = mv.parse("EUR/USD sell 1.0850 sl 1.0880 tp 1.0800")
    assert (f["ticker"], f["side"], f["entry"], f["stop"], f["targets"]) == ("EURUSD=X", "sell", 1.085, 1.088, [1.08])
    b = mv.parse("BTCUSD long entry 68000 stop 66000 target 72000")
    assert b["targets"] == [72000] and b["ticker"] == "BTC-USD"
    assert mv.parse("Bank Nifty bearish, strength only above 52500")["wrong_if"] == ("above", 52500.0)
    assert mv.parse("Nifty IT looks strong") is None or mv.parse("Nifty IT looks strong")["ticker"] != "^NSEI"
    assert mv.parse("BUY TATASTEEL 150 SL 145") is None


def test_evaluate_view_uses_one_to_one_target():
    v = mv.parse(DARK_HORSE)
    h = _bars(np.linspace(24000, 24600, 400))
    verdict, reasons, plan = mv.evaluate(v, h=h, d=None)
    assert plan["stop"] == 24290 and abs(plan["target"] - (24600 + 310)) < 1 and plan["side"] == "buy"
    assert verdict in ("GOOD", "NEUTRAL", "RISKY")


def test_walk_stop_first_and_entry_wait():
    up = _bars([100, 101, 103, 106])
    assert mv._walk(up, "buy", 100, 98, 105, False)[0] == "target"
    both = pd.DataFrame({"open": [100], "high": [106], "low": [97], "close": [100]},
                        index=pd.date_range("2026-11-06", periods=1, freq="h", tz="UTC"))
    assert mv._walk(both, "buy", 100, 98, 105, False)[0] == "stop"          # same bar: stop counted first
    assert mv._walk(_bars([110, 111, 112]), "buy", 100, 98, 105, True)[0] == "waiting entry"


def test_track_marks_outcome_and_alerts(monkeypatch, tmp_path):
    monkeypatch.setattr(tipcheck, "TIPS_F", tmp_path / "ft.csv")
    t0 = datetime(2026, 11, 6, 4, tzinfo=timezone.utc)
    tipcheck.save({"symbol": "Nifty 50", "side": "buy", "horizon": "60 min", "raw": DARK_HORSE}, "NEUTRAL",
                  {"entry": 24600, "stop": 24290, "target": 24910}, "Dark Horse", outcome="open",
                  extra={"kind": "index view", "ticker": "^NSEI", "checked_utc": t0.isoformat(), "hours": 72})
    rising = _bars(np.linspace(24600, 25000, 10), start="2026-11-06 05:00")
    msgs = mv.track(send=False, now=t0, fetch=lambda tk, period=None: rising)
    assert len(msgs) == 1 and "RIGHT" in msgs[0]
    assert pd.read_csv(tipcheck.TIPS_F)["outcome"].iloc[0] == "target"
    assert "1 of 1" in mv.source_record("Dark Horse")
    assert mv.track(send=False, now=t0, fetch=lambda tk, period=None: rising) == []   # alert only once


def test_track_expires_after_its_time(monkeypatch, tmp_path):
    monkeypatch.setattr(tipcheck, "TIPS_F", tmp_path / "ft.csv")
    t0 = datetime(2026, 11, 6, 4, tzinfo=timezone.utc)
    tipcheck.save({"symbol": "Gold (USD)", "side": "buy", "raw": "x"}, "RISKY",
                  {"entry": 2650, "stop": 2640, "target": 2670}, "FX", outcome="open",
                  extra={"kind": "commodity setup", "ticker": "GC=F", "checked_utc": t0.isoformat(), "hours": 24})
    flat = _bars([2650] * 30, start="2026-11-06 05:00")
    later = datetime(2026, 11, 8, 4, tzinfo=timezone.utc)
    assert "NO RESULT" in mv.track(send=False, now=later, fetch=lambda tk, period=None: flat)[0]


def test_earlier_unknown_message_is_reread_and_tracked(monkeypatch, tmp_path):
    monkeypatch.setattr(tipcheck, "TIPS_F", tmp_path / "ft.csv")
    monkeypatch.setattr("swing.config.on_github", lambda: True)
    tipcheck.save({"symbol": None, "side": "buy", "horizon": "swing", "raw": DARK_HORSE}, "UNKNOWN", {}, "Dark Horse",
                  outcome="n/a")
    df = pd.read_csv(tipcheck.TIPS_F)
    df.loc[0, "checked"] = "2026-11-06 06:11:00"            # 11:41 IST, stored in UTC on GitHub
    df.to_csv(tipcheck.TIPS_F, index=False)
    h = _bars(list(np.linspace(24300, 24600, 300)) + [24620, 24700, 24800, 24950], start="2026-10-24 00:00")
    msgs = mv.track(send=False, now=datetime(2026, 11, 7, tzinfo=timezone.utc), fetch=lambda tk, period=None: h)
    out = pd.read_csv(tipcheck.TIPS_F).iloc[0]
    assert out["ticker"] == "^NSEI" and out["stop"] == 24290
    assert out["outcome"] in ("open", "target") and (out["outcome"] == "open" or "RIGHT" in msgs[0])


def test_reply_card_structure():
    from swing import reply_card as rc
    t = rc.build("RISKY", "Nifty 50 · view (buy)", said="Bullish", now="24,600", pros=["trend up"],
                 cons=["odds weak"], p=48, need=50, plan={"side": "buy", "entry": 24600, "stop": 24290,
                                                          "target": 24910, "rr": 1.0}, raw="SURE SHOT jackpot")
    for part in ("RISKY", "What the tip says", "Why it could work", "Why it could fail", "The odds", "Bottom line",
                 "hype words", "48 out of 100"):
        assert part in t
    assert "The plan" not in rc.build("AVOID", "x", plan={"stop": 1, "entry": 2, "target": 3})   # no plan on skip
