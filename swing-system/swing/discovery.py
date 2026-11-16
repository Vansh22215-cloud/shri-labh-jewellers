"""STRATEGY DISCOVERY ENGINE (D112) - the system invents new strategies by itself, every week, safely.

1. INVENT   ~50 building blocks (a stock among the lowest/highest 20% of the market by 1-week / 1-month / 1-year
            move, 2-day RSI, distance from its averages, 52-week high, volume surge, volatility, fear (Vix Fix),
            WaveTrend, closing strength, strength vs market; squeeze on/off; market above/below its 200-day average,
            market dipped/stretched, breadth...). Each week ~400 NEW combinations of 2-3 blocks x 3 holding periods
            (5 / 10 / 20 trading days) are generated (never the same combination twice).
2. TEST     on 13 years of the point-in-time top-300, net of 0.35% costs, only FRESH signals (first day of a run).
            A combination must pass ALL THREE separate periods - discovery 2013-2019, validation 2020-2022, and the
            last 3 years - with enough trades, >= 53% of trades in profit, a solid average, and beat the average stock
            on the same days by >= 0.7% a trade in EVERY period. Also positive in >= 70% of years.
3. PROVE    survivors become CANDIDATES: followed silently on live data every evening (shadow). After >= 20 live
            results with >= 55% in profit and a positive average -> PROMOTED: they send real tips (rank 7/10).
4. RETIRE   a promoted strategy whose live record turns negative (>= 20 tips) is retired automatically.
At most 5 candidates and 3 promoted strategies at a time; near-duplicates of existing ones are skipped.
The owner gets one Telegram message when a strategy is promoted or retired ('autopilot' label).
"""
import json
import time

import numpy as np
import pandas as pd

from .config import DATA, get_logger, load_settings

log = get_logger()
STATE_F = DATA / "discovery.json"
SHADOW_F = DATA / "discovery_shadow.csv"
COST, N_PER_WEEK = 0.0035, 400
P1, P2, P3 = ("2013-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-11-01", "2100-01-01")
RANK_FEATS = {"r5": "1-week move", "r20": "1-month move", "r60": "3-month move", "r250": "1-year move",
              "rsi2": "2-day RSI", "rsi14": "14-day RSI", "d20": "distance above its 20-day average",
              "d50": "distance above its 50-day average", "d200": "distance above its 200-day average",
              "hi52": "closeness to its 52-week high", "vratio": "volume surge (5 vs 60 days)",
              "vol20": "volatility", "wvf": "fear level (Vix Fix)", "wt1": "WaveTrend", "rngpos": "close within the "
              "day's range", "gap": "opening gap", "rs_r60": "3-month strength vs the market",
              "turnover": "traded value", "r250_20": "1-year move excluding the last month"}


def blocks():
    """name -> (description, function(P, X) -> bool array)."""
    B = {}
    for f, d in RANK_FEATS.items():
        B[f"{f}_low"] = (f"among the lowest 20% of the market by {d}", lambda P, X, f=f: (X[f] < 0.2).values)
        B[f"{f}_high"] = (f"among the highest 20% of the market by {d}", lambda P, X, f=f: (X[f] > 0.8).values)
    raw = {"sqz_on": ("price compressed (Squeeze ON)", lambda P, X: (P["sqz"] == 1).values),
           "sqz_off": ("no squeeze", lambda P, X: (P["sqz"] == 0).values),
           "mkt_up": ("Nifty above its 200-day average", lambda P, X: (P["n_up200"] == 1).values),
           "mkt_down": ("Nifty below its 200-day average", lambda P, X: (P["n_up200"] == 0).values),
           "mkt_dip": ("Nifty dipped (2-day RSI < 20)", lambda P, X: (P["n_rsi2"] < 20).values),
           "mkt_hot": ("Nifty stretched (2-day RSI > 80)", lambda P, X: (P["n_rsi2"] > 80).values),
           "breadth_hi": ("most stocks above their 50-day average", lambda P, X: (P["breadth"] > 0.6).values),
           "breadth_lo": ("few stocks above their 50-day average", lambda P, X: (P["breadth"] < 0.4).values),
           "uptrend": ("stock above its 200-day average", lambda P, X: (P["d200"] > 0).values),
           "near_high": ("within 5% of its 52-week high", lambda P, X: (P["hi52"] > -0.05).values),
           "down4": ("down 4+ of the last 5 days", lambda P, X: (P["dn_days"] >= 4).values)}
    B.update(raw)
    return B


def family_of(name):
    return name.rsplit("_", 1)[0] if name.split("_")[0] in RANK_FEATS or name.startswith("r250_20") else name


