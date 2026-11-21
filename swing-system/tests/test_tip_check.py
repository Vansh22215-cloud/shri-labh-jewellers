"""Tip check: the owner's tips replayed minute by minute (entry, stop before targets, targets, 30-minute close stop)."""
import json

import numpy as np
import pandas as pd

from swing import daemon, kite, tip_check as tc


def mins(day, path, start="09:15"):
    idx = pd.date_range(pd.Timestamp(day) + pd.Timedelta(start + ":00"), periods=len(path), freq="1min")
    c = np.array(path, float)
    return pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5, "close": c, "volume": 1.0}, index=idx)


TIP = {"id": "a", "day": "2026-11-20", "time": "09:26", "underlying": "NIFTY", "kind": "CE", "strike": 25450,
       "side": "BUY", "entry": "above", "price": 116, "sl": 95, "targets": [130, 140, 150], "text": "x"}


def test_breakout_buy_reaches_two_targets_then_back_to_cost():
    path = [109] * 12 + list(np.linspace(110, 141, 30)) + list(np.linspace(141, 110, 40)) + [110] * 300
    r = tc.evaluate(TIP, mins("2026-11-20", path))
    e = r["entry_px"]
    assert r["entered"] and 116 <= e < 117                                  # filled at 116, or the open if above
    assert [x for x, _ in r["hits"]] == [130, 140] and r["stop"]           # stop moved to cost after target 1
    assert r["pts_t1"] == round(130 - e, 2) and abs(r["pts_thirds"] - ((130 - e) + (140 - e)) / 3) < 0.02


def test_entry_never_reached_means_no_trade():
    r = tc.evaluate(TIP, mins("2026-11-20", [109] * 375))
    assert r["entered"] is None and "never reached" in r["note"]


def test_sell_with_thirty_minute_close_stop_ignores_a_spike():
    tip = {"id": "c", "day": "2026-11-20", "time": "10:19", "underlying": "PAYTM", "kind": "FUT", "side": "SELL",
           "entry": "at", "price": 1762, "sl": 1775, "sl_rule": "30min_close", "targets": [1745, 1725, 1700], "text": "x"}
    path = [1755] * 70 + [1763, 1778, 1770] + list(np.linspace(1768, 1740, 60)) + [1740] * 242
    r = tc.evaluate(tip, mins("2026-11-20", path))
    assert r["entered"] and r["stop"] is None                               # 1778 spike, but no 30-min close above
    assert r["hits"][0][0] == 1745


def test_daemon_runs_pending_tips_first_outside_market_hours(monkeypatch):
    from datetime import datetime
    from swing.daemon import IST
    tc.INBOX.write_text(json.dumps([TIP]))
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    sat = datetime(2026, 11, 21, 22, 0, tzinfo=IST)
    assert daemon.due(sat) == ["tips"]
    tc.DONE_F.write_text(json.dumps({"a": "done"}))
    assert "tips" not in daemon.due(sat)
