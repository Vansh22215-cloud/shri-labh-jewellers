"""Improvement research - runs exactly what IMPROVE_PREREGISTRATION.md fixed before any test.
python3 improve.py runs      -> trades for E1, E2, D1, D2 and the all-stock universe (U)
python3 improve.py analyse   -> improve_results.json (A filters, M meta-labeling, E, U, D verdicts)
"""
import json
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

import os as _os
_REPO = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
SW = _os.path.join(_REPO, "swing-system")
sys.path.insert(0, SW)
sys.path.insert(0, f"{SW}/validation")
sys.path.insert(0, _os.path.join(_REPO, "vantage-ai", "validation"))
import independent_validation as iv  # noqa: E402
import replica  # noqa: E402

HERE = _os.path.join(_REPO, "vantage-ai", "validation")
OOS = pd.Timestamp("2023-11-01")
COST = 0.0035
BASE_P = {"exitMode": "Fixed risk/reward", "usePullback": False}
VARIANTS = {"E1": {"beAtR": 1.0}, "E2": {"timeStopBars": 20}, "D1": {"dipRsi": 5.0}, "D2": {"dipRsi": 10.0}}
BENCH = None
PARAMS = None


def _one(args):
    sym, d, m, src = args
    try:
        tr = replica.run(d, BENCH, allow=m, p=dict(BASE_P, **PARAMS))
        for x in tr:
            x.update(sym=sym, src=src)
        return tr
    except Exception as e:
        return [{"error": f"{sym}: {e}"}]


def all_stocks():
    """U: every stock with price data (Yahoo files + delisted NSE rebuilds), ETFs excluded, no top-300 limit."""
    from swing import data_prices
    from swing.tipcheck import equity_list
    import re
    eq = set(equity_list()["SYMBOL"].astype(str))
    fund = re.compile(r"BEES$|ETF|^LIQUID|GOLD|SILVER|^SETF|NIFTY|SHARE$|CASE$|^LIQ")
    dl = iv._delisted()
    syms = {p.stem for p in data_prices.PRICES.glob("*.csv") if not p.stem.startswith("^")} | set(dl)
    for sym in sorted(syms):
        if sym not in eq and fund.search(sym):
            continue
        d0 = data_prices.load(sym)
        src = "yahoo"
        if (d0 is None or not len(d0)) and sym in dl:
            d0, src = dl[sym], "nse"
        if d0 is None or len(d0) < 520:
            continue
        if "adj_close" not in d0:
            d0 = d0.assign(adj_close=d0["close"])
        f = (d0["adj_close"] / d0["close"]).fillna(1.0)
        d = pd.DataFrame({"open": d0["open"] * f, "high": d0["high"] * f, "low": d0["low"] * f,
                          "close": d0["adj_close"], "volume": d0["volume"], "raw_close": d0["close"]}).dropna()
        d = d[(d.index >= "2012-01-01") & (d[["open", "high", "low", "close"]] > 0).all(axis=1)]
        if len(d) >= 520:
            yield sym, d, np.ones(len(d), bool), src


