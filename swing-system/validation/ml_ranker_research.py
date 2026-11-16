"""D110 research: a market-wide MACHINE-LEARNING RANKER - does it find better trades than the rules?

Every day, every stock in the point-in-time top-300 gets ~30 features (momentum, mean reversion, trend, volatility,
volume, 52-week position, strength vs Nifty, Vix Fix, WaveTrend, squeeze, market regime). A gradient-boosted model
learns which combinations precede the best NEXT-10-DAY returns (target = the stock's percentile rank among all
stocks that day, so it learns 'better than the rest', not market direction).
STRICT WALK-FORWARD: the model for year Y is trained only on data that ended 15 trading days before Y started
(so no overlapping future), then predicts all of year Y. Nothing about year Y is ever seen in training.
Evaluation (net of 0.35% costs): each day buy the model's top-5 at the next open, hold 10 trading days.
Compared with the average stock (what a random pick would have earned). Holdout = 2023-11 onwards.
"""
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
sys.path.insert(0, f"{ROOT}/validation")
import indicator_lab as L  # noqa: E402
from swing import data_prices  # noqa: E402

H, COST = 10, 0.0035
OUT = f"{ROOT}/validation/ml_panel.parquet"


def rsi(c, n):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean().values
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean().values
    return 100 - 100 / (1 + up / np.where(dn == 0, np.nan, dn))


def features(sym, d, m):
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    s = pd.Series(c)
    lr = lambda k: np.log(c / s.shift(k).values)
    sma = lambda k: s.rolling(k).mean().values
    tr = L.true_range(h, l, c)
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values
    ret = s.pct_change().values
    vol20 = pd.Series(ret).rolling(20).std().values
    vol60 = pd.Series(ret).rolling(60).std().values
    hi = s.rolling(250).max().values
    lo = s.rolling(250).min().values
    val = pd.Series(c * v).rolling(20).median().values
    hc = s.rolling(22).max().values
    wvf = (hc - l) / hc
    ap = (h + l + c) / 3
    esa = L.ema(ap, 10)
    dd = L.ema(np.abs(ap - esa), 10)
    wt1 = L.ema(np.nan_to_num((ap - esa) / (0.015 * np.where(dd == 0, np.nan, dd))), 21)
    basis = sma(20)
    dev = 2 * s.rolling(20).std(ddof=0).values
    rng = pd.Series(tr).rolling(20).mean().values
    sqz = ((basis - dev > basis - 1.5 * rng) & (basis + dev < basis + 1.5 * rng)).astype(float)
    f = pd.DataFrame({
        "r1": lr(1), "r5": lr(5), "r20": lr(20), "r60": lr(60), "r120": lr(120), "r250": lr(250),
        "r250_20": lr(250) - lr(20), "rsi2": rsi(c, 2), "rsi14": rsi(c, 14),
        "d20": c / sma(20) - 1, "d50": c / sma(50) - 1, "d200": c / sma(200) - 1, "s50_200": sma(50) / sma(200) - 1,
        "atr_pct": atr / c, "vol20": vol20, "vol60": vol60, "vol_ratio": vol20 / vol60,
        "vratio": pd.Series(v).rolling(5).mean().values / pd.Series(v).rolling(60).mean().values,
        "turnover": np.log1p(val), "hi52": c / hi - 1, "lo52": c / lo - 1,
        "wvf": wvf, "wt1": wt1, "sqz": sqz, "gap": o / np.r_[np.nan, c[:-1]] - 1,
        "rngpos": (c - l) / np.where(h - l == 0, np.nan, h - l),
        "dn_days": pd.Series((np.diff(c, prepend=c[0]) < 0).astype(float)).rolling(5).sum().values,
    }, index=d.index)
    f["fwd"] = np.r_[o[1 + H:] / o[1:-H] - 1, np.full(H + 1, np.nan)][:len(c)] if len(c) > H + 1 else np.nan
    f["sym"], f["member"] = sym, m
    return f[m & (np.arange(len(c)) >= 260)]


def _one(a):
    try:
        return features(*a)
    except Exception:
        return None


def build_panel():
    t0 = time.time()
    data = list(L.daily_universe())
    with Pool(4) as p:
        parts = [x for x in p.imap_unordered(_one, data, chunksize=4) if x is not None and len(x)]
    P = pd.concat(parts)
    P.index.name = "date"
    P = P.reset_index()
    nf = data_prices.load("NIFTY50")["close"]
    mk = pd.DataFrame({"n_r5": np.log(nf / nf.shift(5)), "n_r20": np.log(nf / nf.shift(20)),
                       "n_rsi2": pd.Series(rsi(nf.values, 2), index=nf.index),
                       "n_up200": (nf > nf.rolling(200).mean()).astype(float),
                       "n_vol20": nf.pct_change().rolling(20).std()})
    P = P.merge(mk, left_on="date", right_index=True, how="left")
    br = P.groupby("date")["d50"].apply(lambda x: (x > 0).mean()).rename("breadth")
    P = P.merge(br, left_on="date", right_index=True, how="left")
    for k in ("r20", "r60"):                            # strength vs Nifty
        P[f"rs_{k}"] = P[k] - P[f"n_{k}"] if f"n_{k}" in P else P[k]
    P["rs_r60"] = P["r60"] - P.groupby("date")["r60"].transform("median")
    print(f"panel {len(P):,} rows, {P.sym.nunique()} stocks, {time.time() - t0:.0f}s", file=sys.stderr)
    P.to_parquet(OUT)
    return P


