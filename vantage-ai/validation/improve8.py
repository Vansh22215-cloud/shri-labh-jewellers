"""Round 8 (IMPROVE8_PREREGISTRATION.md): #1 turn of month, #2 upper circuit, #3 results reaction, #6 panic sizing.
python3 improve8.py [tom|circuit|results|panic|all] -> improve8_results.json (merged)"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import iv, HERE, OOS, COST, SW  # noqa: E402

RES_F = f"{HERE}/improve8_results.json"


def load(name):
    T = pd.read_csv(f"{HERE}/{name}", parse_dates=["signal", "entry_date", "exit_date"])
    T = T[T["entry"] > 0].copy()
    T["net"] = T["exit"] / T["entry"] - 1 - COST
    return T


SETS = {"top300": "trades_FINAL.csv", "all": "improve_trades_U.csv"}


def g(T):
    if not len(T):
        return {"n": 0}
    r = T["net"]
    lo = -r[r <= 0].sum()
    return {"n": int(len(r)), "win": round(float((r > 0).mean() * 100), 1), "per_trade": round(float(r.mean() * 100), 2),
            "pf": round(float(r[r > 0].sum() / lo), 2) if lo > 0 else None}


def calendar():
    return iv.nifty()["close"].index


# ---------------------------------------------------------------------------------------------- #1
def tom():
    cal = pd.Series(calendar())
    per = cal.dt.to_period("M")
    from_start = cal.groupby(per).cumcount() + 1
    from_end = cal.groupby(per).cumcount(ascending=False) + 1
    inwin = pd.Series(((from_start <= 10) | (from_end <= 2)).values, index=cal.values)
    out, ok = {}, True
    for k, f in SETS.items():
        T = load(f)
        T["tom"] = T["entry_date"].map(inwin).fillna(False).astype(bool)
        out[k] = {}
        for p, m in (("dev", T["signal"] < OOS), ("holdout", T["signal"] >= OOS)):
            a, b = g(T[m & T["tom"]]), g(T[m & ~T["tom"]])
            out[k][p] = {"inside": a, "outside": b}
            ok &= (a["n"] >= 150 and b["n"] >= 150 and a["per_trade"] - b["per_trade"] >= 1.0 and a["win"] >= b["win"])
    out["PASS"] = bool(ok)
    return out


# ---------------------------------------------------------------------------------------------- #2
def circuit_trades(sym, d, m, raw):
    o, h, l, c = (d[k].values for k in ("open", "high", "low", "close"))
    rc = raw.values
    turn = (pd.Series(rc) * d["volume"].values).rolling(20).mean().values
    chg = np.r_[np.nan, rc[1:] / rc[:-1] - 1] * 100
    n, t, out = len(c), 260, []
    while t < n - 7:
        band = any(abs(chg[t] - b) <= 0.15 for b in (5, 10, 20))
        if m[t] and band and c[t] >= 0.999 * h[t] and turn[t] >= 2e7:
            e, stop = t + 1, l[t]
            px, ex, exd = o[e], None, None
            if px <= stop:
                t += 1
                continue
            for k in range(e, min(n, e + 6)):
                if k > e and o[k] <= stop:
                    ex, exd = o[k], k
                    break
                if l[k] <= stop:
                    ex, exd = stop, k
                    break
                if k - e >= 5:
                    ex, exd = o[k], k
                    break
            if ex is None:
                break
            out.append({"sym": sym, "signal": d.index[t], "band": round(chg[t]), "entry": px, "exit": ex,
                        "net": ex / px - 1 - COST})
            t = exd
        else:
            t += 1
    return out


def circuit():
    res = {}
    for uni in ("top300", "all"):
        rows = []
        if uni == "top300":
            for s, d, m, src in iv.universe(include_delisted=True):
                rows += circuit_trades(s, d, np.asarray(m, bool), d["close"])
        else:
            for s, d, m, src in im.all_stocks():
                rows += circuit_trades(s, d, np.asarray(m, bool), d["raw_close"])
        T = pd.DataFrame(rows)
        T.to_csv(f"{HERE}/improve8_circuit_{uni}.csv", index=False)
        dev, ho = T[T["signal"] < OOS], T[T["signal"] >= OOS]
        wk_h = max(1, (ho["signal"].max() - OOS).days / 7)
        sd, sh = g(dev), g(ho)
        sh["per_week"] = round(len(ho) / wk_h, 1)
        res[uni] = {"dev": sd, "holdout": sh,
                    "holdout_by_band": {int(b): g(x) for b, x in ho.groupby("band")},
                    "holdout_by_year": {int(y): g(x) for y, x in ho.groupby(ho["signal"].dt.year)}}
    a = res["all"]
    res["PASS"] = bool(a["holdout"]["per_trade"] >= 1.0 and (a["holdout"]["pf"] or 0) >= 1.3 and (a["dev"]["pf"] or 0) >= 1.3
                       and a["holdout"]["per_week"] >= 2 and a["dev"]["per_trade"] > 0)
    return res


# ---------------------------------------------------------------------------------------------- #3
def results():
    from swing import data_prices
    import glob
    import os
    cal = calendar()
    files = glob.glob(f"{SW}/data/events/earnings/*.csv")
    syms = [os.path.basename(f)[:-4] for f in files]
    px = {}
    for s in syms:
        d = data_prices.load(s)
        if d is not None and len(d) > 300:
            c = (d["adj_close"] if "adj_close" in d else d["close"]).astype(float)
            px[s] = pd.DataFrame({"c": c, "o": d["open"].astype(float) * (c / d["close"].astype(float))})
    close = pd.DataFrame({s: v["c"] for s, v in px.items()}).reindex(cal)
    ew = close.pct_change(fill_method=None).mean(axis=1)                       # equal-weight average stock
    ew_cum = (1 + ew.fillna(0)).cumprod()
    ev = []
    for f in files:
        s = os.path.basename(f)[:-4]
        if s not in px:
            continue
        dates = pd.to_datetime(pd.read_csv(f)["date"], errors="coerce").dropna().dt.normalize().unique()
        c = close[s]
        o = px[s]["o"].reindex(cal)
        for dt in dates:
            i = cal.searchsorted(dt)                                          # first trading day on/after the date
            if i < 1 or i + 7 >= len(cal):
                continue
            before, react = i - 1, i + 1 if cal[i] == dt else i               # reaction = next trading day after date
            if react + 6 >= len(cal) or np.isnan(c.iloc[before]) or np.isnan(c.iloc[react]):
                continue
            R = c.iloc[react] / c.iloc[before] - 1
            drift = c.iloc[react + 5] / c.iloc[react] - 1 - (ew_cum.iloc[react + 5] / ew_cum.iloc[react] - 1)
            trade = o.iloc[react + 6] / o.iloc[react + 1] - 1 - COST if o.iloc[react + 1] > 0 else np.nan
            ev.append({"sym": s, "date": cal[react], "R": R, "drift": drift, "trade": trade})
    E = pd.DataFrame(ev).dropna()
    E.to_csv(f"{HERE}/improve8_results_events.csv", index=False)
    out = {"events": int(len(E))}
    okA = okB = True
    for p, m in (("dev", E["date"] < OOS), ("holdout", E["date"] >= OOS)):
        dn, up = E[m & (E["R"] <= -0.05)], E[m & (E["R"] >= 0.05)]
        tr = up["trade"]
        lo = -tr[tr <= 0].sum()
        out[p] = {"bad_n": int(len(dn)), "bad_drift_pct": round(float(dn["drift"].mean() * 100), 2),
                  "good_n": int(len(up)), "good_trade_pct": round(float(tr.mean() * 100), 2),
                  "good_trade_pf": round(float(tr[tr > 0].sum() / lo), 2) if lo > 0 else None,
                  "good_win": round(float((tr > 0).mean() * 100), 1)}
        okA &= len(dn) >= 100 and out[p]["bad_drift_pct"] <= -1.0
        okB &= out[p]["good_trade_pct"] >= 1.0 and (out[p]["good_trade_pf"] or 0) >= 1.3
    out["PASS_avoid_after_bad"], out["PASS_ride_good"] = bool(okA), bool(okB)
    # 3b guard
    bad = E[E["R"] <= -0.05]
    calidx = pd.Series(np.arange(len(cal)), index=cal)
    badpos = {s: calidx.reindex(x["date"]).values for s, x in bad.groupby("sym")}
    okC = True
    out["guard"] = {}
    for k, f in SETS.items():
        T = load(f)
        T = T[T["sym"].isin(px)].copy()
        pos = calidx.reindex(T["signal"]).values
        flag = []
        for s, p_ in zip(T["sym"], pos):
            bp = badpos.get(s)
            flag.append(bool(bp is not None and np.isfinite(p_) and ((p_ - bp > 0) & (p_ - bp <= 10)).any()))
        T["after_bad"] = flag
        out["guard"][k] = {}
        for p, m in (("dev", T["signal"] < OOS), ("holdout", T["signal"] >= OOS)):
            a, b = g(T[m & T["after_bad"]]), g(T[m & ~T["after_bad"]])
            out["guard"][k][p] = {"after_bad_results": a, "others": b}
            okC &= a["n"] >= 50 and b["per_trade"] - a["per_trade"] >= 1.0
    out["PASS_guard"] = bool(okC)
    return out


# ---------------------------------------------------------------------------------------------- #6
def sim(T, panic, cap0=45000, risk=0.01, maxpct=0.25, seed=0, half=True):
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T))).sort_values(["entry_date", "rnd"])
    cash, eq, opn, hist, taken = cap0, cap0, [], [], 0
    for r in T.itertuples():
        keep = []
        for (xd, pe, pxx, q) in opn:
            if xd <= r.entry_date:
                cash += q * pxx * (1 - 0.00175)
                eq += q * (pxx - pe) - q * (pe + pxx) * 0.00175
                hist.append((xd, eq))
            else:
                keep.append((xd, pe, pxx, q))
        opn = keep
        rk = risk * (0.5 if half and panic.get(r.signal, False) else 1.0)
        if r.entry <= r.init_stop:
            continue
        q = min(int(cap0 * rk // (r.entry - r.init_stop)), int(cap0 * maxpct // r.entry))
        if q < 1 or q * r.entry * 1.00175 > cash:
            continue
        cash -= q * r.entry * 1.00175
        opn.append((r.exit_date, r.entry, r.exit, q))
        taken += 1
    for (xd, pe, pxx, q) in opn:
        eq += q * (pxx - pe) - q * (pe + pxx) * 0.00175
        hist.append((xd, eq))
    H = pd.Series([e for _, e in sorted(hist)], index=[d for d, _ in sorted(hist)])
    H = H.groupby(level=0).last()
    yrs = (T["entry_date"].max() - T["entry_date"].min()).days / 365.25
    return {"cagr": ((eq / cap0) ** (1 / yrs) - 1) * 100, "maxdd": float((H / H.cummax() - 1).min() * 100),
            "per_week": taken / (yrs * 52)}


def panic():
    n = iv.nifty()["close"]
    vol = n.pct_change().rolling(20).std()
    thr = vol.rolling(500, min_periods=250).quantile(0.9).shift(1)
    P = (vol > thr)
    pan = P.to_dict()
    out, ok = {"panic_days_pct": round(float(P.mean() * 100), 1)}, True
    for k, f in SETS.items():
        T = load(f)
        out[k] = {}
        for p, m in (("dev", T["signal"] < OOS), ("holdout", T["signal"] >= OOS)):
            S = T[m]
            r = {}
            for name, half in (("today", False), ("half_in_panic", True)):
                R = [sim(S, pan, seed=s, half=half) for s in range(15)]
                r[name] = {x: round(float(np.median([z[x] for z in R])), 1) for x in ("cagr", "maxdd", "per_week")}
            r["panic_share_of_signals_pct"] = round(float(S["signal"].map(pan).fillna(False).astype(bool).mean() * 100), 1)
            out[k][p] = r
            ok &= (r["half_in_panic"]["maxdd"] - r["today"]["maxdd"] >= 2.0
                   and r["today"]["cagr"] - r["half_in_panic"]["cagr"] <= 1.0)
    out["PASS"] = bool(ok)
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    try:
        R = json.load(open(RES_F))
    except Exception:
        R = {}
    for k, fn in (("1_turn_of_month", tom), ("2_upper_circuit", circuit), ("3_results", results), ("6_panic_sizing", panic)):
        if which in ("all", k.split("_", 1)[1].split("_")[0], k[0]):
            R[k] = fn()
            json.dump(R, open(RES_F, "w"), indent=1, default=str)
            print(k, "PASS" if R[k].get("PASS") else {x: v for x, v in R[k].items() if x.startswith("PASS")}, flush=True)
