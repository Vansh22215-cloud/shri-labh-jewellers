"""ATLAS Context Engine (CONTEXT_PROTOCOL.md): which rule works, on which kind of stock, in which market - discovered
from behaviour, verified walk-forward (only the past at every date), re-learned every year.
  python context_engine.py   -> context_results.json, CONTEXT_RESULTS.md, context_scores.json (for live use)"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import improve as im  # noqa: E402
import auto_lab as al  # noqa: E402
from improve import OOS  # noqa: E402

SHRINK, MIN_PAST = 50, 50
BEH = ["atr_pct", "beta", "corr", "up_weeks", "wk_autocorr", "gap_freq", "worst_fall_1y", "from_52w_high", "ret_6m",
       "log_turnover"]
_N = {}


def _nifty():
    if "n" not in _N:
        _N["n"] = im.iv.nifty()["close"].pct_change()
    return _N["n"]


def behaviour(d):
    """Per-day behaviour of one stock from the 250 days up to that day (all trailing windows: no look-ahead)."""
    c, o = d["close"], d["open"]
    r = c.pct_change()
    n = _nifty().reindex(r.index)
    cov = r.rolling(250, min_periods=150).cov(n)
    var = n.rolling(250, min_periods=150).var()
    w = c.resample("W-FRI").last().pct_change()
    upw = (w > 0).astype(float).rolling(52, min_periods=30).mean()
    ac = w.rolling(52, min_periods=30).apply(lambda x: pd.Series(x).autocorr(1), raw=True)
    wk = pd.DataFrame({"up_weeks": upw, "wk_autocorr": ac}).shift(1)        # last COMPLETED week only
    wk = wk.reindex(c.index, method="ffill")
    gap = ((o / c.shift() - 1).abs() > 0.02).astype(float).rolling(250, min_periods=150).mean()
    roll_max = c.rolling(250, min_periods=150).max()
    dd = (c / roll_max - 1).rolling(250, min_periods=150).min()
    return pd.DataFrame({"beta": cov / var, "corr": r.rolling(250, min_periods=150).corr(n), "gap_freq": gap,
                         "worst_fall_1y": dd, "up_weeks": wk["up_weeks"], "wk_autocorr": wk["wk_autocorr"]})


_NEED = set()


def _one(args):
    sym, d, _, _src = args
    if sym not in _NEED:
        return None
    B = behaviour(d)
    B["sym"] = sym
    return B.reset_index(names="signal")


def build_behaviour(X, procs=4):
    global _NEED
    _NEED = set(X["sym"])
    _nifty()
    with Pool(procs) as p:
        parts = [x for x in p.imap_unordered(_one, im.all_stocks(), chunksize=8) if x is not None]
    B = pd.concat(parts, ignore_index=True)
    X = X.merge(B, on=["sym", "signal"], how="left")
    X["log_turnover"] = np.log10(X["turnover_cr"].clip(lower=0.01))
    return X


def discover_groups(X, ks=(6, 10)):
    """K-means on standardized behaviour, fitted on DEVELOPMENT trades only."""
    from sklearn.cluster import KMeans
    D = X[X["signal"] < OOS][BEH].dropna()
    mu, sd = D.mean(), D.std().replace(0, 1)
    Z = ((X[BEH] - mu) / sd).fillna(0).clip(-4, 4)
    out = {}
    for k in ks:
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(((D - mu) / sd).clip(-4, 4))
        X[f"cluster{k}"] = "B" + pd.Series(km.predict(Z), index=X.index).astype(str)
        out[k] = {"centres": pd.DataFrame(km.cluster_centers_, columns=BEH).round(2).to_dict("index"),
                  "mu": mu.to_dict(), "sd": sd.to_dict()}
    return out


def add_groupings(X):
    q = lambda c: pd.qcut(X[c].rank(method="first"), 5, labels=False).astype("Int64").astype(str)
    X["size5"], X["swing5"] = "S" + q("turnover_cr"), "V" + q("atr_pct")
    X["market"] = X["mkt_trend"].astype(str) + "|" + X["mkt_mood"].astype(str)
    G = {"sector": X["sector"].astype(str), "size": X["size5"], "swing": X["swing5"], "setup": X["setup"].astype(str),
         "market": X["market"], "behaviour6": X["cluster6"], "behaviour10": X["cluster10"],
         "behaviour10 x market": X["cluster10"] + "~" + X["market"], "sector x market": X["sector"].astype(str) + "~" + X["market"],
         "size x swing": X["size5"] + "~" + X["swing5"], "behaviour10 x setup": X["cluster10"] + "~" + X["setup"].astype(str),
         "behaviour6 x market x setup": X["cluster6"] + "~" + X["market"] + "~" + X["setup"].astype(str),
         # owner 19 Nov: never depend on one view - compare company, sector, behaviour, market, setup, combinations
         "company": X["sym"].astype(str), "company x setup": X["sym"].astype(str) + "~" + X["setup"].astype(str),
         "sector x setup": X["sector"].astype(str) + "~" + X["setup"].astype(str),
         "sector x behaviour10": X["sector"].astype(str) + "~" + X["cluster10"],
         "market x setup": X["market"] + "~" + X["setup"].astype(str),
         "size x sector": X["size5"] + "~" + X["sector"].astype(str),
         "discovered tree (all facts)": pd.Series("TREE", index=X.index)}
    return pd.DataFrame(G, index=X.index)


TREE_FACTS = BEH + ["vol_surge", "range_10d", "vs_200d", "signal_day_move", "up_days_10", "nifty_1m", "nifty_vs_200d",
                    "nifty_vol_20d", "stop_dist"]


def tree_scores(X, years=range(2014, 2027)):
    """ATLAS discovers its own segments: a small decision tree (any combination of facts, setup and market) is fitted
    every year on trades CLOSED before that year only, and predicts that year's trades."""
    from sklearn.tree import DecisionTreeRegressor
    F = X[[c for c in TREE_FACTS if c in X]].copy()
    F["setup_c"] = X["setup"].astype("category").cat.codes
    F["market_c"] = X["market"].astype("category").cat.codes
    F = F.replace([np.inf, -np.inf], np.nan)
    F = F.fillna(F.median()).clip(-1e6, 1e6)
    sc = pd.Series(np.nan, index=X.index)
    pn = pd.Series(0, index=X.index)
    for y in years:
        P = X["exit_date"] < pd.Timestamp(f"{y}-01-01")
        idx = X.index[X["signal"].dt.year == y]
        if P.sum() < 1000 or not len(idx):
            continue
        t = DecisionTreeRegressor(max_depth=4, min_samples_leaf=max(150, int(P.sum() / 40)), random_state=0)
        t.fit(F[P], X.loc[P, "net"].clip(-0.5, 1.0))
        sc[idx] = t.predict(F.loc[idx])
        pn[idx] = MIN_PAST
    return sc, pn