def describe(c):
    B = blocks()
    return " + ".join(B[b][0] for b in c["blocks"]) + f"; buy next open, sell after {c['hold']} trading days"


def _state():
    try:
        return json.loads(STATE_F.read_text())
    except Exception:
        return {"tested": [], "candidates": [], "promoted": [], "retired": [], "last_search": None, "next_id": 1}


def _save(s):
    STATE_F.write_text(json.dumps(s, indent=1, default=str))


def _key(blks, hold):
    return "|".join(sorted(blks)) + f"@{hold}"


def generate(n, tested, seed):
    rng = np.random.default_rng(seed)
    names = list(blocks())
    out, seen = [], set(tested)
    tries = 0
    while len(out) < n and tries < n * 50:
        tries += 1
        k = int(rng.choice([2, 3], p=[0.6, 0.4]))
        b = list(rng.choice(names, size=k, replace=False))
        fams = [family_of(x) for x in b]
        if len(set(fams)) < k:
            continue
        hold = int(rng.choice([5, 10, 20]))
        key = _key(b, hold)
        if key in seen:
            continue
        seen.add(key)
        out.append({"blocks": sorted(b), "hold": hold, "key": key})
    return out


def _fresh(mask, prev_idx):
    prev = np.where(prev_idx >= 0, mask[np.clip(prev_idx, 0, None)], False)
    return mask & ~prev


def evaluate(P, X, cands, prev_idx, dates, day_mean):
    """-> list of (candidate, stats) for those passing every gate."""
    B = blocks()
    cache = {}
    passed = []
    yrs = dates.dt.year.values
    for c in cands:
        m = np.ones(len(P), bool)
        for b in c["blocks"]:
            if b not in cache:
                cache[b] = np.nan_to_num(B[b][1](P, X)).astype(bool)
            m &= cache[b]
        m = _fresh(m, prev_idx)
        fwd = P[f"fwd{c['hold']}" if c["hold"] != 10 else "fwd"].values
        ok = m & np.isfinite(fwd)
        if ok.sum() < 300:
            continue
        r = fwd[ok] - COST
        ex = fwd[ok] - day_mean[c["hold"]][ok]
        d = dates.values[ok]
        st = {}
        good = True
        for nm, (a, b), need_n, need_win, need_avg in (("discovery", P1, 150, 53, 1.0), ("validation", P2, 50, 53, 0.8),
                                                       ("recent", P3, 30, 53, 0.5)):
            sel = (d >= np.datetime64(a)) & (d <= np.datetime64(b))
            n = int(sel.sum())
            if n < need_n:
                good = False
                break
            w, av, xs = float((r[sel] > 0).mean() * 100), float(r[sel].mean() * 100), float(ex[sel].mean() * 100)
            st[nm] = {"n": n, "win": round(w, 1), "avg": round(av, 2), "excess": round(xs, 2)}
            if w < need_win or av < need_avg or xs < 0.7:     # must BEAT the average stock in every period
                good = False
                break
        if not good:
            continue
        yy = pd.Series(r).groupby(yrs[ok]).mean()
        if (yy > 0).mean() < 0.7:
            continue
        st["years_positive"] = f"{int((yy > 0).sum())}/{len(yy)}"
        st["all"] = {"n": int(ok.sum()), "win": round(float((r > 0).mean() * 100), 1), "avg": round(float(r.mean() * 100), 2)}
        passed.append((c, st, m))
    return passed


