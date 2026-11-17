"""FAILURE-INJECTION tests (audit 17 Nov 2026). Each test breaks something on purpose and checks that the system
(1) detects it, (2) stays safe - no false or duplicate trade tip -, (3) keeps exit monitoring, (4) recovers or
tells the owner. Results are summarised in FAILURE_TEST_REPORT.md."""
import json
import multiprocessing as mp

import numpy as np
import pandas as pd
import pytest

from swing import live_engine as le
from swing import safety, telegram

S = {"capital": 45000, "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25, "daily_loss_pct": 2}}


def _row(sym="ABC", entry=100.0, stop=95.0, qty=None, **kw):
    q = safety.size(entry, stop, S) if qty is None else qty
    r = {"type": "NORMAL", "symbol": sym, "side": "buy", "entry": entry, "stop": stop, "targets": "", "rank": 9,
         "qty": q, "status": "open", "hit": 0, "day": "2026-11-17", "setup": "HP", "taken": "yes"}
    r.update(kw)          # taken = the owner confirmed buying it (/bought): only those count toward the limits
    return r


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(telegram, "send", lambda s, text, html=False, label="": (sent.append((label, text)),
                                                                                  "Telegram message sent")[1])
    return sent


# ---------------------------------------------------------------- kill switch / emergency
def test_kill_switch_blocks_new_tips_but_not_exits(outbox, monkeypatch):
    s = dict(S, kill_switch=True)
    assert le.issue_tip(_row(), "BUY ABC", s) is False
    assert not le.load_tips().shape[0] and not outbox
    # an already-open tip still gets its exit alert with the kill switch ON
    s2 = dict(S)
    assert le.issue_tip(_row("XYZ"), "BUY XYZ", s2)
    q = {"XYZ": {"last": 90.0}}
    msgs = le.exits(q, pd.Timestamp("2026-11-18 10:00"))
    assert any("stop-loss" in m for m in msgs)


def test_emergency_latches_blocks_and_needs_integrity_to_clear(outbox, monkeypatch):
    safety.emergency("test: stale data")
    assert safety.emergency_active()
    assert le.issue_tip(_row(), "BUY", S) is False
    assert any("SAFETY STOP" in t for _, t in outbox)
    monkeypatch.setattr(safety, "integrity_check", lambda s=None: (False, ["still stale"]))
    assert safety.try_clear(S) is False and safety.emergency_active()
    monkeypatch.setattr(safety, "integrity_check", lambda s=None: (True, []))
    assert safety.try_clear(S) is True and not safety.emergency_active()
    assert any("Integrity check passed" in t for _, t in outbox)


def test_missing_capital_blocks_tips(monkeypatch, tmp_path, outbox):
    (tmp_path / "settings.yaml").write_text("kill_switch: false\n")
    monkeypatch.setattr(safety, "ROOT", tmp_path)
    ok, why = safety.check_new_entry(_row(), S)
    assert not ok and "capital" in why


# ---------------------------------------------------------------- invalid numbers
@pytest.mark.parametrize("bad, why", [
    (dict(entry=float("nan")), "non-finite"), (dict(entry=float("inf")), "non-finite"), (dict(entry=-5.0, stop=-6.0), "non-positive"),
    (dict(stop=105.0), "wrong side"), (dict(qty=0), "quantity"), (dict(qty=5000), "per-trade limit"),
    (dict(stop=40.0, qty=1), "50%"), (dict(targets="90"), "target on the wrong side"),
])
def test_invalid_tip_numbers_are_refused(bad, why, outbox):
    r = _row(**bad)
    ok, reason = safety.validate(r, S)
    assert not ok and why in reason
    assert le.issue_tip(r, "BUY", S) is False and not outbox


# ---------------------------------------------------------------- duplicates / record-before-notify
def test_same_signal_twice_is_sent_once(outbox):
    assert le.issue_tip(_row(), "BUY ABC", S)
    assert le.issue_tip(_row(), "BUY ABC", S) is False
    assert len([1 for l, _ in outbox if l == "trade tip"]) == 1 and len(le.load_tips()) == 1


def test_tip_is_recorded_before_it_is_sent(monkeypatch):
    seen = []

    def fake_send(s, text, html=False, label=""):
        seen.append(len(le.load_tips()))          # how many tips were recorded at the moment of sending
        return "Telegram message sent"
    monkeypatch.setattr(telegram, "send", fake_send)
    le.issue_tip(_row(), "BUY", S)
    assert seen == [1]


# ---------------------------------------------------------------- Telegram down
def test_telegram_down_keeps_tip_and_retries(monkeypatch):
    calls = {"n": 0}

    def down(s, text, html=False, label=""):
        calls["n"] += 1
        return "Telegram failed: 502"
    monkeypatch.setattr(telegram, "send", down)
    assert le.issue_tip(_row(), "BUY ABC", S)               # recorded although Telegram is down
    assert len(le.load_tips()) == 1
    box = telegram._outbox()
    assert box.exists() and "BUY ABC" in box.read_text()
    assert telegram.flush_outbox(S) == 0                     # still down: kept
    ok = []
    monkeypatch.setattr(telegram, "send", lambda s, text, html=False, label="": (ok.append(text), "Telegram message sent")[1])
    assert telegram.flush_outbox(S) == 1 and "BUY ABC" in ok[0]
    assert not box.read_text().strip()


# ---------------------------------------------------------------- tip store damage / crash mid-write
def test_corrupted_store_is_restored_and_new_tips_stop(outbox):
    assert le.issue_tip(_row("AAA"), "BUY", S)
    assert le.issue_tip(_row("BBB"), "BUY", S)               # second write makes a backup of the first state
    le.TIPS_F.write_bytes(b"\x00\x01garbage,,,\n\xff\xfe")
    t = le.load_tips()
    assert len(t) >= 1 and safety.emergency_active()
    assert le.issue_tip(_row("CCC"), "BUY", S) is False         # no new tips until the integrity check passes
    assert le.TIPS_F.with_suffix(".damaged").exists()


def test_crash_before_rename_leaves_old_store_intact(monkeypatch):
    le.issue_tip(_row("AAA"), "BUY", S)
    before = le.TIPS_F.read_text()
    real_replace = type(le.TIPS_F).replace

    def boom(self, target):
        raise OSError("power cut")
    monkeypatch.setattr(type(le.TIPS_F), "replace", boom)
    with pytest.raises(OSError):
        le.write_tips(pd.concat([le.load_tips(), pd.DataFrame([_row("ZZZ")])]))
    monkeypatch.setattr(type(le.TIPS_F), "replace", real_replace)
    assert le.TIPS_F.read_text() == before


def _writer(path, k):
    from swing import live_engine as L
    from pathlib import Path
    L.TIPS_F = Path(path)
    L.BACKUP_F = Path(path).with_suffix(".bak")
    for i in range(25):
        L.save_tip({"type": "NORMAL", "symbol": f"P{k}-{i}", "side": "buy", "entry": 10, "stop": 9, "qty": 1,
                    "status": "open", "day": "2026-11-17"})


def test_two_processes_writing_at_once_lose_nothing(tmp_path):
    p = str(tmp_path / "tips.csv")
    ctx = mp.get_context("fork")
    ps = [ctx.Process(target=_writer, args=(p, k)) for k in range(2)]
    [x.start() for x in ps]
    [x.join(60) for x in ps]
    df = pd.read_csv(p)
    assert len(df) == 50 and df["symbol"].nunique() == 50


# ---------------------------------------------------------------- portfolio limits
def test_portfolio_open_risk_and_position_limits(outbox):
    s = dict(S, risk_limits=dict(S["risk_limits"], max_open_risk_pct=3, max_open_positions=50))
    sent = sum(bool(le.issue_tip(_row(f"S{i}"), "BUY", s)) for i in range(6))
    assert sent == 3                                          # 1% each, 3% total cap
    s2 = dict(S, risk_limits=dict(S["risk_limits"], max_open_positions=4, max_open_risk_pct=50))
    sent2 = sum(bool(le.issue_tip(_row(f"T{i}"), "BUY", s2)) for i in range(4))
    assert sent2 == 1                                         # 3 already open, max 4


def test_losing_streak_cooldown(outbox):
    t = pd.DataFrame([dict(_row(f"L{i}"), status="stop", result_pct=-2.0,
                           closed_at=str(pd.Timestamp.now().floor("min") - pd.Timedelta(hours=10 - i))) for i in range(8)])
    le.write_tips(t)
    ok, why = safety.portfolio_check(_row("NEW"), S)
    assert not ok and "losing tips in a row" in why


# ---------------------------------------------------------------- Kite failures
def test_kite_down_rate_limited_or_expired_never_crashes(monkeypatch):
    from swing import kite
    monkeypatch.setattr(kite, "logged_in", lambda now=None: True)
    monkeypatch.setattr(kite, "token", lambda now=None: "t")
    monkeypatch.setattr(kite, "keys", lambda: ("k", "s"))

    class R:
        def __init__(self, code):
            self.status_code = code
        def raise_for_status(self):
            if self.status_code >= 400:
                raise kite.requests.HTTPError(str(self.status_code))
        def json(self):
            return {"data": {}}
    for code in (429, 500, 503):
        monkeypatch.setattr(kite.requests, "get", lambda *a, c=code, **k: R(c))
        assert kite.quotes(["INFY"]) == {}                  # caller falls back to Yahoo / skips
    monkeypatch.setattr(kite.requests, "get", lambda *a, **k: (_ for _ in ()).throw(kite.requests.ConnectionError("net down")))
    assert kite.quotes(["INFY"]) == {}
    monkeypatch.setattr(kite.requests, "get", lambda *a, **k: R(403))
    with pytest.raises(RuntimeError):
        kite._get("/quote", params=[("i", "NSE:INFY")])    # expired session: refused, token dropped


def test_empty_or_partial_quote_response_is_ignored(monkeypatch):
    from swing import kite
    monkeypatch.setattr(kite, "logged_in", lambda now=None: True)

    class R:
        def json(self):
            return {"data": {"NSE:INFY": {"ohlc": {}}}}        # no last_price
    monkeypatch.setattr(kite, "_get", lambda *a, **k: R())
    assert kite.quotes(["INFY"]) == {}


# ---------------------------------------------------------------- bad market data
def test_price_loader_cleans_duplicates_unsorted_and_invalid_rows(tmp_path, monkeypatch):
    from swing import data_prices
    df = pd.DataFrame({"date": ["2026-01-03", "2026-01-02", "2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"],
                       "open": [10, 9, 9.5, 0, np.nan, 11], "high": [11, 10, 10, 1, 12, 10],
                       "low": [9, 8, 9, 0, 10, 12], "close": [10.5, 9.5, 9.8, 0, 11, 11], "volume": [1, 1, 1, 0, 1, 1]})
    clean = data_prices.sanitize(df.set_index(pd.to_datetime(df["date"])).drop(columns="date"))
    assert list(clean.index.strftime("%Y-%m-%d")) == ["2026-01-02", "2026-01-03"]
    assert clean.loc["2026-01-02", "close"] == 9.8          # last duplicate kept


@pytest.mark.parametrize("shock", ["gap_up_20", "lower_circuit", "zero_volume", "flat"])
def test_strategies_survive_extreme_and_degenerate_data(shock):
    from swing import high_prob, positional
    from swing.confirmations import assess
    rng = np.random.default_rng(7)
    n = 400
    c = 100 * np.exp(np.cumsum(0.001 + 0.015 * rng.standard_normal(n)))
    v = np.full(n, 1e5)
    if shock == "gap_up_20":
        c[-5:] *= 1.2
    elif shock == "lower_circuit":
        c[-3:] = c[-4] * np.array([0.8, 0.64, 0.512])
    elif shock == "zero_volume":
        v[-30:] = 0
    elif shock == "flat":
        c[:] = 100.0
    o = np.r_[c[0], c[:-1]]
    d = pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.002, "low": np.minimum(o, c) * 0.998, "close": c,
                      "adj_close": c, "volume": v}, index=pd.bdate_range("2024-01-01", periods=n))
    sg = high_prob.signal(d)
    if sg:
        assert np.isfinite(sg["stop"]) and sg["stop"] < sg["close"]
    a = high_prob.adjusted(d)
    a["volume"] = v
    psg = positional.signal(a)
    if psg:
        assert np.isfinite(psg["stop"]) and psg["stop"] < psg["close"]
    tier, why = assess(a)
    assert tier in ("A", "B", "C", None)


