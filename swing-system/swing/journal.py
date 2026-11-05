"""Journal of every tip and its outcome, plus the monitor for trades YOU mark as taken.

journal/tips.csv      - every tip ever shown (and 'shadow' picks when tips are blocked),
                        tracked automatically with the exact backtest exit rules.
data/my_trades.csv    - trades you actually placed (private, not in the public repo). Easiest: tell the Telegram
                        bot "/bought TCS 3 3500" (symbol qty price [stop]) and "/sold TCS".
"""
import math

import numpy as np
import pandas as pd

from . import costs
from .config import DATA, PRIVATE, JOURNAL, ROOT

TIPS = JOURNAL / "tips.csv"
MY_TRADES = PRIVATE / "my_trades.csv"   # personal: never committed to the (public) repository
COLUMNS = ["date", "symbol", "kind", "strategy", "setup", "score", "signal_close", "entry_low", "entry_high",
           "stop", "target1", "target2", "qty", "claude_verdict", "status", "entry_date", "entry_price",
           "exit_date", "exit_price", "exit_reason", "pnl", "r_multiple", "days"]


def load_tips():
    if TIPS.exists():
        df = pd.read_csv(TIPS, dtype={"claude_verdict": str})
        for c in COLUMNS:
            if c not in df.columns:
                df[c] = np.nan
        return df[COLUMNS]
    return pd.DataFrame(columns=COLUMNS)


def add_tips(day, plans, kind, strategy):
    df = load_tips()
    day = str(pd.Timestamp(day).date())
    rows = []
    for p in plans:
        if ((df["date"] == day) & (df["symbol"] == p["symbol"])).any():
            continue
        rows.append({"date": day, "symbol": p["symbol"], "kind": kind, "strategy": strategy,
                     "setup": p["setup"], "score": round(p["score"], 1), "signal_close": p["last_close"],
                     "entry_low": p["entry_low"], "entry_high": p["entry_high"], "stop": p["stop"],
                     "target1": p["target1"], "target2": p["target2"], "qty": p["qty"],
                     "claude_verdict": p.get("claude_verdict", ""), "status": "pending"})
    if rows:
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True) if len(df) else pd.DataFrame(rows)
    df.to_csv(TIPS, index=False)
    return df


def simulate_trade(o, h, l, c, signal_date, tip, p):
    """Follow one tip through the daily bars by running the BACKTEST ENGINE ITSELF on a
    one-stock panel, so paper results use exactly the tested rules (entry zone, stop,
    targets / trailing stop / exit signal, time exit, costs, slippage)."""
    from . import backtest
    sd = pd.Timestamp(signal_date)
    idx = c.index[c.index >= sd]
    if len(idx) <= 1:
        return {"status": "pending"}
    sym = "X"
    f = lambda s: pd.DataFrame({sym: s.reindex(idx).astype(float)})
    P = {"open": f(o), "high": f(h), "low": f(l), "close": f(c)}
    close0 = float(tip.get("signal_close", np.nan)) if hasattr(tip, "get") else float(tip["signal_close"])
    if not np.isfinite(close0):
        close0 = float(c.loc[:sd].iloc[-1])
    atr_val = (close0 - float(tip["stop"])) / p["stop_atr_mult"]
    elig = pd.DataFrame(False, index=idx, columns=[sym])
    elig.iloc[0] = True
    sig = {"score": pd.DataFrame(1.0, index=idx, columns=[sym]), "eligible": elig,
           "setup": pd.DataFrame("tip", index=idx, columns=[sym]),
           "atr": pd.DataFrame(atr_val, index=idx, columns=[sym]), "regime_ok": pd.Series(True, index=idx)}
    pp = dict(p, max_open_positions=1)
    big = 1e9
    import swing.backtest as bt
    eq, tr, ex = bt.run(P, sig, pp, idx[0], idx[-1], big, None, max_candidates=1,
                        qty_override=int(tip["qty"]))
    if len(tr):
        t = tr.iloc[0]
        return {"status": "closed", "entry_date": str(t["entry_date"].date()), "entry_price": t["entry"],
                "exit_date": str(t["exit_date"].date()), "exit_reason": t["exit_reason"], "pnl": t["pnl"],
                "r_multiple": t["r_multiple"], "days": int(t["days"])}
    held = ex[ex > 0]
    if len(held):
        pnl = round(float(eq.iloc[-1] - big), 2)
        r = (close0 - float(tip["stop"])) * int(tip["qty"])
        return {"status": "open", "entry_date": str(held.index[0].date()), "pnl": pnl,
                "r_multiple": round(pnl / r, 3) if r > 0 else 0, "days": int(len(held))}
    return {"status": "skipped (opened outside entry zone)", "entry_date": str(idx[1].date())}


