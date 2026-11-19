"""Round 22 (IMPROVE22_PREREGISTRATION.md): swap a slow trade for a dip-buy."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import iv, HERE, OOS  # noqa: E402
from improve10 import load  # noqa: E402


def sim(T, opens, seed, swap=None, cap0=45000, risk=0.01, maxpct=0.25):
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T))).sort_values(["entry_date", "rnd"])
    cash, eq, opn, hist, swaps = cap0, cap0, [], [], 0
    for r in T.itertuples():
        keep = []
        for o in opn:
            if o["xd"] <= r.entry_date:
                cash += o["q"] * o["px"] * (1 - 0.00175)
                eq += o["q"] * (o["px"] - o["pe"]) - o["q"] * (o["pe"] + o["px"]) * 0.00175
                hist.append((o["xd"], eq))
            else:
                keep.append(o)
        opn = keep
        q = min(int(cap0 * risk // (r.entry - r.init_stop)), int(cap0 * maxpct // r.entry))
        need = q * r.entry * 1.00175
        if q >= 1 and need > cash and swap and r.setup == "Dip-buy":
            cands = [o for o in opn if o["setup"] in ("RCP", "Breakout")]
            vals = []
            for o in cands:
                op = opens.get(o["sym"])
                px = op.get(r.entry_date) if op is not None else None
                if px and px == px:
                    vals.append((o, float(px)))
            if vals:
                if swap == "SW1":
                    o, px = min(vals, key=lambda v: v[1] / v[0]["pe"])
                elif swap == "SW2":
                    o, px = min(vals, key=lambda v: v[0]["ed"])
                else:
                    o, px = max(vals, key=lambda v: v[1] / v[0]["pe"])
                if cash + o["q"] * px * (1 - 0.00175) >= need:
                    opn.remove(o)
                    cash += o["q"] * px * (1 - 0.00175)
                    eq += o["q"] * (px - o["pe"]) - o["q"] * (o["pe"] + px) * 0.00175
                    hist.append((r.entry_date, eq))
                    swaps += 1
        if q < 1 or need > cash:
            continue
        cash -= need
        opn.append({"xd": r.exit_date, "pe": r.entry, "px": r.exit, "q": q, "sym": r.sym, "setup": r.setup, "ed": r.entry_date})
    for o in opn:
        eq += o["q"] * (o["px"] - o["pe"]) - o["q"] * (o["pe"] + o["px"]) * 0.00175
        hist.append((o["xd"], eq))
    H = pd.Series([v for _, v in sorted(hist, key=lambda z: z[0])], index=[d for d, _ in sorted(hist, key=lambda z: z[0])])
    H = H.groupby(level=0).last()
    yrs = (T["entry_date"].max() - T["entry_date"].min()).days / 365.25
    yearly = (H.groupby(H.index.year).last() / H.groupby(H.index.year).last().shift(1).fillna(cap0) - 1) * 100
    return {"cagr": ((eq / cap0) ** (1 / yrs) - 1) * 100, "maxdd": float((H / H.cummax() - 1).min() * 100), "swaps": swaps,
            "yearly": yearly.round(1).to_dict()}


out, ok = {}, {k: True for k in ("SW1", "SW2", "SW3")}
for st, f, gen in (("top300", "trades_FINAL.csv", lambda: iv.universe(include_delisted=True)),
                   ("all", "improve_trades_U2.csv", im.all_stocks)):
    T = load(f)
    opens = {s: d["open"].to_dict() for s, d, m, src in gen() if s in set(T["sym"])}
    out[st] = {}
    for p in ("dev", "holdout", "all_years"):
        S = T[T["signal"] < OOS] if p == "dev" else T[T["signal"] >= OOS] if p == "holdout" else T
        res = {}
        for name in ("today", "SW1", "SW2", "SW3"):
            R = [sim(S, opens, s, None if name == "today" else name) for s in range(15 if p != "all_years" else 7)]
            res[name] = {k: round(float(np.median([r[k] for r in R])), 1) for k in ("cagr", "maxdd", "swaps")}
            if p == "all_years":
                ys = sorted(R[0]["yearly"])
                res[name]["yearly"] = {int(y): round(float(np.median([r["yearly"].get(y, np.nan) for r in R])), 1) for y in ys}
        if p != "all_years":
            for k in ok:
                ok[k] &= res[k]["cagr"] >= res["today"]["cagr"] + 1.0 and res[k]["maxdd"] >= res["today"]["maxdd"] - 2.0
        else:
            for k in ok:
                res[k]["years_better"] = int(sum(res[k]["yearly"][y] > res["today"]["yearly"][y] for y in res[k]["yearly"]))
                res[k]["years_total"] = len(res[k]["yearly"])
        out[st][p] = res
        print(st, p, {k: {x: v[x] for x in v if x != "yearly"} for k, v in res.items()}, flush=True)
out.update({k + "_PASS": bool(v) for k, v in ok.items()})
json.dump(out, open(f"{HERE}/improve22_results.json", "w"), indent=1)
print({k: v for k, v in out.items() if k.endswith("PASS")})
