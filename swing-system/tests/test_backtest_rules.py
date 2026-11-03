"""Hand-built price paths to check every exit rule of the backtest and the paper-trade simulator."""
import numpy as np
import pandas as pd

from swing import backtest, costs, journal


def make(open_, high, low, close, signal_day=0, stop=95.0, atr=2.5, regime=True):
    idx = pd.bdate_range("2024-01-01", periods=len(close))
    f = lambda x: pd.DataFrame({"A": x}, index=idx, dtype=float)
    P = {"open": f(open_), "high": f(high), "low": f(low), "close": f(close)}
    elig = pd.DataFrame(False, index=idx, columns=["A"])
    elig.iloc[signal_day] = True
    sig = {"score": f([50] * len(close)), "eligible": elig,
           "setup": pd.DataFrame("breakout", index=idx, columns=["A"]),
           "atr": f([atr] * len(close)), "regime_ok": pd.Series(regime, index=idx)}
    return P, sig, idx


def test_entry_next_open_and_gap_through_stop(params):
    # signal day 0 close 100, ATR 2.5 -> stop 95. Day1 opens 100.5 (entry). Day2 gaps to 90 -> exit at 90 open.
    P, sig, idx = make([100, 100.5, 90, 91], [101, 101, 91, 92], [99, 99.5, 89, 90], [100, 100, 90, 91])
    eq, tr, _ = backtest.run(P, sig, params, idx[0], idx[-1], 45000)
    assert len(tr) == 1
    t = tr.iloc[0]
    assert t["entry_date"] == idx[1]
    assert abs(t["entry"] - costs.fill_price(100.5, "buy")) < 0.01
    assert t["exit_reason"] == "stop_gap" and t["exit_date"] == idx[2]
    assert t["r_multiple"] < -1.5      # worse than -1R because of the gap


def test_intraday_stop_exits_at_stop(params):
    P, sig, idx = make([100, 100.5, 99, 99], [101, 101, 99.5, 100], [99, 99.5, 94, 98], [100, 100, 96, 99])
    _, tr, _ = backtest.run(P, sig, params, idx[0], idx[-1], 45000)
    assert tr.iloc[0]["exit_reason"] == "stop" and tr.iloc[0]["exit_date"] == idx[2]


def test_do_not_buy_gap_up(params):
    # opens 102 > 100 + 0.5*2.5 = 101.25 -> no trade
    P, sig, idx = make([100, 102, 103, 104], [101, 103, 104, 105], [99, 101, 102, 103], [100, 102, 103, 104])
    _, tr, _ = backtest.run(P, sig, params, idx[0], idx[-1], 45000)
    assert len(tr) == 0


def test_target1_then_breakeven(params):
    # entry ~100.65, r ~5.65 -> T1 ~109.1. Day2 high 110 -> half sold; Day3 low 100 -> rest at breakeven stop
    P, sig, idx = make([100, 100.5, 105, 104], [101, 101, 110, 104.5], [99, 99.5, 104, 100], [100, 100.6, 108, 101])
    _, tr, _ = backtest.run(P, sig, params, idx[0], idx[-1], 45000)
    t = tr.iloc[0]
    assert t["exit_reason"] == "stop" and t["exit_date"] == idx[3]
    assert t["pnl"] > 0


def test_weak_market_blocks_entries(params):
    P, sig, idx = make([100, 100.5, 101, 102], [101, 101, 102, 103], [99, 99.5, 100, 101], [100, 100.6, 101, 102],
                       regime=False)
    _, tr, _ = backtest.run(P, sig, params, idx[0], idx[-1], 45000)
    assert len(tr) == 0


def test_time_stop(params):
    n = 40
    c = [100] + [101] * (n - 1)
    P, sig, idx = make(c, [x + 0.5 for x in c], [x - 0.5 for x in c], c)
    _, tr, _ = backtest.run(P, sig, params, idx[0], idx[-1], 45000)
    assert tr.iloc[0]["exit_reason"] == "time"
    assert tr.iloc[0]["days"] == params["max_hold_days"] + 1