def search(now=None, n=N_PER_WEEK):
    """Weekly: invent + test new combinations; add the best survivors as live candidates."""
    from .ml_ranker import panel
    t0 = time.time()
    s = _state()
    P, X = panel()
    P = P.reset_index(drop=True)
    X = X.reset_index(drop=True)
    order = np.lexsort((P["date"].values, P["sym"].values))
    prev_idx = np.full(len(P), -1)
    so = P["sym"].values[order]
    same = np.r_[False, so[1:] == so[:-1]]
    prev_idx[order[1:]] = np.where(same[1:], order[:-1], -1)
    dates = pd.to_datetime(P["date"])
    day_mean = {h: P.groupby("date")[f"fwd{h}" if h != 10 else "fwd"].transform("mean").values for h in (5, 10, 20)}
    seed = int(pd.Timestamp(now or pd.Timestamp.now()).strftime("%Y%W"))
    if not s["tested"]:
        n = max(n, 1500)                         # first search: a bigger first sweep
    cands = generate(n, s["tested"], seed)
    passed = evaluate(P, X, cands, prev_idx, dates, day_mean)
    s["tested"] = (s["tested"] + [c["key"] for c in cands])[-20000:]
    active = s["candidates"] + s["promoted"]
    masks = {}
    added = []
    for c, st, m in sorted(passed, key=lambda x: -x[1]["recent"]["avg"]):
        if len(s["candidates"]) >= 5:
            break
        dup = False
        for a in active + added:      # near-duplicate: shares most blocks with an existing one
            if len(set(a["blocks"]) & set(c["blocks"])) >= max(2, len(c["blocks"]) - 0):
                dup = True
                break
        if dup:
            continue
        c = dict(c, id=f"S{s['next_id']}", stats=st, found=str(pd.Timestamp.now().date()), status="candidate",
                 text=describe(c))
        s["next_id"] += 1
        s["candidates"].append(c)
        added.append(c)
        masks[c["id"]] = m
    s["last_search"] = str(pd.Timestamp(now or pd.Timestamp.now()).date())
    s["last_result"] = {"tested": len(cands), "passed": len(passed), "added": len(added),
                        "seconds": round(time.time() - t0)}
    _save(s)
    log.info("Discovery: %d new combinations tested, %d passed all 3 periods, %d new candidate(s) (%.0fs)",
             len(cands), len(passed), len(added), time.time() - t0)
    return s


def maybe_search(now=None, every_days=7):
    s = _state()
    last = s.get("last_search")
    if last and (pd.Timestamp(now or pd.Timestamp.now()) - pd.Timestamp(last)).days < every_days:
        return None
    return search(now)


def _today():
    """Today's cross-section (same features as the panel) -> P, X with close/atr for the top-300."""
    from .high_prob import universe
    from .ml_ranker import _adjusted, _finish, _market, features
    rows = []
    for sym in universe():
        d = _adjusted(sym)
        if d is None:
            continue
        f = features(d).iloc[[-1]].copy()
        f["sym"], f["close"] = sym, float(d["raw_close"].iloc[-1])
        f["atr_raw"] = float(f["atr"].iloc[0]) * f["close"].iloc[0] / float(d["close"].iloc[-1])
        rows.append(f)
    P = pd.concat(rows)
    P.index.name = "date"
    P = P.reset_index()
    P["date"] = P["date"].max()
    P, X = _finish(P, _market())
    return P.reset_index(drop=True), X.reset_index(drop=True)


def _notify(text):
    try:
        from . import telegram
        telegram.send(load_settings(), text, label="autopilot")
    except Exception:
        pass


def evening(day, settings=None):
    """Every evening: record candidates' signals (shadow), settle due shadow results, promote / retire, and send
    promoted strategies' tips. Returns the number of real tips sent."""
    s = _state()
    strategies = s["candidates"] + s["promoted"]
    if not strategies:
        return 0
    settings = settings or load_settings()
    P, X = _today()
    B = blocks()
    sh = pd.read_csv(SHADOW_F) if SHADOW_F.exists() else pd.DataFrame(
        columns=["sid", "sym", "day", "entry", "hold", "status", "result"])
    px = dict(zip(P["sym"], P["close"]))
    # settle shadow results that are due (hold trading days ~ calendar days x 7/5)
    for i, r in sh[sh["status"] == "open"].iterrows():
        if (pd.Timestamp(day) - pd.Timestamp(r["day"])).days >= int(r["hold"]) * 7 / 5 + 1 and r["sym"] in px:
            sh.loc[i, "result"] = round((px[r["sym"]] / float(r["entry"]) - 1 - COST) * 100, 2)
            sh.loc[i, "status"] = "closed"
    sent = 0
    for c in strategies:
        m = np.ones(len(P), bool)
        for b in c["blocks"]:
            m &= np.nan_to_num(B[b][1](P, X)).astype(bool)
        hits = P.loc[m, ["sym", "close", "atr_raw"]]
        for _, h in hits.iterrows():
            if not ((sh["sid"] == c["id"]) & (sh["sym"] == h["sym"]) & (sh["status"] == "open")).any():
                sh = pd.concat([sh, pd.DataFrame([{"sid": c["id"], "sym": h["sym"], "day": str(day), "entry": h["close"],
                                                    "hold": c["hold"], "status": "open", "result": None}])],
                               ignore_index=True)
                if c["status"] == "promoted":
                    sent += _send_tip(c, h, day, settings)
    sh.tail(50000).to_csv(SHADOW_F, index=False)
    _review(s, sh)
    return sent


