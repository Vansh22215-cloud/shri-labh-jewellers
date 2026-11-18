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
STATE = PRIVATE / "learning_state.json"
TYPE_MAP = {"VANTAGE Rolling Candle Profile": "RCP", "VANTAGE Breakout": "Breakout", "VANTAGE Dip-buy A": "Dip-buy A",
            "VANTAGE Dip-buy B": "Dip-buy B", "VANTAGE Dip-buy C": "Dip-buy C"}
MIN_CLOSED, MIN_BUCKET = 20, 10


def profile():
    try:
        return json.loads(PROFILE.read_text()).get("holdout", {})
    except Exception:
        return {}


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
    M = _market(load)
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
                w = d[(d.index >= ed) & (d.index <= xd)]
                if len(w):
                    x["best_pct"] = round((float(w["high"].max()) / e - 1) * 100, 2)
                    x["worst_pct"] = round((float(w["low"].min()) / e - 1) * 100, 2)
                st = getattr(r, "stop", None)
                if st == st and st and e > st and r.result_pct == r.result_pct:
                    x["result_R"] = round(r.result_pct / ((e - st) / e * 100), 2)
        x["results_week"] = "yes" if _results_days(r.symbol, day) else "no"
        x["weekday"] = day.strftime("%a")
        rows.append(x)
    return pd.concat([R.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


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


BUCKETS = ["market", "market_mood", "liquidity", "from_52w_high", "results_week", "weekday"]


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
        g = g[g["n"] >= MIN_BUCKET]
        if len(g) < 2:
            continue
        hi, lo = g.loc[g["avg_pct"].idxmax()], g.loc[g["avg_pct"].idxmin()]
        if hi["avg_pct"] - lo["avg_pct"] >= 3:
            out.append({"key": f"{src}|{col}|{hi['value']}>{lo['value']}", "source": src, "situation": col,
                        "lesson": f"{src}: when {col.replace('_', ' ')} = {hi['value']}, ideas averaged {hi['avg_pct']:+.1f}% "
                                  f"(n={hi['n']}) vs {lo['avg_pct']:+.1f}% when {lo['value']} (n={lo['n']})",
                        "status": "to research (test on 13 years before any change)"})
    return out


def write(R, E, W, Ls, today=None):
    today = today or pd.Timestamp.now(tz="Asia/Kolkata").strftime("%d %b %Y")
    L = [f"# The Learner ({today})", "", "Every idea tracked by swing/tracker.py, with its situation and journey "
         "(swing/learning.py). Lessons go to research; live tips change only after a passed test and the owner's yes.", "",
         "## 1. Live vs the 13-year test"] + [f"- {x[2]}" for x in E] + (["- No VANTAGE tips yet."] if not E else [])
    L += ["", "## 2. When it works and when not (bought ideas; open ones at today's value)",
          "| Source | Situation | Value | Ideas | Average | Won |", "|---|---|---|---|---|---|"]
    for r in W.itertuples():
        L.append(f"| {r.source} | {r.situation.replace('_', ' ')} | {r.value} | {r.n} | {r.avg_pct:+.2f}% | {r.win_pct}% |")
    L += ["", "## 3. Lessons to research"] + ([f"- {x['lesson']}" for x in Ls] or ["- None yet (needs at least "
                                                                                 f"{MIN_BUCKET} ideas per situation)."])
    J.mkdir(parents=True, exist_ok=True)
    MD.write_text("\n".join(L) + "\n")
    if Ls:
        try:
            Q = pd.read_csv(QUEUE)
        except Exception:
            Q = pd.DataFrame(columns=["first_seen", "key", "source", "situation", "lesson", "status"])
        new = [dict(x, first_seen=str(pd.Timestamp.now().date())) for x in Ls if x["key"] not in set(Q["key"])]
        if new:
            pd.concat([Q, pd.DataFrame(new)], ignore_index=True).to_csv(QUEUE, index=False)


def weekly_message(R, E, Ls, today=None):
    today = pd.Timestamp(today or pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).normalize())
    wk = R[pd.to_datetime(R["date"], errors="coerce") >= today - pd.Timedelta(days=7)]
    closed_wk = R[(R["status"] == "closed") & (pd.to_datetime(R["exit_date"], errors="coerce") >= today - pd.Timedelta(days=7))]
    L = ["📒 Weekly learning", "", f"Ideas sent this week: {len(wk)}"]
    if len(closed_wk):
        L.append(f"Closed this week: {len(closed_wk)} - won {int((closed_wk['result_pct'] > 0).sum())}, "
                 f"average {closed_wk['result_pct'].mean():+.1f}%")
    for src, g in R[R["status"].isin(["open", "closed"])].groupby("source"):
        c = g[g["status"] == "closed"]
        L.append(f"• {src}: {len(g)} bought" + (f", {len(c)} closed ({(c['result_pct'] > 0).mean() * 100:.0f}% won, "
                                                 f"avg {c['result_pct'].mean():+.1f}%)" if len(c) else "")
                 + f", open avg {g[g['status'] == 'open']['result_pct'].mean():+.1f}%" * bool((g['status'] == 'open').any()))
    for x in E:
        if x[1] in ("below expected", "watch", "early warning"):
            L.append(f"⚠️ {x[2]}")
    if Ls:
        L.append(f"🔎 {len(Ls)} lesson(s) sent to research, e.g.: {Ls[0]['lesson']}")
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
    E, W = expectation(R, profile()), when_it_works(R)
    Ls = lessons(W)
    write(R, E, W, Ls)
    return R, E, W, Ls


def run():
    try:
        R, E, W, Ls = build()
        n = alerts(E)
        log.info("Learner: %d ideas, %d expectation lines, %d lessons, %d alerts", len(R), len(E), len(Ls), n)
    except Exception as e:
        log.warning("Learner failed: %s", type(e).__name__)


def send_weekly():
    from . import telegram
    from .config import load_settings
    R, E, W, Ls = build()
    return telegram.send(load_settings(), weekly_message(R, E, Ls), label="weekly learning")
