"""THE WHY-ENGINE (owner 19 Nov: "our tip worked but not the way we thought - research; it didn't work - research;
it failed for a reason we did not know - research; ask 'why' for everything, dig deep, find patterns, test, again").

Every evening, for every FINISHED tip (sent VANTAGE and live-engine tips; also the silent 'rejected' ones):
 1. EXPECTED - what 13 years of similar trades said at the signal: same setup, same strength (6-month return fifth),
    same distance from the 52-week high, same market trend -> how often they won, the typical result, how long, and
    the usual way they ended (stop / sell signal / target / time limit).
 2. ACTUAL - result, days, how it ended, best and worst point, the market during the trade, results, gaps.
 3. SURPRISE - one of: as expected | won differently (another exit, much bigger, much faster/slower) | won against
    the odds | lost, known cause | lost, unknown cause.
 4. WHY - the main driver in plain words (the market carried it / company results / an overnight gap / the stock
    itself / slow drift), with numbers.
 5. QUESTION + HISTORY ANSWER - for each surprise, the entry facts where this tip was unusual (top or bottom 10% of
    13 years) are checked at once on the history: did trades with that fact do clearly better/worse in BOTH periods?
    Confirmed in both -> a LEAD: it goes to the research list and the weekly automatic research tests it as a rule
    (exact bucket) on the account, with the full 4-step bar. Otherwise the answer is recorded ("a one-off").
Outputs: journal/why_log.csv + journal/why_log.md, strategies/why_leads.json. Market facts only (no money/holdings).
Nothing here changes a tip: only a rule that passes the weekly research AND gets the owner's /approve does."""
import json

import numpy as np
import pandas as pd

from .config import ROOT, DATA, get_logger

log = get_logger()
LOG_CSV = ROOT / "journal" / "why_log.csv"
LOG_MD = ROOT / "journal" / "why_log.md"
LEADS_F = ROOT / "strategies" / "why_leads.json"
HIST_FILES = [DATA / "auto_research" / "features.csv.gz",
              ROOT.parent / "vantage-ai" / "validation" / "lab_features.csv.gz"]
OOS = pd.Timestamp("2023-11-01")
NUM = ["turnover_cr", "from_52w_high", "ret_6m", "ret_1m", "ret_1w", "vol_surge", "atr_pct", "range_10d", "vs_200d",
       "signal_day_move", "price_rs", "up_days_10", "nifty_1m", "nifty_vs_200d", "nifty_vol_20d", "stop_dist"]
NAMES = {"turnover_cr": "money traded a day", "from_52w_high": "distance from the 52-week high",
         "ret_6m": "6-month rise", "ret_1m": "1-month rise", "ret_1w": "1-week rise", "vol_surge": "volume vs normal",
         "atr_pct": "daily swing", "range_10d": "10-day range", "vs_200d": "distance above the 200-day average",
         "signal_day_move": "signal-day move", "price_rs": "share price", "up_days_10": "up-days in the last 10",
         "nifty_1m": "NIFTY 1-month move", "nifty_vs_200d": "NIFTY vs its 200-day average", "nifty_vol_20d": "NIFTY swing",
         "score": "signal score", "stop_dist": "stop-loss distance"}
_H = {}


def history():
    """13-year trade table with facts (top-300 set), newest file first."""
    if "h" in _H:
        return _H["h"]
    for f in HIST_FILES:
        try:
            H = pd.read_csv(f, parse_dates=["signal"], low_memory=False)
            H = H[H["set"] == "top300"].copy()
            if "stop_dist" not in H:
                H["stop_dist"] = (H["entry"] - H["init_stop"]) / H["entry"]
            H["exit_kind"] = H["why"].map(exit_kind)
            _H["h"] = H
            return H
        except Exception:
            continue
    _H["h"] = None
    return None


