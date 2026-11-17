"""Round 5 (IMPROVE5_PREREGISTRATION.md): new short-term families P1-P3.
python3 improve5.py -> improve5_trades_P*.csv + improve5_results.json"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
from improve import iv, HERE, OOS, COST  # noqa: E402


def ind(d):
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    s = pd.Series(c)
    return dict(o=o, h=h, l=l, c=c, v=v, pc=pc, atr=pd.Series(tr).rolling(14).mean().values,
                s5=s.rolling(5).mean().values, s10=s.rolling(10).mean().values, s50=s.rolling(50).mean().values,
                s200=s.rolling(200).mean().values, hi252=pd.Series(h).rolling(252, min_periods=200).max().values,
                turn=(pd.Series(c * v).rolling(20).mean() / 1e7).values, rng=h - l)


def signals(fam, x, rs_ok):
    n = len(x["c"])
    c, o, v, pc = x["c"], x["o"], x["v"], x["pc"]
    sig = np.zeros(n, bool)
    for t in range(260, n - 1):
        if not (x["turn"][t] >= 2):
            continue
        if fam == "P1":
            if c[t] > o[t] and c[t] > pc[t] and c[t] > x["s50"][t] and x["s50"][t] > x["s50"][t - 10] \
                    and c[t] >= 0.85 * x["hi252"][t]:
                dn = [v[k] for k in range(t - 10, t) if c[k] < x["pc"][k]]
                sig[t] = bool(dn) and v[t] > max(dn)
        elif fam == "P2":
            sig[t] = x["rng"][t] <= np.min(x["rng"][t - 6:t + 1]) and c[t] > x["s50"][t] > x["s200"][t]
        else:
            sig[t] = c[t] > x["s200"][t] and c[t] < c[t - 1] < c[t - 2] < c[t - 3] and rs_ok[t]
    return sig


def trades(fam, sym, d, m, rs_ok):
    x = ind(d)
    sig = signals(fam, x, rs_ok) & m
    o, h, l, c = x["o"], x["h"], x["l"], x["c"]
    n, out, t = len(c), [], 0
    while t < n - 1:
        if not sig[t]:
            t += 1
            continue
        e = t + 1
        if fam == "P2":
            trig = h[t] * 1.0005
            if h[e] < trig:
                t += 1
                continue
            px, stop = max(o[e], trig), l[t]
            if px <= stop:
                t += 1
                continue
        else:
            px = o[e]
            stop = px - (2 if fam == "P1" else 3) * x["atr"][t]
        maxd = 10 if fam == "P3" else 30
        ex, exd, why = None, None, ""
        for k in range(e, min(n, e + maxd + 1)):
            if k > e and o[k] <= stop:
                ex, exd, why = o[k], k, "stop-gap"; break
            if l[k] <= stop:
                ex, exd, why = stop, k, "stop"; break
            done = (c[k] > x["s5"][k]) if fam == "P3" else (c[k] < x["s10"][k])
            if (done or k - e >= maxd) and k + 1 < n:
                ex, exd, why = o[k + 1], k + 1, "rule" if done else "time"; break
        if ex is None:
            break
        out.append({"sym": sym, "signal": d.index[t], "entry_date": d.index[e], "exit_date": d.index[exd], "entry": px,
                    "exit": ex, "stop": stop, "why": why, "net": ex / px - 1 - COST})
        t = exd
    return out


def stats(T, weeks):
    if not len(T):
        return {"n": 0}
    r = T["net"]
    w, lo = r[r > 0].sum(), -r[r <= 0].sum()
    return {"n": int(len(r)), "per_week": round(len(r) / weeks, 1), "win": round(float((r > 0).mean() * 100), 1),
            "per_trade": round(float(r.mean() * 100), 2), "pf": round(float(w / lo), 2) if lo > 0 else None}


def main():
    data = list(iv.universe(include_delisted=True))
    close = pd.DataFrame({s: d["close"] for s, d, m, src in data}).sort_index()
    mem = pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, src in data}).reindex(close.index).fillna(False).astype(bool)
    r126 = (close / close.shift(126) - 1).where(mem)
    top30 = r126.rank(axis=1, pct=True) >= 0.70
    out = {}
    for fam in ("P1", "P2", "P3"):
        rows = []
        for s, d, m, src in data:
            rs_ok = top30[s].reindex(d.index).fillna(False).values
            rows += trades(fam, s, d, np.asarray(m, bool), rs_ok)
        T = pd.DataFrame(rows)
        T.to_csv(f"{HERE}/improve5_trades_{fam}.csv", index=False)
        dev, ho = T[T["signal"] < OOS], T[T["signal"] >= OOS]
        wd = max(1, (OOS - dev["signal"].min()).days / 7)
        wh = max(1, (ho["signal"].max() - OOS).days / 7)
        sd, sh = stats(dev, wd), stats(ho, wh)
        ok = sh["per_trade"] >= 1.0 and (sh["pf"] or 0) >= 1.3 and (sd["pf"] or 0) >= 1.3 and sh["per_week"] >= 2 \
            and sd["per_trade"] > 0
        out[fam] = {"PASS": bool(ok), "dev": sd, "holdout": sh,
                    "holdout_by_year": {int(y): stats(g, 52) for y, g in ho.groupby(ho["signal"].dt.year)}}
        print(fam, json.dumps(out[fam]), file=sys.stderr)
    json.dump(out, open(f"{HERE}/improve5_results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