def test_insufficient_history_gives_no_signal():
    from swing import high_prob, positional
    d = pd.DataFrame({"open": [10.0] * 50, "high": [10.5] * 50, "low": [9.5] * 50, "close": [10.0] * 50,
                      "adj_close": [10.0] * 50, "volume": [1e5] * 50}, index=pd.bdate_range("2026-01-01", periods=50))
    assert high_prob.signal(d) is None


# ---------------------------------------------------------------- stale data / holidays
def test_stale_prices_detected(monkeypatch):
    from swing import health
    monkeypatch.setattr(health, "traded_today", lambda now=None: True)
    exp = health.expected_day(pd.Timestamp("2026-11-13"), pd.Timestamp("2026-11-17 19:00"))
    assert exp == pd.Timestamp("2026-11-17")
    assert not health.freshness(pd.Timestamp("2026-11-13"), exp)


def test_holiday_is_not_treated_as_stale(monkeypatch):
    from swing import health
    monkeypatch.setattr(health, "traded_today", lambda now=None: False)      # weekday holiday: Nifty did not trade
    exp = health.expected_day(pd.Timestamp("2026-11-13"), pd.Timestamp("2026-11-16 19:00"))
    assert health.freshness(pd.Timestamp("2026-11-13"), exp)


def test_integrity_check_flags_stale_nifty(monkeypatch):
    from swing import data_prices
    old = pd.DataFrame({"close": [100.0]}, index=pd.to_datetime(["2026-10-01"]))
    monkeypatch.setattr(data_prices, "load", lambda s: old)
    ok, probs = safety.integrity_check(S)
    assert not ok and any("stale" in p for p in probs)