def exit_kind(why):
    w = str(why).lower()
    if "stop" in w:
        return "stop-loss"
    if "target" in w:
        return "target"
    if "time" in w or "days" in w and "exit" in w:
        return "time limit"
    if "sell" in w or "5-day average" in w or "exit" in w:
        return "sell signal"
    return "other"


def _setup_of(r):
    t = str(r.get("type", ""))
    for k in ("Rolling Candle Profile", "Breakout", "Dip-buy"):
        if k in t:
            return "RCP" if k.startswith("Rolling") else k
    return None


def expected(H, setup, x):
    """Similar trades of 13 years -> dict (n, win, median, days, usual exit, exits share)."""
    if H is None:
        return None
    S = H[H["setup"] == setup] if setup else H
    sim = S
    for c in ("ret_6m", "from_52w_high"):
        if x and x.get(c) is not None and x.get(c) == x.get(c):
            q = S[c].quantile([0.2, 0.4, 0.6, 0.8]).values
            b = np.searchsorted(q, float(x[c]))
            lo = -np.inf if b == 0 else q[b - 1]
            hi = np.inf if b == 4 else q[b]
            cand = sim[(sim[c] >= lo) & (sim[c] < hi)]
            if len(cand) >= 40:
                sim = cand
    if x and str(x.get("mkt_trend", "")) in ("rising", "falling"):
        cand = sim[sim["mkt_trend"] == x["mkt_trend"]]
        if len(cand) >= 40:
            sim = cand
    if not len(sim):
        return None
    w = sim[sim["net"] > 0]
    ex = sim["exit_kind"].value_counts(normalize=True)
    return {"n": int(len(sim)), "win_pct": round(float((sim["net"] > 0).mean() * 100), 0),
            "median_pct": round(float(sim["net"].median() * 100), 1), "p90_pct": round(float(sim["net"].quantile(0.9) * 100), 1),
            "days": int(sim["days"].median()), "win_exit": (w["exit_kind"].value_counts().index[0] if len(w) else ""),
            "exits": {k: round(float(v) * 100) for k, v in ex.items()}}


def why_text(r):
    """Main driver of the result, plain words."""
    res, nif = float(r.get("result_pct") or 0), r.get("nifty_same_days_pct")
    nif = float(nif) if nif == nif and nif is not None else 0.0
    code = str(r.get("mistake", ""))
    if str(r.get("results_week")) == "yes" and abs(res) >= 5:
        return "company results during the trade moved it"
    if code == "gap_through_stop":
        return "an overnight gap jumped over the stop-loss"
    if abs(nif) >= 3 and np.sign(nif) == np.sign(res):
        return f"the whole market carried it (NIFTY {nif:+.1f}% over the same days)"
    if code == "gave_back":
        return "it rose first and then gave the profit back"
    if code == "never_worked":
        return "it never got going - the stock choice did not work this time"
    if res > 0:
        return f"the stock itself ({float(r.get('vs_nifty_pct') or 0):+.1f}% better than NIFTY)"
    return "it drifted down without a clear event"


def surprise(r, e):
    res, days = float(r.get("result_pct") or 0), float(r.get("days") or 0)
    kind = exit_kind(r.get("why"))
    if e is None:
        return "no history to compare"
    if res > 0:
        if e["win_pct"] < 40:
            return "won against the odds"
        if res >= e["p90_pct"]:
            return "won much bigger than usual"
        if e["win_exit"] and kind not in (e["win_exit"], "other") and e["exits"].get(kind, 0) < 25:
            return f"won differently (ended by {kind}, usually {e['win_exit']})"
        if e["days"] and (days < 0.3 * e["days"] or days > 2.5 * e["days"]):
            return f"won in {int(days)} days (usual {e['days']})"
        return "as expected"
    from .learning import TESTED
    code = str(r.get("mistake", ""))
    if code in TESTED:
        return "lost, known cause"
    return "lost, unknown cause"


