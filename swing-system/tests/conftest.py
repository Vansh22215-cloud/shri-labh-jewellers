import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging  # noqa: E402
logging.getLogger("swing").addHandler(logging.NullHandler())


@pytest.fixture(autouse=True)
def _clean_job_environment(monkeypatch):
    """The self-tests run inside a GitHub job: never let that job's own settings change test results."""
    for k in ("SWING_CLAIMED", "SWING_DAEMON_MINUTES", "GITHUB_ACTIONS", "GH_TOKEN", "GITHUB_RUN_ID",
              "GITHUB_REF_NAME", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "KITE_API_KEY", "KITE_API_SECRET"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch, request):
    """No test touches real records, the candle library, Telegram or Kite."""
    from swing import candles, kite, telegram, tips, daemon, backtest, learner, backup
    monkeypatch.setattr(telegram, "_outbox", lambda: tmp_path / "outbox.jsonl")
    monkeypatch.setattr(kite, "UNAVAIL_F", tmp_path / "_kite_unavailable.json")
    monkeypatch.setattr(kite, "report_unavailable", lambda *a, **k: False)
    monkeypatch.setattr(candles, "BASE", tmp_path / "candles")
    monkeypatch.setattr(candles, "STATE_F", tmp_path / "candles" / "state.json")
    monkeypatch.setattr(candles, "REPORT", tmp_path / "candle_library.md")
    monkeypatch.setattr(tips, "TIPS_F", tmp_path / "tips.csv")
    monkeypatch.setattr(daemon, "STATE", tmp_path / "jobs_done.json")
    monkeypatch.setattr(daemon, "TEST_QUEUE", tmp_path / "test_queue.json")
    monkeypatch.setattr(daemon, "DATA", tmp_path)
    from swing import market_days
    monkeypatch.setattr(market_days, "holidays", lambda: set(market_days.BUILTIN))   # no network in tests
    (tmp_path / "replay_done.txt").write_text("done")             # the one-time replay is tested on its own
    monkeypatch.setattr(backtest, "TESTS", tmp_path / "tests")
    monkeypatch.setattr(backtest, "OUT", tmp_path / "results_tests")
    monkeypatch.setattr(learner, "OUT", tmp_path / "results_learner")
    monkeypatch.setattr(learner, "PRIVATE", tmp_path)
    monkeypatch.setattr(backup, "PRIVATE", tmp_path / "private")
    monkeypatch.setattr(backup, "HASH_F", tmp_path / "backup_hash.txt")
    sent = []
    if "test_telegram_send" not in request.node.module.__name__:
        monkeypatch.setattr(telegram, "send", lambda s, text, html=False, label="message": sent.append((label, text)) or "Telegram message sent")
    request.node.sent = sent
    yield sent


def candles_frame(start="2024-01-01 09:15", n=300, freq="15min", seed=1, intraday=True):
    """Synthetic candles (trading hours only when intraday)."""
    rng = np.random.default_rng(seed)
    if intraday:
        days = pd.bdate_range(pd.Timestamp(start).normalize(), periods=n // 25 + 2)
        idx = [d + pd.Timedelta(minutes=15 + i * 15) for d in days for i in range(25)][:n]
        idx = pd.DatetimeIndex([d + pd.Timedelta(hours=9) for d in idx])
    else:
        idx = pd.bdate_range(start, periods=n)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.006, len(idx))))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.002, len(idx))))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.002, len(idx))))
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": rng.integers(1e4, 1e5, len(idx)).astype(float)},
                        index=pd.DatetimeIndex(idx, name="date"))
