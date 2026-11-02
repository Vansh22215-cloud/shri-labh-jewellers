"""Journal of every tip and its outcome, plus the monitor for trades YOU mark as taken.

journal/tips.csv      - every tip ever shown (and 'shadow' picks when tips are blocked),
                        tracked automatically with the exact backtest exit rules.
my_trades.csv         - (in the main folder) trades you actually placed. Add one line per
                        trade in Excel/Notepad: symbol,buy_date,buy_price,qty,stop
"""
import math

import numpy as np
import pandas as pd

from . import costs
from .config import JOURNAL, ROOT

TIPS = JOURNAL / "tips.csv"
MY_TRADES = ROOT / "my_trades.csv"
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
    """Follow one tip through the daily bars using the SAME rules as the backtest.
    o/h/l/c: Series for the stock (real, unadjusted-for-the-future prices). Returns dict."""
    after = c.index[c.index > pd.Timestamp(signal_date)]
    if len(after) == 0:
        return {"status": "pending"}
    d0 = after[0]
    op = o[d0]
    if not np.isfinite(op) or op > tip["entry_high"] or op <= tip["stop"]:
        return {"status": "skipped (opened outside entry zone)", "entry_date": str(d0.date())}
    entry = costs.fill_price(op, "buy")
    qty = int(tip["qty"])
    r = entry - tip["stop"]
    t1, t2, stop = entry + p["target1_r"] * r, entry + p["target2_r"] * r, tip["stop"]
    fee_in = costs.buy_cost(qty * entry)
    left, cash_in, t1_done, days = qty, 0.0, False, 0
    last_reason = None
    for d in after:
        new = d == d0
        if not new:
            days += 1
        od, hd, ld = o[d], h[d], l[d]
        if not np.isfinite(od):
            continue

        def sell(q, px):
            f = costs.fill_price(px, "sell")
            return q * f - costs.sell_cost(q * f)
        if not new and days > p["max_hold_days"]:
            cash_in += sell(left, od); left = 0; last_reason = "time"
        elif not new and od <= stop:
            cash_in += sell(left, od); left = 0; last_reason = "stop_gap"
        elif ld <= stop:
            cash_in += sell(left, stop); left = 0; last_reason = "stop" if not t1_done else "breakeven"
        else:
            if not t1_done and hd >= t1:
                px = od if (not new and od >= t1) else t1
                half = left // 2
                if half >= 1:
                    cash_in += sell(half, px); left -= half
                t1_done, stop = True, max(stop, entry)
            if left > 0 and hd >= t2:
                px = od if (not new and od >= t2) else t2
                cash_in += sell(left, px); left = 0; last_reason = "target2"
        if left == 0:
            pnl = cash_in - qty * entry - fee_in
            return {"status": "closed", "entry_date": str(d0.date()), "entry_price": round(entry, 2),
                    "exit_date": str(d.date()), "exit_reason": last_reason, "pnl": round(pnl, 2),
                    "r_multiple": round(pnl / (r * qty), 3) if r > 0 and qty else 0, "days": days,
                    "exit_price": round(cash_in / qty, 2)}
    last = c.dropna().iloc[-1]
    open_pnl = cash_in + left * last - qty * entry - fee_in
    return {"status": "open", "entry_date": str(d0.date()), "entry_price": round(entry, 2),
            "pnl": round(open_pnl, 2), "r_multiple": round(open_pnl / (r * qty), 3) if r > 0 and qty else 0,
            "days": days, "t1_done": t1_done, "current_stop": round(stop, 2)}


def update_outcomes(load_prices, p_by_strategy):
    """Re-simulate every not-yet-closed tip with the latest data."""
    df = load_tips()
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
        if last <= stop:
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