def unusual_facts(H, setup, x, top=3):
    """Entry facts where this tip sat in the top/bottom 10% of 13 years of the same setup."""
    out = []
    if H is None or not x:
        return out
    S = H[H["setup"] == setup] if setup else H
    for c in NUM:
        v = x.get(c)
        if v is None or v != v or c not in S:
            continue
        col = S[c].dropna()
        if len(col) < 200:
            continue
        p = float((col < float(v)).mean())
        if p <= 0.10 or p >= 0.90:
            out.append((c, p))
    return sorted(out, key=lambda z: -abs(z[1] - 0.5))[:top]


def history_answer(H, setup, c, side):
    """Did trades with fact c in the same 10% tail do clearly better/worse than the rest, in BOTH periods?"""
    S = H[H["setup"] == setup] if setup else H
    col = S[c]
    lo, hi = (col.quantile(0.9), np.inf) if side == "high" else (-np.inf, col.quantile(0.1))
    m = (col >= lo) & (col < hi)
    res = {}
    for per, P in (("dev", S["signal"] < OOS), ("holdout", S["signal"] >= OOS)):
        a, b = S.loc[m & P, "net"], S.loc[~m & P, "net"]
        res[per] = {"n": int(len(a)), "tail_pct": round(float(a.mean() * 100), 2) if len(a) else None,
                    "rest_pct": round(float(b.mean() * 100), 2) if len(b) else None}
    d = [res[p]["tail_pct"] - res[p]["rest_pct"] for p in res if res[p]["tail_pct"] is not None and res[p]["n"] >= 50]
    if len(d) < 2:
        verdict = "not enough history"
    elif all(x <= -1 for x in d):
        verdict = "confirmed: worse in both periods"
    elif all(x >= 1 for x in d):
        verdict = "confirmed: better in both periods"
    else:
        verdict = "a one-off (history does not agree in both periods)"
    return verdict, [float(lo), float(hi)], res


def _facts(r):
    from . import lab_rules
    b = {"signal": r.get("date"), "setup": _setup_of(r) or "", "close": r.get("entry"), "stop": r.get("stop"), "score": 0}
    try:
        return lab_rules._features(str(r["symbol"]), b, r.get("date"))
    except Exception:
        return None


def explain(R, facts=_facts):
    """R = tracker rows -> why-log rows for finished tips."""
    H = history()
    rows = []
    done = R[(R["status"] == "closed") & R["source"].isin(["VANTAGE", "live engine", "rejected by VANTAGE"])]
    for _, r in done.iterrows():
        r = r.to_dict()
        setup = _setup_of(r)
        x = facts(r) or {}
        x.setdefault("mkt_trend", r.get("market", ""))
        e = expected(H, setup, x)
        s = surprise(r, e)
        row = {"source": r["source"], "type": r.get("type"), "symbol": r["symbol"], "date": r.get("date"),
               "result_pct": r.get("result_pct"), "days": r.get("days"), "ended_by": exit_kind(r.get("why")),
               "expected": (f"{e['win_pct']:.0f}% won, typical {e['median_pct']:+.1f}% in {e['days']} days, "
                            f"usually ended by {max(e['exits'], key=e['exits'].get)} (n={e['n']})") if e else "",
               "surprise": s, "why": why_text(r), "question": "", "history_answer": "", "lead": ""}
        if s != "as expected" and H is not None:
            for c, p in unusual_facts(H, setup, x):
                side = "high" if p >= 0.9 else "low"
                verdict, rng, res = history_answer(H, setup, c, side)
                q = f"Its {NAMES.get(c, c)} was in the {'top' if side == 'high' else 'bottom'} 10% of 13 years - does that matter?"
                ans = f"{verdict} (top-300 {setup or 'all'} trades in that 10%: dev {res['dev']['tail_pct']}% vs {res['dev']['rest_pct']}%, " \
                      f"recent {res['holdout']['tail_pct']}% vs {res['holdout']['rest_pct']}% per trade)"
                row["question"] = (row["question"] + " | " if row["question"] else "") + q
                row["history_answer"] = (row["history_answer"] + " | " if row["history_answer"] else "") + ans
                want = "worse" if float(r.get("result_pct") or 0) <= 0 else "better"
                if verdict.startswith("confirmed") and want in verdict:      # the pattern must explain THIS result
                    row["lead"] = (row["lead"] + " | " if row["lead"] else "") + f"{c} {side}"
                    _add_lead(setup, c, side, rng, verdict, res, r)
        rows.append(row)
    return pd.DataFrame(rows)


