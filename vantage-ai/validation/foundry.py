"""ATLAS Strategy Foundry (FOUNDRY_PROTOCOL.md): ATLAS designs complete new strategies (entry x filter x exit) from
building blocks and judges each one on the ₹51,000 account after verified costs and tax - alone and next to the
current live system.
  python foundry.py           -> foundry_results.json + FOUNDRY_RESULTS.md (+ trades of survivors)
Step order: development screen (all) -> luck worlds (survivors) -> holdout (best 10) -> fresh (weekly, later)."""
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import improve as im  # noqa: E402
from improve import OOS, iv  # noqa: E402
import auto_lab as al  # noqa: E402

FRESH = pd.Timestamp("2026-11-20")
NIFTY_FUND = {"dev": 13.5, "holdout": 7.8}      # same dates, total return after tax (INVESTIGATION_19NOV.md)
W = 121                                           # longest trade window (120-day limit + next-open exit)
P = {}                                            # the panel and indicators (filled by load())


# ----------------------------------------------------------------------------------------------- data
def load():
    if P:
        return P
    data = list(iv.universe(include_delisted=True))
    dates = sorted(set().union(*[d.index for _, d, _, _ in data]))
    idx = pd.DatetimeIndex(dates)
    syms = [s for s, _, _, _ in data]
    get = lambda col: pd.DataFrame({s: d[col] for s, d, _, _ in data}).reindex(idx)
    O, H, L, C, V = (get(c) for c in ("open", "high", "low", "close", "volume"))
    M = pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, _ in data}).reindex(idx).fillna(False).astype(bool)
    n = iv.nifty()["close"].reindex(idx).ffill()
    pc = C.shift()
    tr = pd.concat([H - L, (H - pc).abs(), (L - pc).abs()]).groupby(level=0).max().reindex(idx)
    atr = tr.rolling(14, min_periods=10).mean()
    ma10, ma20, ma50, ma100, ma200 = (C.rolling(k, min_periods=int(k * 0.8)).mean() for k in (10, 20, 50, 100, 200))
    d = C.diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    rsi2 = 100 - 100 / (1 + up.ewm(alpha=0.5, adjust=False).mean() / dn.ewm(alpha=0.5, adjust=False).mean().replace(0, np.nan))
    ret126 = C / C.shift(126) - 1
    rs = ret126.where(M).rank(axis=1, pct=True)
    rng10 = (H.rolling(10).max() - L.rolling(10).min()) / C
    squeeze = rng10 <= rng10.rolling(250, min_periods=120).quantile(0.2)
    above200 = (C > ma200).where(M)
    breadth = above200.sum(axis=1) / above200.notna().sum(axis=1).replace(0, np.nan)
    downs = (d < 0).astype(int)
    down3 = (downs.rolling(3).sum() == 3).shift(1, fill_value=False) if False else downs.rolling(3).sum().shift(1) == 3
    loc = (C - L) / (H - L).replace(0, np.nan)
    vr = V / V.rolling(50, min_periods=30).median().shift(1)
    base60 = (H.rolling(60).max() - L.rolling(60).min()) / C < 0.25
    P.update(idx=idx, syms=syms, O=O, H=H, L=L, C=C, M=M, atr=atr, ma10=ma10, ma20=ma20, ma50=ma50, ma200=ma200,
             ma100=ma100, base60=base60, hh100=H.rolling(100).max().shift(1), ret5=C / C.shift(5) - 1,
             rsi2=rsi2, rs=rs, squeeze=squeeze, breadth=breadth, down3=down3, loc=loc, vr=vr,
             hh20=H.rolling(20).max().shift(1), hh55=H.rolling(55).max().shift(1), hh252=H.rolling(252, min_periods=200).max().shift(1),
             gap=C.shift(0) * 0 + (O / pc - 1), ret1=C / pc - 1, ret3=C / C.shift(3) - 1,
             nifty_up=pd.Series(n > n.rolling(200).mean(), index=idx))
    for k in ("O", "H", "L", "C", "atr", "ma10", "ma20", "ma50"):
        P[k + "_a"] = P[k].values.astype(np.float64)
    return P


