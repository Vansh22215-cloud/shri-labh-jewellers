"""Weekly SAFE self-improvement session (Windows Task Scheduler, Saturdays).

Steps:
  1. Copy the code into sandbox/ and run the test suite there (live code is untouched).
  2. Auto-rollback check: if live paper performance has deteriorated beyond the
     threshold, roll back to the previous version (or pause tips if there is none).
  3. Re-validate the live version on the newest data (updates the gate).
  4. Test every proposal in IMPROVEMENTS.md whose reason was written BEFORE this run.
     Promote only if it (a) passes the full gate, (b) beats the live version in a
     majority of walk-forward periods AND has higher walk-forward CAGR. Recent trades
     alone never change live logic.
  5. Measure whether the optional Claude review has helped.
  6. Rotate the holdout when it gets long; optionally ask Claude for new proposals
     (they are only tested NEXT week, so the reason always precedes the test).
Everything is recorded in CHANGELOG.md.
"""
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import date

import pandas as pd

from . import journal, validate, validation_report
from .config import DATA as DATA_DIR, ROOT, STRATEGIES, get_logger, load_settings, load_state, load_strategy, save_state

log = get_logger()
IMPROVEMENTS = ROOT / "IMPROVEMENTS.md"
CHANGELOG = ROOT / "CHANGELOG.md"
BLOCK = re.compile(r"```proposal\n(.*?)```", re.S)

ROLLBACK_MIN_TRADES = 20
ROLLBACK_PAPER_DD = 15.0


def changelog(text):
    with open(CHANGELOG, "a", encoding="utf-8") as f:
        f.write(f"\n## {date.today()} (automatic)\n{text}\n")


def parse_proposals():
    txt = IMPROVEMENTS.read_text(encoding="utf-8")
    out = []
    for m in BLOCK.finditer(txt):
        d = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                d[k.strip()] = v.strip()
        d["_raw"] = m.group(0)
        out.append(d)
    return out


def set_proposal_status(raw, status):
    txt = IMPROVEMENTS.read_text(encoding="utf-8")
    new = re.sub(r"status:.*", f"status: {status}", raw, count=1)
    IMPROVEMENTS.write_text(txt.replace(raw, new), encoding="utf-8")


def set_live(name):
    f = ROOT / "settings.yaml"
    s = f.read_text(encoding="utf-8")
    s = re.sub(r"(?m)^live_strategy:.*$", f"live_strategy: {name}", s)
    f.write_text(s, encoding="utf-8")


def versions():
    return sorted((p.stem for p in STRATEGIES.glob("v*.json")), key=lambda x: int(x[1:]))


def sandbox_tests():
    sb = ROOT / "sandbox" / str(date.today())
    if sb.exists():
        shutil.rmtree(sb)
    for d in ("swing", "strategies", "tests", "validation"):
        shutil.copytree(ROOT / d, sb / d, ignore=shutil.ignore_patterns("__pycache__", "*.png", "*.html", "trades_*"))
    shutil.copy(ROOT / "settings.yaml", sb / "settings.yaml")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=sb, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1]


