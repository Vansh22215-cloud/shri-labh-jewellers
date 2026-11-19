"""THE LEARNER (owner 18 Nov: "two things simultaneously: one finds trades, the other tracks every trade given and we
learn from them - what's right, what's wrong, when it works and when not").

Runs every evening after swing/tracker.py (which follows every idea from every source). For every idea it adds:
  - the SITUATION on the day it was sent (only facts known that day): market trend (NIFTY vs its 200-day average),
    market mood (NIFTY 20-day swings vs its own past year), stock liquidity, distance from the 52-week high, company
    results within 5 trading days, weekday;
  - the JOURNEY: best and worst point since buying (MFE / MAE), result in units of risk (R).
Then it judges:
  1. EXPECTED vs LIVE per tip type, against the 13-year test (vantage-ai/validation/tested_profile.json): a win rate or
     average outside the 90% expected range after enough closed tips -> "below/above expected"; open tips already
     deeper than the tested worst-10% -> early warning;
  2. WHEN it works / when not: every situation bucket per source, with counts;
  3. LESSONS: bucket gaps big enough to matter become research items (journal/learning_queue.csv) - never a change
     to live tips (only tested + owner-approved changes reach the tips).
Outputs (saved to GitHub for the research): journal/all_tips.csv (enriched), journal/learning.md, learning_queue.csv.
Owner: a short plain "weekly learning" message on Saturdays; an instant message only when a tip type is clearly
below expectation (once per type and level). Market ideas only - no owner money/quantities/holdings."""
import json
import math

import numpy as np
import pandas as pd

from .config import PRIVATE, ROOT, DATA, get_logger

log = get_logger()
J = ROOT / "journal"
MD, QUEUE = J / "learning.md", J / "learning_queue.csv"
PROFILE = ROOT.parent / "vantage-ai" / "validation" / "tested_profile.json"
CENSUS = ROOT.parent / "vantage-ai" / "validation" / "mistake_census.json"
MEMORY = ROOT.parent / "vantage-ai" / "validation" / "situation_memory.json"
BELIEFS = ROOT.parent / "vantage-ai" / "validation" / "beliefs.json"
EXPERIMENTS = ROOT.parent / "vantage-ai" / "validation" / "experiments.json"
STATE = PRIVATE / "learning_state.json"
TYPE_MAP = {"VANTAGE Rolling Candle Profile": "RCP", "VANTAGE Breakout": "Breakout", "VANTAGE Dip-buy A": "Dip-buy A",
            "VANTAGE Dip-buy B": "Dip-buy B", "VANTAGE Dip-buy C": "Dip-buy C"}
MIN_CLOSED, MIN_BUCKET = 20, 10
MIN_SIGN = 2                    # owner 18 Nov: "bare minimum - we can't wait": a cause seen twice is already a lesson


def evidence(n):
    return "strong" if n >= 10 else "medium" if n >= 5 else "weak"
_LAST = (pd.DataFrame(), [], pd.DataFrame(), [])
_OPP = []
BR, TODAY_KEY = None, None
_CHECKS = []
_MISSED = []
_MISSED_N = 0


def profile():
    try:
        return json.loads(PROFILE.read_text()).get("holdout", {})
    except Exception:
        return {}


def _breadth(load, days=420):
    """Share of the 300 most-traded stocks above their 200-day average, per day (market memory)."""
    try:
        u = pd.read_csv(DATA / "universe_history.csv")
        syms = u[u["asof"] == u["asof"].max()].nsmallest(300, "rank")["symbol"].astype(str)
    except Exception:
        return None
    cols = {}
    for sym in syms:
        d = load(sym)
        if d is not None and len(d) > 220:
            c = d["close"].astype(float).tail(days + 200)
            cols[sym] = c > c.rolling(200).mean()
    if not cols:
        return None
    A = pd.DataFrame(cols).sort_index().tail(days)
    return A.mean(axis=1)


def situation_key(trend_up, jumpy, breadth):
    b = "weak" if breadth < 0.4 else "middle" if breadth <= 0.6 else "strong"
    return f"{'rising' if trend_up else 'falling'} | {'jumpy' if jumpy else 'calm'} | breadth {b}"


def memory_line(key):
    try:
        m = json.loads(MEMORY.read_text()).get(key)
    except Exception:
        m = None
    if not m:
        return f"{key}: no memory yet"
    a = m["all"]
    types = "; ".join(f"{t} {v['avg_pct']:+.1f}% (n={v['n']})" for t, v in m.items() if t not in ("all", "days_in_13y"))
    return (f"{key} - in 13 years VANTAGE tips on such days ({m['days_in_13y']} days) averaged {a['avg_pct']:+.1f}%, "
            f"won {a['win_pct']:.0f}% ({a['n']} tips); by type: {types}" + (" - the best kind of day in the test (both periods)"
                                                        if key == "falling | jumpy | breadth weak" else ""))


def _market(load):
    n = load("NIFTY50")
    if n is None or not len(n):
        return None
    c = n["close"].astype(float)
    vol = c.pct_change().rolling(20).std()
    return pd.DataFrame({"trend_up": c > c.rolling(200).mean(),
                         "vol_high": vol > vol.rolling(250, min_periods=120).quantile(0.8)})


def _results_days(sym, day):
    try:
        from .vantage import results_soon
        return results_soon(sym, pd.Timestamp(day)) is not None
    except Exception:
        return None