def _review(s, sh):
    """Promote candidates that proved themselves live; retire candidates / promoted ones that failed."""
    closed = sh[sh["status"] == "closed"]
    keep_c = []
    for c in s["candidates"]:
        g = closed[closed["sid"] == c["id"]]
        n, win, avg = len(g), (g["result"] > 0).mean() * 100 if len(g) else 0, g["result"].mean() if len(g) else 0
        if n >= 20 and win >= 55 and avg > 0 and len(s["promoted"]) < 3:
            c["status"], c["promoted_on"] = "promoted", str(pd.Timestamp.now().date())
            c["live"] = {"n": n, "win": round(win, 1), "avg": round(avg, 2)}
            s["promoted"].append(c)
            _notify(f"🧪 New strategy PROMOTED by the system: {c['id']} - {c['text']}.\nTested 13 years: "
                    f"{c['stats']['all']['win']}% in profit, avg {c['stats']['all']['avg']:+.2f}%; live (silent) "
                    f"record: {n} trades, {win:.0f}% in profit, avg {avg:+.2f}%. It now sends 'Discovered strategy' "
                    "tips (rank 7/10).")
        elif n >= 30 and (avg <= 0 or win < 50):
            c["status"] = "retired"
            s["retired"].append(c)
        else:
            keep_c.append(c)
    s["candidates"] = keep_c
    keep_p = []
    for c in s["promoted"]:
        g = closed[(closed["sid"] == c["id"]) & (pd.to_datetime(closed["day"]) >= pd.Timestamp(c.get("promoted_on", "2000-01-01")))]
        if len(g) >= 20 and g["result"].mean() < 0:
            c["status"] = "retired"
            s["retired"].append(c)
            _notify(f"🧪 Strategy {c['id']} RETIRED by the system - its last {len(g)} live trades averaged "
                    f"{g['result'].mean():+.2f}%. ({c['text']})")
        else:
            keep_p.append(c)
    s["promoted"] = keep_p
    s["retired"] = s["retired"][-200:]
    _save(s)


def _send_tip(c, h, day, settings):
    from .live_engine import already, save_tip, send, tv_link
    if already(h["sym"], "NORMAL", str(day)):
        return 0
    cap = float(settings.get("capital", 45000))
    stop = round(h["close"] - 4 * h["atr_raw"], 2)
    qty = int(min(cap * 0.01 / max(1e-9, h["close"] - stop), cap * 0.25 / h["close"]))
    if qty < 1:
        return 0
    st = c["stats"]["all"]
    send(f"• Discovered strategy {c['id']} (found and proven by the system itself)\n\n"
         f"Buy #{h['sym']} at the next market open ≈ {h['close']:,.2f} 📊\n\nSL at {stop:,.2f} ❗️ (wide safety stop)\n\n"
         f"Exit: sell after {c['hold']} trading days - I'll alert you\n\n1% Risk\n\n"
         f"⭐ RANK - 7/10 · Qty {qty} · Rule: {c['text']}. Tested 13 years: {st['win']}% in profit, avg "
         f"{st['avg']:+.2f}%; live record {c.get('live', {}).get('win', '-')}% in profit.\n\n"
         f"{tv_link(h['sym'], daily=True)}")
    save_tip({"time": str(pd.Timestamp.now(tz='Asia/Kolkata').tz_localize(None))[:16], "type": "NORMAL",
              "symbol": h["sym"], "side": "buy", "entry": h["close"], "stop": stop, "targets": "", "rank": 7,
              "qty": qty, "status": "open", "hit": 0, "day": str(day), "setup": f"D{c['id']}:{c['hold']}"})
    return 1


def evening_exits(day):
    """Promoted strategies' tips: sell after their holding period."""
    from .autopilot import close_tip
    from .live_engine import _LOCK, TIPS_F, load_tips, send
    from .ml_ranker import _adjusted
    msgs = []
    with _LOCK:
        t = load_tips()
        if not len(t) or "setup" not in t:
            return msgs
        for i, r in t[(t["status"] == "open") & t["setup"].astype(str).str.startswith("DS")].iterrows():
            hold = int(str(r["setup"]).split(":")[-1])
            d = _adjusted(r["symbol"])
            if d is None:
                continue
            if len(d[d.index > pd.Timestamp(str(r["day"]))]) >= hold:
                raw = float(d["raw_close"].iloc[-1])
                close_tip(t, i, "time", raw)
                msgs.append(f"⌛ #{r['symbol']} (discovered strategy) - {hold} trading days done: sell at the next market "
                            f"open (now {raw:,.2f}, {(raw / float(r['entry']) - 1) * 100:+.1f}%).")
        t.to_csv(TIPS_F, index=False)
    for m in msgs:
        send(m, label="exit alert")
    return msgs
