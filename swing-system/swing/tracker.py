"""EVERY TIP, TRACKED (owner 18 Nov: "every tip given must be tracked, understood and analysed... that's what makes us
better and lets us know what is working, when and when not").

One evening job follows every idea the system ever sent, from every source, with the same simple rules:
  - strategy tips (journal/tips.csv + tips_retired.csv) and hourly-scan ideas (journal/scan_signals.csv): bought at the
    next day's open only if it opens inside the entry zone (else "skipped - opened outside the zone"); then the
    stop-loss (exit at the stop, or at the open if it gaps below) or target 1 (exit at the target) - whichever comes
    first; otherwise still open, valued at today's close;
  - VANTAGE tips (data/private/vantage_signals.csv): from the "buy ≈" close, to the recorded exit or today's close;
  - live-engine tips (data/private/live_tips.csv): from their entry, to their recorded result or today's close;
  - live alerts / 3:20 pm buy-now alerts: confirmed or cancelled at the close;
  - company of the day (journal/company_picks.csv): price change since the pick (research, not a trade);
  - monthly basket: average change of its stocks since the list;
  - silent promoter record (D132).
Closed trades pay 0.35% costs. Written to journal/all_tips.csv (one row per idea) and journal/all_tips.md (summary by
source and type, with the 13-year test next to it) and saved to GitHub for the research. Market ideas only: the
owner's own trades, quantities, money and /bought flags are never written."""
import json

import pandas as pd

from .config import DATA, PRIVATE, ROOT, get_logger

log = get_logger()
J = ROOT / "journal"
CSV, MD = J / "all_tips.csv", J / "all_tips.md"
MUTED_FROM = "2026-11-11"     # D95: evening strategy tips and hourly-scan ideas are log-only from this day
COST = 0.0035


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def zone_trade(d, day, lo, hi, stop, tgt):
    """-> dict for a tip with an entry zone, following the daily bars after `day`."""
    after = d[d.index > pd.Timestamp(day)]
    if not len(after):
        return {"status": "waiting (no trading day yet)"}
    e = after.iloc[0]
    if not (lo <= e["open"] <= hi):
        return {"status": "skipped - opened outside the zone", "entry_date": str(after.index[0].date())}
    entry = float(e["open"])
    for k in range(len(after)):
        b = after.iloc[k]
        if b["low"] <= stop:
            x = min(float(b["open"]), stop) if k else stop
            return {"status": "closed", "why": "stop-loss", "entry_date": str(after.index[0].date()), "entry": entry,
                    "exit_date": str(after.index[k].date()), "exit": x, "days": k + 1}
        if tgt and b["high"] >= tgt:
            x = max(float(b["open"]), tgt) if k else tgt
            return {"status": "closed", "why": "target 1", "entry_date": str(after.index[0].date()), "entry": entry,
                    "exit_date": str(after.index[k].date()), "exit": x, "days": k + 1}
    return {"status": "open", "entry_date": str(after.index[0].date()), "entry": entry, "exit": float(after["close"].iloc[-1]),
            "days": len(after)}


def _row(source, kind, day, sym, res, **extra):
    r = {"source": source, "type": kind, "date": str(day)[:10], "symbol": sym, **extra, **res}
    if r.get("entry") and r.get("exit"):
        r["result_pct"] = round((r["exit"] / r["entry"] - 1 - (COST if r["status"] == "closed" else 0)) * 100, 2)
    return r


