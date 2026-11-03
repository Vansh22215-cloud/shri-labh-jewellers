"""The nightly job: update data -> health checks -> score -> shortlist -> report.

Tips are sent ONLY if every safety condition holds:
  kill switch off, data healthy, tests pass, strategy passed the validation gate,
  no auto-pause/rollback in force, market regime OK, paper drawdown < 10%.
Otherwise the report says "No tips" and explains why in plain English.
"""
import json
import subprocess
import sys
import traceback
from datetime import date, datetime

import numpy as np
import pandas as pd

from . import data_nse, data_prices, engine, fundamentals, health, journal, report, review, telegram, update
from .config import (DISCLAIMER, LOGS, ROOT, get_logger, load_settings, load_state, load_strategy, save_state)
from .strategy import position_size, trade_plan
from .validate import GATE

log = get_logger()


def run_tests():
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", str(ROOT / "tests")],
                           capture_output=True, text=True, timeout=900, cwd=ROOT)
        tail = (r.stdout or "").strip().splitlines()[-1:] or [""]
        return r.returncode == 0, tail[0]
    except Exception as e:
        return False, str(e)


def error_summary(since):
    """Plain-English summary of today's warnings/errors from logs/system.log."""
    f = LOGS / "system.log"
    if not f.exists():
        return []
    msgs = []
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines()[-4000:]:
        if line[:19] >= since and (" ERROR " in line or " WARNING " in line):
            msgs.append(line[24:].split(" ", 1)[-1][:160])
    uniq = list(dict.fromkeys(msgs))
    return uniq[:6] + ([f"... and {len(uniq) - 6} more (see logs/system.log)"] if len(uniq) > 6 else [])


def gate_status(strategy):
    try:
        g = json.loads(GATE.read_text())
        return g.get(strategy, {"passed": False, "checks": [], "note": "never validated"})
    except Exception:
        return {"passed": False, "checks": [], "note": "validation has not been run yet"}


def search_html():
    """One line per strategy search (swing, short-term, intraday)."""
    parts = []
    for fname, label, unit in (("search_latest.json", "Swing (days-weeks)", "years"),
                               ("search_short.json", "Short-term (1-5 days)", "years"),
                               ("search_intraday.json", "Intraday (same day)", "quarters")):
        try:
            o = json.loads((ROOT / "validation" / fname).read_text())
        except Exception:
            continue
        won = sum(p["beat_niftybees"] in (True, "True") for p in o["picks"])
        parts.append(f"<li><b>{label}</b> ({o['date']}): {o['variants_searched']} strategies searched; honest "
                     f"walk-forward picks beat NIFTYBEES in {won} of {len(o['picks'])} {unit} - "
                     f"<b class='{'good' if o['passed'] else 'bad'}'>{'PASSED' if o['passed'] else 'FAILED'}</b></li>")
    if not parts:
        return ""
    return ("<p><b>Strategy searches</b> (each period's strategy chosen only from earlier data). Details in the "
            "validation folder (search*.html).</p><ul>" + "".join(parts) + "</ul>")


def gate_html(g):
    if not g.get("checks"):
        return f"<p class='bad'>Not validated: {g.get('note', '')}</p>"
    rows = "".join(f"<tr><td class='{'good' if c['passed'] else 'bad'}'>{'PASS' if c['passed'] else 'FAIL'}</td>"
                   f"<td>{c['check']}</td><td>{c['detail']}</td></tr>" for c in g["checks"])
    return (f"<p>Last validated {g.get('date', '?')} - overall: <b class='{'good' if g['passed'] else 'bad'}'>"
            f"{'PASSED' if g['passed'] else 'FAILED'}</b>. Variants tried so far: {g.get('variants_tried', '?')}. "
            f"Full report: validation/latest.html</p><table>{rows}</table>")


