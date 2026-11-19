"""AUTO-LAB (AUTO_LAB_PROTOCOL.md): generate every possibility from the situation features and test each one.
  python auto_lab.py step1   -> development screen + luck count -> auto_lab_step1.json (commit before step 2)
  python auto_lab.py step2   -> holdout, year by year, placebo for step-1 survivors -> auto_lab_results.json"""
import json
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = "/home/user/shri-labh-jewellers/vantage-ai/validation"
OOS = pd.Timestamp("2023-11-01")
CAP0, RISK, MAXPCT, HALF_COST = 51000, 0.01, 0.25, 0.00175
NUM = ["turnover_cr", "from_52w_high", "ret_6m", "ret_1m", "ret_1w", "vol_surge", "atr_pct", "range_10d", "vs_200d",
       "signal_day_move", "price_rs", "up_days_10", "nifty_1m", "nifty_vs_200d", "nifty_vol_20d", "score", "stop_dist",
       "day_of_month", "stock_past_trades", "stock_past_win"]
CAT = ["setup", "mkt_trend", "mkt_mood", "mkt_breadth", "weekday", "month", "sector", "results_soon"]


def load():
    X = pd.read_csv(f"{HERE}/lab_features.csv.gz", parse_dates=["signal", "entry_date", "exit_date"], low_memory=False)
    X = X[(X["entry"] > X["init_stop"]) & (X["entry"] > 0)].copy()
    X["stop_dist"] = (X["entry"] - X["init_stop"]) / X["entry"]
    X["month"] = X["month"].astype(str)
    X["dev"] = X["signal"] < OOS
    return X


