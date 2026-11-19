"""Fair NIFTY comparison (owner 19 Nov 2026): identical dates, identical ₹51,000, same cash treatment, total return.
System: costs_real.sim (verified Zerodha charges, DP per stock-day, 0.1% slippage, 20.8% STCG per financial year).
NIFTY: ₹51,000 put into a NIFTY 50 index fund at the close of the system's first buy day, held to the day of the
system's last sale, then sold. Total return = NIFTY 50 price + dividend yield (assumption: 1.1% / 1.3% / 1.5% a year;
the free price data has no dividends) - 0.05% a year fund fee. Costs: stamp 0.015% buy, DP ₹15.34 at the sale.
Tax: long-term (held > 1 year) 12.5% + 4% cess on the gain above ₹1.25 lakh, paid once at the sale.
Cash: the system's unused money earns nothing (as in every test); NIFTY is fully invested from day 1."""
import json
import os
import numpy as np
import pandas as pd
from improve import HERE, OOS, iv
import improve21 as r21
import improve29 as r29
from costs_real import med

N = iv.nifty()["close"]


def nifty(start, end, cap=51000, div=0.013, fee=0.0005, tax=True):
    x = N[(N.index >= pd.Timestamp(start)) & (N.index <= pd.Timestamp(end))]
    yrs = (x.index[-1] - x.index[0]).days / 365.25
    grow = x.iloc[-1] / x.iloc[0] * (1 + div - fee) ** yrs
    v = cap * (1 - 0.00015) * grow - 15.34
    if tax and yrs > 1:
        v -= max(0.0, v - cap - 125000) * 0.125 * 1.04
    dd = float((x / x.cummax() - 1).min() * 100)
    return {"cagr": round(((v / cap) ** (1 / yrs) - 1) * 100, 1), "end_rs": int(v), "maxdd_price": round(dd, 1)}


if __name__ == "__main__":
    out = {}
    for k, T in {"VANTAGE live setup": r21.SETUPS["C+A"], "VANTAGE + live dip-buy": r29.B}.items():
        out[k] = {}
        for per, S in (("dev", T[T["signal"] < OOS]), ("holdout", T[T["signal"] >= OOS])):
            row = {"system after costs + tax (fixed ₹51,000 sizing)": med(S),
                   "system after costs + tax (capital updated monthly)": med(S, mode="monthly"),
                   "system after costs, before tax": med(S, tax=False)}
            a, b = row["system after costs + tax (fixed ₹51,000 sizing)"]["start"], row["system after costs + tax (fixed ₹51,000 sizing)"]["end"]
            if os.environ.get("SWING_PRICE_SOURCE") == "kite_strict":   # stocks are price-only -> NIFTY price-only too
                row["NIFTY price only, after tax (strict Kite, like-for-like)"] = nifty(a, b, div=0.0, fee=0.0)
            for d in (0.011, 0.013, 0.015):
                row[f"NIFTY fund, dividends {d*100:.1f}%, after tax"] = nifty(a, b, div=d)
            row["NIFTY fund, dividends 1.3%, before tax"] = nifty(a, b, tax=False)
            row["NIFTY price only (what earlier answers used)"] = nifty(a, b, div=0, fee=0, tax=False)
            out[k][per] = row
            print(k, per, json.dumps(row), flush=True)
    json.dump(out, open(f"{HERE}/benchmark_fair_results.json", "w"), indent=1)
