"""Round 10 (IMPROVE10_PREREGISTRATION.md): account-level use of money."""
import json
import sys
from multiprocessing import Pool
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
import improve as im  # noqa: E402
from improve import iv, HERE, OOS  # noqa: E402


def run_u_d2():
    im.BENCH, im.PARAMS = iv.nifty()["close"], {"dipRsi": 10.0}
    jobs = [(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in im.all_stocks()]
    tr = []
    with Pool(4) as p:
        for r in p.imap_unordered(im._one, jobs, chunksize=4):
            tr += [t for t in r if "error" not in t]
    pd.DataFrame(tr).to_csv(f"{HERE}/improve10_trades_U_D2.csv", index=False)


def load(f, drop_breakouts=False):
    T = pd.read_csv(f"{HERE}/{f}", parse_dates=["signal", "entry_date", "exit_date"])
    T = T[(T["entry"] > T["init_stop"]) & (T["entry"] > 0)]
    if drop_breakouts:
        T = T[T["setup"] != "Breakout"]
    return T


def sim(T, seed, reserve=None, cap0=45000, risk=0.01, maxpct=0.25):
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T))).sort_values(["entry_date", "rnd"])
    cash, eq, opn, hist = cap0, cap0, [], []
    took = {"dip": 0, "dip_skipped": 0, "all": 0}
    for r in T.itertuples():
        keep = []
        for (xd, pe, px, q, dip) in opn:
            if xd <= r.entry_date:
                cash += q * px * (1 - 0.00175)
                eq += q * (px - pe) - q * (pe + px) * 0.00175
                hist.append((xd, eq))
            else:
                keep.append((xd, pe, px, q, dip))
        opn = keep
        dip = r.setup == "Dip-buy"
        q = min(int(cap0 * risk // (r.entry - r.init_stop)), int(cap0 * maxpct // r.entry))
        need = q * r.entry * 1.00175
        used_slow = sum(q_ * pe for (_, pe, _, q_, d_) in opn if not d_)
        # "the money" = the account's value now (cash + open trades at cost); fixed 45,000 was a bug (see results)
        ok = q >= 1 and need <= cash and (dip or reserve is None or used_slow + need <= reserve * (cash + sum(q_ * pe for (_, pe, _, q_, _) in opn)))
        if not ok:
            if dip:
                took["dip_skipped"] += 1
            continue
        cash -= need
        opn.append((r.exit_date, r.entry, r.exit, q, dip))
        took["all"] += 1
        took["dip"] += dip
    for (xd, pe, px, q, _) in opn:
        eq += q * (px - pe) - q * (pe + px) * 0.00175
        hist.append((xd, eq))
    H = pd.Series([e for _, e in sorted(hist)], index=[d for d, _ in sorted(hist)]).groupby(level=0).last()
    yrs = (T["entry_date"].max() - T["entry_date"].min()).days / 365.25
    return {"cagr": ((eq / cap0) ** (1 / yrs) - 1) * 100, "maxdd": float((H / H.cummax() - 1).min() * 100),
            "per_week": took["all"] / (yrs * 52), "dips_taken": took["dip"], "dips_skipped": took["dip_skipped"]}


def med(T, reserve=None):
    R = [sim(T, s, reserve) for s in range(15)]
    return {k: round(float(np.median([r[k] for r in R])), 1) for k in R[0]}


def analyse():
    sets = {"top300": ("trades_FINAL.csv", "improve_trades_D2.csv"), "all": ("improve_trades_U.csv", "improve10_trades_U_D2.csv")}
    out = {}
    for k, (base, wide) in sets.items():
        out[k] = {}
        for per in ("dev", "holdout"):
            sel = (lambda T: T[T["signal"] < OOS]) if per == "dev" else (lambda T: T[T["signal"] >= OOS])
            out[k][per] = {"V0": med(sel(load(base))), "V1": med(sel(load(base)), 0.7), "V2": med(sel(load(wide))),
                           "V3": med(sel(load(wide)), 0.7), "V4": med(sel(load(base, True)))}
            print(k, per, out[k][per], flush=True)
    for v in ("V1", "V2", "V3", "V4"):
        out[v + "_PASS"] = bool(all(out[k][p][v]["cagr"] >= out[k][p]["V0"]["cagr"] + 1.0
                                    and out[k][p][v]["maxdd"] >= out[k][p]["V0"]["maxdd"] - 2.0
                                    for k in sets for p in ("dev", "holdout")))
    json.dump(out, open(f"{HERE}/improve10_results.json", "w"), indent=1)
    print({v: out[v + "_PASS"] for v in ("V1", "V2", "V3", "V4")})


if __name__ == "__main__":
    {"wide": run_u_d2, "analyse": analyse}[sys.argv[1]]()