def sim(entry_date, exit_date, entry, stop, exitp, mult, order, seed):
    """Account simulation (same rules as improve10/21: realized equity, fixed-size 1% risk, 25% cap).
    Open trades sit in a heap by exit date (same accounting, much faster with many open trades)."""
    import heapq
    rng = np.random.default_rng(seed)
    key = np.lexsort((rng.random(len(entry)), order, entry_date))
    ed_l, xd_l = entry_date.astype("datetime64[D]").astype(np.int64), exit_date.astype("datetime64[D]").astype(np.int64)
    ed_l, xd_l, en_l, st_l, ex_l, mu_l = ed_l.tolist(), xd_l.tolist(), entry.tolist(), stop.tolist(), exitp.tolist(), mult.tolist()
    cash = eq = float(CAP0)
    opn, hist, n = [], [], 0
    for i in key.tolist():
        ed = ed_l[i]
        while opn and opn[0][0] <= ed:
            xd, _, pe, px, q = heapq.heappop(opn)
            cash += q * px * (1 - HALF_COST)
            eq += q * (px - pe) - q * (pe + px) * HALF_COST
            hist.append((xd, eq))
        if mu_l[i] <= 0:
            continue
        e = en_l[i]
        q = min(int(CAP0 * RISK * mu_l[i] // (e - st_l[i])), int(CAP0 * MAXPCT // e))
        need = q * e * (1 + HALF_COST)
        if q < 1 or need > cash:
            continue
        cash -= need
        n += 1
        heapq.heappush(opn, (xd_l[i], n, e, ex_l[i], q))
    while opn:
        xd, _, pe, px, q = heapq.heappop(opn)
        eq += q * (px - pe) - q * (pe + px) * HALF_COST
        hist.append((xd, eq))
    v = np.array([x[1] for x in hist])
    dd = float((v / np.maximum.accumulate(v) - 1).min() * 100) if len(v) else 0.0
    yrs = max((entry_date.max() - entry_date.min()) / np.timedelta64(1, "D") / 365.25, 0.5)
    return ((eq / CAP0) ** (1 / yrs) - 1) * 100, dd


def run(S, rule, seeds):
    """-> (median growth, median worst fall) for one rule on one trade set/period."""
    mult = np.ones(len(S))
    order = np.zeros(len(S))
    kind, col, val = rule["kind"], rule.get("col"), rule.get("val")
    if kind in ("skip", "half"):
        m = rule_mask(S, rule)
        mult[m] = 0.0 if kind == "skip" else 0.5
    elif kind in ("prefer_high", "prefer_low"):
        x = S[col].astype(float).fillna(S[col].astype(float).median()).values
        order = -x if kind == "prefer_high" else x
    elif kind == "random_skip":
        mult[np.random.default_rng(rule["seed"]).random(len(S)) < val] = 0.0
    a = (S["entry_date"].values, S["exit_date"].values, S["entry"].values.astype(float),
         S["init_stop"].values.astype(float), S["exit"].values.astype(float), mult, order)
    R = [sim(*a, s) for s in range(seeds)]
    return float(np.median([r[0] for r in R])), float(np.median([r[1] for r in R]))


def rule_mask(S, rule):
    col, val = rule["col"], rule["val"]
    if rule.get("num"):
        x = S[col].astype(float)
        lo, hi = val
        return ((x >= lo) & (x < hi)).values
    return (S[col].astype(str) == str(val)).values


def possibilities(X):
    """Every rule from the protocol, bucket edges from DEVELOPMENT trades of the top-300 set."""
    D = X[X["dev"] & (X["set"] == "top300")]
    out = []
    for c in NUM:
        q = D[c].astype(float).quantile([0.2, 0.4, 0.6, 0.8]).values
        e = [-np.inf, *q, np.inf]
        if len(set(np.round(q, 12))) < 4:
            continue
        nm = lambda a, b: f"{c} {'' if a == -np.inf else f'{a:.4g}'}..{'' if b == np.inf else f'{b:.4g}'}"
        for kind, (a, b) in [("skip", (e[0], e[1])), ("skip", (e[4], e[5])), ("skip", (e[0], e[2])),
                             ("skip", (e[3], e[5])), ("half", (e[0], e[1])), ("half", (e[4], e[5]))]:
            out.append({"kind": kind, "col": c, "val": [a, b], "num": True, "name": f"{kind} {nm(a, b)}"})
        out += [{"kind": "prefer_high", "col": c, "name": f"prefer high {c}"},
                {"kind": "prefer_low", "col": c, "name": f"prefer low {c}"}]
    for c in CAT:
        vc = D[c].astype(str).value_counts(normalize=True)
        for v in vc[vc >= 0.03].index:
            if v in ("nan", "unknown"):
                continue
            for kind in ("skip", "half"):
                out.append({"kind": kind, "col": c, "val": v, "name": f"{kind} {c} = {v}"})
    for r in out:
        r["val"] = [float(x) for x in r["val"]] if r.get("num") else r.get("val")
    return out


def _job(args):
    tag, S, rule, seeds = args
    return tag, rule["name"], run(S, rule, seeds)


def screen(X, rules, seeds=7, procs=4):
    sets = {k: X[X["dev"] & (X["set"] == k)].reset_index(drop=True) for k in ("top300", "all")}
    base = {k: run(S, {"kind": "none"}, seeds) for k, S in sets.items()}
    jobs = [(k, S, r, seeds) for r in rules for k, S in sets.items()]
    res = {}
    with Pool(procs) as p:
        for k, name, v in p.imap_unordered(_job, jobs, chunksize=4):
            res.setdefault(name, {})[k] = v
    passed = []
    for r in rules:
        v = res[r["name"]]
        ok = all(v[k][0] >= base[k][0] + 1 and v[k][1] >= base[k][1] - 2 for k in sets)
        r["dev"] = {k: {"cagr": round(v[k][0], 2), "maxdd": round(v[k][1], 2)} for k in sets}
        if ok:
            passed.append(r)
    return base, passed


def shuffled(X, seed):
    """Luck world: every situation column shuffled within each year (the link to results is cut)."""
    rng = np.random.default_rng(seed)
    Y = X.copy()
    yr = Y["signal"].dt.year.values
    for c in NUM + CAT:
        v = Y[c].values.copy()
        for y in np.unique(yr):
            i = np.where(yr == y)[0]
            v[i] = v[rng.permutation(i)]
        Y[c] = v
    return Y


def step1():
    X = load()
    rules = possibilities(X)
    print(len(rules), "possibilities", flush=True)
    base, passed = screen(X, rules)
    print("development: base", base, "passed", len(passed), flush=True)
    luck = []
    for s in (1, 2, 3, 4, 5):
        _, p = screen(shuffled(X, s), [dict(r) for r in rules])
        luck.append(len(p))
        print("luck world", s, "passed", len(p), flush=True)
    json.dump({"possibilities": len(rules), "base_dev": base, "passed_dev": len(passed), "luck_passes": luck,
               "survivors": passed, "all_rules_dev": [{"name": r["name"], "dev": r["dev"]} for r in rules]},
              open(f"{HERE}/auto_lab_step1.json", "w"), indent=1, default=str)


def step2():
    X = load()
    S1 = json.load(open(f"{HERE}/auto_lab_step1.json"))
    surv = S1["survivors"]
    H = {k: X[~X["dev"] & (X["set"] == k)].reset_index(drop=True) for k in ("top300", "all")}
    base = {k: run(S, {"kind": "none"}, 15) for k, S in H.items()}
    T3 = X[X["set"] == "top300"].reset_index(drop=True)
    D3 = X[X["dev"] & (X["set"] == "top300")].reset_index(drop=True)
    years = sorted(T3["signal"].dt.year.unique())
    out = []
    for r in surv:
        v = {k: run(S, r, 15) for k, S in H.items()}
        r["holdout"] = {k: {"cagr": round(v[k][0], 2), "maxdd": round(v[k][1], 2)} for k in H}
        r["holdout_pass"] = all(v[k][0] >= base[k][0] + 1 and v[k][1] >= base[k][1] - 2 for k in H)
        better = 0
        for y in years:
            Y = T3[T3["signal"].dt.year == y].reset_index(drop=True)
            if len(Y) < 50:
                continue
            better += run(Y, r, 7)[0] >= run(Y, {"kind": "none"}, 7)[0]
        r["years_better"] = f"{better} of {len(years)}"
        r["years_pass"] = better >= 0.6 * len(years)
        if r["kind"] == "skip":
            frac = float(rule_mask(D3, r).mean())
            g = run(D3, r, 7)[0]
            pl = [run(D3, {"kind": "random_skip", "val": frac, "seed": s}, 7)[0] for s in range(20)]
            r["placebo_beaten"] = f"{sum(g > x for x in pl)} of 20"
            r["placebo_pass"] = sum(g > x for x in pl) >= 18
        else:
            r["placebo_pass"] = True
        r["CANDIDATE"] = bool(r["holdout_pass"] and r["years_pass"] and r["placebo_pass"])
        print(r["name"], r["holdout"], r["years_better"], r.get("placebo_beaten", "-"), "CANDIDATE" * r["CANDIDATE"],
              flush=True)
        out.append(r)
    json.dump({"base_holdout": base, "tested": len(out), "candidates": [r["name"] for r in out if r["CANDIDATE"]],
               "results": out}, open(f"{HERE}/auto_lab_results.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    {"step1": step1, "step2": step2}[sys.argv[1]]()