def enrich(R, load):
    """Adds situation + journey columns (no look-ahead: situation uses data up to the signal day only)."""
    if not len(R):
        return R
    R = R.drop(columns=[c for c in ENRICHED if c in R.columns])     # a re-run replaces, never duplicates, these columns
    M = _market(load)
    global BR, TODAY_KEY
    BR = _breadth(load)
    TODAY_KEY = None
    if M is not None and BR is not None and len(M) and len(BR):
        TODAY_KEY = situation_key(M["trend_up"].iloc[-1], M["vol_high"].iloc[-1], float(BR.iloc[-1]))
    rows = []
    for r in R.itertuples():
        x = {}
        d = load(r.symbol)
        day = pd.Timestamp(str(r.date)[:10])
        if M is not None:
            m = M[M.index <= day]
            if len(m):
                x["market"] = "rising" if bool(m["trend_up"].iloc[-1]) else "falling"
                x["market_mood"] = "jumpy" if bool(m["vol_high"].iloc[-1]) else "calm"
                if BR is not None:
                    br = BR[BR.index <= day]
                    if len(br):
                        x["day_type"] = situation_key(m["trend_up"].iloc[-1], m["vol_high"].iloc[-1], float(br.iloc[-1]))
        if d is not None and len(d):
            h = d[d.index <= day]
            if len(h) >= 20:
                turn = float((h["close"] * h["volume"]).tail(20).mean()) / 1e7
                x["liquidity"] = "under 10 cr" if turn < 10 else "10-50 cr" if turn < 50 else "over 50 cr"
                hi = float(h["high"].tail(252).max())
                dist = float(h["close"].iloc[-1]) / hi - 1
                x["from_52w_high"] = "within 5%" if dist > -0.05 else "5-15% below" if dist > -0.15 else "15%+ below"
            e = getattr(r, "entry", None)
            if e == e and e and str(r.status) in ("open", "closed"):
                ed = pd.Timestamp(str(r.entry_date)[:10]) if str(r.entry_date) not in ("nan", "") else day
                xd = pd.Timestamp(str(r.exit_date)[:10]) if str(getattr(r, "exit_date", "nan")) not in ("nan", "") else d.index[-1]
                # bought at the signal day's close (VANTAGE) -> only the days AFTER count; zone tips: from the entry day
                w = d[((d.index > ed) if str(r.source) == "VANTAGE" else (d.index >= ed)) & (d.index <= xd)]
                if len(w):
                    x["best_pct"] = round((float(w["high"].max()) / e - 1) * 100, 2)
                    x["worst_pct"] = round((float(w["low"].min()) / e - 1) * 100, 2)
                st = getattr(r, "stop", None)
                if st == st and st and e > st and r.result_pct == r.result_pct:
                    x["result_R"] = round(r.result_pct / ((e - st) / e * 100), 2)
            # OPPORTUNITY COST (owner 18 Nov): what else the same money could have done over the same days
            if e == e and e and str(r.status) in ("open", "closed") and r.result_pct == r.result_pct:
                n = load("NIFTY50")
                if n is not None and len(n):
                    a = pd.Timestamp(str(r.entry_date)[:10]) if str(r.entry_date) not in ("nan", "") else day
                    b = pd.Timestamp(str(r.exit_date)[:10]) if str(getattr(r, "exit_date", "nan")) not in ("nan", "", "None") else n.index[-1]
                    w = n[(n.index >= a) & (n.index <= b)]["close"]
                    if len(w) >= 2:
                        x["nifty_same_days_pct"] = round((float(w.iloc[-1]) / float(w.iloc[0]) - 1) * 100, 2)
                        x["vs_nifty_pct"] = round(r.result_pct - x["nifty_same_days_pct"], 2)
                dv = getattr(r, "days", None)
                dd = max(1, int(dv)) if dv == dv and dv else 1
                x["per_day_pct"] = round(r.result_pct / dd, 3)
        x["results_week"] = "yes" if _results_days(r.symbol, day) else "no"
        x["weekday"] = day.strftime("%a")
        rows.append(x)
    return pd.concat([R.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


# ============================================================================== MISTAKES (owner 18 Nov: "how we learn
# from our mistakes is more important than the trade we find") - every losing / weak idea gets a plain diagnosis.
CODES = {
    "never_worked": "Never worked - it never rose meaningfully above the buy price (a selection mistake)",
    "gave_back": "Gave back a profit - it was up 3%+ and then turned into a loss (an exit mistake)",
    "fast_stop": "Stopped out within 3 days (timing / normal noise)",
    "gap_through_stop": "Opened below the stop-loss - the loss was bigger than planned (overnight risk)",
    "market_fell": "The whole market fell 3%+ during the trade (not the stock's fault)",
    "results_shock": "Company results came during the trade and hit the price",
    "slow_bleed": "Drifted down slowly (no clear cause)",
}


# Causes already researched on 13 years: a lesson about them says so instead of asking for the same test again.
TESTED = {"gave_back": "tested twice (rounds 1 E1 and 20): break-even stops cost more than they save - the price of "
                       "letting winners run",
          "market_fell": "tested (rounds 6, 8, 12, 19 and the market-break exit): no rule helped",
          "results_shock": "tested (round 2 R4 -> half quantity before results, live; selling before results did not help)",
          "fast_stop": "tested (round 18): tighter stops made it worse"}


def _nifty_move(load, a, b):
    n = load("NIFTY50")
    if n is None or not len(n):
        return None
    w = n[(n.index >= pd.Timestamp(a)) & (n.index <= pd.Timestamp(b))]["close"]
    return float(w.iloc[-1] / w.iloc[0] - 1) if len(w) >= 2 else None


def _results_inside(sym, a, b):
    import glob
    from .config import DATA as _D
    f = _D / "events" / "earnings" / f"{sym}.csv"
    if not f.exists():
        return False
    try:
        d = pd.to_datetime(pd.read_csv(f)["date"], errors="coerce").dropna()
        return bool(((d > pd.Timestamp(a)) & (d <= pd.Timestamp(b))).any())
    except Exception:
        return False


def diagnose(r, load):
    """-> (code, plain line) for an idea that lost money (closed) or is down 3%+ (open); ('', '') otherwise."""
    res = r.get("result_pct")
    if res != res or res is None or str(r.get("status")) not in ("open", "closed"):
        return "", ""
    if not ((r["status"] == "closed" and res <= 0) or (r["status"] == "open" and res <= -3)):
        return "", ""
    a = str(r.get("entry_date") or r.get("date"))[:10]
    b = str(r.get("exit_date"))[:10] if str(r.get("exit_date")) not in ("nan", "", "None") else str(pd.Timestamp.now().date())
    best, days = r.get("best_pct"), r.get("days")
    mkt = _nifty_move(load, a, b)
    stopped = "stop" in str(r.get("why", "")).lower()               # "stop-loss", "Stop-loss (live)", "Stop-loss"
    if r["status"] == "closed" and stopped and r.get("stop") == r.get("stop") \
            and r.get("exit") == r.get("exit") and r["exit"] < r["stop"] * 0.995:
        code = "gap_through_stop"
    elif _results_inside(r["symbol"], a, b) and res <= -3:
        code = "results_shock"
    elif mkt is not None and mkt <= -0.03:
        code = "market_fell"
    elif best == best and best is not None and best >= 3:
        code = "gave_back"
    elif r["status"] == "closed" and stopped and days == days and days is not None and days <= 3:
        code = "fast_stop"
    elif best == best and best is not None and best < 1:
        code = "never_worked"
    else:
        code = "slow_bleed"
    tag = "" if str(r.get("sent")) in ("sent", "nan", "None") else f", {r.get('sent')}"
    line = (f"{r['symbol']} ({r['source']}{tag}, {str(r['date'])[:10]}): {res:+.1f}%"
            + (f", best point {best:+.1f}%" if best == best and best is not None else "")
            + (f", market {mkt * 100:+.1f}%" if mkt is not None else "") + f" -> {CODES[code]}")
    return code, line


def what_if(r, load):
    """Simple counterfactuals for one bought idea (information only, never a rule):
    - sold at its best point would have been +X% (how much an exit rule could save at most);
    - a target at +10% would have been reached or not."""
    best = r.get("best_pct")
    if best != best or best is None:
        return {}
    return {"reached_plus10": bool(best >= 10), "max_possible_pct": round(best, 2)}


def mistakes(R, load):
    rows, lines = [], []
    for r in R.to_dict("records"):
        code, line = diagnose(r, load)
        if code:
            rows.append({"source": r["source"], "type": r["type"], "symbol": r["symbol"], "date": r["date"], "code": code,
                         "result_pct": r["result_pct"]})
            lines.append(line)
    M = pd.DataFrame(rows)
    return M, lines


def repeats(R):
    """The same stock sent again and again (several channels or days) - concentration and repeat-mistake risk."""
    B = R[R["source"].isin(["strategy tip", "strategy tip (retired list)", "hourly scan", "VANTAGE", "live engine", "ATLAS strategy"])]
    if "sent" in B:
        B = B[B["sent"].astype(str) == "sent"]                   # only what actually reached the owner
    g = B.groupby("symbol").agg(times=("symbol", "size"), sources=("source", lambda x: ", ".join(sorted(set(x)))),
                                avg=("result_pct", "mean")).reset_index()
    return g[g["times"] >= 3].sort_values("times", ascending=False)


def skipped_review(R, load):
    """Ideas skipped because they opened outside the buy zone: winners missed or losses avoided?"""
    S = R[R["status"].astype(str).str.startswith("skipped")]
    out = []
    for r in S.itertuples():
        d = load(r.symbol)
        if d is None:
            continue
        p0 = d[d.index > pd.Timestamp(str(r.date)[:10])]
        if len(p0):
            out.append((r.symbol, r.source, round((float(d["close"].iloc[-1]) / float(p0["open"].iloc[0]) - 1) * 100, 2)))
    return out


def missed_movers(R, load, days=20, top=20):
    """ATLAS opportunity intelligence: the biggest risers of the last `days` trading days among stocks trading
    >= Rs 2 cr/day - which did the system tip, and what did the missed ones look like when the rise began?"""
    try:
        from .vantage import symbols
        syms = symbols()
    except Exception:
        return []
    rows = []
    for sym in syms:
        d = load(sym)
        if d is None or len(d) < 260:
            continue
        c, v, h = d["close"].astype(float), d["volume"].astype(float), d["high"].astype(float)
        k0 = len(c) - 1 - days
        turn = float((c * v).iloc[k0 - 20:k0].mean())
        if turn < 2e7 or c.iloc[k0] <= 0:
            continue
        rows.append({"symbol": sym, "rise_pct": (c.iloc[-1] / c.iloc[k0] - 1) * 100, "start": str(c.index[k0].date()),
                     "ret6m_at_start": (c.iloc[k0] / c.iloc[max(0, k0 - 126)] - 1) * 100,
                     "from_high_at_start": (c.iloc[k0] / h.iloc[max(0, k0 - 251):k0 + 1].max() - 1) * 100})
    if not rows:
        return []
    M = pd.DataFrame(rows).sort_values("rise_pct", ascending=False).head(top)
    start = pd.Timestamp(M["start"].iloc[0]) - pd.Timedelta(days=10)
    tipped = set(R.loc[pd.to_datetime(R["date"], errors="coerce") >= start, "symbol"].astype(str))
    sent = set(R.loc[(pd.to_datetime(R["date"], errors="coerce") >= start) & (R.get("sent", "") == "sent"), "symbol"].astype(str)) \
        if "sent" in R else tipped
    M["tipped"] = [("sent" if s in sent else "recorded/blocked/rejected" if s in tipped else "missed") for s in M["symbol"]]
    miss = M[M["tipped"] == "missed"]
    global _MISSED_N
    _MISSED_N = len(miss)
    L = [f"- Top {len(M)} risers of the last {days} trading days (stocks >= Rs 2 cr/day): {int((M['tipped'] == 'sent').sum())} "
         f"were sent to you, {int((M['tipped'] != 'missed').sum() - (M['tipped'] == 'sent').sum())} were seen but not sent, "
         f"{len(miss)} were never detected"]
    if len(miss):
        L.append(f"- Missed ones at the start of their rise: 6-month return median {miss['ret6m_at_start'].median():+.0f}%, "
                 f"{miss['from_high_at_start'].median():+.0f}% from the 52-week high (VANTAGE usually picks strong stocks "
                 "near their highs - missed risers far from highs are a different kind of opportunity)")
        L.append("- Missed: " + ", ".join(f"{r.symbol} +{r.rise_pct:.0f}%" for r in miss.head(8).itertuples()))
    return L


def belief_checks(R, E):
    """ATLAS input: each belief's live check -> (id, belief, status, detail). status: holding / at risk / broken /
    waiting (not enough live data yet)."""
    try:
        B = json.loads(BELIEFS.read_text())["beliefs"]
    except Exception:
        return []
    V = R[(R["source"] == "VANTAGE") & R["status"].isin(["open", "closed"])]
    C = V[V["status"] == "closed"]
    out = []
    for b in B:
        st, det = "no live check", ""
        k = b.get("check")
        if k == "vantage_vs_nifty":
            x = C["vs_nifty_pct"].dropna() if "vs_nifty_pct" in C else pd.Series(dtype=float)
            st, det = ("waiting", f"{len(x)} of 30 closed") if len(x) < 30 else \
                (("holding" if (x > 0).mean() >= 0.5 else "broken"), f"{(x > 0).mean() * 100:.0f}% beat NIFTY")
        elif k == "next_open_gap":
            x = V["next_open_vs_buy_pct"].dropna() if "next_open_vs_buy_pct" in V else pd.Series(dtype=float)
            st, det = ("waiting", f"{len(x)} of 30 tips") if len(x) < 30 else \
                (("holding" if x.mean() >= 0 else "at risk"), f"next open {x.mean():+.2f}% vs the 3:20 pm price")
            if 0 < len(x) < 30:
                det += f" (so far {x.mean():+.2f}%)"
        elif k == "add_more":
            a = C[C.get("added", pd.Series(index=C.index, dtype=str)).astype(str) == "yes"] if "added" in C else C.iloc[0:0]
            n = C.drop(a.index)
            st, det = ("waiting", f"{len(a)} of 10 add-ons closed") if len(a) < 10 else \
                (("holding" if a["result_pct"].mean() > n["result_pct"].mean() else "at risk"),
                 f"with {a['result_pct'].mean():+.2f}% vs without {n['result_pct'].mean():+.2f}%")
        elif k == "results_week":
            y = C[C.get("results_week", pd.Series(index=C.index, dtype=str)) == "yes"] if "results_week" in C else C.iloc[0:0]
            st, det = ("waiting", f"{len(y)} of 20") if len(y) < 20 else \
                (("holding" if y["result_pct"].mean() < C.drop(y.index)["result_pct"].mean() else "at risk"),
                 f"results-week {y['result_pct'].mean():+.2f}% vs others {C.drop(y.index)['result_pct'].mean():+.2f}%")
        elif k == "panic_days":
            y = V[V.get("day_type", pd.Series(index=V.index, dtype=str)) == "falling | jumpy | breadth weak"] if "day_type" in V else V.iloc[0:0]
            st, det = ("waiting", f"{len(y)} of 10 panic-day tips") if len(y) < 10 else \
                (("holding" if y["result_pct"].mean() >= V.drop(y.index)["result_pct"].mean() else "at risk"),
                 f"panic days {y['result_pct'].mean():+.2f}% vs others {V.drop(y.index)['result_pct'].mean():+.2f}%")
        elif k in ("rejected_thin", "blocked"):
            src = "rejected by VANTAGE" if k == "rejected_thin" else "blocked repeat"
            y = R[R["source"] == src]
            need = 20 if k == "rejected_thin" else 10
            st, det = ("waiting", f"{len(y)} of {need}") if len(y) < need else \
                (("holding" if y["result_pct"].mean() <= V["result_pct"].mean() + 1 else "at risk"),
                 f"{src} {y['result_pct'].mean():+.2f}% vs sent {V['result_pct'].mean():+.2f}%")
        elif k == "expectation":
            bad = [x for x in E if x[1] == "below expected"]
            st, det = ("broken", "; ".join(x[0] for x in bad)) if bad else ("holding", "no type below its tested range")
        out.append((b["id"], b["belief"], b["level"], st, det, b["wrong_if"]))
    return out


def daily_question(checks):
    """ATLAS: 'What do we currently believe that might be wrong, and what experiment could prove us wrong?'"""
    order = {"broken": 0, "at risk": 1, "waiting": 2, "holding": 3, "no live check": 4}
    weak = sorted(checks, key=lambda c: (order.get(c[3], 5), 0 if "assumption" in c[2] else 1))
    if not weak:
        return ""
    c = weak[0]
    return f"Could we be wrong that \"{c[1]}\" ({c[2]}, live: {c[3]}{' - ' + c[4] if c[4] else ''})? It is wrong if {c[5]}."


def scorecard(R, E, checks):
    """ATLAS 'is the system getting smarter?' scorecard."""
    L = []
    try:
        X = json.loads(EXPERIMENTS.read_text())
        L.append(f"- Discovery productivity: {X['count']} ideas tested, {X['passed']} passed "
                 f"({X['passed'] / max(1, X['count']) * 100:.0f}%) - failures are kept so none is retested blindly")
    except Exception:
        pass
    V = R[(R["source"] == "VANTAGE") & (R["status"] == "closed")]
    if len(V) and "likely_pct" in V:
        pass
    if len(V) >= 5:
        L.append(f"- Calibration: closed VANTAGE tips won {(V['result_pct'] > 0).mean() * 100:.0f}% ({len(V)} tips) vs "
                 "the 46-80% the messages say by type")
    if "next_open_vs_buy_pct" in R:
        x = R["next_open_vs_buy_pct"].dropna()
        if len(x):
            L.append(f"- Execution: the next morning opened {x.mean():+.2f}% vs the 3:20 pm buy price on average ({len(x)} tips)")
    for src in ("rejected by VANTAGE", "blocked repeat"):
        y = R[R["source"] == src]
        if len(y):
            L.append(f"- Opportunity capture: {src} ideas {y['result_pct'].mean():+.2f}% on average ({len(y)}) - "
                     "high = we are leaving money; low = the rules protect us")
    L.append(f"- Edge decay watch: {sum(1 for x in E if x[1] in ('below expected', 'watch', 'early warning'))} type(s) "
             f"flagged; beliefs at risk or broken: {sum(1 for c in checks if c[3] in ('at risk', 'broken'))}")
    return L


def strategies_live(R):
    """Project ALPHA 'strategy lifecycle': live results per registered strategy (strategies/registry.json)."""
    try:
        doc = json.loads((ROOT / "strategies" / "registry.json").read_text())
        reg, stages = doc["strategies"], {x["n"]: x for x in doc.get("stages", [])}
    except Exception:
        return []
    L = []
    for st in reg:
        n = st.get("stage")
        sx = "" if n is None else (" · stage 0 retired" if n == 0 else
                                   f" · stage {n}/7 {stages.get(n, {}).get('name', '')}")
        tr = st.get("track")
        if not tr:
            L.append(f"- {st['id']} {st['name']}: {st['status']}{sx}")
            continue
        g = R[R["source"] == tr["source"]]
        if "type" in tr:
            g = g[g["type"] == tr["type"]]
        if "type_prefix" in tr:
            g = g[g["type"].astype(str).str.startswith(tr["type_prefix"])]
        if "added" in tr and "added" in g:
            g = g[g["added"].astype(str) == tr["added"]]
        c = g[g["status"] == "closed"]
        o = g[g["status"].isin(["open", "watch"])]
        nxt = ""
        if n in (4, 6):                # readiness for the next stage, from the live record
            need = 30 if n == 4 else 100
            nxt = f" · ready for review: {len(c)}/{need} closed"
        L.append(f"- {st['id']} {st['name']} [{st['status']}{sx}{nxt}]: {len(g)} ideas"
                 + (f", closed {len(c)} ({(c['result_pct'] > 0).mean() * 100:.0f}% won, avg {c['result_pct'].mean():+.2f}%)" if len(c) else "")
                 + (f", open {len(o)} (avg {o['result_pct'].mean():+.2f}%)" if len(o) and o['result_pct'].notna().any() else ""))
    return L


def same_day(R):
    """Each bought idea vs the average of the other ideas of the same source sent the same day (choice quality)."""
    B = R[R["status"].isin(["open", "closed"]) & R["result_pct"].notna()].copy()
    if not len(B):
        return R
    g = B.groupby(["source", "date"])["result_pct"]
    B["vs_same_day_pct"] = (B["result_pct"] - (g.transform("sum") - B["result_pct"]) / (g.transform("count") - 1)).round(2)
    B.loc[g.transform("count") < 2, "vs_same_day_pct"] = np.nan
    R = R.drop(columns=[c for c in ("vs_same_day_pct",) if c in R.columns])
    return R.merge(B[["source", "date", "symbol", "vs_same_day_pct"]], on=["source", "date", "symbol"], how="left")


def opportunity(R, prof):
    """Opportunity cost, in plain lines: vs NIFTY, money's speed vs a fresh tip, what skipped/blocked ideas did."""
    L = []
    B = R[R["status"].isin(["open", "closed"]) & R["result_pct"].notna()]
    for src, g in B.groupby("source"):
        if "vs_nifty_pct" in g and g["vs_nifty_pct"].notna().any():
            v = g["vs_nifty_pct"].dropna()
            L.append(f"- {src}: {int((v > 0).sum())} of {len(v)} beat simply holding NIFTY over the same days "
                     f"(average {v.mean():+.2f} points)")
    V = B[B["source"] == "VANTAGE"]
    for kind, g in V.groupby("type"):
        p = prof.get(TYPE_MAP.get(kind, ""), {})
        if p and p.get("median_days"):
            fresh = p["avg_pct"] / max(1.0, p["median_days"])
            slow = g[(g["per_day_pct"] < fresh) & (g["days"] >= 10)] if "per_day_pct" in g else g.iloc[0:0]
            L.append(f"- {kind}: a fresh tip of this type earns about {fresh:+.3f}% a day in the test; {len(slow)} of "
                     f"{len(g)} open/closed tips held 10+ days are earning less (money that could work harder)")
    if "added" in V:
        a, n = V[V["added"].astype(str) == "yes"], V[V["added"].astype(str) != "yes"]
        if len(a):
            L.append(f"- ADD MORE (a small edge in the test, 6 of 14 years better): {len(a)} tips got a second lot, average "
                     f"{a['result_pct'].mean():+.2f}% vs {n['result_pct'].mean():+.2f}% for tips without")
    S = R[R["source"] == "blocked repeat"]
    if len(S):
        L.append(f"- Blocked repeats: {len(S)}, average {S['result_pct'].mean():+.2f}% since (if this is high, blocking "
                 "cost us; if low, it saved us)")
    return L


def expectation(R, prof):
    """-> list of (type, verdict, plain line) for VANTAGE types with a tested profile."""
    out = []
    for kind, g in R[R["source"] == "VANTAGE"].groupby("type"):
        p = prof.get(TYPE_MAP.get(kind, ""), {})
        if not p:
            continue
        c = g[g["status"] == "closed"]
        n = len(c)
        if n >= MIN_CLOSED:
            pw = p["win_pct"] / 100
            lo_w = (pw - 1.645 * math.sqrt(pw * (1 - pw) / n)) * 100
            lo_a = p["avg_pct"] - 1.645 * p["sd_pct"] / math.sqrt(n)
            w, a = (c["result_pct"] > 0).mean() * 100, c["result_pct"].mean()
            verdict = "below expected" if (w < lo_w and a < lo_a) else "watch" if (w < lo_w or a < lo_a) else "on track"
            out.append((kind, verdict, f"{kind}: {n} closed, won {w:.0f}% (test {p['win_pct']:.0f}%), average {a:+.2f}% "
                                       f"(test {p['avg_pct']:+.2f}%) -> {verdict}"))
        else:
            o = g[g["status"] == "open"]
            deep = (o.get("worst_pct", pd.Series(dtype=float)) < p.get("mae_p90", -99)).sum() if len(o) else 0
            verdict = "early warning" if len(o) >= 10 and deep / len(o) > 0.25 else "too early"
            out.append((kind, verdict, f"{kind}: {n} closed of {len(g)} (need {MIN_CLOSED} to judge); "
                                       f"{deep} of {len(o)} open tips are deeper than 90% of tested trades -> {verdict}"))
    return out


BUCKETS = ["market", "market_mood", "day_type", "liquidity", "from_52w_high", "results_week", "weekday"]
ENRICHED = BUCKETS + ["best_pct", "worst_pct", "result_R", "mistake", "nifty_same_days_pct", "vs_nifty_pct",
                      "per_day_pct", "vs_same_day_pct"]


def when_it_works(R):
    """-> rows: source, situation, value, n, avg result, win %. Bought ideas only (closed result or open value)."""
    B = R[R["status"].isin(["open", "closed"]) & R["result_pct"].notna()]
    rows = []
    for src, g in B.groupby("source"):
        for col in BUCKETS:
            if col not in g:
                continue
            for val, h in g.groupby(col):
                rows.append({"source": src, "situation": col, "value": val, "n": len(h),
                             "avg_pct": round(h["result_pct"].mean(), 2), "win_pct": round((h["result_pct"] > 0).mean() * 100)})
    return pd.DataFrame(rows)


def lessons(W):
    """Gaps worth researching: within a source and situation, best vs worst value differ by >= 3 points, both n>=MIN_BUCKET."""
    out = []
    if not len(W):
        return out
    for (src, col), g in W.groupby(["source", "situation"]):
        g = g[g["n"] >= 3]
        if len(g) < 2:
            continue
        hi, lo = g.loc[g["avg_pct"].idxmax()], g.loc[g["avg_pct"].idxmin()]
        if hi["avg_pct"] - lo["avg_pct"] >= 2:
            out.append({"key": f"{src}|{col}|{hi['value']}>{lo['value']}", "source": src, "situation": col,
                        "lesson": f"{src}: when {col.replace('_', ' ')} = {hi['value']}, ideas averaged {hi['avg_pct']:+.1f}% "
                                  f"(n={hi['n']}) vs {lo['avg_pct']:+.1f}% when {lo['value']} (n={lo['n']})",
                        "evidence": evidence(min(hi["n"], lo["n"])),
                        "status": "to research (test on 13 years before any change)"})
    return out


def mistake_lessons(M):
    out = []
    if not len(M):
        return out
    for src, g in M.groupby("source"):
        for code, k in g["code"].value_counts().items():
            if k >= MIN_SIGN and code != "slow_bleed":
                out.append({"key": f"{src}|mistake|{code}", "source": src, "situation": "mistake",
                            "lesson": f"{src}: {k} of {len(g)} losing ideas - {CODES[code]}",
                            "evidence": evidence(k),
                            "status": ("known: " + TESTED[code]) if code in TESTED else
                                      "to research (test on 13 years before any change)"})
    return out


def write(R, E, W, Ls, today=None, extra=None):
    today = today or pd.Timestamp.now(tz="Asia/Kolkata").strftime("%d %b %Y")
    L = [f"# The Learner ({today})", "", "Every idea tracked by swing/tracker.py, with its situation and journey "
         "(swing/learning.py). Lessons go to research; live tips change only after a passed test and the owner's yes.", "",
         "**" + __import__("swing.data_prices", fromlist=["x"]).provenance_line() + "**", "",
         "## 1. Live vs the 13-year test"] + [f"- {x[2]}" for x in E] + (["- No VANTAGE tips yet."] if not E else [])
    L += ["", "## 2. When it works and when not (bought ideas; open ones at today's value)",
          "| Source | Situation | Value | Ideas | Average | Won |", "|---|---|---|---|---|---|"]
    for r in W.itertuples():
        L.append(f"| {r.source} | {r.situation.replace('_', ' ')} | {r.value} | {r.n} | {r.avg_pct:+.2f}% | {r.win_pct}% |")
    L += ["", "## Today's market, from memory"] + [f"- {memory_line(TODAY_KEY)}" if TODAY_KEY else "- unknown"]
    global _CHECKS
    _CHECKS = belief_checks(R, E)
    L += ["", "## Today's question (what might we be wrong about?)", "- " + (daily_question(_CHECKS) or "none")]
    L += ["", "## Beliefs and their live checks (vantage-ai/validation/beliefs.json)",
          "| Belief | Evidence | Live | Detail |", "|---|---|---|---|"]
    L += [f"| {c[1]} | {c[2]} | {c[3]} | {c[4]} |" for c in _CHECKS]
    L += ["", "## Is the system getting smarter? (scorecard)"] + scorecard(R, E, _CHECKS)
    L += ["", "## Opportunities we never detected (biggest risers)"] + (_MISSED or ["- not computed"])
    L += ["", "## 0. Strategies and their status (strategies/registry.json)"] + strategies_live(R)
    L += ["", "## 2b. Opportunity cost: could the same money have done better?"] + (_OPP or ["- Not enough bought ideas yet."])
    L += ["", "## 3. Lessons to research (evidence: weak = 2-4 cases, medium = 5-9, strong = 10+)"] + \
        ([f"- [{x.get('evidence', '?')}] {x['lesson']} - {x['status']}" for x in Ls] or ["- None yet."])
    if extra:
        M, lines, Rp, Sk = extra
        L += ["", "## 4. Mistakes: why each losing idea lost (plain diagnosis)"]
        if len(M):
            L += ["| Mistake | Ideas | Average | Sources |", "|---|---|---|---|"]
            for code, g in M.groupby("code"):
                L.append(f"| {CODES[code]} | {len(g)} | {g['result_pct'].mean():+.1f}% | {', '.join(sorted(set(g['source'])))} |")
            L += [""] + [f"- {x}" for x in lines]
        else:
            L.append("- No losing ideas to diagnose yet.")
        try:   # the normal mix of mistakes in 13 years (all stocks, last 3 years) - is the live mix different?
            cen = json.loads(CENSUS.read_text())["all holdout"]["causes"]
            L += ["", "**Normal mix in the 13-year test (all stocks, Nov 2023+), share of money lost:** "
                  + "; ".join(f"{k.split(' - ')[0]} {v['share_of_all_money_lost']:.0f}%"
                              for k, v in sorted(cen.items(), key=lambda z: -z[1]["share_of_all_money_lost"]))]
            V = M[M["source"] == "VANTAGE"]
            if len(V) >= MIN_SIGN:
                live = V.groupby("code")["result_pct"].sum() / V["result_pct"].sum() * 100
                for code, sh in live.items():
                    norm = cen.get(CODES[code], {}).get("share_of_all_money_lost", 0)
                    if sh - norm >= 15:
                        L.append(f"- ⚠️ VANTAGE live: '{CODES[code].split(' - ')[0]}' is {sh:.0f}% of money lost vs {norm:.0f}% "
                                 f"normally ({len(V)} losing tips, evidence {evidence(len(V))})")
        except Exception:
            pass
        L += ["", "## 5. Repeat stocks (sent 3+ times)"]
        L += [f"- {r.symbol}: {r.times} times ({r.sources}), average {r.avg:+.1f}%" for r in Rp.itertuples()] or ["- None."]
        L += ["", "## 6. Skipped ideas (opened outside the buy zone): missed winners or avoided losses?"]
        L += [f"- {a} ({b}): {c:+.1f}% since that open" for a, b, c in Sk] or ["- None."]
        if Sk:
            v = [c for _, _, c in Sk]
            L.append(f"- In total: {sum(x > 0 for x in v)} of {len(v)} would be up, average {np.mean(v):+.1f}%")
    J.mkdir(parents=True, exist_ok=True)
    MD.write_text("\n".join(L) + "\n")
    if Ls:
        try:
            Q = pd.read_csv(QUEUE)
        except Exception:
            Q = pd.DataFrame(columns=["first_seen", "key", "source", "situation", "lesson", "evidence", "status"])
        new = [dict(x, first_seen=str(pd.Timestamp.now().date())) for x in Ls if x["key"] not in set(Q["key"])]
        if new:
            pd.concat([Q, pd.DataFrame(new)], ignore_index=True).to_csv(QUEUE, index=False)


def portfolio_risk(R, settings, gap=0.10):
    """ATLAS portfolio risk intelligence (Telegram weekly only, never written to git): if every OPEN sent tip had
    been bought exactly as advised (1% risk sizing, 25% cap), how much money it needs and what is at risk.
    No capital configured -> no money lines (never guess capital)."""
    from . import safety
    ok, _ = safety.configured(settings)
    try:
        cap = float(settings.get("capital") or 0)
    except (TypeError, ValueError):
        cap = 0
    if not ok or cap <= 0:
        return []
    o = R[(R["status"] == "open") & (R["sent"].astype(str) == "sent")
          & R["source"].isin(["VANTAGE", "live engine", "ATLAS strategy"])] if "sent" in R else R.iloc[0:0]   # channels that send now
    need = at_stop = at_gap = 0.0
    n = jumped = 0
    for r in o.itertuples():
        try:
            e, st, now = float(r.entry), float(r.stop), float(r.exit)
        except (TypeError, ValueError):
            continue
        if not all(x == x and x > 0 for x in (e, st, now)) or st >= e:
            continue
        q = safety.size(e, st, settings)
        if q <= 0:
            continue
        n += 1
        need += q * e
        at_stop += q * max(0.0, now - st)                 # from today's price down to the stop
        at_gap += q * now * gap                            # a gap open: stop-losses cannot sell above the open
        jumped += now * (1 - gap) < st
    if not n:
        return []
    return [f"🧮 If you bought every open tip as advised: {n} positions, money needed ≈ ₹{need:,.0f} "
            f"({need / cap * 100:.0f}% of ₹{cap:,.0f})"
            + (" - more than your money: take tips as they come and skip new ones when money runs out (selling open trades to make room was tested and lost)" if need > cap else ""),
            f"   Loss if all hit their stop-loss from today's prices ≈ ₹{at_stop:,.0f} ({at_stop / cap * 100:.1f}%); "
            f"if the whole market opened {gap * 100:.0f}% lower one morning ≈ ₹{at_gap:,.0f} "
            f"({at_gap / cap * 100:.1f}%; {jumped} of {n} would open below their stop)"]


def weekly_message(R, E, Ls, today=None, settings=None):
    today = pd.Timestamp(today or pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).normalize())
    wk = R[pd.to_datetime(R["date"], errors="coerce") >= today - pd.Timedelta(days=7)]
    if "sent" in wk:
        wk = wk[wk["sent"].astype(str) == "sent"]
    closed_wk = R[(R["status"] == "closed") & (pd.to_datetime(R["exit_date"], errors="coerce") >= today - pd.Timedelta(days=7))]
    L = ["📒 ATLAS weekly learning", "", f"Ideas sent this week: {len(wk)}"]
    if TODAY_KEY:
        L.append("🧠 Market memory: " + memory_line(TODAY_KEY))
    q = daily_question(_CHECKS)
    if q:
        L.append("❓ " + q)
    bad = [c for c in _CHECKS if c[3] in ("at risk", "broken")]
    for c in bad:
        L.append(f"⚠️ Belief {c[3]}: {c[1]} ({c[4]})")
    if len(closed_wk):
        L.append(f"Closed this week: {len(closed_wk)} - won {int((closed_wk['result_pct'] > 0).sum())}, "
                 f"average {closed_wk['result_pct'].mean():+.1f}%")
    for src, g in R[R["status"].isin(["open", "closed"])].groupby("source"):
        c = g[g["status"] == "closed"]
        snt = g["sent"].astype(str).value_counts().index[0] if "sent" in g else ""
        L.append(f"• {src}{' (recorded only, not sent)' if snt == 'recorded only' else ''}: {len(g)} bought" + (f", {len(c)} closed ({(c['result_pct'] > 0).mean() * 100:.0f}% won, "
                                                 f"avg {c['result_pct'].mean():+.1f}%)" if len(c) else "")
                 + f", open avg {g[g['status'] == 'open']['result_pct'].mean():+.1f}%" * bool((g['status'] == 'open').any()))
    M, lines, Rp, Sk = _LAST
    if len(M):
        top = M["code"].value_counts()
        L.append(f"❌ Main mistake so far: {CODES[top.index[0]]} ({top.iloc[0]} of {len(M)} losing ideas)")
        worst = M.sort_values("result_pct").head(3)
        L.append("Worst: " + ", ".join(f"{r.symbol} {r.result_pct:+.1f}%" for r in worst.itertuples()))
    if len(Rp):
        L.append("🔁 Sent 3+ times: " + ", ".join(f"{r.symbol} ×{r.times}" for r in Rp.head(4).itertuples()))
    for x in E:
        if x[1] in ("below expected", "watch", "early warning"):
            L.append(f"⚠️ {x[2]}")
    if Ls:
        L.append(f"🔎 {len(Ls)} lesson(s) sent to research, e.g.: {Ls[0]['lesson']}")
    try:
        from .why_engine import weekly_lines
        L += weekly_lines()
    except Exception:
        pass
    if settings is not None:
        L += portfolio_risk(R, settings)
    L.append("Nothing changes in your tips without a passed test and your yes.")
    return "\n".join(L)


def alerts(E, s=None):
    """Instant message once per type+verdict when a VANTAGE type is clearly below its tested range."""
    from . import telegram
    from .config import load_settings
    try:
        st = json.loads(STATE.read_text())
    except Exception:
        st = {}
    sent = 0
    for kind, verdict, line in E:
        k = f"{kind}|{verdict}"
        if verdict == "below expected" and not st.get(k):
            telegram.send_reliable(s or load_settings(), "⚠️ Learning check\n\n" + line +
                                   "\n\nLive results are below what the 13-year test expects. I am researching why. "
                                   "Your tips are unchanged.", label="system problem")
            st[k] = str(pd.Timestamp.now().date())
            sent += 1
    if sent:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(st))
    return sent


