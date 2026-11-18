import json

import pandas as pd

from swing import monitor


def _cap(monkeypatch):
    sent = []
    monkeypatch.setattr(monitor, "_send", lambda text: sent.append(text))
    return sent


def test_recovery_message_after_a_gap(monkeypatch, tmp_path):
    sent = _cap(monkeypatch)
    monkeypatch.setattr(monitor, "HB_F", tmp_path / "hb.json")
    monkeypatch.setattr(monitor, "_STARTED", {"done": False})
    (tmp_path / "hb.json").write_text(json.dumps({"last": "2026-11-17 10:00:00"}))
    monitor.heartbeat(pd.Timestamp("2026-11-17 12:30"))
    assert sent and "recovered" in sent[0] and "2.5 h" in sent[0]
    monitor.heartbeat(pd.Timestamp("2026-11-17 12:31"))
    assert len(sent) == 1


def test_no_recovery_message_for_a_normal_handover(monkeypatch, tmp_path):
    sent = _cap(monkeypatch)
    monkeypatch.setattr(monitor, "HB_F", tmp_path / "hb.json")
    monkeypatch.setattr(monitor, "_STARTED", {"done": False})
    (tmp_path / "hb.json").write_text(json.dumps({"last": "2026-11-17 10:00:00"}))
    monitor.heartbeat(pd.Timestamp("2026-11-17 10:02"))
    assert not sent


def test_kill_switch_change_is_announced(monkeypatch, tmp_path):
    sent = _cap(monkeypatch)
    monkeypatch.setattr(monitor, "DATA", tmp_path)
    monitor.kill_switch_watch({"kill_switch": False})
    monitor.kill_switch_watch({"kill_switch": True})
    monitor.kill_switch_watch({"kill_switch": True})
    monitor.kill_switch_watch({"kill_switch": False})
    assert len(sent) == 2 and "KILL SWITCH ON" in sent[0] and "OFF" in sent[1]


def test_status_explains_why_no_tips(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "DATA", tmp_path)
    monkeypatch.setattr("swing.health.traded_today", lambda now=None: True)
    (tmp_path / "evening_status.json").write_text(json.dumps({"date": "2026-11-17", "fresh": False, "last_bar": "2026-11-14",
                                                             "counts": {}, "failed": []}))
    t = monitor.status_text(pd.Timestamp("2026-11-17 19:30"))
    assert "data unavailable" in t and "NOT fresh" in t
    (tmp_path / "evening_status.json").write_text(json.dumps({"date": "2026-11-17", "fresh": True, "counts": {"positional tips": 0},
                                                             "failed": []}))
    assert "no stock met the tested rules" in monitor.status_text(pd.Timestamp("2026-11-17 19:30"))
    monkeypatch.setattr("swing.health.traded_today", lambda now=None: False)
    assert "market closed" in monitor.status_text(pd.Timestamp("2026-11-17 19:30"))
    (tmp_path / "evening_status.json").unlink()
    monkeypatch.setattr("swing.health.traded_today", lambda now=None: True)
    assert "did not run" in monitor.status_text(pd.Timestamp("2026-11-17 19:30"))


def test_daily_status_lists_todays_tips_by_likely_win(monkeypatch, tmp_path):
    import pandas as pd
    from swing import live_engine as le, monitor, vantage
    day = "2026-11-17"
    for sym, setup, rank in (("ICICIBANK", "RCP", 6), ("TITAN", "HP", 10), ("MCX", "BRK", 6)):
        le.save_tip({"time": f"{day} 18:41", "type": "NORMAL", "symbol": sym, "side": "buy", "entry": 100, "stop": 90,
                     "targets": "", "rank": rank, "qty": 4, "status": "open", "hit": 0, "day": day, "setup": setup})
    monkeypatch.setattr(vantage, "SIGNALS_F", tmp_path / "v.csv")
    pd.DataFrame([{"sym": "GLENMARK", "signal": day, "setup": "RCP", "likely": "46", "sent_at": f"{day} 15:42",
                   "status": "open"}]).to_csv(tmp_path / "v.csv", index=False)
    lines = monitor.tips_ranked(day)
    assert lines[1] == "Tips (most likely to win first):"
    assert lines[2:] == ["#DIPBUY #TITAN - 79%", "#VANTAGE #GLENMARK (trend) - 46%", "#POSITIONAL #ICICIBANK - 45%",
                         "#BREAKOUT #MCX - 38%",
                         "(VANTAGE % = how often that type of signal won in 13 years of NSE data)"]
    assert "#DIPBUY #TITAN - 79%" in monitor.status_text(pd.Timestamp(f"{day} 19:20"))


def test_tips_list_sent_once_on_its_own_if_the_status_already_went_out(monkeypatch):
    import pandas as pd
    from swing import monitor, daemon
    claimed, sent = set(), []
    monkeypatch.setattr(daemon, "claim_once", lambda k, now=None: (k not in claimed, claimed.add(k))[0])
    monkeypatch.setattr(monitor, "_send", lambda text: sent.append(text))
    monkeypatch.setattr(monitor, "tips_ranked", lambda day, limit=15: ["", "Tips (most likely to win first):", "#VANTAGE #X - 80%"])
    claimed.add("daily status")                               # today's status was sent by the old version
    t = pd.Timestamp("2026-11-17 21:55")
    monitor.daily_status(t)
    monitor.daily_status(t)
    assert len(sent) == 1 and "#VANTAGE #X - 80%" in sent[0]