def runs():
    global BENCH, PARAMS
    BENCH = iv.nifty()["close"]
    top = list(iv.universe(include_delisted=True))
    jobs = [(k, v, top) for k, v in VARIANTS.items()]
    jobs.append(("U", {}, [(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in all_stocks()]))
    for name, prm, data in jobs:
        PARAMS = prm
        tr = []
        with Pool(4) as p:
            for r in p.imap_unordered(_one, data, chunksize=4):
                tr += r
        T = pd.DataFrame([t for t in tr if "error" not in t])
        T.to_csv(f"{HERE}/improve_trades_{name}.csv", index=False)
        print(name, len(T), "trades,", sum("error" in t for t in tr), "errors", file=sys.stderr)


# ----------------------------------------------------------------------------- analysis
def stats(T):
    if not len(T):
        return {"n": 0}
    r = T["gross"] - COST
    w, l = r[r > 0], r[r <= 0]
    R = r / T["stop_pct"].clip(lower=0.005)
    eq = (R * 0.01).groupby(T["exit_date"]).sum().sort_index().cumsum()
    return {"n": int(len(r)), "win": round(float((r > 0).mean() * 100), 1), "exp": round(float(r.mean() * 100), 2),
            "pf": round(float(w.sum() / -l.sum()), 2) if l.sum() < 0 else None,
            "dd_1pct": round(float((eq - eq.cummax()).min() * 100), 1)}


def frame(path):
    T = pd.read_csv(path, parse_dates=["signal", "entry_date", "exit_date"])
    T["gross"] = T["exit"] / T["entry"] - 1
    T["stop_pct"] = ((T["entry"] - T["init_stop"]) / T["entry"]).clip(lower=0.005)
    T["net"] = T["gross"] - COST
    return T


def split(T):
    return T[T["signal"] < OOS], T[T["signal"] >= OOS]


def features(T, data):
    """Every feature is known at the signal day's close."""
    by = {s: d for s, d, m, src in data}
    raw = pd.DataFrame({s: d["close"] for s, d, m, src in data}).sort_index().astype(float)
    mem = pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, src in data}).reindex(raw.index).fillna(False).astype(bool)
    breadth = ((raw > raw.rolling(200, min_periods=200).mean()).astype(float).where(mem).sum(1)
               / mem.sum(1).replace(0, np.nan) * 100)
    r126 = (raw / raw.shift(126) - 1).where(mem)
    rs = r126.rank(axis=1, pct=True)
    sec = pd.read_csv(f"{SW}/data/events/nifty500.csv")
    smap = dict(zip(sec["Symbol"].astype(str), sec["Industry"].astype(str)))
    cols = [c for c in r126.columns if c in smap]
    sret = pd.DataFrame({ind: r126[[c for c in cols if smap[c] == ind]].mean(axis=1)
                         for ind in sorted({smap[c] for c in cols})})
    srank = sret.rank(axis=1, pct=True)
    deliv = pd.read_csv(f"{SW}/data/delivery_panel.csv.gz", index_col=0, parse_dates=True)
    dz = (deliv - deliv.rolling(20, min_periods=10).mean().shift(1)) / deliv.rolling(20, min_periods=10).std().shift(1)
    nif = iv.nifty()["close"]
    nif200 = nif / nif.rolling(200).mean() - 1
    rows = []
    for t in T.itertuples():
        d, day = by.get(t.sym), t.signal
        f = {}
        if d is not None and day in d.index:
            k = d.index.get_loc(day)
            w = d.iloc[max(0, k - 260):k + 1]
            c, h, l, v = w["close"], w["high"], w["low"], w["volume"]
            tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
            dlt = c.diff()
            up, dn = dlt.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(), (-dlt.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
            f = {"atr_pct": float(tr.tail(14).mean() / c.iloc[-1] * 100),
                 "dist52": float(c.iloc[-1] / h.tail(252).max() - 1) * 100,
                 "rvol": float(v.iloc[-1] / max(1.0, v.iloc[-21:-1].mean())),
                 "rsi14": float(100 - 100 / (1 + up.iloc[-1] / max(dn.iloc[-1], 1e-9))),
                 "ret20": float(c.iloc[-1] / c.iloc[-21] - 1) * 100 if len(c) > 21 else np.nan}
        f["breadth"] = float(breadth.get(day, np.nan))
        f["rs"] = float(rs.at[day, t.sym]) if t.sym in rs.columns and day in rs.index else np.nan
        ind = smap.get(t.sym)
        f["sector_rank"] = float(srank.at[day, ind]) if ind and day in srank.index else np.nan
        f["deliv"] = float(deliv.at[day, t.sym]) if t.sym in deliv.columns and day in deliv.index else np.nan
        f["deliv_z"] = float(dz.at[day, t.sym]) if t.sym in dz.columns and day in dz.index else np.nan
        f["nifty200"] = float(nif200.asof(day) * 100)
        rows.append(f)
    F = pd.DataFrame(rows, index=T.index)
    return pd.concat([T, F], axis=1)


def judge_filter(T, keep):
    dev, ho = split(T)
    kd, kh = keep.loc[dev.index], keep.loc[ho.index]
    b_dev, b_ho, f_dev, f_ho = stats(dev), stats(ho), stats(dev[kd]), stats(ho[kh])
    ok = (f_ho.get("n", 0) >= 0.5 * b_ho["n"] and f_ho["exp"] > b_ho["exp"] and f_ho["win"] >= b_ho["win"]
          and f_dev["exp"] > b_dev["exp"])
    return {"PASS": bool(ok), "dev_base": b_dev, "dev_filtered": f_dev, "holdout_base": b_ho, "holdout_filtered": f_ho,
            "kept_holdout_pct": round(100 * f_ho.get("n", 0) / max(1, b_ho["n"]))}


FEATS = ["is_dip", "is_rcp", "is_brk", "tier_n", "score", "breadth", "rs", "sector_rank", "atr_pct", "dist52", "rvol",
         "rsi14", "ret20", "nifty200", "stop_pct100", "deliv", "deliv_z"]


def meta(T):
    from sklearn.ensemble import HistGradientBoostingClassifier
    T = T.copy()
    T["is_dip"], T["is_rcp"], T["is_brk"] = (T["setup"] == "Dip-buy") * 1, (T["setup"] == "RCP") * 1, (T["setup"] == "Breakout") * 1
    T["tier_n"] = T["tier"].map({"A": 3, "B": 2, "C": 1}).fillna(0)
    T["stop_pct100"] = T["stop_pct"] * 100
    T["y"] = (T["net"] > 0) * 1
    T["p"] = np.nan
    T["keep_meta"] = True
    for Y in range(2016, 2027):
        tr = T[T["exit_date"] < pd.Timestamp(f"{Y}-01-01")]
        te = T[(T["signal"] >= pd.Timestamp(f"{Y}-01-01")) & (T["signal"] < pd.Timestamp(f"{Y + 1}-01-01"))]
        if len(tr) < 500 or not len(te):
            continue
        m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40,
                                           random_state=0)
        m.fit(tr[FEATS], tr["y"])
        cut = np.quantile(m.predict_proba(tr[FEATS])[:, 1], 0.30)
        p = m.predict_proba(te[FEATS])[:, 1]
        T.loc[te.index, "p"] = p
        T.loc[te.index, "keep_meta"] = p >= cut
    W = T[T["p"].notna()]
    res = judge_filter(W, W["keep_meta"])
    ho = W[W["signal"] >= OOS]
    bins = pd.cut(ho["p"], [0, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0])
    res["calibration_holdout"] = {str(k): {"n": int(len(g)), "predicted": round(float(g["p"].mean() * 100)) if len(g) else None,
                                           "actual_win": round(float(g["y"].mean() * 100)) if len(g) else None,
                                           "exp": round(float(g["net"].mean() * 100), 2) if len(g) else None}
                                  for k, g in ho.groupby(bins, observed=True)}
    res["walk_forward_years"] = "2016-2026"
    return res, T