def build(load=None):
    from . import tracker, data_prices
    load = load or data_prices.load
    try:
        R = pd.read_csv(tracker.CSV)
    except Exception:
        R = tracker.build(load)
    R = enrich(R, load)
    R.to_csv(tracker.CSV, index=False)
    R = same_day(R)
    global _MISSED
    try:
        _MISSED = missed_movers(R, load)
    except Exception as e:
        _MISSED = [f"- failed: {type(e).__name__}"]
    E, W = expectation(R, profile()), when_it_works(R)
    global _OPP
    _OPP = opportunity(R, profile())
    M, lines = mistakes(R, load)
    Rp, Sk = repeats(R), skipped_review(R, load)
    Ls = lessons(W) + mistake_lessons(M)
    if len(M):
        R = R.drop(columns=[c for c in ("mistake",) if c in R.columns])
        R = R.merge(M[["source", "symbol", "date", "code"]].rename(columns={"code": "mistake"}),
                    on=["source", "symbol", "date"], how="left")
        R.to_csv(tracker.CSV, index=False)
    write(R, E, W, Ls, extra=(M, lines, Rp, Sk))
    try:   # ATLAS research budget manager: ranked list of what to test next
        from . import research_queue
        research_queue.build(_CHECKS, _MISSED_N)
    except Exception as e:
        log.warning("research queue failed: %s", type(e).__name__)
    global _LAST
    _LAST = (M, lines, Rp, Sk)
    return R, E, W, Ls


def run():
    try:
        R, E, W, Ls = build()
        try:   # ATLAS immutable memory: append-only, hash-chained history of every idea
            from . import ledger
            ok, n0 = ledger.verify()
            if not ok:
                log.warning("LEDGER TAMPERING: the idea history was edited after line %d", n0)
            log.info("Ledger: %d new lines (history intact: %s)", ledger.append(R), ok)
        except Exception as e:
            log.warning("ledger failed: %s", type(e).__name__)
        n = alerts(E)
        log.info("Learner: %d ideas, %d expectation lines, %d lessons, %d alerts", len(R), len(E), len(Ls), n)
    except Exception as e:
        log.warning("Learner failed: %s", type(e).__name__)


def send_weekly():
    from . import telegram
    from .config import load_settings
    R, E, W, Ls = build()
    s = load_settings()
    return telegram.send(s, weekly_message(R, E, Ls, settings=s), label="weekly learning")
