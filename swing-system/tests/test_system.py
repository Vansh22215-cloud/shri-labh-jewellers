"""Runner schedule, bot commands, one-time clean start, backup, and: no Yahoo anywhere."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from swing import backup, bot, daemon, kite, reset, strategy
from swing.strategy import Strategy

IST = timezone(timedelta(hours=5, minutes=30))
ROOT = Path(__file__).resolve().parent.parent


def test_no_yahoo_and_no_order_endpoints_in_the_code():
    for f in list((ROOT / "swing").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        s = f.read_text()
        assert "yfinance" not in s and "import yf" not in s, f
        assert not re.search(r"/orders|/gtt|place_order|/portfolio", s), f
    assert "yfinance" not in (ROOT / "requirements.txt").read_text()
    assert kite.READ_ONLY_PREFIXES == ("/quote", "/instruments")
    with pytest.raises(PermissionError):
        kite._get("/orders/regular")


def test_downloads_never_in_market_hours_and_learner_on_saturday(monkeypatch):
    assert daemon.key("candles", datetime(2026, 11, 20, 10, 0, tzinfo=IST)) is None
    assert daemon.key("candles", datetime(2026, 11, 20, 15, 45, tzinfo=IST)) is None
    assert daemon.key("candles", datetime(2026, 11, 20, 19, 0, tzinfo=IST))
    assert daemon.key("candles", datetime(2026, 11, 21, 11, 0, tzinfo=IST))
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    assert daemon.due(datetime(2026, 11, 21, 10, 31, tzinfo=IST)) == ["learner"]
    assert daemon.due(datetime(2026, 11, 20, 19, 0, tzinfo=IST)) == ["company"]    # evening: company first
    daemon.claim("company", datetime(2026, 11, 20, 19, 0, tzinfo=IST))
    assert daemon.due(datetime(2026, 11, 20, 19, 0, tzinfo=IST)) == ["candles"]
    assert daemon.due(datetime(2026, 11, 22, 11, 0, tzinfo=IST)) == ["candles"]    # Sunday morning
    assert daemon.due(datetime(2026, 11, 20, 11, 0, tzinfo=IST)) == []


def test_test_queue_waits_for_complete_history(monkeypatch):
    class T(Strategy):
        name, interval = "t1", "day"

        def entries(self, d):
            return d["close"] > 0
    monkeypatch.setattr(strategy, "load_all", lambda: {"t1": T()})
    monkeypatch.setattr(kite, "logged_in", lambda: False)
    daemon.TEST_QUEUE.write_text(json.dumps(["t1"]))
    from swing import candles
    monkeypatch.setattr(candles, "complete", lambda iv="day": False)
    assert "test" not in daemon.due(datetime(2026, 11, 20, 19, 0, tzinfo=IST))
    monkeypatch.setattr(candles, "complete", lambda iv="day": True)
    assert "test" in daemon.due(datetime(2026, 11, 20, 19, 0, tzinfo=IST))
    assert "test" not in daemon.due(datetime(2026, 11, 20, 11, 0, tzinfo=IST))     # never in market hours


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    p = tmp_path / "settings.yaml"
    p.write_text("capital: 51000\nkill_switch: false\nstop_loss_pct: 1.0\nlive_strategies: []\n")
    monkeypatch.setattr(bot, "ROOT", tmp_path)
    from swing import config
    monkeypatch.setattr(bot, "load_settings", lambda: config.load_settings(p))
    monkeypatch.setattr(bot, "RESULTS", tmp_path / "results")
    return p


def test_bot_capital_kill_and_approval_needs_a_test(settings_file, monkeypatch):
    class T(Strategy):
        name, interval = "t1", "day"

        def entries(self, d):
            return d["close"] > 0
    monkeypatch.setattr(strategy, "load_all", lambda: {"t1": T()})
    assert "60,000" in bot.capital_command("/capital 60000")
    assert "capital: 60000" in settings_file.read_text()
    assert "big change" in bot.capital_command("/capital 500000")
    bot.kill_command(True)
    assert "kill_switch: true" in settings_file.read_text()
    bot.kill_command(False)
    assert "not been tested" in bot.approve_command("/approve t1")
    (bot.RESULTS / "tests").mkdir(parents=True)
    (bot.RESULTS / "tests" / "t1.json").write_text("{}")
    assert "approved" in bot.approve_command("/approve t1")
    assert "live_strategies: [t1]" in settings_file.read_text()
    assert "stopped" in bot.approve_command("/unapprove t1", False)
    assert "live_strategies: []" in settings_file.read_text()
    assert "No strategy" in bot.approve_command("/approve nope")


def test_clean_start_deletes_old_data_and_records_keeps_kite(tmp_path, monkeypatch):
    data, priv = tmp_path / "data", tmp_path / "data" / "private"
    for p in ["prices/RELIANCE.csv", "bhavcopy/x.csv", "delisted_raw.csv", "kite_daily/A.csv", "bot_offset.txt",
              "kite_candles/60minute/A.parquet", "private/kite_token.bin", "private/vantage_signals.csv",
              "private/old_system/my_trades.csv", "fundamentals/A.json", "fundamentals/nse_xbrl/1.json"]:
        f = data / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
    (data / "kite_candles" / "state.json").write_text(json.dumps({"60minute|A": {"ended": True}}))
    monkeypatch.setattr(reset, "DATA", data)
    monkeypatch.setattr(reset, "PRIVATE", priv)
    monkeypatch.setattr(reset, "FLAG", data / "reset_v3.done")
    r = reset.maybe_run(force=True)
    for gone in ("prices", "bhavcopy", "kite_daily", "fundamentals", "private/old_system", "private/vantage_signals.csv"):
        assert not (data / gone).exists(), gone
    assert (data / "candles" / "60minute" / "A.parquet").exists()
    assert json.loads((data / "candles" / "state.json").read_text())["60minute|A"]["ended"]
    assert (priv / "kite_token.bin").exists() and (data / "bot_offset.txt").exists()
    assert r["removed"] == 2 and reset.maybe_run(force=True) is None             # only once


def test_backup_roundtrip(tmp_path):
    p = backup.PRIVATE
    p.mkdir(parents=True)
    pd.DataFrame({"id": ["a"], "sym": ["X"]}).to_csv(p / "tips.csv", index=False)
    (p / "kite_token.bin").write_text("secret")
    blob = backup.build()
    import io
    import zipfile
    assert "kite_token.bin" not in zipfile.ZipFile(io.BytesIO(blob)).namelist()
    pd.DataFrame({"id": ["b"], "sym": ["Y"]}).to_csv(p / "tips.csv", index=False)
    assert backup.restore(blob) == 1
    assert set(pd.read_csv(p / "tips.csv")["id"]) == {"a", "b"}


def test_replay_runs_once_outside_market_hours(monkeypatch):
    (daemon.DATA / "replay_done.txt").unlink()
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    assert "replay" in daemon.due(datetime(2026, 11, 20, 19, 0, tzinfo=IST))
    assert "replay" not in daemon.due(datetime(2026, 11, 20, 11, 0, tzinfo=IST))
    (daemon.DATA / "replay_wait.txt").write_text("1")                       # failed a moment ago: waits 30 min
    assert "replay" not in daemon.due(datetime(2026, 11, 20, 19, 0, tzinfo=IST))