def build_reasons_risks(sym, sig, d, plan, q, results_date, p, deals):
    reasons, risks = [], []
    rs = sig["rs_rank"].at[d, sym] * 100
    reasons.append(f"Stronger than {rs:.0f}% of the top-500 stocks vs Nifty over 6 months")
    sr = sig["sector_rank"].at[d, sym] * 100
    reasons.append(f"Its industry ranks in the top {100 - sr:.0f}% by strength" if sr >= 50
                   else f"Industry strength is below average (rank {sr:.0f}/100)")
    reasons.append("Healthy uptrend: price above rising 50- and 200-day averages")
    setup_text = {"breakout": "Breakout to a 50-day closing high on above-average volume",
                  "pullback": "Pullback to the 20-day average followed by a reversal day (closed above yesterday's high)"}
    reasons.append(setup_text.get(plan["setup"], f"Entry signal: {plan['setup']}"))
    reasons += [f"Fundamentals: {x}" for x in q.get("positives", [])]
    stop_pct = (plan["last_close"] - plan["stop"]) / plan["last_close"] * 100
    risks.append(f"Stop is {stop_pct:.1f}% below the last close; a gap down can cause a bigger loss")
    if stop_pct > 10:
        risks.append("Volatile stock (wide stop)")
    ext = (plan["last_close"] / sig["sma50"].at[d, sym] - 1) * 100
    if ext > 15:
        risks.append(f"Already {ext:.0f}% above its 50-day average (stretched)")
    if results_date is not None:
        days = (results_date - d).days
        if days <= 10:
            risks.append(f"RESULTS DUE {results_date.date()} (in {days} days) - big gap risk around results")
    else:
        risks.append("Next results date unknown - check on NSE/Zerodha before buying")
    if q.get("years_available", 0) == 0:
        risks.append("No free fundamental data available - business quality not checked")
    if q.get("insider_pct") is not None and q["insider_pct"] < 0.30:
        risks.append(f"Promoter/insider holding only {q['insider_pct']*100:.0f}% (approx.)")
    risks.append("Promoter pledge data not available from a free automatable source - check on Zerodha/Tijori")
    if deals is not None and len(deals) and "Symbol" in deals.columns:
        dd = deals[deals["Symbol"] == sym]
        if len(dd):
            risks.append(f"Recent bulk/block deal(s): {len(dd)} on record - see stocks/{sym}.md")
    return reasons, risks