def collect(load):
    rows = []
    # 1) strategy tips + hourly-scan ideas (entry zone)
    for f, src in (("tips.csv", "strategy tip"), ("tips_retired.csv", "strategy tip (retired list)"), ("scan_signals.csv", "hourly scan")):
        try:
            T = pd.read_csv(J / f)
        except Exception:
            continue
        for t in T.itertuples():
            if str(getattr(t, "date", ""))[:4] < "2025":
                continue                                             # placeholder/test rows
            d = load(t.symbol)
            lo, hi, st, tg = _f(t.entry_low), _f(t.entry_high), _f(t.stop), _f(getattr(t, "target1", None))
            if d is None or None in (lo, hi, st):
                continue
            from .corp_actions import split_factor
            f = split_factor(d, t.date)                              # prices recorded before a split/bonus
            if f != 1.0:
                lo, hi, st, tg = lo / f, hi / f, st / f, (tg / f if tg else tg)
            kind = str(getattr(t, "strategy", "scan")) + ("" if str(getattr(t, "kind", "tip")) == "tip" else " (shadow)")
            sent = "sent" if (str(getattr(t, "kind", "tip")) == "tip" and str(t.date)[:10] < MUTED_FROM) else "recorded only"
            rows.append(_row(src, kind, t.date, t.symbol, zone_trade(d, t.date, lo, hi, st, tg), stop=st, target=tg,
                             sent=sent))
    # 2) VANTAGE tips
    try:
        from .vantage import _load_signals
        S = _load_signals()
    except Exception:
        S = pd.DataFrame()
    for t in S.itertuples():
        d, ref = load(t.sym), _f(t.close)
        if d is None or ref is None:
            continue
        closed = str(t.status) == "closed" and _f(getattr(t, "exit_price", None))
        after = d[d.index > pd.Timestamp(t.signal)]
        xp, xd = (float(t.exit_price) if closed else float(d["close"].iloc[-1])), None
        why = str(getattr(t, "exit_why", "")) if closed else ""
        if closed and "live" not in why.lower() and str(getattr(t, "exit_date", "")) not in ("", "nan"):
            nxt = d[d.index > pd.Timestamp(str(t.exit_date)[:10])]          # the SELL says "sell at the next open"
            if len(nxt):
                xp, xd = float(nxt["open"].iloc[0]), str(nxt.index[0].date())
        res = {"status": "closed" if closed else "open", "entry": ref, "entry_date": str(t.signal), "exit": xp,
               "exit_date": xd or (str(t.exit_date)[:10] if closed else None), "days": int(len(after)), "why": why}
        kind = "VANTAGE " + ("Rolling Candle Profile" if t.setup == "RCP" else str(t.setup)) + \
            (f" {t.tier}" if str(t.tier) not in ("", "nan") else "")
        nxt = round(float(after["open"].iloc[0]), 2) if len(after) else None
        rows.append(_row("VANTAGE", kind, t.signal, t.sym, res, stop=_f(t.stop), sent="sent", next_open=nxt,
                         next_open_vs_buy_pct=round((nxt / ref - 1) * 100, 2) if nxt else None,
                         added="yes" if str(getattr(t, "added", "")) not in ("", "nan") else ""))
    # 3) live-engine tips (no qty / taken written)
    try:
        L = pd.read_csv(PRIVATE / "live_tips.csv", dtype=str)
    except Exception:
        L = pd.DataFrame()
    for t in L.itertuples():
        d, e = load(t.symbol), _f(t.entry)
        if d is None or e is None:
            continue
        closed = str(t.status).lower().startswith(("closed", "stop", "target", "exit"))
        res = {"status": "closed" if closed else ("open" if str(t.status) in ("open", "active") else str(t.status)),
               "entry": e, "entry_date": str(t.day)[:10], "days": int((d.index > pd.Timestamp(str(t.day)[:10])).sum())}
        if closed and _f(t.result_pct) is not None:
            res["exit"] = e * (1 + _f(t.result_pct) / 100 + COST)
        elif not closed:
            res["exit"] = float(d["close"].iloc[-1])
        rows.append(_row("live engine", f"{t.type} {'' if str(t.setup) == 'nan' else t.setup}".strip(), t.day, t.symbol, res,
                         stop=_f(t.stop), sent="sent"))
    # 3b) repeats blocked by D139 - followed as if bought, to learn whether blocking them was right
    try:
        P = pd.read_csv(PRIVATE / "suppressed_repeats.csv", dtype=str)
    except Exception:
        P = pd.DataFrame()
    for t in P.itertuples():
        d, ref = load(t.symbol), _f(t.ref_price)
        if d is None or ref is None:
            continue
        rows.append(_row("blocked repeat", f"{t.channel} (held by {t.held_by})", t.day, t.symbol,
                         {"status": "watch", "entry": ref, "exit": float(d["close"].iloc[-1]), "entry_date": t.day},
                         stop=_f(t.stop), sent="blocked"))
    # 3c) VANTAGE signals the scanner rejected (thin stock, kill switch) - counterfactuals
    try:
        Q = pd.read_csv(PRIVATE / "vantage_rejected.csv", dtype=str)
    except Exception:
        Q = pd.DataFrame()
    for t in Q.itertuples():
        d, ref = load(t.symbol), _f(t.ref_price)
        if d is None or ref is None:
            continue
        rows.append(_row("rejected by VANTAGE", f"{t.setup} - {str(t.why).split(' (')[0]}", t.day, t.symbol,
                         {"status": "watch", "entry": ref, "exit": float(d["close"].iloc[-1]), "entry_date": t.day},
                         stop=_f(t.stop), sent="rejected"))
    # 4) company of the day (research pick, not a trade)
    try:
        C = pd.read_csv(J / "company_picks.csv")
    except Exception:
        C = pd.DataFrame()
    for t in C.itertuples():
        d = load(t.symbol)
        if d is None or not len(d):
            continue
        p0 = _f(t.price) or float(d[d.index <= pd.Timestamp(t.date)]["close"].iloc[-1])
        rows.append(_row("company of the day", "research pick", t.date, t.symbol,
                         {"status": "watch", "entry": p0, "exit": float(d["close"].iloc[-1]), "entry_date": str(t.date)},
                         sent="sent"))
    # 5) monthly basket
    try:
        B = json.loads((PRIVATE / "basket.json").read_text())
        for h in B.get("history", []):
            for s in h.get("holdings", []):
                d = load(s)
                if d is None:
                    continue
                day = B.get("sent_day") if h is B["history"][-1] else h["month"] + "-28"
                p0 = d[d.index <= pd.Timestamp(day)]["close"]
                if len(p0):
                    rows.append(_row("monthly basket", h["month"], day, s,
                                     {"status": "watch", "entry": float(p0.iloc[-1]), "exit": float(d["close"].iloc[-1])}))
    except Exception:
        pass
    return pd.DataFrame(rows)