def walk_scores(X, labels, years=range(2014, 2027)):
    """Each trade's context score = shrunk average result of past trades (closed before its year) in its group."""
    if len(labels) and (labels == "TREE").all():
        return tree_scores(X, years)
    sc = pd.Series(np.nan, index=X.index)
    past_n = pd.Series(0, index=X.index)
    for y in years:
        cut = pd.Timestamp(f"{y}-01-01")
        P = X["exit_date"] < cut
        if P.sum() < 200:
            continue
        g = X.loc[P].groupby(labels[P])["net"].agg(["mean", "count"])
        overall = X.loc[P, "net"].mean()
        shr = (g["mean"] * g["count"] + overall * SHRINK) / (g["count"] + SHRINK)
        idx = X.index[X["signal"].dt.year == y]
        sc[idx] = labels[idx].map(shr).fillna(overall).values
        past_n[idx] = labels[idx].map(g["count"]).fillna(0).values
    return sc, past_n


def grouping_power(X, labels, years=range(2016, 2027)):
    sc, _ = walk_scores(X, labels)
    spreads = []
    for y in years:
        m = (X["signal"].dt.year == y) & sc.notna()
        if m.sum() < 90:
            continue
        s, r = sc[m], X.loc[m, "net"]
        t, b = s >= s.quantile(2 / 3), s <= s.quantile(1 / 3)
        spreads.append(float((r[t].mean() - r[b].mean()) * 100))
    return {"spread_pts": round(float(np.mean(spreads)), 2) if spreads else None,
            "years_positive": f"{sum(x > 0 for x in spreads)} of {len(spreads)}",
            "matters": bool(spreads and np.mean(spreads) > 0.5 and sum(x > 0 for x in spreads) >= 0.6 * len(spreads))}


def account(S, mult, order, seeds=15):
    a = (S["entry_date"].values, S["exit_date"].values, S["entry"].values.astype(float),
         S["init_stop"].values.astype(float), S["exit"].values.astype(float))
    R = [al.sim(*a, mult, order, s) for s in range(seeds)]
    return round(float(np.median([x[0] for x in R])), 1), round(float(np.median([x[1] for x in R])), 1)


def rule_arrays(S, sc, pn, kind):
    mult, order = np.ones(len(S)), np.zeros(len(S))
    s = sc.loc[S.index].fillna(sc.loc[S.index].median()).values
    if kind == "C-ORDER":
        order = -s
    else:
        mult[(s < 0) & (pn.loc[S.index].values >= MIN_PAST)] = 0.0
    return mult, order


