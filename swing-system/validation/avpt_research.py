"""'Anchored VWAP Pullback & Target Zones [PhenLabs]' (c) PhenLabs, MPL-2.0 - rebuilt for NSE testing (LONG side).

The pasted source ended inside the trade-management step, so this is a REBUILD:
  * taken from the pasted code: ATR(14), relative activity, Kaufman efficiency (10 bars), reclaim quality score,
    pivot lows with 10 bars each side, 1.4 ATR minimum impulse, 2 pullbacks per anchor, 12-bar pullback window,
    crash guard (5-bar move > 3.6 ATR), the 6 profiles' numbers (band sigma, outer sigma, min efficiency, min quality,
    stop scale, minimum risk in ATR, relative volume), 0.20 ATR stop buffer, 1R/2R/3R targets, stop to break-even
    after TP1, 60-bar expiry
  * from the author's page (the code for it was cut off): AVWAP is volume-weighted from the confirmed swing low;
    a pullback = price trading inside AVWAP + k*sigma .. AVWAP - m*sigma; the BUY = a close back above the value band
    with a bullish body, AVWAP sloping up, efficiency and quality above the profile's minimum; stop beyond the
    deepest pullback low or the outer band minus the ATR buffer, never less than the profile's minimum risk;
    'magnet' = TP2 snaps to the impulse high when it lies between 1.5R and 3R
Two accountings: (1) REAL money - 1/3 sold at each target, break-even stop after TP1, entry at the NEXT open,
0.35% costs; (2) the indicator's own dashboard style - a trade counts as a WIN once TP1 was touched.
Usage: python validation/avpt_research.py daily|hourly
"""
import glob
import sys

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
from swing import data_prices  # noqa: E402

COST = 0.0035
SWING, MAX_PB, MIN_IMP, PB_WIN, SL_BUF, EXPIRE = 10, 2, 1.40, 12, 0.20, 60
#          name                band  outer  minEr  minQual slScale minRiskAtr minRelAct
PROFILES = [("Balanced", 1.00, 2.00, 26.0, 52.0, 1.00, 0.35, 0.00),
            ("Conservative", 0.80, 1.75, 35.0, 60.0, 1.15, 0.35, 0.00),
            ("Aggressive", 1.25, 2.30, 18.0, 44.0, 0.85, 0.30, 0.00),
            ("Shallow Pullback", 0.65, 1.60, 30.0, 55.0, 0.90, 0.30, 0.00),
            ("Deep Value Reclaim", 1.45, 2.50, 22.0, 48.0, 1.25, 0.40, 0.00),
            ("Volume Climax", 1.00, 2.00, 24.0, 58.0, 0.95, 0.32, 1.25)]


def metrics(d):
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.r_[c[0], c[:-1]]), np.abs(l - np.r_[c[0], c[:-1]])))
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values          # ta.atr = RMA
    span = np.maximum(h - l, 1e-9)
    vs = pd.Series(v).rolling(20).mean().values
    real = (v > 0) & np.isfinite(vs) & (vs > 0)
    rel = np.where(real, v / np.where(real, vs, 1), span / np.maximum(atr, 1e-9))
    act = np.clip(rel / 2, 0, 1)
    w = np.where(real, np.maximum(v, 1e-6), np.maximum(rel, 0.1))
    net = np.abs(c - np.r_[np.full(10, np.nan), c[:-10]])
    path = pd.Series(np.abs(np.diff(c, prepend=c[0]))).rolling(10).mean().values * 10
    er = np.where(path > 0, np.clip(np.nan_to_num(net) / np.where(path > 0, path, 1) * 100, 0, 100), 0)
    ern = np.clip(er / 55, 0, 1)
    share = np.clip((c - l) / span, 0, 1)
    qual = np.clip((0.40 * share + 0.35 * ern + 0.25 * act) * 100 * np.where(c > o, 1.0, 0.85), 0, 100)
    move5 = (c - np.r_[np.full(5, np.nan), c[:-5]]) / np.maximum(atr, 1e-9)
    crash = (np.nan_to_num(move5) > 3.6) & (c > o)                                 # bullCrashGuard: don't chase
    return o, h, l, c, atr, rel, w, er, qual, crash


