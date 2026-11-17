"""Rounds 3-4 (IMPROVE3_PREREGISTRATION.md).
python3 improve3.py runs     -> improve3_trades_C1.csv
python3 improve3.py analyse  -> improve3_results.json (C1 + momentum M1-M3)
"""
import json
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
import improve as im  # noqa: E402
from improve import iv, HERE, stats, split, frame, OOS, COST  # noqa: E402


def runs():
    im.BENCH = iv.nifty()["close"]
    im.PARAMS = {"entryAtClose": True}
    data = list(iv.universe(include_delisted=True))
    tr = []
    with Pool(4) as p:
        for r in p.imap_unordered(im._one, data, chunksize=4):
            tr += r
    T = pd.DataFrame([t for t in tr if "error" not in t])
    T.to_csv(f"{HERE}/improve3_trades_C1.csv", index=False)
    print("C1", len(T), "trades", sum("error" in t for t in tr), "errors", file=sys.stderr)


def c1():
    base, V = frame(f"{HERE}/trades_FINAL.csv"), frame(f"{HERE}/improve3_trades_C1.csv")
    (bd, bh), (vd, vh) = split(base), split(V)
    sb, sv = {"dev": stats(bd), "holdout": stats(bh)}, {"dev": stats(vd), "holdout": stats(vh)}
    ok = all(sv[k]["exp"] > sb[k]["exp"] and sv[k]["win"] >= sb[k]["win"] and sv[k]["n"] >= 0.9 * sb[k]["n"]
             for k in ("dev", "holdout"))
    by = {}
    for s in sorted(V["setup"].unique()):
        by[s] = {"base_holdout": stats(bh[bh["setup"] == s]), "C1_holdout": stats(vh[vh["setup"] == s]),
                 "base_dev": stats(bd[bd["setup"] == s]), "C1_dev": stats(vd[vd["setup"] == s])}
    return {"PASS": bool(ok), "baseline": sb, "C1": sv, "by_setup": by}


def _curve(rets):
    eq = (1 + rets).cumprod()
    yrs = len(rets) / 12
    return {"cagr": round(float(eq.iloc[-1] ** (1 / yrs) - 1) * 100, 1),
            "maxdd": round(float((eq / eq.cummax() - 1).min()) * 100, 1)}


def momentum(top=20):
    data = list(iv.universe(include_delisted=True))
    close = pd.DataFrame({s: d["close"] for s, d, m, src in data}).sort_index()
    opn = pd.DataFrame({s: d["open"] for s, d, m, src in data}).reindex(close.index)
    mem = pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, src in data}).reindex(close.index).fillna(False).astype(bool)
    nif = iv.nifty()["close"].reindex(close.index).ffill()
    me = close.groupby(close.index.to_period("M")).apply(lambda x: x.index[-1]).tolist()   # month-end days
    dret = close.pct_change(fill_method=None)
    vol = dret.rolling(252, min_periods=200).std() * np.sqrt(252)
    out = {}
    for name in ("M1", "M2", "M3"):
        rows, held = [], []
        for i in range(13, len(me) - 1):
            d0, d1 = me[i], me[i + 1]
            k0 = close.index.get_loc(d0)
            if k0 + 1 >= len(close.index):
                break
            x = close.loc[d0]
            ok = mem.loc[d0] & x.notna() & close.shift(252).loc[d0].notna()
            if name == "M1":
                score = close.shift(21).loc[d0] / close.shift(252).loc[d0] - 1
            else:
                v = vol.loc[d0]
                score = ((x / close.shift(126).loc[d0] - 1) / v + (x / close.shift(252).loc[d0] - 1) / v) / 2
            score = score[ok & score.notna()]
            cash = name == "M3" and nif.loc[d0] < nif.rolling(200).mean().loc[d0]
            pick = [] if cash else list(score.sort_values(ascending=False).index[:top])
            # bought at next open after d0, held to next open after d1 (exit at last available price if delisted)
            e_day = close.index[k0 + 1]
            k1 = close.index.get_loc(d1)
            x_day = close.index[min(k1 + 1, len(close.index) - 1)]
            r = []
            for s in pick:
                po = opn.at[e_day, s]
                seg = close.loc[e_day:x_day, s].dropna()
                px = opn.at[x_day, s] if not np.isnan(opn.at[x_day, s]) else (seg.iloc[-1] if len(seg) else np.nan)
                r.append(px / po - 1 if po > 0 and not np.isnan(px) else 0.0)
            turnover = len(set(pick) - set(held)) / top if pick else (1.0 if held else 0.0)
            gross = float(np.mean(r)) if r else 0.0
            rows.append({"month": d1, "ret": gross - turnover * COST * (2 if pick and held else 1)})
            held = pick
        R = pd.DataFrame(rows).set_index("month")["ret"]
        b = []
        for i in range(13, 13 + len(R)):
            d0, d1 = me[i], me[i + 1]
            b.append(nif.loc[d1] / nif.loc[d0] - 1)
        B = pd.Series(b, index=R.index)
        res = {}
        for per, msk in (("dev", R.index < OOS), ("holdout", R.index >= OOS)):
            res[per] = {"strategy": _curve(R[msk]), "nifty": _curve(B[msk])}
        yr = pd.DataFrame({"s": R, "b": B}).groupby(R.index.year).apply(lambda g: ((1 + g["s"]).prod() - 1) > ((1 + g["b"]).prod() - 1))
        res["years_beat_pct"] = round(float(yr.mean() * 100), 0)
        res["PASS"] = bool(all(res[p]["strategy"]["cagr"] >= res[p]["nifty"]["cagr"] + 3
                               and res[p]["strategy"]["maxdd"] >= res[p]["nifty"]["maxdd"] - 10 for p in ("dev", "holdout"))
                           and res["years_beat_pct"] >= 60)
        res["yearly"] = {int(y): [round(((1 + g["s"]).prod() - 1) * 100, 1), round(((1 + g["b"]).prod() - 1) * 100, 1)]
                         for y, g in pd.DataFrame({"s": R, "b": B}).groupby(R.index.year)}
        out[name] = res
        print(name, json.dumps({k: res[k] for k in ("dev", "holdout", "years_beat_pct", "PASS")}), file=sys.stderr)
    return out


def analyse():
    out = {"C1": c1(), "momentum": momentum()}
    json.dump(out, open(f"{HERE}/improve3_results.json", "w"), indent=1, default=str)
    print(json.dumps({"C1": {k: out["C1"][k] for k in ("PASS", "baseline", "C1")}}, indent=1))


if __name__ == "__main__":
    {"runs": runs, "analyse": analyse, "momentum": lambda: momentum()}[sys.argv[1]]()