def alerts_summary():
    out = []
    for f, name in (("vantage_live.csv", "live BUY alerts"), ("vantage_closecall.csv", "3:20 pm buy-now alerts")):
        try:
            A = pd.read_csv(PRIVATE / f, dtype=str)
            done = A[A["outcome"].isin(["confirmed", "cancelled"])]
            if len(done):
                out.append(f"- {name}: {len(A)} sent, {(done['outcome'] == 'confirmed').mean() * 100:.0f}% confirmed at the close")
        except Exception:
            pass
    try:
        from .shadow import summary
        sh = summary()
        out.append(f"- Silent promoter-buying record: {sh['events']} events, {sh['done']} settled"
                   + (f", average {sh['avg_pct']:+.2f}% per trade, {sh['won_pct']:.0f}% won" if sh["done"] else ""))
    except Exception:
        pass
    return out


def tested():
    try:
        from .vantage import calibration
        return calibration()
    except Exception:
        return {}


def report(R, today=None):
    today = today or pd.Timestamp.now(tz="Asia/Kolkata").strftime("%d %b %Y")
    L = [f"# Every tip, tracked ({today})", "",
         "Every idea the system sent, followed with the same rules (see swing/tracker.py). Open = valued at today's close.", ""]
    if not len(R):
        return "\n".join(L + ["No tips yet."]) + "\n"
    L += ["| Source | Type | Sent to owner? | Ideas | Bought (in zone) | Closed: won | Closed avg | Open: up | Open avg |",
          "|---|---|---|---|---|---|---|---|---|"]
    for (src, kind, snt), g in R.groupby(["source", "type", "sent"], dropna=False):
        c = g[g["status"] == "closed"]
        o = g[g["status"].isin(["open", "watch"])]
        bought = g[~g["status"].astype(str).str.startswith(("skipped", "waiting"))]
        L.append(f"| {src} | {kind} | {snt} | {len(g)} | {len(bought)} | "
                 + (f"{int((c['result_pct'] > 0).sum())} of {len(c)}" if len(c) else "-") + " | "
                 + (f"{c['result_pct'].mean():+.2f}%" if len(c) else "-") + " | "
                 + (f"{int((o['result_pct'] > 0).sum())} of {len(o)}" if len(o) else "-") + " | "
                 + (f"{o['result_pct'].mean():+.2f}%" if len(o) else "-") + " |")
    cal = tested()
    if cal:
        L += ["", "**13-year test, for comparison (VANTAGE):** "
              + "; ".join(f"{k}: {v['win_pct']}% won, {v['avg_pct']:+.1f}% per trade" for k, v in cal.items()
                          if k in ("RCP", "Breakout", "Dip-buy A", "Dip-buy B"))]
    L += [""] + alerts_summary()
    L += ["", "Early weeks say little: judge each type after about 100 closed ideas."]
    return "\n".join(L) + "\n"


def build(load=None):
    from . import data_prices
    load = load or data_prices.load
    R = collect(load)
    J.mkdir(parents=True, exist_ok=True)
    cols = ["source", "type", "sent", "date", "symbol", "status", "why", "entry_date", "entry", "stop", "target",
            "exit_date", "exit", "result_pct", "days", "added", "next_open", "next_open_vs_buy_pct"]
    if len(R):
        R = R.reindex(columns=cols)
    R.to_csv(CSV, index=False)
    MD.write_text(report(R))
    return R


def run():
    try:
        R = build()
        log.info("Tracker: %d ideas tracked", len(R))
    except Exception as e:
        log.warning("Tracker failed: %s", type(e).__name__)