def analyse():
    data = list(iv.universe(include_delisted=True))
    base = frame(f"{HERE}/trades_FINAL.csv")
    T = features(base, data)
    out = {"_note": "rules: IMPROVE_PREREGISTRATION.md", "baseline": {"dev": stats(split(T)[0]), "holdout": stats(split(T)[1])}}
    out["F1_breadth50"] = judge_filter(T, T["breadth"].fillna(100) >= 50)
    out["F2_rs70"] = judge_filter(T, T["rs"].fillna(1) >= 0.70)
    out["F3_sector_top_third"] = judge_filter(T, T["sector_rank"].isna() | (T["sector_rank"] >= 2 / 3))
    out["F4_delivery_above_avg"] = judge_filter(T, T["deliv_z"].fillna(1) > 0)
    out["M_meta_label"], TM = meta(T)
    TM.to_csv(f"{HERE}/improve_meta_trades.csv", index=False)
    # E: exits
    bdev, bho = split(base)
    for k in ("E1", "E2"):
        V = frame(f"{HERE}/improve_trades_{k}.csv")
        vd, vh = split(V)
        sd, sh, xd, xh = stats(vd), stats(vh), stats(bdev), stats(bho)
        ok = (sh["exp"] >= xh["exp"] and (sh["dd_1pct"] > xh["dd_1pct"] or (sh["pf"] or 0) > (xh["pf"] or 0))
              and sd["exp"] >= xd["exp"] and (sd["dd_1pct"] > xd["dd_1pct"] or (sd["pf"] or 0) > (xd["pf"] or 0)))
        out[k] = {"PASS": bool(ok), "dev": sd, "holdout": sh, "dev_base": xd, "holdout_base": xh}
    # D: more dip-buys (only the ADDITIONAL trades are judged)
    key = set(zip(base["sym"], base["signal"]))
    for k in ("D1", "D2"):
        V = frame(f"{HERE}/improve_trades_{k}.csv")
        add = V[np.array([(s, d) not in key for s, d in zip(V["sym"], V["signal"])]) & (V["setup"] == "Dip-buy").values]
        ad, ah = split(add)
        sd, sh = stats(ad), stats(ah)
        ok = (sh.get("n", 0) > 0 and sh["win"] >= 70 and sh["exp"] >= 1.5 and sd.get("n", 0) > 0 and sd["win"] >= 70
              and sd["exp"] >= 1.5)
        out[k] = {"PASS": bool(ok), "additional_dev": sd, "additional_holdout": sh,
                  "per_year_added": round(len(add) / 13.9, 1), "all_dev": stats(split(V)[0]), "all_holdout": stats(split(V)[1])}
    # U: bigger universe by liquidity bucket
    U = frame(f"{HERE}/improve_trades_U.csv")
    tv = {}
    from swing import data_prices
    for s in U["sym"].unique():
        d0 = data_prices.load(s)
        if d0 is not None:
            tv[s] = (d0["close"] * d0["volume"]).rolling(20).mean() / 1e7      # ₹ crore a day
    U["tv_cr"] = [float(tv[s].asof(dt)) if s in tv else np.nan for s, dt in zip(U["sym"], U["signal"])]
    bins = [0, 2, 5, 10, 20, 50, 1e9]
    labels = ["<2cr", "2-5cr", "5-10cr", "10-20cr", "20-50cr", ">=50cr"]
    U["bucket"] = pd.cut(U["tv_cr"], bins, labels=labels)
    bwin = stats(split(base)[1])["win"]
    out["U_universe"] = {"baseline_holdout_win": bwin, "per_year_all": round(len(U) / 13.9)}
    for b, g in U.groupby("bucket", observed=True):
        gd, gh = split(g)
        sd, sh = stats(gd), stats(gh)
        ok = all(x.get("n", 0) > 0 and x["exp"] > 0 and (x["pf"] or 0) >= 1.3 and x["win"] >= bwin - 3 for x in (sd, sh))
        out["U_universe"][b] = {"PASS": bool(ok), "dev": sd, "holdout": sh, "per_year": round(len(g) / 13.9)}
    json.dump(out, open(f"{HERE}/improve_results.json", "w"), indent=1, default=str)
    return out


if __name__ == "__main__":
    {"runs": runs, "analyse": analyse}[sys.argv[1]]()