# ----------------------------------------------------------------------------------------------- building blocks
def entries():
    p = load()
    C, O, H = p["C"], p["O"], p["H"]
    up = (C > p["ma200"]) & (p["ma50"] > p["ma200"])
    E = {
        "breakout 20-day high": C > p["hh20"],
        "breakout 55-day high": C > p["hh55"],
        "breakout 52-week high": C > p["hh252"],
        "squeeze then 20-day breakout": p["squeeze"].shift(1, fill_value=False) & (C > p["hh20"]),
        "pullback to 50-day average in uptrend": up & (p["L"] <= p["ma50"]) & (C > p["ma50"]),
        "2-day RSI below 5 in uptrend": up & (p["rsi2"] < 5),
        "2-day RSI below 10 in uptrend": up & (p["rsi2"] < 10),
        "3 down days then strong close (uptrend)": up & p["down3"] & (p["ret1"] > 0) & (p["loc"] > 0.7),
        "gap-up 3%+ closing strong on 2x volume": (p["gap"] > 0.03) & (p["loc"] > 0.75) & (p["vr"] > 2),
        "volume surge 3x up-day 4%+ near the high": (p["vr"] > 3) & (p["ret1"] > 0.04) & (p["loc"] > 0.8),
        "strength leader pulling back 3 days": (p["rs"] > 0.9) & (p["ret3"] < -0.03) & (C > p["ma50"]),
        "within 2% of 52-week high, top-20% strength": (C >= 0.98 * p["hh252"]) & (p["rs"] > 0.8),
        # addendum 1: long-hold / big-move entries
        "50-day average crosses above 200-day": (p["ma50"] > p["ma200"]) & (p["ma50"].shift(1) <= p["ma200"].shift(1)),
        "52-week high after a 60-day base": (C > p["hh252"]) & p["base60"].shift(1, fill_value=False),
        "top-10% strength turning up after a dip": (p["rs"] > 0.9) & (p["ret5"].shift(1) < 0) & (p["ret1"] > 0.01),
        "close above the 100-day high": C > p["hh100"],
    }
    return {k: (v.fillna(False) & p["M"]).astype(bool) for k, v in E.items()}


def filters():
    p = load()
    nf = pd.DataFrame(np.repeat(p["nifty_up"].values[:, None], len(p["syms"]), 1), index=p["idx"], columns=p["syms"])
    bf = pd.DataFrame(np.repeat((p["breadth"] > 0.5).values[:, None], len(p["syms"]), 1), index=p["idx"], columns=p["syms"])
    return {"no filter": None, "NIFTY above 200-day": nf, "stock above 200-day": (p["C"] > p["ma200"]),
            "breadth above 50%": bf}


EXITS = {"stop 2 ATR, 10 days": dict(k=2, T=10), "stop 3 ATR, 20 days": dict(k=3, T=20),
         "stop 2 ATR, 20 days": dict(k=2, T=20),
         "trail below 20-day avg, stop 3 ATR, 60 days": dict(k=3, T=60, trail="ma20"),
         "trail below 10-day avg, stop 3 ATR, 60 days": dict(k=3, T=60, trail="ma10"),
         "target 2R, stop 2 ATR, 20 days": dict(k=2, T=20, R=2), "target 3R, stop 2 ATR, 20 days": dict(k=2, T=20, R=3),
         # addendum 1: long holds
         "trail below 50-day avg, stop 5 ATR, 120 days": dict(k=5, T=120, trail="ma50"),
         "trail below 20-day avg after +10%, stop 3 ATR, 120 days": dict(k=3, T=120, trail="ma20", arm=0.10),
         "target 5R, stop 4 ATR, 120 days": dict(k=4, T=120, R=5)}


# ----------------------------------------------------------------------------------------------- trades
def first_true(B):
    """index of the first True per row (len if none)"""
    a = B.argmax(axis=1)
    a[~B.any(axis=1)] = B.shape[1]
    return a