# ---------------------------------------------------------------- multiple failures at once
def test_telegram_down_plus_kill_switch_plus_bad_numbers(monkeypatch):
    monkeypatch.setattr(telegram, "send", lambda *a, **k: "Telegram failed: down")
    assert le.issue_tip(_row(qty=0), "BUY", dict(S, kill_switch=True)) is False
    assert not le.load_tips().shape[0]
    assert not telegram._outbox().exists() or "BUY" not in telegram._outbox().read_text()
    sk = pd.read_csv(safety.SKIPPED_F)
    assert len(sk) == 1 and "kill switch" in sk["reason"].iloc[0]


# ---------------------------------------------------------------- backups
def test_local_backup_skips_damaged_files_and_restores(tmp_path, monkeypatch):
    from swing import archive
    data, priv = tmp_path / "data", tmp_path / "data" / "private"
    priv.mkdir(parents=True)
    monkeypatch.setattr(archive, "DATA", data)
    monkeypatch.setattr(archive, "PRIVATE", priv)
    monkeypatch.setattr(archive, "BACKUPS", data / "backups")
    pd.DataFrame({"symbol": ["A"], "status": ["open"]}).to_csv(priv / "live_tips.csv", index=False)
    (priv / "my_trades.csv").write_bytes(b"\x00\xff\xfe broken")
    (data / "safety.json").write_text("{not json")
    p, n, bad = archive.local_backup()
    assert n == 1 and set(bad) == {"my_trades.csv", "safety.json"}
    (priv / "live_tips.csv").unlink()                      # disaster: the store is gone
    assert archive.restore_local(p) == 1
    assert pd.read_csv(priv / "live_tips.csv")["symbol"].tolist() == ["A"]


