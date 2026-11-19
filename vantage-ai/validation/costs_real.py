"""Real-cost check (19 Nov 2026, owner: "after brokerage, taxes, slippage and other costs?").
Zerodha equity delivery (zerodha.com/charges, checked 19 Nov 2026): brokerage 0; STT 0.1% on buy and on sell; NSE
transaction 0.00307% each side; SEBI ₹10/crore each side; stamp 0.015% on buy; GST 18% on (exchange + SEBI);
DP charge ₹15.34 once per stock per day it is sold (lots of one stock sold together pay it once);
slippage 0.1% each side (market orders near the close / open). Tax: 20% short-term capital gains on each
financial year's (April-March) net realized profit (20% + 4% cess) (losses offset gains in the same year; carried forward). Same trades and
account rules as every round (₹51,000, 1% risk, 25% cap, 15 random orders)."""
import heapq
import json
import numpy as np
import pandas as pd
from improve import HERE, OOS
import improve21 as r21
import improve29 as r29

SLIP, STT, EXCH, SEBI, STAMP, GST, DP = 0.001, 0.001, 0.0000307, 0.000001, 0.00015, 0.18, 15.34
TAX_RATE = 0.208   # 20% STCG + 4% cess; financial year April-March (verified 19 Nov 2026, zerodha.com/charges)


def buy_cost(v):
    return v * (SLIP + STT + EXCH + SEBI + STAMP) + v * (EXCH + SEBI) * GST


def sell_cost(v, dp=True):
    return v * (SLIP + STT + EXCH + SEBI) + v * (EXCH + SEBI) * GST + (DP if dp else 0.0)


def fy(d):
    return d.year if d.month >= 4 else d.year - 1


def sim(T, seed, mode="fixed", tax=True, cap0=51000, risk=0.01, maxpct=0.25):
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T))).sort_values(["entry_date", "rnd"])
    cash, opn, n, base, month = float(cap0), [], 0, float(cap0), None
    year, pnl_y, carry, hist = None, 0.0, 0.0, []
    fees = 0.0
    dp_paid = set()
    invested = []
    def settle_tax(c, y_pnl, cf):
        taxable = y_pnl + cf
        t = TAX_RATE * taxable if (tax and taxable > 0) else 0.0
        return c - t, (taxable if taxable < 0 else 0.0), t
    taxes = 0.0
    for r in T.itertuples():
        ed = r.entry_date
        while opn and opn[0][0] <= ed:
            xd, _, pe, px, q, bc, sym = heapq.heappop(opn)
            if year is not None and fy(xd) != year:
                cash, carry, t = settle_tax(cash, pnl_y, carry); taxes += t; pnl_y = 0.0
            year = fy(xd)
            sc = sell_cost(q * px, dp=(sym, xd) not in dp_paid)
            dp_paid.add((sym, xd))
            cash += q * px - sc
            pnl_y += q * (px - pe) - sc - bc
            fees += sc
            hist.append((xd, cash + sum(o[2] * o[4] for o in opn)))
        if mode == "monthly" and (ed.year, ed.month) != month:
            month, base = (ed.year, ed.month), cash + sum(o[2] * o[4] for o in opn)
        e = r.entry
        if e <= r.init_stop:
            continue
        q = min(int(base * risk // (e - r.init_stop)), int(base * maxpct // e))
        if q < 1:
            continue
        bc = buy_cost(q * e)
        if q * e + bc > cash:
            continue
        cash -= q * e + bc
        fees += bc
        held = sum(o[2] * o[4] for o in opn) + q * e
        invested.append(held / (held + cash))
        n += 1
        heapq.heappush(opn, (r.exit_date, n, e, r.exit, q, bc, r.sym))
    while opn:
        xd, _, pe, px, q, bc, sym = heapq.heappop(opn)
        sc = sell_cost(q * px, dp=(sym, xd) not in dp_paid)
        dp_paid.add((sym, xd))
        cash += q * px - sc
        pnl_y += q * (px - pe) - sc - bc
        fees += sc
        hist.append((xd, cash + sum(o[2] * o[4] for o in opn)))
    cash, carry, t = settle_tax(cash, pnl_y, carry); taxes += t
    hist.sort()
    v = np.array([x[1] for x in hist])
    start, end = T["entry_date"].min(), pd.Timestamp(max(T["exit_date"].max(), T["entry_date"].max()))
    yrs = (end - start).days / 365.25                      # first buy to the last sale (the money is back in cash)
    inv = float(np.mean(invested)) if invested else 0.0
    return ((cash / cap0) ** (1 / yrs) - 1) * 100, float((v / np.maximum.accumulate(v) - 1).min() * 100), fees, taxes, n, \
        inv, start, end, cash


def med(T, **kw):
    R = [sim(T, s, **kw) for s in range(15)]
    m = lambda i: float(np.median([x[i] for x in R]))
    return {"cagr": round(m(0), 1), "maxdd": round(m(1), 1), "fees_rs": int(m(2)), "tax_rs": int(m(3)), "trades": int(m(4)),
            "invested_share": round(m(5), 2), "start": str(R[0][6].date()), "end": str(R[0][7].date()), "end_rs": int(m(8))}


if __name__ == "__main__":
    setups = {"VANTAGE live setup (top-300, 3:20 pm, ADD MORE)": r21.SETUPS["C+A"],
              "VANTAGE + live dip-buy (what you receive)": r29.B}
    out = {}
    for k, T in setups.items():
        out[k] = {}
        for per, S in (("dev 2013-Oct 2023", T[T["signal"] < OOS]), ("holdout Nov 2023-Nov 2026", T[T["signal"] >= OOS])):
            out[k][per] = {"real costs, no tax": med(S, tax=False),
                           "real costs + 20% tax": med(S),
                           "real costs + tax, monthly capital": med(S, mode="monthly")}
            print(k, per, json.dumps(out[k][per]), flush=True)
    json.dump(out, open(f"{HERE}/costs_real_results.json", "w"), indent=1)
