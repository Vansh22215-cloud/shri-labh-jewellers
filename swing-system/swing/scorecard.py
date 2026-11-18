"""VANTAGE live scorecard (owner 18 Nov: "track the tips you have been giving - that is the valuable result").
Every evening (nightly job): every VANTAGE BUY ever sent is scored from its signal-day close (the "buy ≈" price in the
message) to its exit (closed) or to today's close (open), and set against the 13-year test.
Written to journal/vantage_scorecard.csv (one row per tip) and journal/vantage_scorecard.md (summary) and saved to
GitHub with the other journal files, so the research can read the live record. Market signals only: nothing about the
owner's own trades, money or holdings (/bought, capital) is written."""
import pandas as pd

from .config import ROOT, get_logger

log = get_logger()
CSV = ROOT / "journal" / "vantage_scorecard.csv"
MD = ROOT / "journal" / "vantage_scorecard.md"
COST = 0.0035


def _price(sym, load):
    d = load(sym)
    if d is None or not len(d):
        return None, None
    return float(d["close"].iloc[-1]), d


def build(load=None, today=None):
    from . import vantage, data_prices
    load = load or data_prices.load
    sig = vantage._load_signals()
    if not len(sig):
        return None
    cal = vantage.calibration()
    rows = []
    for r in sig.itertuples():
        try:
            entry, stop = float(r.close), float(r.stop)
        except (TypeError, ValueError):
            continue
        now, d = _price(r.sym, load)
        closed = str(r.status) == "closed" and str(getattr(r, "exit_price", "")) not in ("", "nan")
        px = float(r.exit_price) if closed else now
        if px is None:
            continue
        after = d[d.index > pd.Timestamp(r.signal)] if d is not None else None
        days = int(len(after)) if after is not None else 0
        low = float(after["low"].min()) if after is not None and len(after) else None
        lim = getattr(r, "limit_test", "")
        lim_fill = ""
        if str(lim) not in ("", "nan") and after is not None and len(after):
            lim_fill = "yes" if float(after["low"].iloc[0]) <= float(lim) else "no"
        rows.append({"signal": r.signal, "sym": r.sym, "setup": r.setup, "tier": "" if str(r.tier) == "nan" else r.tier,
                     "likely_pct": r.likely, "buy_ref": round(entry, 2), "stop": round(stop, 2),
                     "status": "closed" if closed else "open", "price_now_or_exit": round(px, 2),
                     "result_pct": round((px / entry - 1 - (COST if closed else 0)) * 100, 2),
                     "trading_days": days, "touched_stop": bool(low is not None and low <= stop and not closed),
                     "exit_why": getattr(r, "exit_why", "") if closed else "",
                     "added": "" if str(getattr(r, "added", "")) in ("", "nan") else "yes",
                     "limit_test_fill": lim_fill})
    S = pd.DataFrame(rows)
    CSV.parent.mkdir(parents=True, exist_ok=True)
    S.to_csv(CSV, index=False)
    MD.write_text(summary_md(S, cal, today))
    return S


def summary_md(S, cal, today=None):
    today = today or pd.Timestamp.now(tz="Asia/Kolkata").strftime("%d %b %Y")
    L = [f"# VANTAGE live scorecard ({today})", "",
         "Every VANTAGE BUY sent on Telegram, scored from the 'buy ≈' price. Open tips use today's close.", ""]
    if not len(S):
        return "\n".join(L + ["No tips yet."])
    c, o = S[S["status"] == "closed"], S[S["status"] == "open"]
    L += [f"- Tips sent: **{len(S)}** ({len(c)} closed, {len(o)} open), first {S['signal'].min()}",
          f"- Closed: won {int((c['result_pct'] > 0).sum())} of {len(c)}"
          + (f" ({(c['result_pct'] > 0).mean() * 100:.0f}%), average {c['result_pct'].mean():+.2f}% after costs" if len(c) else ""),
          f"- Open: {int((o['result_pct'] > 0).sum())} of {len(o)} up, average {o['result_pct'].mean():+.2f}% so far"
          if len(o) else "- Open: none", ""]
    L += ["| Type | Tips | Closed won | Closed avg | Open avg | Tested: won / avg per trade |", "|---|---|---|---|---|---|"]
    for k, g in S.groupby(["setup", "tier"], dropna=False):
        key = f"Dip-buy {k[1]}" if k[0] == "Dip-buy" else k[0]
        t = cal.get(key) or cal.get(k[0]) or {}
        gc, go = g[g["status"] == "closed"], g[g["status"] == "open"]
        L.append(f"| {key} | {len(g)} | " + (f"{(gc['result_pct'] > 0).mean() * 100:.0f}% of {len(gc)}" if len(gc) else "-")
                 + f" | {gc['result_pct'].mean():+.2f}%" * bool(len(gc)) + (" | -" if not len(gc) else "")
                 + (f" | {go['result_pct'].mean():+.2f}%" if len(go) else " | -")
                 + f" | {t.get('win_pct', '-')}% / {t.get('avg_pct', '-')}% |")
    lt = S[S["limit_test_fill"] != ""]
    if len(lt):
        L += ["", f"- Limit-entry forward test (D122): a limit 0.25 ATR below would have filled on "
                  f"{(lt['limit_test_fill'] == 'yes').mean() * 100:.0f}% of {len(lt)} tips."]
    try:
        from .shadow import summary
        sh = summary()
        L += [f"- Silent promoter-buying record (D132): {sh['events']} events, {sh['done']} settled"
              + (f", average {sh['avg_pct']:+.2f}%, won {sh['won_pct']:.0f}%" if sh["done"] else "")]
    except Exception:
        pass
    L += ["", "A few weeks of tips say little; judge after about 100 closed tips."]
    return "\n".join(L) + "\n"


def run():
    try:
        S = build()
        log.info("Scorecard: %s tips", 0 if S is None else len(S))
    except Exception as e:
        log.warning("Scorecard failed: %s", type(e).__name__)
