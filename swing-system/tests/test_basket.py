"""Monthly basket (round 4, M3): 20 strongest stocks, cash when NIFTY is weak, once a month, quantities only when set."""
import numpy as np
import pandas as pd
import pytest

from swing import basket


def _series(drift, n=400, seed=1, vol=0.01):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end="2026-11-30", periods=n)
    c = 100 * np.exp(np.cumsum(rng.normal(drift, vol, n)))
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "adj_close": c, "volume": 1e6}, index=idx)


@pytest.fixture
def env(monkeypatch, tmp_path):
    from swing import data_prices, telegram, health, safety
    sent = []
    stocks = {f"S{i:02d}": _series(0.00002 * i - 0.0012, seed=i) for i in range(120)}
    stocks["NIFTY50"] = _series(0.001, seed=999)
    monkeypatch.setattr(data_prices, "load", lambda s: stocks.get(s))
    monkeypatch.setattr(data_prices, "update", lambda syms: None)
    monkeypatch.setattr(basket, "universe", lambda: [s for s in stocks if s != "NIFTY50"])
    monkeypatch.setattr(basket, "STATE_F", tmp_path / "basket.json")
    monkeypatch.setattr(telegram, "send_reliable", lambda s, text, label="": sent.append(text))
    monkeypatch.setattr(health, "traded_today", lambda now=None: True)
    monkeypatch.setattr(safety, "emergency_active", lambda: False)
    monkeypatch.setattr(basket, "load_settings", lambda: {})
    return sent, stocks


def test_ranks_the_strongest_and_sends_once_a_month(env):
    sent, stocks = env
    r = basket.run(pd.Timestamp("2026-11-30"))                    # last weekday of November
    assert r["stocks"] == 20 and not r["cash"]
    st = basket._state()
    assert np.mean([int(x[1:]) for x in st["holdings"]]) > 85              # mostly the strongest-trending stocks
    assert sent[0].startswith("#VANTAGE MONTHLY BASKET") and "🟢 BUY" in sent[0] and "/basket 20000" in sent[0]
    assert basket.run(pd.Timestamp("2026-11-30"))["why"] == "not due"     # never twice for the same month
    assert basket.run(pd.Timestamp("2026-12-15"))["why"] == "not due"
    assert len(sent) == 1


def test_cash_when_nifty_is_below_its_200_day_average(env):
    sent, stocks = env
    stocks["NIFTY50"] = _series(-0.002, seed=5)
    basket._save({"month": "2026-10", "holdings": ["S01", "S02"]})
    r = basket.run(pd.Timestamp("2026-11-30"))
    assert r["cash"] and r["stocks"] == 0
    assert "hold NO basket stocks" in sent[0] and "SELL: S01, S02" in sent[0]


def test_quantities_only_when_money_is_set(env):
    sent, stocks = env
    basket.set_capital(4000000)
    basket.run(pd.Timestamp("2026-11-30"))
    assert "qty" in sent[0] and "₹200,000 each of ₹4,000,000" in sent[0]


def test_due_dates():
    assert basket.due("2026-11-18", {}) == "2026-10"          # first ever basket: start now
    assert basket.due("2026-11-30", {}) == "2026-11"
    assert basket.due("2026-11-27", {"month": "2026-10"}) is None
    assert basket.due("2026-11-30", {"month": "2026-10"}) == "2026-11"
    assert basket.due("2026-12-01", {"month": "2026-10"}) == "2026-11"   # month-end was a holiday: next day
    assert basket.due("2026-12-01", {"month": "2026-11"}) is None


def test_kill_switch_sends_sells_only(env, monkeypatch):
    sent, stocks = env
    monkeypatch.setattr(basket, "load_settings", lambda: {"kill_switch": True})
    basket._save({"month": "2026-10", "holdings": ["S01"]})
    basket.run(pd.Timestamp("2026-11-30"))
    assert "🟢 BUY" not in sent[0]


def test_funds_are_not_basket_stocks(monkeypatch, tmp_path):
    import swing.tipcheck as tc
    u = pd.DataFrame({"symbol": ["LIQUIDCASE", "GOLDBEES", "TCS", "SKYGOLD"], "med_value": 1, "rank": [1, 2, 3, 4],
                      "asof": "2026-11-01"})
    (tmp_path / "universe_history.csv").write_text(u.to_csv(index=False))
    monkeypatch.setattr(basket, "DATA", tmp_path)
    monkeypatch.setattr(tc, "equity_list", lambda: pd.DataFrame({"SYMBOL": ["TCS", "SKYGOLD"]}))
    assert basket.universe() == ["TCS", "SKYGOLD"]


def test_bot_basket_command(monkeypatch, tmp_path):
    from swing import bot
    monkeypatch.setattr(basket, "STATE_F", tmp_path / "b.json")
    monkeypatch.setattr(basket, "load_settings", lambda: {})
    assert "No monthly basket yet" in bot.basket_command("/basket")
    assert "₹20,000" in bot.basket_command("/basket 20,000")
    assert basket.capital() == 20000
    assert "Use:" in bot.basket_command("/basket abc")


def test_dry_run_never_reaches_telegram(monkeypatch, tmp_path):
    """Practice mode (scripts/dry_run_all.py): messages go to a local file, no network call at all."""
    from swing import telegram
    import swing.config as cfg
    monkeypatch.setenv("SWING_DRY_RUN", "1")
    monkeypatch.setattr(cfg, "DATA", tmp_path)

    def boom(*a, **k):
        raise AssertionError("network used in practice mode")
    monkeypatch.setattr(telegram.requests, "post", boom)
    monkeypatch.setattr(telegram.requests, "get", boom)
    r = telegram.send({"telegram_bot_token": "1:x", "telegram_allowed": ["vantage indicator"]}, "hello",
                      label="vantage indicator")
    assert r == "Telegram message sent"
    assert "hello" in (tmp_path / "private" / "dry_run_messages.txt").read_text()


def test_daemon_runs_the_basket_job_in_the_evening_when_due(monkeypatch, tmp_path):
    from swing import daemon
    monkeypatch.setattr(daemon, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(basket, "STATE_F", tmp_path / "b.json")
    t = pd.Timestamp("2026-11-30 19:10")
    st = {daemon.key("nightly", t): True, daemon.key("vantage", t): True, daemon.key("company", t): True}
    (tmp_path / "state.json").write_text(__import__("json").dumps(st))
    assert "basket" in daemon.due(t)
    assert "basket" not in daemon.due(pd.Timestamp("2026-11-30 18:00"))
    basket._save({"month": "2026-11"})
    assert "basket" not in daemon.due(t)