STOCK = ["r1", "r5", "r20", "r60", "r120", "r250", "r250_20", "rsi2", "rsi14", "d20", "d50", "d200", "s50_200",
         "atr_pct", "vol20", "vol60", "vol_ratio", "vratio", "turnover", "hi52", "lo52", "wvf", "wt1", "sqz", "gap",
         "rngpos", "dn_days", "rs_r20", "rs_r60"]
MARKET = ["n_r5", "n_r20", "n_rsi2", "n_up200", "n_vol20", "breadth"]


def prep(P):
    P = P.replace([np.inf, -np.inf], np.nan)
    X = P.groupby("date")[STOCK].rank(pct=True)          # cross-sectional ranks: robust, comparable across years
    X[MARKET] = P[MARKET]
    y = P.groupby("date")["fwd"].rank(pct=True)
    return X, y


def walk_forward(P, years=range(2016, 2027), top=5):
    from sklearn.ensemble import HistGradientBoostingRegressor
    X, y = prep(P)
    dates = pd.Series(sorted(P["date"].unique()))
    preds = pd.Series(np.nan, index=P.index)
    for Y in years:
        start = pd.Timestamp(f"{Y}-01-01")
        k = dates.searchsorted(start)
        if k >= len(dates):
            break
        cut = dates.iloc[max(0, k - 15)]                 # 15-day gap: no training target overlaps year Y
        tr = (P["date"] < cut) & y.notna()
        tr &= (P["date"].dt.dayofyear % 2 == 0)         # every 2nd day (less overlap, faster)
        te = (P["date"] >= start) & (P["date"] < pd.Timestamp(f"{Y + 1}-01-01"))
        if tr.sum() < 50000 or te.sum() == 0:
            continue
        mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                            min_samples_leaf=800, l2_regularization=1.0, random_state=0)
        mdl.fit(X[tr], y[tr])
        preds[te] = mdl.predict(X[te])
        print(f"  {Y}: trained on {int(tr.sum()):,} rows up to {cut.date()}", file=sys.stderr)
    P = P.assign(pred=preds)
    return P[P["pred"].notna() & P["fwd"].notna()]


def evaluate(R, top=5, step=1, filt=None):
    rows = []
    for dte, g in R.groupby("date"):
        if filt is not None and not filt(g):
            continue
        pick = g.nlargest(top, "pred")
        rows.append({"date": dte, "pick": pick["fwd"].mean() - COST, "all": g["fwd"].mean() - COST,
                     "win": (pick["fwd"] - COST > 0).mean(), "ic": g["pred"].corr(g["fwd"], method="spearman")})
    E = pd.DataFrame(rows)
    E = E.iloc[::step]
    return E


def report(E, label):
    E["year"] = pd.to_datetime(E["date"]).dt.year
    y = E.groupby("year").agg(pick=("pick", "mean"), all=("all", "mean"), win=("win", "mean"), ic=("ic", "mean"))
    y["excess"] = y["pick"] - y["all"]
    ho = E[pd.to_datetime(E["date"]) >= "2023-11-01"]
    print(f"\n== {label} ==")
    print((y * 100).round(2).to_string())
    print(f"ALL YEARS: pick {E.pick.mean() * 100:+.2f}% / 10 days, average stock {E['all'].mean() * 100:+.2f}%, "
          f"excess {(E.pick - E['all']).mean() * 100:+.2f}%, trades in profit {E.win.mean() * 100:.1f}%, "
          f"IC {E.ic.mean():.3f}, years with positive excess {(y.excess > 0).sum()}/{len(y)}")
    print(f"HOLDOUT (2023-11+): pick {ho.pick.mean() * 100:+.2f}%, average {ho['all'].mean() * 100:+.2f}%, "
          f"excess {(ho.pick - ho['all']).mean() * 100:+.2f}%, in profit {ho.win.mean() * 100:.1f}%")


if __name__ == "__main__":
    import os
    P = pd.read_parquet(OUT) if os.path.exists(OUT) and "--rebuild" not in sys.argv else build_panel()
    R = walk_forward(P)
    R[["date", "sym", "pred", "fwd", "n_up200", "breadth"]].to_parquet(f"{ROOT}/validation/ml_preds.parquet")
    report(evaluate(R, 5), "top-5 every day")
    report(evaluate(R, 5, filt=lambda g: g["n_up200"].iloc[0] == 1), "top-5, only when Nifty is above its 200-day avg")
    report(evaluate(R, 10), "top-10 every day")
    report(evaluate(R, 20), "top-20 every day")
