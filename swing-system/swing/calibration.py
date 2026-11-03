"""Calibrated target probabilities for the tips strategy (ROADMAP T1).

For EVERY historical signal of the strategy (not only the trades it happened to take), entering at the next
open inside the do-not-buy band, we follow the daily bars and record which comes first within the holding window:
the stop, T1, T2 or T3 (stop-first when both inside one day). Results are split by market regime.
Gives: P(T1 before stop), P(T2 ...), P(T3 ...), median days to T1, and the sample size.
"""
import json

import numpy as np
import pandas as pd

from . import engine
from .config import ROOT, get_logger, load_strategy
from .research import regime_frame

log = get_logger()
OUT = ROOT / "validation" / "calibration.json"


def run(name):
    p = load_strategy(name)
    P, sig, nifty, *_ = engine.build(p)
    o, h, l, c = (P[k].values for k in ("open", "high", "low", "close"))
    dates = P["close"].index
    el = sig["eligible"].values & sig["regime_ok"].values[:, None]
    atr = sig["atr"].values
    reg = regime_frame(nifty.reindex(dates), sig["breadth"])
    rs = [p["target1_r"], p["target2_r"], p["target2_r"] * 1.5]       # T3 = 1.5 x T2 distance
    H = p["max_hold_days"]
    rows = []
    ii, jj = np.nonzero(el[:-1])
    for i, j in zip(ii, jj):
        if not np.isfinite(atr[i, j]):
            continue
        stop = c[i, j] - p["stop_atr_mult"] * atr[i, j]
        e = o[i + 1, j]
        if not np.isfinite(e) or e > c[i, j] + p["do_not_buy_gap_atr"] * atr[i, j] or e <= stop:
            continue
        r = e - stop
        tg = [e + k * r for k in rs]
        hit = [None, None, None]
        stopped, days_t1 = False, None
        for k in range(i + 1, min(len(dates), i + 2 + H)):
            if not np.isfinite(l[k, j]):
                continue
            if l[k, j] <= stop:
                stopped = True
                break
            for t in range(3):
                if hit[t] is None and h[k, j] >= tg[t]:
                    hit[t] = k
                    if t == 0:
                        days_t1 = k - i
        rows.append({"date": dates[i], "t1": hit[0] is not None, "t2": hit[1] is not None, "t3": hit[2] is not None,
                     "stopped": stopped, "days_t1": days_t1})
    df = pd.DataFrame(rows).join(reg[["trend", "fear"]], on="date")
    summ = lambda g: {"signals": int(len(g)), "p_t1": round(g["t1"].mean() * 100, 1), "p_t2": round(g["t2"].mean() * 100, 1),
                      "p_t3": round(g["t3"].mean() * 100, 1), "p_stop": round(g["stopped"].mean() * 100, 1),
                      "median_days_t1": float(g["days_t1"].median()) if g["days_t1"].notna().any() else None}
    out = {"strategy": name, "targets_r": rs, "all": summ(df),
           "by_regime": {f"{a}/{b}": summ(g) for (a, b), g in df.groupby(["trend", "fear"]) if len(g) >= 30}}
    allc = json.loads(OUT.read_text()) if OUT.exists() else {}
    allc[name] = out
    OUT.write_text(json.dumps(allc, indent=1, default=str))
    log.info("Calibration for %s: %s", name, out["all"])
    return out


def for_regime(name, regime_key):
    try:
        c = json.loads(OUT.read_text())[name]
    except Exception:
        return None
    r = c["by_regime"].get(regime_key)
    base = c["all"]
    use = r if r else base
    spread = np.std([v["p_t1"] for v in c["by_regime"].values()]) if c["by_regime"] else 0
    n = use["signals"]
    conf = "HIGH" if n >= 300 and spread < 6 else "MEDIUM" if n >= 100 else "LOW"
    return {**use, "regime": regime_key if r else "all markets", "confidence": conf, "targets_r": c["targets_r"],
            "p_t1_spread_across_regimes": round(float(spread), 1)}
