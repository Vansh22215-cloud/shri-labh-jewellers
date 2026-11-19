"""Re-run of the main tests on Kite exchange prices (owner 19 Nov: "check if the tests used accurate Kite data - if not,
do it again"). Runs on GitHub once Kite daily history is complete (kite_daily.coverage() >= 90%).
Same VANTAGE code, same rules, same account simulation (verified Zerodha costs + 20.8% tax), only the price source
changes: Kite first; stocks Kite does not have (delisted) keep the official NSE bhavcopy rebuilds.
-> swing-system/journal/kite_recheck.md (results only; Kite data stays in the private cache)."""
import os
import sys

os.environ["SWING_PRICE_SOURCE"] = "kite_strict"   # owner 19 Nov: strict Kite, no Yahoo filling
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import improve as im  # noqa: E402
from improve import OOS, iv  # noqa: E402
import auto_lab as al  # noqa: E402
import autoresearch as ar  # noqa: E402

FRESH = pd.Timestamp("2026-11-20")


def build(data, params):
    im.PARAMS = params
    return ar._trades(data)


def stats(T, per):
    T = T[(T["entry"] > T["init_stop"]) & (T["entry"] > 0)]
    S = T[T["signal"] < OOS] if per == "dev" else T[(T["signal"] >= OOS) & (T["signal"] < FRESH)]
    if not len(S):
        return None
    net = S["exit"] / S["entry"] - 1 - 0.0035
    a = (S["entry_date"].values.astype("datetime64[ns]"), S["exit_date"].values.astype("datetime64[ns]"),
         S["entry"].values.astype(float), S["init_stop"].values.astype(float), S["exit"].values.astype(float),
         np.ones(len(S)), np.zeros(len(S)))
    R = [al.sim(*a, s) for s in range(15)]
    return {"trades": len(S), "win": round(float((net > 0).mean() * 100), 1), "avg": round(float(net.mean() * 100), 2),
            "cagr": round(float(np.median([r[0] for r in R])), 1), "fall": round(float(np.median([r[1] for r in R])), 1)}


def main():
    load = lambda f: pd.read_csv(os.path.join(HERE, f), parse_dates=["signal", "entry_date", "exit_date"])
    yahoo = {"top-300, next open (B)": load("trades_FINAL.csv"), "top-300, 3:20 pm buy (C1)": load("improve3_trades_C1.csv"),
             "all stocks, next open (U)": load("improve_trades_U2.csv")}
    top = list(iv.universe(include_delisted=True))
    allx = [(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in im.all_stocks()]
    kite = {"top-300, next open (B)": build(top, {}), "top-300, 3:20 pm buy (C1)": build(top, {"entryAtClose": True}),
            "all stocks, next open (U)": build(allx, {})}
    L = ["# The main tests re-run on Kite exchange prices", "",
         f"Run {pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST. Same VANTAGE code and rules; only the price source "
         "changed (Kite first, NSE bhavcopy rebuilds for delisted stocks Kite does not list). Account: ₹51,000, 1% risk, "
         "25% cap, verified Zerodha costs + 20.8% tax, 15 random orders.", "",
         "| Trade set | Period | Source | Trades | Win % | Avg / trade (before tax) | Account growth a year | Worst fall |",
         "|---|---|---|---|---|---|---|---|"]
    for k in yahoo:
        for per in ("dev", "holdout"):
            for src, T in (("Yahoo (old)", yahoo[k]), ("Kite", kite[k])):
                s = stats(T, per)
                if s:
                    L.append(f"| {k} | {per} | {src} | {s['trades']:,} | {s['win']} | {s['avg']:+.2f}% | {s['cagr']}% | {s['fall']}% |")
    from swing.data_prices import provenance_line
    L += ["", "**" + provenance_line() + "** (the 'Yahoo (old)' rows are the earlier test files.)"]
    L += ["", "If Kite and Yahoo agree within about a point a year, every earlier conclusion stands; any bigger gap is "
              "listed and the affected decisions are re-checked."]
    out = os.path.join(im.SW, "journal", "kite_recheck.md")
    open(out, "w").write("\n".join(L) + "\n")
    for k, T in kite.items():
        T.to_csv(os.path.join(im.SW, "data", "auto_research", f"kite_trades_{k.split()[0]}_{'C1' if 'C1' in k else 'B'}.csv.gz"),
                 index=False)
    return L


if __name__ == "__main__":
    print("\n".join(main()))