def rollback_check(settings, bt):
    live = settings["live_strategy"]
    tips = journal.load_tips()
    mine = tips[(tips["strategy"] == live) & (tips["status"] == "closed")]
    s = journal.paper_summary(mine.assign(kind="x"), "x")
    msg = f"Paper check for {live}: {s}"
    if s.get("closed", 0) < ROLLBACK_MIN_TRADES:
        return msg + f" - fewer than {ROLLBACK_MIN_TRADES} closed trades, too early to judge (no action)."
    eq = settings["capital"] + mine.sort_values("exit_date")["pnl"].astype(float).cumsum()
    dd = float((eq / eq.cummax() - 1).min() * 100)
    worse = (bt.get("avg_r") is not None and s["avg_r"] < bt["avg_r"] - 2 * (s.get("r_std_err") or 0) and s["avg_r"] < 0)
    if worse or dd <= -ROLLBACK_PAPER_DD:
        vs = versions()
        prev = vs[vs.index(live) - 1] if live in vs and vs.index(live) > 0 else None
        why = f"avg R {s['avg_r']} vs backtest {bt.get('avg_r')}, paper drawdown {dd:.1f}%"
        if prev:
            set_live(prev)
            changelog(f"- ROLLBACK: {live} -> {prev}. Reason: live paper performance deteriorated ({why}).")
            return msg + f" - ROLLED BACK to {prev}."
        st = load_state()
        st["auto_paused"] = f"{live} paper results deteriorated ({why}); no earlier version to roll back to"
        save_state(st)
        changelog(f"- AUTO-PAUSE: tips paused. {st['auto_paused']}")
        return msg + " - tips PAUSED."
    return msg + " - within tolerance."


def claude_effect():
    t = journal.load_tips()
    t = t[(t["status"] == "closed") & t["claude_verdict"].notna() & (t["claude_verdict"].astype(str) != "")]
    if len(t) < 20:
        return f"Claude review: {len(t)} reviewed trades closed - too few to judge; it remains an explainer only."
    g = t.groupby("claude_verdict")["r_multiple"].agg(["count", "mean"]).round(2)
    ok = g["mean"].get("OK")
    caut = g.drop(index="OK", errors="ignore")
    helped = ok is not None and len(caut) and (caut["mean"] < ok).all()
    return (f"Claude review by verdict (count, avg R): {g.to_dict('index')}. "
            + ("Trades Claude flagged did worse - review appears useful (still advisory only)."
               if helped else "No evidence the review improves results - kept as an explainer only."))


def tip_checker_review(min_tips=30):
    """Is the Telegram tip-checker's verdict actually useful? (GOOD tips should beat AVOID tips.)"""
    from . import tipcheck
    sc = tipcheck.source_scorecard()
    bv = sc.get("by_verdict", {}) if sc else {}
    n = sum(v["tips"] for v in bv.values())
    if n < min_tips:
        return f"Tip checker: {n} forwarded tips resolved so far - need {min_tips} before judging its verdicts."
    good, avoid = bv.get("GOOD"), bv.get("AVOID")
    if good and avoid and good["target_hit_pct"] <= avoid["target_hit_pct"]:
        msg = (f"Tip checker WARNING: GOOD tips hit target {good['target_hit_pct']}% vs AVOID {avoid['target_hit_pct']}% "
               f"- its verdicts are not helping; flagged in IMPROVEMENTS.md for review.")
        with open(IMPROVEMENTS, "a", encoding="utf-8") as f:
            f.write(f"\n- {date.today()}: {msg} (needs a human/Claude review of tipcheck.py rules)\n")
        return msg
    return f"Tip checker verdicts by outcome: {bv}"


def rotate_holdout(data_end):
    hs = pd.Timestamp(validate.holdout_start())
    if (pd.Timestamp(data_end) - hs).days > 30 * 30.4:
        new = (hs + pd.DateOffset(months=12)).date()
        h = json.loads(validate.HOLDOUT_FILE.read_text())
        h.setdefault("history", []).append({"old_start": str(hs.date()), "new_start": str(new), "on": str(date.today())})
        h["start"] = str(new)
        validate.HOLDOUT_FILE.write_text(json.dumps(h, indent=1))
        changelog(f"- Holdout rotated: {hs.date()} -> {new} (older data joins walk-forward).")
        return f"Holdout rotated to start {new}"
    return f"Holdout unchanged (starts {hs.date()})"


