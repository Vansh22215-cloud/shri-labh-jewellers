"""Owner 17 Nov: 'instant message on Telegram once the stop-loss is hit'."""
import pandas as pd

from swing import live_engine as le


def _tip(**kw):
    r = {"time": "2026-11-16 18:40", "type": "NORMAL", "symbol": "ABC", "side": "buy", "entry": 100.0, "stop": 95.0,
         "targets": "", "rank": 6, "qty": 40, "status": "open", "hit": 0, "day": "2026-11-16", "setup": "RCP"}
    r.update(kw)
    return r


def _sent(monkeypatch):
    out = []
    monkeypatch.setattr(le, "send", lambda text, label="trade tip": out.append((label, text)))
    return out


def test_touch_between_two_checks_is_caught_for_a_tip_from_before_today(monkeypatch):
    sent = _sent(monkeypatch)
    le.save_tip(_tip())
    now = pd.Timestamp("2026-11-17 11:00")
    # price is back above the stop now, but today's low (after the tip, which was sent last evening) touched it
    le.exits({"ABC": {"last": 96.5, "open": 99.0, "high": 99.5, "low": 94.8}}, now)
    assert sent and sent[0][0] == "exit alert" and "STOP-LOSS HIT" in sent[0][1] and "positional" in sent[0][1]
    t = le.load_tips()
    assert t["status"].iloc[0] == "stop" and float(t["exit_px"].iloc[0] if "exit_px" in t else 95.0) == 95.0


def test_gap_below_the_stop_reports_the_real_exit_price(monkeypatch):
    sent = _sent(monkeypatch)
    le.save_tip(_tip())
    le.exits({"ABC": {"last": 91.0, "open": 90.0, "high": 91.5, "low": 89.5}}, pd.Timestamp("2026-11-17 09:15:30"))
    msg = sent[0][1]
    assert "straight through the stop" in msg and "90" in msg and "-10.0%" in msg and "₹400" in msg


def test_same_day_tip_ignores_moves_before_it_was_sent(monkeypatch):
    sent = _sent(monkeypatch)
    le.save_tip(_tip(time="2026-11-17 11:00", type="INTRADAY", setup="VWAP"))
    le.exits({"ABC": {"last": 97.0, "open": 99.0, "high": 101, "low": 94.0}}, pd.Timestamp("2026-11-17 11:30"))
    assert sent == []                       # the day's low of 94 came before the tip


def test_target_message_has_result(monkeypatch):
    sent = _sent(monkeypatch)
    le.save_tip(_tip(targets="104/108"))
    le.exits({"ABC": {"last": 104.5, "open": 100.0, "high": 104.6, "low": 99.0}}, pd.Timestamp("2026-11-17 10:00"))
    assert "TARGET 1 HIT" in sent[0][1] and "+4.0%" in sent[0][1] and "₹160" in sent[0][1]


def test_fast_watcher_alerts_within_one_cycle(monkeypatch):
    from swing import kite
    sent = _sent(monkeypatch)
    le.save_tip(_tip())
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    calls = []
    monkeypatch.setattr(kite, "quotes", lambda syms: calls.append(list(syms)) or
                        {"ABC": {"last": 94.0, "open": 99.0, "high": 99.0, "low": 93.9}})
    monkeypatch.setattr(le, "now_ist", lambda: pd.Timestamp("2026-11-17 10:00"))
    e = le.Engine()
    monkeypatch.setattr(le.time, "sleep", lambda s: setattr(e, "stop_flag", True))
    e.watch_exits(every=5)
    assert calls == [["ABC"]]               # one small request for just the open tips
    assert sent and "STOP-LOSS HIT" in sent[0][1]


def test_ai_picks_are_off_in_settings():
    from swing.config import load_settings
    assert load_settings()["ai_picks"] is False


def test_rotated_bot_key_hands_over_once(monkeypatch, tmp_path):
    from swing import bot, daemon
    monkeypatch.setattr(daemon, "DATA", tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(bot, "TOKEN_REFUSED_SINCE", None)
    assert not daemon.token_rotated(1000.0)
    monkeypatch.setattr(bot, "TOKEN_REFUSED_SINCE", 1000.0)
    assert not daemon.token_rotated(1100.0)          # wait 3 minutes first (a single hiccup is not a rotation)
    assert daemon.token_rotated(1200.0)              # hand over: next run gets the new GitHub Secret
    assert not daemon.token_rotated(1300.0)          # at most once every 30 minutes - no fast restart loop
    assert daemon.token_rotated(1200.0 + 1900)


def test_only_bought_tips_count_toward_limits_and_skipped_ones_stay_quiet(monkeypatch):
    from swing import bot, safety
    sent = _sent(monkeypatch)
    S = {"capital": 45000, "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25, "max_open_risk_pct": 2}}
    for i in range(3):                                         # 3 positional tips, 1% risk each, none confirmed
        le.save_tip(_tip(symbol=f"P{i}", qty=90, status="open"))
    ok, why = safety.portfolio_check(_tip(symbol="NEW", qty=90), S)
    assert ok, why                                             # unconfirmed tips never block (no positional cap)
    assert "Noted" in bot.trade_command("/bought P0") and "Noted" in bot.trade_command("/bought P1")
    ok, why = safety.portfolio_check(_tip(symbol="NEW", qty=90), S)
    assert not ok and "total money at risk" in why            # 2 bought at 1% each = the 2% limit
    assert "did not take" in bot.trade_command("/skip P2")
    le.exits({"P2": {"last": 90.0, "open": 99.0, "high": 99.0, "low": 89.0}}, pd.Timestamp("2026-11-17 10:00"))
    assert sent == []                                          # skipped tip: no exit alert
    assert le.load_tips().set_index("symbol").loc["P2", "status"] == "stop"   # but its result is still recorded


def test_kite_connected_notice_once_a_day(monkeypatch, tmp_path):
    monkeypatch.setattr(le, "DATA", tmp_path)
    assert le.late_login_notice_due(pd.Timestamp("2026-11-17 10:30"))
    assert not le.late_login_notice_due(pd.Timestamp("2026-11-17 12:23"))     # next run hand-over: no repeat
    assert le.late_login_notice_due(pd.Timestamp("2026-11-18 10:00"))