def trades(sig, ex, t_s=None):
    """sig: bool DataFrame (signal at the close). -> trades with entry next open, exit by the rule (gap-adjusted)."""
    p = load()
    if t_s is None:
        first = sig & ~sig.shift(1, fill_value=False)
        t, s = np.nonzero(first.values)
    else:
        t, s = t_s
    nT = len(p["idx"])
    keep = t + 1 < nT
    t, s = t[keep], s[keep]
    rows = np.minimum(t[:, None] + 1 + np.arange(W)[None, :], nT - 1)
    past_end = (t[:, None] + 1 + np.arange(W)[None, :]) >= nT
    g = lambda k: p[k + "_a"][rows, s[:, None]]
    O, H, L, C = g("O"), g("H"), g("L"), g("C")
    O[past_end] = H[past_end] = L[past_end] = C[past_end] = np.nan
    e = O[:, 0]
    atr = p["atr_a"][t, s]
    ok = np.isfinite(e) & np.isfinite(atr) & (atr > 0) & (e > 0)
    T = ex["T"]
    stop = e - ex["k"] * atr
    tgt = e + ex["R"] * (e - stop) if ex.get("R") else None
    Wt = T + 1
    O, H, L, C = O[:, :Wt], H[:, :Wt], L[:, :Wt], C[:, :Wt]
    with np.errstate(invalid="ignore"):
        js = first_true(L <= stop[:, None])
        jt = first_true(H >= tgt[:, None]) if tgt is not None else np.full(len(e), Wt)
        if ex.get("trail"):
            MA = p[ex["trail"] + "_a"][rows[:, :Wt], s[:, None]]
            below = C[:, :T] < MA[:, :T]
            if ex.get("arm"):                                  # trailing starts only once the close was +arm above entry
                armed = np.maximum.accumulate(np.nan_to_num(C[:, :T], nan=0.0) >= (e * (1 + ex["arm"]))[:, None], axis=1)
                below &= armed
            jr = first_true(below) + 1                         # close below -> sell at the NEXT open
            jr[jr > T] = Wt
        else:
            jr = np.full(len(e), Wt)
        jd = first_true(~np.isfinite(C))                      # data stops (delisting or end of data)
    jtime = np.full(len(e), T - 1)
    cand = np.vstack([js, jt, jr, jtime])
    j = cand.min(axis=0)
    kind = np.argmin(cand, axis=0)                            # ties: stop first (conservative)
    ar = np.arange(len(e))
    jj = np.minimum(j, Wt - 1)
    px = np.where(kind == 0, np.where(jj == 0, stop, np.minimum(O[ar, jj], stop)),
         np.where(kind == 1, np.where(jj == 0, tgt if tgt is not None else 0, np.maximum(O[ar, jj], tgt if tgt is not None else 0)),
         np.where(kind == 2, O[ar, jj], C[ar, jj])))
    # data stopped before the exit: delisted -> last valid close; end of data -> trade still open (dropped)
    dl = jd <= j
    last_valid = np.maximum(jd - 1, 0)
    end_of_data = past_end[ar, np.minimum(jd, W - 1)] & dl
    px = np.where(dl, C[ar, last_valid], px)
    j = np.where(dl, last_valid, j)
    good = ok & np.isfinite(px) & ~end_of_data & (stop < e)
    idx = p["idx"]
    xrow = np.minimum(t + 1 + j, nT - 1)
    return pd.DataFrame({"sym": np.array(p["syms"])[s[good]], "signal": idx[t[good]], "entry_date": idx[t[good] + 1],
                         "exit_date": idx[xrow[good]], "entry": e[good], "exit": px[good], "init_stop": stop[good],
                         "t": t[good], "s": s[good]})


# ----------------------------------------------------------------------------------------------- account
def account(T, seeds=7, base=None):
    S = T if base is None else pd.concat([base, T[base.columns]], ignore_index=True)
    a = (S["entry_date"].values.astype("datetime64[ns]"), S["exit_date"].values.astype("datetime64[ns]"),
         S["entry"].values.astype(float), S["init_stop"].values.astype(float), S["exit"].values.astype(float),
         np.ones(len(S)), np.zeros(len(S)))
    R = [al.sim(*a, sd) for sd in range(seeds)]
    return round(float(np.median([r[0] for r in R])), 2), round(float(np.median([r[1] for r in R])), 2)


_BASE = {}


def current_system():
    """The live system's trades (VANTAGE live setup + live dip-buy), as in round 29."""
    if "b" not in _BASE:
        import improve29 as r29
        B = r29.B[["sym", "signal", "entry_date", "exit_date", "entry", "exit", "init_stop"]].copy()
        _BASE["b"] = B
    return _BASE["b"]


def period(T, per):
    if per == "dev":
        return T[T["signal"] < OOS]
    if per == "holdout":
        return T[(T["signal"] >= OOS) & (T["signal"] < FRESH)]
    return T[T["signal"] >= FRESH]


# ----------------------------------------------------------------------------------------------- the run
def _eval(args):
    name, ek, fk, xk = args
    E, F = _E[ek], _F[fk]
    sig = E if F is None else (E & F.fillna(False).astype(bool))
    T = trades(sig, EXITS[xk])
    D = period(T, "dev")
    if len(D) < 150:
        return {"name": name, "entry": ek, "filter": fk, "exit": xk, "dev_trades": int(len(D)), "screen": False}
    alone = account(D, seeds=5)
    B = period(current_system(), "dev")
    base = account(B, seeds=5)
    comb = account(D, seeds=5, base=B)
    win = float((D["exit"] / D["entry"] - 1 - 0.0035 > 0).mean() * 100)
    ok = (alone[0] >= NIFTY_FUND["dev"] and alone[1] >= -30 and comb[0] >= base[0] + 1 and comb[1] >= base[1] - 2)
    return {"name": name, "entry": ek, "filter": fk, "exit": xk, "dev_trades": int(len(D)), "win_pct": round(win, 1),
            "avg_pct": round(float((D["exit"] / D["entry"] - 1).mean() * 100 - 0.35), 2), "dev_alone": alone,
            "dev_with_current": comb, "dev_current": base, "screen": bool(ok)}