def run():
    t0 = datetime.now()
    since = f"{t0:%Y-%m-%d} 00:00:00"
    settings = load_settings()
    state = load_state()
    sname = settings.get("live_strategy", "v1")
    g = gate_status(sname)
    # AGGRESSIVE MODE (owner's explicit choice): if nothing is validated, use the best available strategy
    aggressive = settings.get("tips_mode") == "aggressive" and not g.get("passed")
    if aggressive:
        sname = settings.get("aggressive_strategy", "a1")
    p = load_strategy(sname)
    capital = float(settings["capital"])
    blockers, health_items = [], []

    def ok(t):
        health_items.append(("good", "OK - " + t))

    def bad(t):
        health_items.append(("bad", "PROBLEM - " + t))

    # 1) data update (fails gracefully; cached data is still usable for diagnosis)
    try:
        info = update.refresh(first_time=False)
        for e in info.get("errors", []):
            bad(e)
    except Exception as e:
        log.error("Data update crashed: %s", e)
        bad(f"data update failed ({e}); using cached data")

    # 2) health checks
    nifty_raw = data_prices.load("NIFTY50")
    last_bar = nifty_raw.index[-1] if nifty_raw is not None else pd.Timestamp("1900-01-01")
    bhav_dates = sorted(f.stem for f in (data_nse.BHAV).glob("*.csv") if f.stat().st_size > 0)
    expected = pd.Timestamp(bhav_dates[-1]) if bhav_dates else last_bar
    fresh = health.freshness(last_bar, expected)
    if not fresh:
        # attempt a fix: force a full re-download of the index data, then re-check
        log.warning("Stale index data (%s vs %s); retrying full download", last_bar.date(), expected.date())
        data_prices.download_full(list(data_prices.INDEX_TICKERS))
        nifty_raw = data_prices.load("NIFTY50")
        last_bar = nifty_raw.index[-1]
        fresh = health.freshness(last_bar, expected)
    (ok if fresh else bad)(f"latest prices dated {last_bar.date()} (NSE latest trading day {expected.date()})")
    if not fresh:
        blockers.append("Price data is not up to date - the free data source may be late. Will retry tomorrow.")

    try:
        hist_syms = sorted(set(pd.read_csv(update.universe.UNIVERSE_FILE)["symbol"]))
        q = health.build_quarantine(hist_syms)
        ok(f"{len(q)} stocks quarantined for suspicious data (excluded)")
    except Exception as e:
        bad(f"quarantine check failed: {e}")
        blockers.append("Data quality check could not run")

    tests_ok, tests_msg = run_tests()
    (ok if tests_ok else bad)(f"self-tests: {tests_msg}")
    if not tests_ok:
        blockers.append("The system's self-tests failed, so its calculations cannot be trusted today")

    # 3) signals (same code as the backtest)
    P, sig, nifty, industry, coverage, _ = engine.build(p, use_results_filter=(p.get("results_rule") == "exclude"))
    d = P["close"].index[-1]
    member_today = sig["member"].loc[d]
    have_bar = P["close"].loc[d][member_today].notna().mean() if member_today.any() else 0
    (ok if have_bar > 0.9 else bad)(f"{have_bar:.0%} of universe stocks have a price for {d.date()} "
                                    f"({int(member_today.sum())} stocks in universe)")
    if have_bar < 0.9:
        blockers.append("Too many stocks are missing today's price")
    day_ret = P["close"].pct_change(fill_method=None).loc[d][member_today]
    n_out = int((day_ret.abs() > 0.2).sum())
    health_items.append(("good" if n_out < 10 else "warn", f"{n_out} universe stocks moved more than 20% today"))
    if P["close"].index.duplicated().any():
        bad("duplicate dates in price panel")
        blockers.append("Duplicate rows in price data")

    regime = bool(sig["regime_ok"].loc[d])                       # used by this strategy version
    market_ok = bool(sig.get("market_regime_ok", sig["regime_ok"]).loc[d])  # shown to you
    nlast = float(nifty.loc[:d].iloc[-1])
    n200 = float(nifty.loc[:d].tail(200).mean())
    vix = data_prices.load("INDIAVIX")
    market = {
        "Nifty 50 close": f"{nlast:,.0f} ({(nlast / n200 - 1) * 100:+.1f}% vs 200-day average)",
        "Breadth (% of top-500 above 50-day avg)": f"{sig['breadth'].loc[d]:.0f}%",
        "India VIX (fear gauge)": f"{vix['close'].iloc[-1]:.1f}" if vix is not None else "n/a",
        "Market filter": ("HEALTHY" if market_ok else "WEAK") + (
            "" if p.get("use_regime_filter", True) else " (this strategy version does not use the market filter)"),
    }
    secs = []
    for k in data_prices.INDEX_TICKERS:
        if k.startswith("NIFTY") and k not in ("NIFTY50", "NIFTYBEES"):
            s = data_prices.load(k)
            if s is not None and len(s) > 22:
                secs.append((k, (s["close"].iloc[-1] / s["close"].iloc[-22] - 1) * 100))
    secs.sort(key=lambda x: -x[1])
    if secs:
        market["Strongest sectors (1 month)"] = ", ".join(f"{a} {b:+.1f}%" for a, b in secs[:3])
        market["Weakest sectors (1 month)"] = ", ".join(f"{a} {b:+.1f}%" for a, b in secs[-3:])

    # 4) candidates -> safety screens -> plans
    try:
        stats_file = json.loads((ROOT / "validation" / "latest.json").read_text())
        setup_hits = stats_file.get("setup_stats", {})
        bt_ref = stats_file.get("wf_summary", {})
        if aggressive and p.get("backtest_stats"):
            bs_ = p["backtest_stats"]
            setup_hits = {s_: {"win_rate_pct": bs_["win_rate_pct"], "avg_r": "n/a", "trades": bs_["trades"]}
                          for s_ in ("20/50 average crossover", p.get("family", ""))}
            bt_ref = {"closed": bs_["trades"], "win_rate_pct": bs_["win_rate_pct"], "avg_r": "-", "total_pnl": "-"}
    except Exception:
        setup_hits, bt_ref = {}, {}
    try:
        deals = data_nse.deals()
    except Exception:
        deals = None
    plans, removed = [], []
    elig = sig["eligible"].loc[d]
    names = list(sig["score"].loc[d, elig[elig].index].sort_values(ascending=False).index[:15])
    if not regime:
        names = []   # same as the backtest: no candidates at all in a weak market
    for sym in names:
        if len(plans) >= 8:
            break
        close, a = float(P["close"].at[d, sym]), float(sig["atr"].at[d, sym])
        lv = trade_plan(close, a, p)
        qty = position_size(capital, capital, close, lv["stop"], p)
        if qty < 1:
            removed.append({"symbol": sym, "reason": "price too high for 25% position cap with your capital"})
            continue
        snap = fundamentals.fetch_fundamentals(sym)
        qsum = fundamentals.quality_summary(snap, asof=d)
        if qsum["flags"] and qsum.get("years_available", 0) > 0:
            removed.append({"symbol": sym, "reason": "quality screen: " + "; ".join(qsum["flags"])})
            continue
        rd = fundamentals.next_results_date(sym, d)
        if p.get("results_rule") == "exclude" and rd is not None and (rd - d).days <= p["exclude_results_within_days"] * 7 / 5:
            removed.append({"symbol": sym, "reason": f"results due {rd.date()}"})
            continue
        plan = {"symbol": sym, "name": snap.get("name"), "setup": sig["setup"].at[d, sym],
                "score": float(sig["score"].at[d, sym]), "last_close": round(close, 2), **lv, "qty": qty,
                "risk_rupees": round(qty * (close - lv["stop"]), 0), "max_hold": p["max_hold_days"],
                "results": str(rd.date()) if rd is not None else None,
                "hit_rate": setup_hits.get(sig["setup"].at[d, sym], {}),
                "exit_style": p.get("exit_style", "targets"), "trail_atr": round(p.get("trail_atr_mult", 3.0) * a, 2)}
        plan["reasons"], plan["risks"] = build_reasons_risks(sym, sig, d, plan, qsum, rd, p, deals)
        plans.append(plan)

    probs = health.sanity_check_plans(plans, capital)
    if probs:
        for pr in probs:
            bad("output sanity: " + pr)
        bad_syms = {pr.split(":")[0] for pr in probs}
        plans = [x for x in plans if x["symbol"] not in bad_syms]   # fix: drop the broken plans
        removed += [{"symbol": s, "reason": "failed output sanity check"} for s in bad_syms]
    else:
        ok("all trade plans passed sanity checks (levels in order, quantity, risk, position cap)")

    # 5) journal + paper results
    tips_df = journal.update_outcomes(data_prices.load, lambda name: load_strategy(name if isinstance(name, str) else sname))
    paper = journal.paper_summary(tips_df, "tip")
    shadow = journal.paper_summary(tips_df, "shadow")
    paper_dd = 0.0
    closed = tips_df[(tips_df["kind"] == "tip") & (tips_df["status"] == "closed")].sort_values("exit_date")
    if len(closed):
        eq = capital + closed["pnl"].astype(float).cumsum()
        paper_dd = float((eq / np.maximum.accumulate(np.r_[capital, eq.values])[1:] - 1).min() * 100)
    open_paper = int(tips_df[(tips_df["kind"] == "tip") & tips_df["status"].isin(["open", "pending"])].shape[0])

    if settings.get("kill_switch"):
        blockers.insert(0, "Kill switch is ON in settings.yaml")
    if not g.get("passed") and not aggressive:
        blockers.append("Strategy not validated: it did not pass the validation gate (see the table below)")
    if aggressive:
        agg = tips_df[(tips_df["kind"] == "tip") & (tips_df["strategy"].astype(str).str.startswith("a"))]
        agg_pnl = float(agg["pnl"].astype(float).fillna(0).sum()) if len(agg) else 0.0
        if agg_pnl <= -capital * settings.get("aggressive_hard_stop_pct", 20) / 100:
            blockers.append(f"HARD STOP: aggressive tips have lost Rs {-agg_pnl:,.0f} "
                            f"(limit {settings.get('aggressive_hard_stop_pct', 20)}% of capital). Change the setting "
                            "only after reviewing what went wrong.")
    if state.get("auto_paused"):
        blockers.append(f"Automatic pause: {state['auto_paused']}")
    if not regime:
        blockers.append("Weak market: Nifty below its 200-day average or too few stocks in uptrends")
    if len(closed):
        eqc = capital + closed["pnl"].astype(float).cumsum()
        cur_dd = float(eqc.iloc[-1] / max(capital, eqc.max()) - 1) * 100
        breach = closed.loc[(eqc / np.maximum.accumulate(np.r_[capital, eqc.values])[1:] - 1) * 100
                            <= -p["drawdown_pause_pct"], "exit_date"]
        if cur_dd <= -p["drawdown_pause_pct"] and len(breach) and \
                (pd.Timestamp(d) - pd.Timestamp(breach.iloc[0])).days < 28:
            blockers.append(f"Drawdown {cur_dd:.1f}% exceeds the {p['drawdown_pause_pct']}% limit: "
                            f"4-week pause (capital protection)")
    slots = max(0, p["max_open_positions"] - open_paper)

    # Claude review (optional explainer)
    if settings.get("claude_review") and plans:
        msg = review.review(plans, int(settings.get("claude_review_max_stocks", 6)))
        health_items.append(("good", msg))

    tips = plans if not blockers else []
    day = str(d.date())
    if tips:
        journal.add_tips(day, tips, "tip", sname)
    elif plans:
        journal.add_tips(day, plans, "shadow", sname)   # tracked silently to measure the system

    paper_start = pd.Timestamp(settings.get("paper_start_date", day))
    weeks = (pd.Timestamp(day) - paper_start).days / 7
    in_paper = settings.get("mode", "paper") == "paper" or weeks < settings.get("paper_weeks", 8)
    mode_text = f"PAPER (week {int(weeks) + 1} of {settings.get('paper_weeks', 8)})" if in_paper else "LIVE"
    if aggressive:
        mode_text += " | AGGRESSIVE MODE - strategy NOT validated (your choice)"

    if tips:
        headline = (f"{len(tips)} trade idea(s) for tomorrow, best first. You can hold {slots} more position(s) "
                    f"- take them in order and skip any that open outside the buy zone.")
        if in_paper:
            headline = "PAPER MODE - do not use real money yet. " + headline
        if aggressive:
            headline = ("AGGRESSIVE MODE (not validated - higher risk, your choice): " + headline +
                        " Never risk more than the quantity shown.")
        why, money = [], None
    else:
        if not g.get("passed"):
            headline = "No tips: strategy not validated. Use the index fund."
            money = ("Put long-term money in a low-cost Nifty 50 index fund or NIFTYBEES via SIP, and keep "
                     "short-term money in a liquid fund. The system will keep testing itself and will tell you "
                     "if a version ever passes the gate.")
        else:
            headline = "No tips today."
            money = None
        why = blockers or ["No stock met every rule today."]

    my = journal.load_my_trades()
    my_status = journal.monitor_my_trades(my, data_prices.load, p,
                                          lambda s: fundamentals.next_results_date(s, d)) if len(my) else []
    # forwarded tips (Telegram bot): update outcomes and show the scorecard
    try:
        from . import tipcheck
        fwd = tipcheck.source_scorecard()
    except Exception as e:
        log.warning("forwarded-tip scorecard failed: %s", e)
        fwd = {}
    for e in error_summary(since):
        health_items.append(("warn", "log: " + e))

    for pl in tips or plans:
        raw = data_prices.load(pl["symbol"])
        pl["chart"] = report.stock_chart(pl["symbol"], raw, pl, day)
        report.append_stock_note(pl["symbol"], day, pl, {"Shown as": "TIP" if tips else "shadow (not shown, tips blocked)"})

    ctx = {"day": day, "strategy": sname, "mode_text": mode_text, "headline": headline, "why": why,
           "money_advice": money, "market": market, "forwarded": fwd, "tips": tips, "removed": removed, "my_trades": my_status,
           "paper": paper, "shadow": shadow, "backtest_ref": bt_ref, "health": health_items,
           "gate_html": search_html() + gate_html(g),
           "paper_text": f"started {paper_start.date()}, {max(0, weeks):.1f} weeks so far; paper drawdown {paper_dd:.1f}%"}
    f = report.daily_html(ctx)

    lines = [f"Swing report {day}", headline] + [f"- {w}" for w in (why or [])]
    for i, pl in enumerate(tips, 1):
        lines.append(f"{i}. {pl['symbol']} ({pl['setup']}) buy {pl['entry_low']}-{pl['entry_high']}, "
                     f"stop {pl['stop']}, T1 {pl['target1']}, T2 {pl['target2']}, qty {pl['qty']}")
    for s in my_status:
        lines.append(f"[Your trade] {s['symbol']}: {s['status']}")
    lines.append(DISCLAIMER)
    tg = telegram.send(settings, "\n".join(lines))
    state = load_state()
    state.update({"last_nightly_run": str(datetime.now()), "last_report": str(f), "last_trading_day": day,
                  "telegram": tg})
    save_state(state)
    log.info("Nightly done: %s (%d tips, %d shadow)", headline, len(tips), 0 if tips else len(plans))
    return f


def main():
    try:
        return run()
    except Exception:
        tb = traceback.format_exc()
        log.error("NIGHTLY RUN CRASHED:\n%s", tb)
        from .config import REPORTS
        msg = (f"<!doctype html><meta charset='utf-8'><title>Swing report error</title><body style='font-family:sans-serif'>"
               f"<h1>No tips today: the system hit an error</h1><p>{DISCLAIMER}</p>"
               f"<p>The nightly run crashed, so no tips are given. It will retry tomorrow. "
               f"Technical details (for Claude to fix) are in logs/system.log.</p><pre>{tb[-3000:]}</pre></body>")
        (REPORTS / "latest.html").write_text(msg, encoding="utf-8")
        (REPORTS / f"{date.today()}_error.html").write_text(msg, encoding="utf-8")
        st = load_state()
        st["last_crash"] = str(datetime.now())
        save_state(st)
        return None