def plans(d, prof):
    """-> list of (signal_index, stop, tp1, tp2, tp3) long plans for one profile."""
    _, band, outer, min_er, min_q, sl_scale, min_risk, min_rel = prof
    o, h, l, c, atr, rel, w, er, qual, crash = metrics(d)
    n = len(d)
    hlc3 = (h + l + c) / 3
    out = []
    anchor = None                      # dict: idx, price, sums, imp_high, armed, used, in_zone, pb_low, pb_t
    av_hist = np.full(n, np.nan)
    for t in range(2 * SWING + 1, n):
        p = t - SWING                  # pivot low at p confirmed on bar t (10 bars each side)
        if l[p] == l[p - SWING:p + SWING + 1].min() and (l[p - SWING:p] > l[p]).all():
            sw, swp, swp2 = 0.0, 0.0, 0.0
            for k in range(p, t + 1):  # reconstruct AVWAP from the true swing bar
                sw += w[k]; swp += w[k] * hlc3[k]; swp2 += w[k] * hlc3[k] ** 2
            anchor = {"idx": p, "price": l[p], "sw": sw, "swp": swp, "swp2": swp2,
                      "imp": h[p:t + 1].max(), "armed": False, "used": 0, "zone": False, "pbl": np.inf, "pbt": -1}
        elif anchor is not None:
            anchor["sw"] += w[t]; anchor["swp"] += w[t] * hlc3[t]; anchor["swp2"] += w[t] * hlc3[t] ** 2
            anchor["imp"] = max(anchor["imp"], h[t])
        if anchor is None:
            continue
        if c[t] < anchor["price"]:     # structure broken - anchor dead until the next swing low
            anchor = None
            continue
        av = anchor["swp"] / anchor["sw"]
        var = max(0.0, anchor["swp2"] / anchor["sw"] - av * av)
        bars = t - anchor["idx"] + 1
        blend = min(1.0, bars / 20)    # early bars: sigma blends with local ATR
        sd = max(np.sqrt(var) * blend + 0.5 * atr[t] * (1 - blend), 0.1 * atr[t])
        av_hist[t] = av
        if not anchor["armed"] and anchor["imp"] - anchor["price"] >= MIN_IMP * atr[t]:
            anchor["armed"] = True
        if not anchor["armed"] or anchor["used"] >= MAX_PB:
            continue
        top, bot = av + band * sd, av - outer * sd
        if l[t] <= top and c[t] >= bot:                       # trading inside the value zone
            if not anchor["zone"]:
                anchor["zone"], anchor["pbl"], anchor["pbt"] = True, l[t], t
            anchor["pbl"] = min(anchor["pbl"], l[t])
        if anchor["zone"] and t - anchor["pbt"] > PB_WIN:     # pullback too old
            anchor["zone"] = False
        reclaim = anchor["zone"] and c[t] > top and c[t] > o[t] and t > anchor["pbt"]
        if not reclaim:
            continue
        slope_ok = np.isfinite(av_hist[t - 5]) and av > av_hist[t - 5]
        ok = slope_ok and er[t] >= min_er and qual[t] >= min_q and rel[t] >= min_rel and not crash[t]
        anchor["zone"] = False
        if not ok:
            continue
        anchor["used"] += 1
        stop = min(anchor["pbl"], bot) - SL_BUF * atr[t] * sl_scale
        risk = max(c[t] - stop, min_risk * atr[t])
        stop = c[t] - risk
        tp1, tp2, tp3 = c[t] + risk, c[t] + 2 * risk, c[t] + 3 * risk
        if c[t] + 1.5 * risk <= anchor["imp"] <= c[t] + 3 * risk:   # impulse-high magnet
            tp2 = anchor["imp"]
            tp3 = max(tp3, tp2 + risk)
        out.append((t, stop, tp1, tp2, tp3))
    return out


def simulate(d, pl):
    """Real money: entry next open, 1/3 at each target, break-even after TP1, expire at 60 bars."""
    o, h, l, c = (d[k].values for k in ("open", "high", "low", "close"))
    res, busy = [], -1
    for t, stop, t1, t2, t3 in pl:
        if t <= busy or t + 1 >= len(d):
            continue
        e = o[t + 1]
        if e <= stop or e >= t1:          # gapped through the plan
            continue
        left, got, sl, hit1, j = 1.0, 0.0, stop, False, t + 1
        while j < len(d):
            if l[j] <= sl:
                got += left * (min(sl, o[j]) / e - 1); left = 0; break
            if not hit1 and h[j] >= t1:
                got += (1 / 3) * (t1 / e - 1); left -= 1 / 3; hit1 = True; sl = e
            if hit1 and left > 0.5 and h[j] >= t2:
                got += (1 / 3) * (t2 / e - 1); left -= 1 / 3
            if left > 0 and left < 0.5 and h[j] >= t3:
                got += left * (t3 / e - 1); left = 0; break
            if j - (t + 1) >= EXPIRE - 1:
                got += left * (c[j] / e - 1); left = 0; break
            j += 1
        if left > 0:
            break
        res.append((d.index[t + 1], got - COST, hit1, j - t))
        busy = j
    return res


def load(which):
    if which == "daily":
        u = pd.read_csv(f"{ROOT}/data/universe_history.csv")
        for sym in sorted(set(u[u["rank"] <= 300]["symbol"])):
            d0 = data_prices.load(sym)
            if d0 is None or len(d0) < 300:
                continue
            f = (d0["adj_close"] / d0["close"]).fillna(1.0)
            d = pd.DataFrame({"open": d0.open * f, "high": d0.high * f, "low": d0.low * f, "close": d0.adj_close,
                              "volume": d0.volume}).dropna()
            yield d[d.index >= "2012-01-01"]
    else:
        for fp in sorted(glob.glob(f"{ROOT}/data/intraday/*.csv")):
            d = pd.read_csv(fp, parse_dates=["Datetime"], index_col="Datetime").dropna()
            if len(d) >= 500:
                yield d


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "daily"
    split = "2023-11-01" if which == "daily" else "2025-06-01"
    R = {p[0]: [] for p in PROFILES}
    for d in load(which):
        if len(d) < 300:
            continue
        for p in PROFILES:
            R[p[0]].extend(simulate(d, plans(d, p)))
    rows = []
    for k, v in R.items():
        df = pd.DataFrame(v, columns=["date", "ret", "tp1", "bars"])
        if not len(df):
            continue
        ho = df[df.date >= split]
        rows.append({"profile": k, "trades": len(df), "REAL_win%": round((df.ret > 0).mean() * 100, 1),
                     "REAL_avg%": round(df.ret.mean() * 100, 2), "dashboard_win% (TP1 touched)": round(df.tp1.mean() * 100, 1),
                     "dev_avg%": round(df[df.date < split].ret.mean() * 100, 2),
                     "HOLD_win%": round((ho.ret > 0).mean() * 100, 1), "HOLD_avg%": round(ho.ret.mean() * 100, 2),
                     "bars": round(df.bars.mean(), 1)})
    out = pd.DataFrame(rows)
    print(f"== AVPT {which} ==")
    print(out.to_string(index=False))
    out.to_csv(f"{ROOT}/validation/avpt_{which}.csv", index=False)
