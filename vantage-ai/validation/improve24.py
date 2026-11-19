"""Round 24 (IMPROVE24_PREREGISTRATION.md): crash scenario - market opens 5/10/20% lower on the worst day."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))), "swing-system"))
from improve import HERE, OOS  # noqa: E402
import improve21 as r21  # noqa: E402
from swing import data_prices  # noqa: E402


def worst_day(T):
    days = pd.bdate_range(T["entry_date"].min(), T["exit_date"].max())
    s, e = T["entry_date"].values, T["exit_date"].values
    cnt = [int(((s <= d) & (e > d)).sum()) for d in days.values]
    return pd.Timestamp(days[int(np.argmax(cnt))]), max(cnt)


_P = {}


def prev_close(sym, d):
    if sym not in _P:
        x = data_prices.load(sym)
        _P[sym] = None if x is None or not len(x) else x["close"]
    c = _P[sym]
    if c is None:
        return None
    c = c[c.index < d]
    return float(c.iloc[-1]) if len(c) else None


def crash(T, d, gap):
    T = T.copy()
    m = (T["entry_date"] <= d) & (T["exit_date"] > d)
    for i in T.index[m]:
        pc = prev_close(T.at[i, "sym"], d)
        px = (pc if pc else T.at[i, "entry"]) * (1 - 1.5 * gap)
        T.at[i, "exit_date"], T.at[i, "exit"] = d, px
    return T, int(m.sum())


def one_day_loss(T, d, gap, seed, cap0=51000, risk=0.01, maxpct=0.25, cost=0.0035):
    """The account's loss ON the crash morning (marked at yesterday's close), as % of the account - the realized-only
    equity curve of the main simulation understates a one-day hit, so it is measured directly."""
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T))).sort_values(["entry_date", "rnd"])
    half, cash, eq, opn = cost / 2, cap0, cap0, []
    for r in T.itertuples():
        if r.entry_date > d:
            break
        keep = []
        for (xd, pe, px, q, sym) in opn:
            if xd <= r.entry_date:
                cash += q * px * (1 - half)
                eq += q * (px - pe) - q * (pe + px) * half
            else:
                keep.append((xd, pe, px, q, sym))
        opn = keep
        e = r.entry
        q = min(int(cap0 * risk // (e - r.init_stop)), int(cap0 * maxpct // e))
        if q < 1 or q * e * (1 + half) > cash:
            continue
        cash -= q * e * (1 + half)
        opn.append((r.exit_date, e, r.exit, q, r.sym))
    held = [(q, prev_close(sym, d) or pe) for (xd, pe, px, q, sym) in opn if xd > d]
    value = cash + sum(q * pc for q, pc in held)
    return 100 * sum(q * pc * 1.5 * gap for q, pc in held) / value, len(held), 100 * (value - cash) / value


out = {}
for per in ("holdout", "dev"):
    out[per] = {}
    for k in ("B", "C+A"):
        T = r21.SETUPS[k]
        S = T[T["signal"] >= OOS] if per == "holdout" else T[T["signal"] < OOS]
        d, n = worst_day(S)
        row = {"crash_day": str(d.date()), "open_that_day": n}
        for gap in (0.0, 0.05, 0.10, 0.20):
            X, hit = crash(S, d, gap) if gap else (S, 0)
            R = [r21.sim(X, s) for s in range(15)]
            row[f"gap {int(gap * 100)}%"] = {"cagr": round(float(np.median([a for a, b in R])), 1),
                                             "maxdd": round(float(np.median([b for a, b in R])), 1)}
            if gap:
                D = [one_day_loss(S, d, gap, s) for s in range(15)]
                row[f"gap {int(gap * 100)}%"].update(
                    one_day_loss_pct=round(float(np.median([a for a, b, c in D])), 1),
                    positions=int(np.median([b for a, b, c in D])),
                    invested_pct=round(float(np.median([c for a, b, c in D])), 0))
        out[per][k] = row
        print(per, k, row, flush=True)
g = [out[p]["C+A"]["gap 10%"] for p in out]
out["survives_10pct"] = all(x["cagr"] > 0 and x["maxdd"] >= -40 and x["one_day_loss_pct"] <= 40 for x in g)
json.dump(out, open(f"{HERE}/improve24_results.json", "w"), indent=1)
print("survives 10% gap:", out["survives_10pct"])
