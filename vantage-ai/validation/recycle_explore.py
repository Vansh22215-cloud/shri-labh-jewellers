"""Capital recycling - EXPLORATION on development data only (signals before Nov 2023).
For RCP (trend) trades: at day d after entry, how much does the rest of the trade still earn, by its state at d,
compared with what a fresh trend signal earns per day? Writes recycle_paths.csv (both periods, for the later test)."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
import improve as im  # noqa: E402
from improve import iv, OOS, COST  # noqa: E402

CHECK = (10, 15, 20, 30, 40)


def paths(trades, data):
    out = []
    for t in trades.itertuples():
        d = data.get(t.sym)
        if d is None or t.entry_date not in d.index:
            continue
        k0 = d.index.get_loc(t.entry_date)
        kx = d.index.searchsorted(t.exit_date)
        row = {"set": t.set, "sym": t.sym, "signal": t.signal, "entry_date": t.entry_date, "exit_date": t.exit_date,
               "entry": t.entry, "exit": t.exit, "held": kx - k0}
        for c in CHECK:
            if k0 + c < kx and k0 + c + 1 < len(d):
                row[f"c{c}"] = d["close"].iloc[k0 + c] / t.entry - 1        # unrealised at the close of day c
                row[f"o{c}"] = d["open"].iloc[k0 + c + 1]                   # exit price if cut (next open)
                row[f"od{c}"] = d.index[k0 + c + 1]
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    F = pd.read_csv("trades_FINAL.csv", parse_dates=["signal", "entry_date", "exit_date"]).assign(set="top300")
    U = pd.read_csv("improve_trades_U.csv", parse_dates=["signal", "entry_date", "exit_date"]).assign(set="all")
    top = {s: d for s, d, m, src in iv.universe(include_delisted=True)}
    allx = {s: d for s, d, m, src in im.all_stocks()}
    P = pd.concat([paths(F[F.setup == "RCP"], top), paths(U[U.setup == "RCP"], allx)], ignore_index=True)
    P.to_csv("recycle_paths.csv", index=False)
    D = P[P.signal < OOS]
    for st in ("top300", "all"):
        x = D[D.set == st]
        net = x.exit / x.entry - 1 - COST
        base = net.sum() / x.held.sum()                     # fresh trend trade: profit per trading day held
        print(f"\n{st} development: {len(x)} trend trades, fresh-trade profit per day {base * 100:.3f}%")
        for c in CHECK:
            y = x.dropna(subset=[f"c{c}"])
            rem = y.exit / y[f"o{c}"] - 1 - COST / 2        # rest of the trade from the next open (half cost: sell side)
            days = (y.held - c).clip(lower=1)
            b = pd.cut(y[f"c{c}"], [-1, -0.10, -0.05, -0.02, 0, 0.03, 0.08, 10])
            tab = pd.DataFrame({"n": y.groupby(b).size(), "remaining_%": rem.groupby(b).mean() * 100,
                                "per_day_%": (rem.groupby(b).sum() / days.groupby(b).sum()) * 100}).round(3)
            tab["vs_fresh"] = (tab["per_day_%"] / (base * 100)).round(2)
            print(f" day {c}:"); print(tab.to_string())
