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
        # the one exception, approved in writing by the owner (21 Nov 2026): Kite's margin calculator, which places nothing
        assert not re.search(r"/orders|/gtt|place_order|/portfolio", s.replace('"/margins/orders"', "")), f
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


def test_nse_holiday_is_not_a_market_day(monkeypatch):
    from swing import market_days, candles
    monkeypatch.setattr(market_days, "holidays", lambda: {"2026-11-24"})
    assert not market_days.is_trading_day("2026-11-24") and market_days.is_trading_day("2026-11-23")
    tue = datetime(2026, 11, 24, 10, 0, tzinfo=IST)
    assert not daemon.feed_window(tue) and not daemon.market_minutes(tue)
    assert daemon.key("candles", tue)                                 # downloads may run on the holiday
    assert not candles.in_market_hours(pd.Timestamp("2026-11-24 10:00", tz="Asia/Kolkata"))
    assert daemon.feed_window(datetime(2026, 11, 23, 10, 0, tzinfo=IST))


def test_proof_file_lists_every_trade(tmp_path, monkeypatch):
    import csv
    from swing import config
    monkeypatch.setattr(config, "PRIVATE", tmp_path)
    monkeypatch.setattr(bot, "DATA", tmp_path)
    (tmp_path / "paper_replay.json").write_text(json.dumps({"start": 50800, "cash": 52000, "open": {}, "closed": [
        {"entry_time": "2026-11-16 09:40:00", "exit_time": "2026-11-16 10:05:00", "name": "NIFTY 24 NOV 26000 CALL",
         "symbol": "NFO:X", "side": "LONG", "qty": 130, "buy_avg": 80.2, "sell_avg": 96.0, "pnl": 2054, "charges": 60,
         "net": 1994, "why": "target", "strategy": "NIFTY options"}]}))
    f, n, start, cash = bot.proof_file("replay")
    rows = list(csv.DictReader(open(f)))
    assert n == 1 and rows[0]["entry_time"] == "2026-11-16 09:40:00" and rows[0]["buy_avg"] == "80.2"


def test_margin_calculator_is_the_only_extra_kite_call(monkeypatch):
    """Owner 21 Nov 2026: 'Yes, allow Kite's margin calculator (/margins/orders)'. It computes only; every order,
    GTT, holdings, positions and funds address stays blocked."""
    import inspect
    calls = []

    class R:
        status_code = 200

        def json(self):
            return {"data": [{"total": 25000.0}]}
    monkeypatch.setattr(kite, "keys", lambda: ("k", "s"))
    monkeypatch.setattr(kite, "token", lambda now=None: "t")
    monkeypatch.setattr(kite.requests, "post", lambda url, **kw: calls.append((url, kw["json"])) or R())
    kite._MARGIN.clear()
    assert kite.mis_ratio("RELIANCE", 1000.0, "BUY") == 25000 / (100 * 1000.0)
    assert calls[0][0].endswith("/margins/orders") and calls[0][1][0]["product"] == "MIS"
    src = inspect.getsource(kite)
    assert src.count("requests.post(") == 2                       # the daily login + the calculator, nothing else
    for bad in ("/orders", "/orders/regular", "/gtt/triggers", "/user/margins", "/portfolio/holdings"):
        with pytest.raises(PermissionError):
            kite._get(bad)


def test_stock_list_refresh_is_safe_with_many_threads(tmp_path, monkeypatch):
    """21 Nov: three download threads refreshing Kite's stock list at once crashed the download."""
    import threading
    import time as _t
    calls = []

    class R:
        text = "instrument_token,tradingsymbol,name,segment,instrument_type,lot_size,tick_size\n1,AAA,A,NSE,EQ,1,0.05\n"
    monkeypatch.setattr(kite, "INSTR_F", tmp_path / "ins.csv")
    monkeypatch.setattr(kite, "_INSTR", {"df": None, "t": 0.0, "lock": threading.Lock()})
    monkeypatch.setattr(kite, "_get", lambda *a, **k: (calls.append(1), _t.sleep(0.05), R())[2])
    out = []
    th = [threading.Thread(target=lambda: out.append(len(kite.instruments()))) for _ in range(6)]
    [t.start() for t in th]
    [t.join() for t in th]
    assert out == [1] * 6 and len(calls) == 1                      # one refresh, everyone gets the whole list


def test_candle_job_is_claimed_per_hour():
    assert daemon.key("candles", datetime(2026, 11, 21, 6, 33, tzinfo=IST)) != daemon.key("candles", datetime(2026, 11, 21, 7, 1, tzinfo=IST))


def test_downloads_continue_while_long_test_waits_for_a_fresh_run(monkeypatch):
    from swing import candles
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    monkeypatch.setattr(candles, "complete", lambda iv="day": True)
    sat = datetime(2026, 11, 21, 19, 0, tzinfo=IST)
    daemon.claim("learner", sat)
    daemon.claim("company", sat)
    assert daemon.due(sat) == ["longtest"]
    assert daemon.due(sat, skip={"longtest"}) == ["candles"]


def test_strategy_search_runs_after_the_long_test_on_a_fresh_run(monkeypatch):
    from swing import candles
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    monkeypatch.setattr(candles, "complete", lambda iv="day": True)
    sat = datetime(2026, 11, 21, 21, 0, tzinfo=IST)
    daemon.claim("learner", sat)
    daemon.claim("company", sat)
    (daemon.DATA / "long_test_done_v2.txt").write_text("done")
    assert daemon.due(sat) == ["search"]
    assert daemon.due(sat, skip={"longtest", "search"}) == ["candles"]
    (daemon.DATA / "strategy_search_done_v4.txt").write_text("done")
    assert daemon.due(sat) == ["candles"]


def test_every_task_in_the_run_workflow_menu_has_a_script():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "scripts"
    for n in ("nightly", "scan", "research", "weekly"):
        assert "bot_poll.py" in (root / f"run_{n}.py").read_text()
    assert (root / "bot_poll.py").exists()
