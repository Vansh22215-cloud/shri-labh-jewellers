"""Round 11 (IMPROVE11_PREREGISTRATION.md)."""
import glob
import json
import os
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
import improve as im  # noqa: E402
from improve import HERE, OOS, COST, SW  # noqa: E402
from improve8 import g  # noqa: E402
from improve9 import px, read, event_trades  # noqa: E402


def verdict(T, key, min_ho, bar, pf):
    dev, ho = T[T[key] < OOS], T[T[key] >= OOS]
    sd, sh = g(dev), g(ho)
    wk = max(1, (ho[key].max() - OOS).days / 7) if len(ho) else 1
    sh["per_week"] = round(len(ho) / wk, 1)
    ok = (sh.get("n", 0) >= min_ho and sh["per_trade"] >= bar and (sh["pf"] or 0) >= pf and (sd.get("pf") or 0) >= pf
          and sd["per_trade"] > 0)
    return {"PASS": bool(ok), "dev": sd, "holdout": sh, "by_year": {int(y): g(x) for y, x in T.groupby(T[key].dt.year)}}


def e1():
    rows = []
    for f in glob.glob(f"{SW}/data/events/earnings/*.csv"):
        s = os.path.basename(f)[:-4]
        d = px(s)
        if d is None:
            continue
        idx = d.index
        for dt in pd.to_datetime(pd.read_csv(f)["date"], errors="coerce").dropna().dt.normalize().unique():
            r = idx.searchsorted(dt)
            if r - 4 < 21 or r >= len(idx):
                continue
            if not (d["turn"].iloc[r - 5] >= 2e7):
                continue
            e, x = d["o"].iloc[r - 4], d["c"].iloc[r - 1]
            if e > 0:
                rows.append({"sym": s, "day": idx[r], "net": x / e - 1 - COST})
    T = pd.DataFrame(rows)
    T.to_csv(f"{HERE}/improve11_E1.csv", index=False)
    return verdict(T, "day", 100, 1.0, 1.3)


def e3():
    Y = read("bonus")
    Y["t"] = pd.to_datetime(Y["an_dt"], errors="coerce", dayfirst=True)
    Y = Y.dropna(subset=["t"]).sort_values("t")
    out, last = [], {}
    for s, t in zip(Y["symbol"], Y["t"].dt.normalize()):
        if s in last and (t - last[s]).days < 90:
            continue
        last[s] = t
        out.append({"sym": s, "day": t})
    T = event_trades(pd.DataFrame(out))
    T.to_csv(f"{HERE}/improve11_E3.csv", index=False)
    return verdict(T, "day", 40, 1.0, 1.3)


def e45():
    rows = []
    for s, d, m, src in im.all_stocks():
        f = d["raw_close"] / d["close"]
        ro, rc = (d["open"] * f).values, d["raw_close"].values
        o, c = d["open"].values, d["close"].values
        turn = (pd.Series(rc) * d["volume"].values).rolling(20).mean().shift(1).values
        gap = np.r_[np.nan, ro[1:] / rc[:-1] - 1]
        intr = c / o - 1
        for t in np.where((np.abs(gap) >= 0.02) & (np.abs(gap) < 0.08) & (turn >= 1e8))[0]:
            if t < 21:
                continue
            rows.append({"sym": s, "day": d.index[t], "gap": gap[t], "intraday": intr[t]})
    T = pd.DataFrame(rows)
    T.to_csv(f"{HERE}/improve11_gaps.csv", index=False)
    L = T[T["gap"] < 0].assign(net=lambda x: x["intraday"] - 0.002)
    S = T[T["gap"] > 0].assign(net=lambda x: -x["intraday"] - 0.002)
    res = {"E4_gap_down_buy": verdict(L, "day", 0, 0.30, 1.2), "E5_gap_up_short": verdict(S, "day", 0, 0.30, 1.2)}
    for k in res:
        res[k]["PASS"] = bool(res[k]["PASS"] and res[k]["holdout"]["per_week"] >= 5)
    return res


if __name__ == "__main__":
    R = {"E1_pre_results": e1()}
    print("E1", R["E1_pre_results"]["PASS"], R["E1_pre_results"]["dev"], R["E1_pre_results"]["holdout"], flush=True)
    R.update(e45())
    for k in ("E4_gap_down_buy", "E5_gap_up_short"):
        print(k, R[k]["PASS"], R[k]["dev"], R[k]["holdout"], flush=True)
    if glob.glob(f"{SW}/data/events/history/bonus/*.csv"):
        R["E3_bonus"] = e3()
        print("E3", R["E3_bonus"]["PASS"], R["E3_bonus"]["dev"], R["E3_bonus"]["holdout"], flush=True)
    json.dump(R, open(f"{HERE}/improve11_results.json", "w"), indent=1, default=str)