def test_paper_simulator_matches_backtest(params):
    P, sig, idx = make([100, 100.5, 105, 104], [101, 101, 110, 104.5], [99, 99.5, 104, 100], [100, 100.6, 108, 101])
    _, tr, _ = backtest.run(P, sig, params, idx[0], idx[-1], 45000)
    tip = {"signal_close": 100.0, "entry_high": 101.25, "stop": 95.0, "qty": tr.iloc[0]["qty"]}
    res = journal.simulate_trade(P["open"]["A"], P["high"]["A"], P["low"]["A"], P["close"]["A"], idx[0], tip, params)
    assert res["status"] == "closed"
    assert abs(res["pnl"] - tr.iloc[0]["pnl"]) < 0.05


def test_equity_never_negative_and_costs_charged(params):
    P, sig, idx = make([100, 100.5, 100.5, 100.5], [101, 101, 101, 101], [99, 99.5, 99.5, 99.5], [100, 100.5, 100.5, 100.5])
    eq, tr, _ = backtest.run(P, sig, params, idx[0], idx[-1], 45000)
    assert (eq > 0).all()
    assert eq.iloc[-1] < 45000   # flat prices -> we lose the charges + slippage


def test_trailing_stop_exit(params):
    p = dict(params, exit_style="trail", trail_atr_mult=3.0)
    # rises to 120 then falls: trail stop = 120 - 7.5 = 112.5 -> exit near there, in profit
    c = [100, 100.5, 105, 110, 115, 120, 118, 114, 110, 108]
    P, sig, idx = make([100, 100.5, 104, 109, 114, 119, 119, 116, 113, 109], [x + 1 for x in c], [x - 1 for x in c], c)
    _, tr, _ = backtest.run(P, sig, p, idx[0], idx[-1], 45000)
    t = tr.iloc[0]
    assert t["exit_reason"] in ("stop", "stop_gap") and t["pnl"] > 0


def test_signal_exit_sells_next_open(params):
    p = dict(params, exit_style="signal")
    c = [100, 99, 98, 97, 96, 99.5, 101, 102]
    P, sig, idx = make([100, 99.2, 98, 97, 96, 97, 101.5, 102], [x + 0.5 for x in c], [x - 0.5 for x in c], c,
                       signal_day=0, atr=5.0)
    _, tr, _ = backtest.run(P, sig, p, idx[0], idx[-1], 45000)
    assert tr.iloc[0]["exit_reason"] == "signal"


def test_paper_tracker_open_and_skipped(params):
    P, sig, idx = make([100, 100.5, 101, 102], [101, 101, 102, 103], [99, 99.5, 100, 101], [100, 100.6, 101.5, 102.5])
    tip = {"signal_close": 100.0, "entry_high": 101.25, "stop": 95.0, "qty": 10}
    res = journal.simulate_trade(P["open"]["A"], P["high"]["A"], P["low"]["A"], P["close"]["A"], idx[0], tip, params)
    assert res["status"] == "open" and res["pnl"] > -50
    P2, _, idx2 = make([100, 103, 104, 105], [101, 104, 105, 106], [99, 102, 103, 104], [100, 103, 104, 105])
    res2 = journal.simulate_trade(P2["open"]["A"], P2["high"]["A"], P2["low"]["A"], P2["close"]["A"], idx2[0], tip, params)
    assert res2["status"].startswith("skipped")


def test_targets_then_trail(params):
    p = dict(params, exit_style="targets_trail", target1_r=1.5, trail_atr_mult=3.0)
    c = [100, 100.5, 110, 120, 130, 140, 135, 128, 122, 118]
    P, sig, idx = make([100, 100.5, 108, 119, 129, 139, 136, 129, 123, 119], [x + 1 for x in c], [x - 1 for x in c], c)
    _, tr, _ = backtest.run(P, sig, p, idx[0], idx[-1], 45000)
    t = tr.iloc[0]
    assert t["exit_reason"] in ("stop", "stop_gap") and t["r_multiple"] > 2   # rode the trend past 3R