def _leads():
    try:
        return json.loads(LEADS_F.read_text())
    except Exception:
        return {"note": "Patterns the why-engine found in live tips AND confirmed in both history periods. The weekly "
                        "automatic research tests each as a skip / half-quantity rule on the account.", "leads": []}


def _add_lead(setup, c, side, rng, verdict, res, r):
    L = _leads()
    key = f"{setup}|{c}|{side}"
    for x in L["leads"]:
        if x["key"] == key:
            if r["symbol"] not in x["seen_in"]:
                x["seen_in"].append(r["symbol"])
            break
    else:
        L["leads"].append({"key": key, "setup": setup, "col": c, "side": side, "range": rng, "verdict": verdict,
                           "history": res, "first_seen": str(pd.Timestamp.now(tz="Asia/Kolkata").date()),
                           "seen_in": [r["symbol"]]})
    LEADS_F.parent.mkdir(parents=True, exist_ok=True)
    LEADS_F.write_text(json.dumps(L, indent=1, default=str))


def write(W, title="Why-log"):
    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    W.to_csv(LOG_CSV, index=False)
    L = [f"# {title} ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y})", "",
         "Every finished tip: what 13 years of similar trades expected, what happened, the surprise, why, and what "
         "history says about the unusual facts. Confirmed patterns become leads for the weekly research.", ""]
    if not len(W):
        return LOG_MD.write_text("\n".join(L + ["No finished tips yet."]) + "\n")
    vc = W["surprise"].str.split(" \\(").str[0].value_counts()
    L += ["## Surprise count", ""] + [f"- {k}: {v}" for k, v in vc.items()]
    L += ["", "## Leads (confirmed in both periods -> tested weekly)"] + \
         ([f"- {x['col']} {x['side']} ({x['setup']}): {x['verdict']}; seen in {', '.join(x['seen_in'][:5])}"
           for x in _leads()["leads"]] or ["- none yet"])
    L += ["", "## Every finished tip", ""]
    for r in W.itertuples():
        L.append(f"- **{r.symbol}** ({r.type}, {r.date}): {float(r.result_pct):+.1f}% in {r.days} days, ended by "
                 f"{r.ended_by}. Expected: {r.expected or 'n/a'}. **{r.surprise}** - why: {r.why}."
                 + (f" Q: {r.question} A: {r.history_answer}" if r.question else ""))
    LOG_MD.write_text("\n".join(L) + "\n")


def weekly_lines(n=3):
    try:
        W = pd.read_csv(LOG_CSV)
    except Exception:
        return []
    S = W[W["surprise"] != "as expected"].tail(n)
    out = [f"🔍 {r.symbol} {float(r.result_pct):+.1f}%: {r.surprise} - {r.why}" for r in S.itertuples()]
    k = len(_leads()["leads"])
    if k:
        out.append(f"🧪 {k} pattern(s) from live tips confirmed on 13 years - being tested as rules")
    return out


def run(R=None):
    try:
        if R is None:
            from . import tracker
            R = pd.read_csv(tracker.CSV)
        W = explain(R)
        write(W)
        log.info("Why-engine: %d finished tips explained, %d surprises, %d leads", len(W),
                 int((W["surprise"] != "as expected").sum()) if len(W) else 0, len(_leads()["leads"]))
        return W
    except Exception as e:
        log.warning("why-engine failed: %s", type(e).__name__)