def ask_claude_for_proposals(summary):
    exe = shutil.which("claude")
    if not exe:
        return "Claude CLI not found; no new proposals drafted."
    prompt = ("You help maintain a swing-trading research system. Based on this weekly summary, propose AT MOST 2 "
              "simple, economically-motivated parameter changes (not curve fitting). Output ONLY blocks like:\n"
              "```proposal\nid: Cx\nstatus: proposed\nwritten: " + str(date.today()) +
              "\nreason: <one sentence why this should work, written before testing>\n"
              "overrides: {\"param\": value}\n```\nAllowed params: " + ", ".join(load_strategy("v1").keys()) +
              "\n\nSUMMARY:\n" + summary)
    try:
        r = subprocess.run([exe, "-p", prompt], capture_output=True, text=True, timeout=300, encoding="utf-8")
        blocks = BLOCK.findall(r.stdout or "")
        if blocks:
            with open(IMPROVEMENTS, "a", encoding="utf-8") as f:
                for b in blocks[:2]:
                    f.write("\n```proposal\n" + b.strip() + "\n```\n")
        return f"Claude drafted {len(blocks[:2])} proposal(s) for NEXT week's test."
    except Exception as e:
        return f"Claude proposal step failed: {e}"


def refresh_aggressive(out, settings):
    """Aggressive mode follows the walk-forward search's CURRENT pick (re-chosen monthly from the last 36 months)."""
    cur = settings.get("aggressive_strategy", "a1")
    try:
        cur_p = load_strategy(cur)
    except Exception:
        cur_p = {}
    pick = out["latest_pick"]
    if cur_p.get("search_variant") == pick["variant"]:
        return f"Aggressive mode keeps {cur} ({pick['how']})."
    aggs = sorted((p.stem for p in STRATEGIES.glob("a*.json")), key=lambda x: int(x[1:]))
    n = int(aggs[-1][1:]) + 1 if aggs else 1
    newp = dict(pick["params"], name=f"a{n}", created=str(date.today()), search_variant=pick["variant"],
                risk_per_trade_pct=1.0, drawdown_pause_pct=10,
                description="AGGRESSIVE MODE (NOT validated): walk-forward search pick - " + pick["how"])
    (STRATEGIES / f"a{n}.json").write_text(json.dumps(newp, indent=2))
    f = ROOT / "settings.yaml"
    f.write_text(re.sub(r"(?m)^aggressive_strategy:.*$", f"aggressive_strategy: a{n}", f.read_text(encoding="utf-8")),
                 encoding="utf-8")
    changelog(f"- Aggressive mode switched {cur} -> a{n}: {pick['how']} (monthly re-pick from the last 36 months).")
    return f"Aggressive mode switched to a{n}: {pick['how']}."


def tips_strategy(settings):
    """The strategy that currently produces tips: the validated live version, or the aggressive one."""
    from .nightly import gate_status
    live = settings["live_strategy"]
    if settings.get("tips_mode") == "aggressive" and not gate_status(live).get("passed"):
        return settings.get("aggressive_strategy", "a1"), True
    return live, False