def update_outcomes(load_prices, p_by_strategy):
    """Re-simulate every not-yet-closed tip with the latest data."""
    df = load_tips().astype(object)   # mixed text/number fields (dates, prices) must not fight column types
    for i, t in df.iterrows():
        if str(t["status"]).startswith(("closed", "skipped")):
            continue
        raw = load_prices(t["symbol"])
        if raw is None:
            continue
        res = simulate_trade(raw["open"], raw["high"], raw["low"], raw["close"], t["date"], t,
                             p_by_strategy(t["strategy"]))
        for k, v in res.items():
            if k in df.columns:
                df.at[i, k] = v
    df.to_csv(TIPS, index=False)
    return df


def paper_summary(df, kind="tip"):
    d = df[(df["kind"] == kind) & (df["status"] == "closed")]
    if len(d) == 0:
        return {"closed": 0}
    pnl = d["pnl"].astype(float)
    r = d["r_multiple"].astype(float)
    return {"closed": int(len(d)), "win_rate_pct": round((pnl > 0).mean() * 100, 1),
            "avg_r": round(r.mean(), 2), "total_pnl": round(pnl.sum(), 0),
            "r_std_err": round(r.std(ddof=1) / math.sqrt(len(r)), 2) if len(r) > 1 else None}


def load_my_trades():
    if not MY_TRADES.exists():
        MY_TRADES.write_text("symbol,buy_date,buy_price,qty,stop\n")
    try:
        df = pd.read_csv(MY_TRADES)
        df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
        return df.dropna(subset=["symbol", "buy_price"])
    except Exception:
        return pd.DataFrame(columns=["symbol", "buy_date", "buy_price", "qty", "stop"])


def monitor_my_trades(my, load_prices, p, next_results):
    """Plain-English daily status for each trade you marked as taken."""
    out = []
    for _, t in my.iterrows():
        s = t["symbol"]
        raw = load_prices(s)
        if raw is None or len(raw) < 30:
            out.append({"symbol": s, "status": "No price data - check the symbol spelling in my_trades.csv"})
            continue
        c, h, l, o = raw["close"], raw["high"], raw["low"], raw["open"]
        last = float(c.iloc[-1])
        buy = float(t["buy_price"])
        tr = (np.maximum(h - l, np.maximum((h - c.shift()).abs(), (l - c.shift()).abs()))).rolling(p["atr_period"]).mean()
        a = float(tr.iloc[-1])
        stop = float(t["stop"]) if "stop" in t and pd.notna(t.get("stop")) else buy - p["stop_atr_mult"] * a
        r = buy - stop if buy > stop else p["stop_atr_mult"] * a
        t1, t2 = buy + p["target1_r"] * r, buy + p["target2_r"] * r
        bd = pd.Timestamp(t["buy_date"]) if pd.notna(t.get("buy_date")) else c.index[-1]
        held = int((c.index > bd).sum())
        since = h[h.index >= bd]
        actions = []
        style = p.get("exit_style", "targets")
        if style == "trail":
            hc = float(c[c.index >= bd].max()) if (c.index >= bd).any() else last
            new_stop = max(stop, hc - p.get("trail_atr_mult", 3.0) * a)
            if last <= new_stop:
                actions.append(f"EXIT: closed at {last:.2f}, at/below trailing stop {new_stop:.2f}. Sell at tomorrow's open.")
            else:
                actions.append(f"Hold. Set/raise your stop to {new_stop:.2f} (trailing; never lower it).")
            t1 = t2 = float("inf")
        elif style == "signal":
            if last > float(c.tail(5).mean()):
                actions.append("EXIT: bounced above its 5-day average - sell at tomorrow's open.")
            elif last <= stop:
                actions.append(f"EXIT: at/below your stop {stop:.2f}. Sell at tomorrow's open.")
            else:
                actions.append(f"Hold. Stop {stop:.2f}.")
            t1 = t2 = float("inf")
        if style != "targets":
            pass
        elif last <= stop:
            actions.append(f"EXIT: closed at {last:.2f}, at/below your stop {stop:.2f}. Sell at tomorrow's open.")
        elif since.max() >= t2:
            actions.append(f"Target 2 ({t2:.2f}) reached: sell the remaining shares.")
        elif since.max() >= t1:
            actions.append(f"Target 1 ({t1:.2f}) reached: sell half if not done; move stop UP to your buy price {buy:.2f}.")
        else:
            actions.append(f"Hold. Keep stop at {stop:.2f}. Target 1 {t1:.2f}, target 2 {t2:.2f}.")
        if held > p["max_hold_days"]:
            actions.append(f"Held {held} days (> {p['max_hold_days']}): time exit - sell at tomorrow's open.")
        nr = next_results(s)
        if nr is not None and (nr - c.index[-1]).days <= 7:
            actions.append(f"Results due {nr.date()}: expect a big move; consider reducing before results.")
        out.append({"symbol": s, "buy": buy, "last": round(last, 2), "pnl_pct": round((last / buy - 1) * 100, 1),
                    "days_held": held, "status": " ".join(actions)})
    return out