def test_lower_ranked_strategies_cannot_use_up_the_dip_buy_room(outbox):
    sent_ai = sum(bool(le.issue_tip(_row(f"A{i}", setup="AI"), "AI PICK", S)) for i in range(6))
    assert sent_ai == 3                                       # AI capped at 3% of capital at risk
    assert le.issue_tip(_row("DIP1", setup="HP"), "DIP BUY", S)   # the dip-buy still has room


def test_option_tip_risk_is_held_to_the_owners_per_trade_limit(outbox):
    """Audit (second pass): option tips used the rank's own risk (up to 5% of capital), bypassing the 1% rule."""
    fno = dict(_row("NIFTY50", entry=24000, stop=23900, qty=1), type="FNO", lot=75, premium=20.0,
               contract="NIFTY26NOV24000CE")
    ok, why = safety.validate(dict(fno, risk_rs=1500), S)            # 3.3% of 45,000
    assert not ok and "per-trade limit" in why
    ok, why = safety.validate(dict(fno, risk_rs=400), S)             # under 1%
    assert ok, why
    ok, why = safety.validate(dict(fno, premium=float("nan"), risk_rs=400), S)
    assert not ok
    ok, why = safety.validate(dict(fno, premium=200.0, risk_rs=400), S)   # 15,000 premium > 25% of capital
    assert not ok and "per-order" in why


def test_option_picker_respects_max_risk_pct(monkeypatch):
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
    c = {"symbol": "VOLTAS", "side": "sell", "entry": 1130.0, "stop": 1134.0, "targets": [1122.0, 1114.0, 1106.0]}
    now = pd.Timestamp("2026-11-12 10:30")
    o = le.option_trade(c, 8, 1130.0, now, 45000, max_risk_pct=1.0, max_cost_pct=25)
    assert o is None or o["loss"] <= 450