_E, _F = {}, {}


def luck_worlds(T, ex, worlds=20, seed=0):
    """Entries moved to random member days of the same stock and year (same count), same exits -> dev growth list."""
    p = load()
    M = p["M"].values
    yr = p["idx"].year.values
    rng = np.random.default_rng(seed)
    D = period(T, "dev")
    out = []
    pool = {}
    for w in range(worlds):
        tt = np.empty(len(D), int)
        for i, (t, s) in enumerate(zip(D["t"].values, D["s"].values)):
            key = (s, yr[t])
            if key not in pool:
                pool[key] = np.nonzero(M[:, s] & (yr == yr[t]))[0]
            c = pool[key]
            tt[i] = c[rng.integers(len(c))] if len(c) else t
        R = trades(None, ex, t_s=(tt, D["s"].values))
        out.append(account(period(R, "dev"), seeds=3)[0])
    return out


def years_better(T, base, per_years):
    b = 0
    n = 0
    for y in per_years:
        Ty = T[T["signal"].dt.year == y]
        By = base[base["signal"].dt.year == y]
        if len(By) < 30:
            continue
        n += 1
        b += account(Ty, 5, base=By)[0] >= account(By, 5)[0]
    return b, n


def main(procs=4):
    t0 = time.time()
    load()
    _E.update(entries())
    _F.update(filters())
    grid = [(f"{e} | {f} | {x}", e, f, x) for e, f, x in itertools.product(_E, _F, EXITS)]
    print(len(grid), "strategies", flush=True)
    with Pool(procs) as pool:
        res = list(pool.imap_unordered(_eval, grid, chunksize=2))
    surv = sorted([r for r in res if r["screen"]], key=lambda r: -(r["dev_with_current"][0] - r["dev_current"][0]))
    print("development survivors:", len(surv), "of", len(res), flush=True)
    for r in surv[:25]:
        ex = EXITS[r["exit"]]
        sig = _E[r["entry"]] if _F[r["filter"]] is None else (_E[r["entry"]] & _F[r["filter"]].fillna(False).astype(bool))
        T = trades(sig, ex)
        L = luck_worlds(T, ex)
        r["luck_dev"] = L
        r["luck_pass"] = sum(r["dev_alone"][0] > x for x in L) >= 18
        print("luck", r["name"], r["dev_alone"][0], "beats", sum(r["dev_alone"][0] > x for x in L), "of 20", flush=True)
    lucky = [r for r in surv[:25] if r.get("luck_pass")]
    base_all = current_system()
    for r in lucky[:10]:
        ex = EXITS[r["exit"]]
        sig = _E[r["entry"]] if _F[r["filter"]] is None else (_E[r["entry"]] & _F[r["filter"]].fillna(False).astype(bool))
        T = trades(sig, ex)
        H, BH = period(T, "holdout"), period(base_all, "holdout")
        r["hold_alone"], r["hold_with_current"], r["hold_current"] = account(H, 15), account(H, 15, base=BH), account(BH, 15)
        yb, yn = years_better(T[T["signal"] < FRESH], base_all[base_all["signal"] < FRESH], range(2013, 2027))
        r["years_better"] = f"{yb} of {yn}"
        r["PASS"] = bool(r["hold_alone"][0] >= NIFTY_FUND["holdout"] and r["hold_with_current"][0] >= r["hold_current"][0] + 1
                         and r["hold_with_current"][1] >= r["hold_current"][1] - 2 and yb >= 0.6 * yn)
        T.to_csv(os.path.join(im.SW, "data", "auto_research", f"foundry_{abs(hash(r['name'])) % 10**8}.csv.gz"), index=False)
        print("holdout", r["name"], r["hold_alone"], r["hold_with_current"], "vs", r["hold_current"], r["years_better"],
              "PASS" if r["PASS"] else "fail", flush=True)
    out = {"on": str(pd.Timestamp.now(tz="Asia/Kolkata"))[:16], "tried": len(res), "dev_survivors": len(surv),
           "luck_passed": len(lucky), "holdout_tested": min(10, len(lucky)),
           "passed": [r["name"] for r in lucky[:10] if r.get("PASS")], "minutes": round((time.time() - t0) / 60, 1),
           "all": sorted(res, key=lambda r: -((r.get("dev_with_current") or [0])[0] - (r.get("dev_current") or [0])[0]))}
    json.dump(out, open(os.path.join(HERE, "foundry_results.json"), "w"), indent=1, default=str)
    return out


if __name__ == "__main__":
    o = main()
    print({k: v for k, v in o.items() if k != "all"})
