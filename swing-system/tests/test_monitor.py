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