def test_rule(X, labels, kind, sets=("top300", "all")):
    out = {}
    for st in sets:
        T = X[X["set"] == st]
        sc, pn = walk_scores(T, labels.loc[T.index])
        row = {}
        for per, m in (("dev", T["signal"] < OOS), ("holdout", T["signal"] >= OOS)):
            S = T[m]
            row[per] = {"rule": account(S, *rule_arrays(S, sc, pn, kind)), "base": account(S, np.ones(len(S)), np.zeros(len(S)))}
        yb = n = 0
        for y in range(2014, 2027):
            S = T[T["signal"].dt.year == y]
            if len(S) < 50:
                continue
            n += 1
            yb += account(S, *rule_arrays(S, sc, pn, kind), seeds=7)[0] >= account(S, np.ones(len(S)), np.zeros(len(S)), seeds=7)[0]
        row["years_better"] = f"{yb} of {n}"
        row["years_ok"] = yb >= 0.6 * n
        out[st] = row
    out["pass_bar"] = all(out[s][p]["rule"][0] >= out[s][p]["base"][0] + 1 and out[s][p]["rule"][1] >= out[s][p]["base"][1] - 2
                          for s in sets for p in ("dev", "holdout")) and all(out[s]["years_ok"] for s in sets)
    return out


def luck(X, labels, kind, worlds=3):
    """Same rule with the group labels shuffled within each year -> holdout growth (top-300) per world.
    For the discovered tree the trades' facts are shuffled within each year instead."""
    res = []
    if len(labels) and (labels == "TREE").all():
        for w in range(worlds):
            rng = np.random.default_rng(100 + w)
            Y = X.copy()
            yr = Y["signal"].dt.year
            for y in yr.unique():
                i = Y.index[yr == y]
                p = rng.permutation(len(i))
                for c in TREE_FACTS + ["setup", "market"]:
                    if c in Y:
                        Y.loc[i, c] = Y.loc[i, c].values[p]
            res.append(test_rule(Y, labels, kind, sets=("top300",))["top300"]["holdout"]["rule"][0])
        return res
    for w in range(worlds):
        rng = np.random.default_rng(100 + w)
        L = labels.copy()
        yr = X["signal"].dt.year
        for y in yr.unique():
            i = L.index[yr == y]
            L[i] = L[i].values[rng.permutation(len(i))]
        r = test_rule(X, L, kind, sets=("top300",))
        res.append(r["top300"]["holdout"]["rule"][0])
    return res


def main():
    X = pd.read_csv(os.path.join(im.SW, "data", "auto_research", "features.csv.gz"),
                    parse_dates=["signal", "entry_date", "exit_date"], low_memory=False)
    X = X[(X["entry"] > X["init_stop"]) & (X["entry"] > 0)].copy()
    X = build_behaviour(X)
    groups = discover_groups(X)
    G = add_groupings(X)
    power = {}
    for name in G.columns:
        power[name] = {s: grouping_power(X[X["set"] == s], G.loc[X["set"] == s, name]) for s in ("top300", "all")}
        print(name, power[name], flush=True)
    ok = [n for n in G.columns if all(power[n][s]["matters"] for s in ("top300", "all"))]
    best = sorted(ok, key=lambda n: -min(power[n][s]["spread_pts"] for s in ("top300", "all")))[:3]
    print("groupings that matter (both sets):", ok, "-> tested:", best, flush=True)
    rules = {}
    for n in best:
        for kind in ("C-ORDER", "C-SKIP"):
            r = test_rule(X, G[n], kind)
            r["luck_holdout_top300"] = luck(X, G[n], kind)
            r["beats_luck"] = r["top300"]["holdout"]["rule"][0] > max(r["luck_holdout_top300"])
            r["PASS"] = bool(r["pass_bar"] and r["beats_luck"])
            rules[f"{kind} by {n}"] = r
            print(kind, n, json.dumps(r, default=str), flush=True)
    out = {"groups": {k: v["centres"] for k, v in groups.items()}, "power": power, "matters": ok, "tested": best,
           "rules": rules}
    # model for live use (only acts after a passed rule + the owner's /approve): group centres + today's group scores
    T = X[X["set"] == "top300"]
    overall = T["net"].mean()
    sc = {}
    for name in ("behaviour10", "behaviour10 x setup"):
        g = T.groupby(G.loc[T.index, name])["net"].agg(["mean", "count"])
        sc[name] = ((g["mean"] * g["count"] + overall * SHRINK) / (g["count"] + SHRINK)).round(5).to_dict()
    model = {"made": str(pd.Timestamp.now(tz="Asia/Kolkata"))[:16], "features": BEH, "k": 10,
             "mu": groups[10]["mu"], "sd": groups[10]["sd"],
             "centres": [[groups[10]["centres"][i][f] for f in BEH] for i in range(10)], "scores": sc}
    json.dump(model, open(os.path.join(im.SW, "strategies", "context_model.json"), "w"), indent=1, default=str)
    json.dump(out, open(os.path.join(HERE, "context_results.json"), "w"), indent=1, default=str)
    X[["set", "sym", "signal", "net"] + BEH + ["cluster6", "cluster10"]].to_csv(
        os.path.join(im.SW, "data", "auto_research", "context_trades.csv.gz"), index=False)
    return out


if __name__ == "__main__":
    main()
