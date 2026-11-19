"""Strict, information-before-each-trade test of behaviour groups (CONTEXT_PROTOCOL.md addendum 2)."""
import json
import os
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import context_engine as ce
from improve import HERE, OOS, SW

C = pd.read_csv(os.environ.get("ATLAS_CONTEXT_TRADES") or os.path.join(SW, "data", "auto_research", "context_trades.csv.gz"), parse_dates=["signal"])
X = pd.read_csv(os.environ.get("ATLAS_FEATURES") or os.path.join(SW, "data", "auto_research", "features.csv.gz"), parse_dates=["signal", "entry_date", "exit_date"],
                low_memory=False)
X = X[(X["entry"] > X["init_stop"]) & (X["entry"] > 0)].copy()
X = X.merge(C.drop(columns=["net", "cluster6", "cluster10"]).drop_duplicates(["set", "sym", "signal"]),
            on=["set", "sym", "signal"], how="left", suffixes=("", "_c"))
for b in ce.BEH:
    if b + "_c" in X:
        X[b] = X[b].fillna(X[b + "_c"])
X = X.sort_values("signal").reset_index(drop=True)
YEARS = range(2014, 2027)


def strict_scores(T, kind, seed=0, shuffle=False):
    """-> per-trade score and past count, every year fitted on the past only."""
    sc, pn = pd.Series(np.nan, index=T.index), pd.Series(0, index=T.index)
    rng = np.random.default_rng(seed)
    for y in YEARS:
        cut = pd.Timestamp(f"{y}-01-01")
        fit = T[(T["signal"] < cut)][ce.BEH].dropna()
        if len(fit) < 500:
            continue
        mu, sd = fit.mean(), fit.std().replace(0, 1)
        km = KMeans(n_clusters=10, n_init=5, random_state=0).fit(((fit - mu) / sd).clip(-4, 4))
        upto = T[T["signal"] < pd.Timestamp(f"{y + 1}-01-01")]
        g = pd.Series(km.predict(((upto[ce.BEH] - mu) / sd).fillna(0).clip(-4, 4)), index=upto.index).astype(str)
        if kind == "PREVIOUS":
            g = g.groupby(upto["sym"]).shift(1).fillna("none")
        elif kind == "MODAL":
            out = []
            for _, gg in g.groupby(upto["sym"]):
                seen = {}
                for i, v in gg.items():
                    out.append((i, max(seen, key=seen.get) if seen else "none"))
                    seen[v] = seen.get(v, 0) + 1
            g = pd.Series(dict(out)).reindex(upto.index)
        cur = upto.index[upto["signal"] >= cut]
        if shuffle:
            g.loc[cur] = g.loc[cur].values[rng.permutation(len(cur))]
        P = upto["exit_date"] < cut
        st = upto.loc[P].groupby(g[P])["net"].agg(["mean", "count"])
        overall = upto.loc[P, "net"].mean()
        shr = (st["mean"] * st["count"] + overall * ce.SHRINK) / (st["count"] + ce.SHRINK)
        sc[cur] = g[cur].map(shr).fillna(overall).values
        pn[cur] = g[cur].map(st["count"]).fillna(0).values
    return sc, pn


def spread(T, sc):
    s = []
    for y in range(2016, 2027):
        m = (T["signal"].dt.year == y) & sc.notna()
        if m.sum() < 90:
            continue
        a, r = sc[m], T.loc[m, "net"]
        s.append(float((r[a >= a.quantile(2 / 3)].mean() - r[a <= a.quantile(1 / 3)].mean()) * 100))
    return {"spread_pts": round(float(np.mean(s)), 2), "years_positive": f"{sum(x > 0 for x in s)} of {len(s)}"}


def acct(T, sc, rule=True, seeds=15):
    S = T
    order = -sc.fillna(sc.median()).values if rule else np.zeros(len(S))
    return ce.account(S, np.ones(len(S)), order, seeds)


out = {}
for kind in ("DYNAMIC", "PREVIOUS", "MODAL"):
    out[kind] = {}
    for st in ("top300", "all"):
        T = X[X["set"] == st].reset_index(drop=True)
        sc, pn = strict_scores(T, kind)
        row = {"power": spread(T, sc)}
        for per, m in (("dev", T["signal"] < OOS), ("holdout", T["signal"] >= OOS)):
            S = T[m].reset_index(drop=True)
            s2 = sc[m].reset_index(drop=True)
            row[per] = {"rule": acct(S, s2), "base": acct(S, s2, rule=False)}
        if st == "top300":
            luck = []
            for w in range(3):
                lsc, _ = strict_scores(T, kind, seed=100 + w, shuffle=True)
                m = T["signal"] >= OOS
                luck.append(acct(T[m].reset_index(drop=True), lsc[m].reset_index(drop=True))[0])
            row["luck_holdout"] = luck
        out[kind][st] = row
        print(kind, st, json.dumps(row), flush=True)
for kind in out:
    r = out[kind]
    out[kind]["PASS"] = all(r[s][p]["rule"][0] >= r[s][p]["base"][0] + 1 and r[s][p]["rule"][1] >= r[s][p]["base"][1] - 2
                            for s in ("top300", "all") for p in ("dev", "holdout")) and \
        r["top300"]["holdout"]["rule"][0] > max(r["top300"]["luck_holdout"])
json.dump(out, open(os.path.join(HERE, "strict_groups_results.json"), "w"), indent=1)
print({k: out[k]["PASS"] for k in out})