def compute_stats(params, capital=45000.0):
    """Per-trade statistics of a strategy for the Telegram cards (walk-forward span; holdout shown separately)."""
    from . import backtest, data_prices, engine
    P, sig, *_ = engine.build(params)
    lf = data_prices.liquid_fund_nav()
    hs = pd.Timestamp(validate.HOLDOUT_START)
    eq, tr, _ = backtest.run(P, sig, params, validate.WF_START, hs - pd.Timedelta(days=1), capital, lf)
    heq, htr, _ = backtest.run(P, sig, params, hs, P["close"].index[-1], capital, lf)
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    out = {"period": f"{eq.index[0]:%Y-%m} to {eq.index[-1]:%Y-%m}",
           "cagr_pct": round(((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100, 2),
           "max_drawdown_pct": round((eq / eq.cummax() - 1).min() * 100, 2), "trades": int(len(tr)),
           "holdout_return_pct": round((heq.iloc[-1] / heq.iloc[0] - 1) * 100, 2) if len(heq) else None,
           "holdout_period": f"{hs:%Y-%m} to {P['close'].index[-1]:%Y-%m}", "holdout_trades": int(len(htr))}
    if len(tr):
        w, l_ = tr[tr["pnl"] > 0], tr[tr["pnl"] <= 0]
        streak = mx = 0
        for x in tr["pnl"]:
            streak = streak + 1 if x <= 0 else 0
            mx = max(mx, streak)
        out.update({"win_rate_pct": round(len(w) / len(tr) * 100, 1),
                    "trades_per_month": round(len(tr) / (yrs * 12), 1), "avg_days_held": round(tr["days"].mean(), 1),
                    "avg_win_rs": int(round(w["pnl"].mean())) if len(w) else 0,
                    "avg_loss_rs": int(round(l_["pnl"].mean())) if len(l_) else 0,
                    "avg_per_trade_rs": int(round(tr["pnl"].mean())),
                    "time_exits_pct": int(round((tr["exit_reason"].astype(str).str.contains("time")).mean() * 100)),
                    "max_losing_streak": int(mx)})
    return out


def test_proposal(prop, settings, live, live_res=None, live_table=None):
    """Test ONE pre-registered proposal against the strategy that currently gives tips.
    Validated line (vN): promote only if it passes the full gate AND beats the base in most walk-forward
    periods AND has higher walk-forward CAGR.
    Aggressive line (aN, already unvalidated): promote if it beats the base in most walk-forward periods,
    has higher walk-forward CAGR AND its walk-forward drawdown is not worse by more than 2 points.
    The holdout is never used to decide (D60)."""
    if not prop.get("reason") or not prop.get("written") or prop["written"] > str(date.today()):
        set_proposal_status(prop["_raw"], "rejected (no reason/date written before testing)")
        return "Rejected proposal without a pre-written reason"
    try:
        overrides = json.loads(prop.get("overrides", "{}"))
    except Exception:
        set_proposal_status(prop["_raw"], "rejected (overrides not valid JSON)")
        return "Rejected proposal with invalid overrides"
    base, aggressive = tips_strategy(settings)
    base_p = load_strategy(base)
    if base != live or live_res is None:
        live_res, _, live_table = validation_report.run(base, params=base_p, note="base for proposal", write=False)
    base_wf = live_table[live_table["period"].str.startswith("WF")].set_index("period")
    cand = dict(base_p, **overrides)
    cand["name"] = f"candidate-{prop.get('id')}"
    res, _, table = validation_report.run(cand["name"], params=cand, note=f"proposal {prop.get('id')}", write=False)
    wf = table[table["period"].str.startswith("WF")].set_index("period")
    common = wf.index.intersection(base_wf.index)
    wins = int((wf.loc[common, "total_return_pct"] > base_wf.loc[common, "total_return_pct"]).sum())
    c_new, c_old = res["continuous"].get("cagr_pct", -99), live_res["continuous"].get("cagr_pct", -99)
    dd_new, dd_old = res["continuous"].get("max_drawdown_pct", -99), live_res["continuous"].get("max_drawdown_pct", -99)
    # The more ideas have been tried, the bigger the improvement must be (protection against lucky flukes, D75).
    n_tested = sum(1 for p_ in parse_proposals() if p_.get("status") != "proposed")
    margin = 0.25 * math.sqrt(math.log(max(n_tested, 2)))           # CAGR points
    need_wins = max(len(common) / 2, math.ceil(0.6 * len(common)) if n_tested >= 50 else 0)
    if aggressive:
        promote = wins > need_wins and c_new > c_old + margin and dd_new >= dd_old - 2
    else:
        promote = res["gate"]["passed"] and wins > len(common) / 2 and c_new > c_old
    summary = (f"{prop.get('id')} vs {base}: beat it in {wins}/{len(common)} walk-forward years, CAGR {c_new}% vs "
               f"{c_old}% (needs +{margin:.2f}), worst fall {dd_new}% vs {dd_old}%, gate {'PASS' if res['gate']['passed'] else 'FAIL'}")
    if not promote:
        set_proposal_status(prop["_raw"], f"rejected {date.today()} - {summary}")
        changelog(f"- Tested proposal {prop.get('id')}: rejected. {summary}")
        return "Rejected " + summary
    prefix = "a" if aggressive else "v"
    fam = sorted((x.stem for x in STRATEGIES.glob(f"{prefix}*.json")), key=lambda x: int(x[1:]))
    n = int(fam[-1][1:]) + 1
    newp = dict(cand, name=f"{prefix}{n}", created=str(date.today()),
                description=base_p.get("description", "") + f" | {prefix}{n}: {prop.get('reason')}")
    newp.pop("backtest_stats", None)                 # never carry the old strategy's numbers over
    try:
        newp["backtest_stats"] = compute_stats(newp)
    except Exception as e:
        log.warning("stats for %s%d failed: %s", prefix, n, e)
    (STRATEGIES / f"{prefix}{n}.json").write_text(json.dumps(newp, indent=2))
    if aggressive:
        f = ROOT / "settings.yaml"
        f.write_text(re.sub(r"(?m)^aggressive_strategy:.*$", f"aggressive_strategy: {prefix}{n}",
                            f.read_text(encoding="utf-8")), encoding="utf-8")
    else:
        set_live(f"{prefix}{n}")
        validation_report.run(f"{prefix}{n}", note=f"promoted from {prop.get('id')}")
    set_proposal_status(prop["_raw"], f"PROMOTED to {prefix}{n} on {date.today()} - {summary}")
    changelog(f"- PROMOTED proposal {prop.get('id')} as {prefix}{n} (previous {base} kept). {summary}")
    return "PROMOTED " + summary


def strategy_search(live, live_table, max_age_days=30):
    """Re-run the walk-forward strategy search monthly; promote its pick only if the search passes the gate."""
    from . import search
    f = ROOT / "validation" / "search_latest.json"
    out = json.loads(f.read_text()) if f.exists() else None
    if out is None or (pd.Timestamp.today() - pd.Timestamp(out["date"])).days > max_age_days:
        out = search.run_search()
    # Monthly re-run of the short-term and intraday searches too (results shown in the daily report).
    extra = []
    fs = ROOT / "validation" / "search_short.json"
    o2 = json.loads(fs.read_text()) if fs.exists() else None
    if o2 is None or (pd.Timestamp.today() - pd.Timestamp(o2["date"])).days > max_age_days:
        o2 = search.run_search(space="short")
    extra.append(f"short-term search gate {'PASSED' if o2['passed'] else 'FAILED'}")
    fi = ROOT / "validation" / "search_intraday.json"
    o3 = json.loads(fi.read_text()) if fi.exists() else None
    if o3 is None or (pd.Timestamp.today() - pd.Timestamp(o3["date"])).days > max_age_days:
        from . import intraday, intraday_data, search_report
        intraday_data.download(__import__("swing.archive", fromlist=["x"]).intraday_universe())
        o3 = intraday.run_search()
        search_report.write_intraday()
    extra.append(f"intraday search gate {'PASSED' if o3['passed'] else 'FAILED'}"
                 + (" - live intraday plans are not built yet; tell Claude to build them" if o3["passed"] else ""))
    if o2["passed"] and not out["passed"]:
        out = o2   # promote the short-term pick through the same path below
    msg = (f"Strategy search ({out['variants_searched']} variants, {out['date']}): walk-forward picks beat "
           f"NIFTYBEES in {sum(p['beat_niftybees'] for p in out['picks'])} of {len(out['picks'])} years; "
           f"gate {'PASSED' if out['passed'] else 'FAILED'}; " + "; ".join(extra))
    if not out["passed"]:
        settings = load_settings()
        if settings.get("tips_mode") != "aggressive":
            return msg + " - nothing promoted."
        # D66: aggressive mode follows the COMBINED search (excess-over-liquid-fund selection), re-run monthly
        fc = ROOT / "validation" / "search_combined.json"
        oc = json.loads(fc.read_text()) if fc.exists() else None
        if oc is None or (pd.Timestamp.today() - pd.Timestamp(oc["date"])).days > max_age_days:
            oc = search.run_search(space="combined")
        if not oc["passed"]:
            return msg + " - nothing validated. " + refresh_aggressive(oc, settings)
        out = oc   # the combined search passed the gate -> promote it through the normal path below
    pick = out["latest_pick"]
    for v in versions():
        if load_strategy(v).get("search_variant") == pick["variant"] and load_strategy(v).get("search_date") == out["date"]:
            return msg + f" - already live as {v}."
    n = int(versions()[-1][1:]) + 1
    params = dict(pick["params"], name=f"v{n}", created=str(date.today()), search_variant=pick["variant"],
                  search_date=out["date"], description=f"Chosen by walk-forward search: {pick['how']}")
    (STRATEGIES / f"v{n}.json").write_text(json.dumps(params, indent=2))
    gs = json.loads(validate.GATE.read_text()) if validate.GATE.exists() else {}
    gs[f"v{n}"] = {"passed": True, "checks": out["checks"], "date": out["date"],
                   "variants_tried": out["search_procedures_tried"], "note": "validated by walk-forward search"}
    validate.GATE.write_text(json.dumps(gs, indent=1))
    set_live(f"v{n}")
    changelog(f"- PROMOTED search pick {pick['variant']} as v{n} ({pick['how']}); previous {live} kept. {msg}")
    return msg + f" - PROMOTED as v{n}."


def run():
    settings = load_settings()
    live = settings["live_strategy"]
    notes = []
    ok, msg = sandbox_tests()
    notes.append(f"Sandbox tests: {msg}")
    if not ok:
        changelog("- Weekly session aborted: sandbox tests failed. Live system untouched.")
        return notes

    live_res, _, live_table = validation_report.run(live, note="weekly re-validation")
    notes.append(f"Live {live} re-validated: gate {'PASSED' if live_res['gate']['passed'] else 'FAILED'}")
    notes.append(rollback_check(settings, live_res.get("wf_summary", {})))

    from .idea_factory import top_up
    top_up(min_open=8, n_new=8)            # weekend batch: test up to 8 ideas
    try:   # refresh the owner's pattern-library implementation audit (library/IMPLEMENTATION_AUDIT.md)
        from .audit import build as build_audit
        cnt = build_audit().sum()
        notes.append(f"Pattern library: {int(cnt.get('implemented', 0))} items built, "
                     f"{int(cnt.get('not_yet_implemented', 0))} still to build, {int(cnt.get('blocked_by_data', 0))} need paid data")
    except Exception as e:
        notes.append(f"pattern-library audit failed: {e}")
    for prop in parse_proposals():
        if prop.get("status") == "proposed":
            notes.append(test_proposal(prop, settings, live, live_res, live_table))
            if notes[-1].startswith("PROMOTED"):
                break   # one change per week

    notes.append(strategy_search(live, live_table))
    notes.append(tip_checker_review())
    notes.append(claude_effect())
    notes.append(rotate_holdout(live_res["data_end"]))
    if settings.get("claude_review"):
        notes.append(ask_claude_for_proposals("\n".join(notes)))
    notes.append(f"Variants tried so far: {validate.n_variants()}")
    try:   # lifelong data store status + backups to your own Telegram (trades/tips weekly, data archive monthly)
        from . import archive
        notes.append(archive.stats_line())
        notes += archive.send_backups(settings)
    except Exception as e:
        notes.append(f"archive/backup step failed: {e}")
    changelog("- Weekly session summary:\n" + "\n".join(f"  - {n}" for n in notes))
    return notes
