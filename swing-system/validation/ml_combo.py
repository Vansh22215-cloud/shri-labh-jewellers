"""D110 part 2: does the walk-forward ML score improve the proven strategies (dip-buy, positional)?"""
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
sys.path.insert(0, f"{ROOT}/validation")
import indicator_confluence as C  # noqa: E402
import indicator_lab as L  # noqa: E402
from rolling_profile_research import run_trades  # noqa: E402

PR = pd.read_parquet(f"{ROOT}/validation/ml_preds.parquet")
PR["pct"] = PR.groupby("date")["pred"].rank(pct=True)
PCT = PR.set_index(["date", "sym"])["pct"]


def one(a):
    sym, d, m = a
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    cs, idx = d["close"], d.index
    out = []
    hp = (cs >= 1.10 * cs.rolling(200).mean()).values & (C.rsi(c) < 2) & C.NUP.reindex(idx).fillna(False).values \
        & (C.NR2.reindex(idx).values < 20) & m
    from swing.confirmations import squeeze_on, vix_fix_spike
    tierok = vix_fix_spike(h, l, c) & ~squeeze_on(h, l, c)
    for date, ret, bars in C.hp_trades(d, hp & tierok):
        out.append(("DIP (current rule)", sym, idx[idx.get_loc(date) - 1], ret))
    from swing.rolling_profile import signals
    rs = signals(d, "price")
    pos = rs["buy"].values & (c >= 0.9 * cs.rolling(250).max().values) & m
    for date, ret, bars in run_trades(d, pos, rs["sell"].values, stop_atr=5.0, max_bars=60):
        out.append(("POS (current rule)", sym, idx[idx.get_loc(date) - 1], ret))
    return out


if __name__ == "__main__":
    rows = []
    with Pool(4) as p:
        for r in p.imap_unordered(one, list(L.daily_universe()), chunksize=2):
            rows += r
    df = pd.DataFrame(rows, columns=["strat", "sym", "date", "ret"])
    df["pct"] = [PCT.get((d, s), np.nan) for d, s in zip(df.date, df.sym)]
    df = df[df.pct.notna()]
    for s, g in df.groupby("strat"):
        g = g.assign(q=pd.cut(g.pct, [0, .33, .67, 1.0], labels=["ML low third", "ML middle", "ML top third"]))
        t = g.groupby("q", observed=True).agg(n=("ret", "size"), win=("ret", lambda r: (r > 0).mean() * 100),
                                             avg=("ret", lambda r: r.mean() * 100))
        ho = g[g.date >= "2023-11-01"].groupby("q", observed=True).agg(
            n_hold=("ret", "size"), win_hold=("ret", lambda r: (r > 0).mean() * 100),
            avg_hold=("ret", lambda r: r.mean() * 100))
        print(f"\n== {s} (2016+, walk-forward ML score on the signal day) ==")
        print(t.join(ho).round(2).to_string())
        print(f"all: n {len(g)}, win {(g.ret > 0).mean() * 100:.1f}%, avg {g.ret.mean() * 100:+.2f}%")
