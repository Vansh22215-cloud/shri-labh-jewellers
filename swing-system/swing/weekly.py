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
import re
import shutil
import subprocess
import sys
from datetime import date

import pandas as pd

from . import journal, validate, validation_report
from .config import ROOT, STRATEGIES, get_logger, load_settings, load_state, load_strategy, save_state

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


def strategy_search(live, live_table, max_age_days=30):
    """Re-run the walk-forward strategy search monthly; promote its pick only if the search passes the gate."""
    from . import search
    f = ROOT / "validation" / "search_latest.json"
    out = json.loads(f.read_text()) if f.exists() else None
    if out is None or (pd.Timestamp.today() - pd.Timestamp(out["date"])).days > max_age_days:
        out = search.run_search()
    msg = (f"Strategy search ({out['variants_searched']} variants, {out['date']}): walk-forward picks beat "
           f"NIFTYBEES in {sum(p['beat_niftybees'] for p in out['picks'])} of {len(out['picks'])} years; "
           f"gate {'PASSED' if out['passed'] else 'FAILED'}")
    if not out["passed"]:
        return msg + " - nothing promoted."
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

    live_p = load_strategy(live)
    live_wf = live_table[live_table["period"].str.startswith("WF")].set_index("period")
    for prop in parse_proposals():
        if prop.get("status") != "proposed":
            continue
        if not prop.get("reason") or not prop.get("written") or prop["written"] > str(date.today()):
            set_proposal_status(prop["_raw"], "rejected (no reason/date written before testing)")
            continue
        try:
            overrides = json.loads(prop.get("overrides", "{}"))
        except Exception:
            set_proposal_status(prop["_raw"], "rejected (overrides not valid JSON)")
            continue
        cand = dict(live_p, **overrides)
        cand["name"] = f"candidate-{prop.get('id')}"
        res, _, table = validation_report.run(cand["name"], params=cand, note=f"proposal {prop.get('id')}", write=False)
        wf = table[table["period"].str.startswith("WF")].set_index("period")
        common = wf.index.intersection(live_wf.index)
        wins = int((wf.loc[common, "total_return_pct"] > live_wf.loc[common, "total_return_pct"]).sum())
        better_cagr = res["continuous"].get("cagr_pct", -99) > live_res["continuous"].get("cagr_pct", -99)
        promote = res["gate"]["passed"] and wins > len(common) / 2 and better_cagr
        summary = (f"{prop.get('id')}: gate {'PASS' if res['gate']['passed'] else 'FAIL'}, beat live in {wins}/{len(common)} "
                   f"walk-forward periods, WF CAGR {res['continuous'].get('cagr_pct')}% vs live "
                   f"{live_res['continuous'].get('cagr_pct')}%, WF maxDD {res['continuous'].get('max_drawdown_pct')}% vs "
                   f"{live_res['continuous'].get('max_drawdown_pct')}%")
        if promote:
            n = int(versions()[-1][1:]) + 1
            newp = dict(cand, name=f"v{n}", created=str(date.today()),
                        description=live_p["description"] + f" | v{n}: {prop.get('reason')}")
            (STRATEGIES / f"v{n}.json").write_text(json.dumps(newp, indent=2))
            set_live(f"v{n}")
            validation_report.run(f"v{n}", note=f"promoted from {prop.get('id')}")
            set_proposal_status(prop["_raw"], f"PROMOTED to v{n} on {date.today()} - {summary}")
            changelog(f"- PROMOTED proposal {prop.get('id')} as v{n} (previous {live} kept). {summary}")
            notes.append("PROMOTED " + summary)
            break   # one change per week
        set_proposal_status(prop["_raw"], f"rejected {date.today()} - {summary}")
        changelog(f"- Tested proposal {prop.get('id')}: rejected. {summary}")
        notes.append("Rejected " + summary)

    notes.append(strategy_search(live, live_table))
    notes.append(claude_effect())
    notes.append(rotate_holdout(live_res["data_end"]))
    if settings.get("claude_review"):
        notes.append(ask_claude_for_proposals("\n".join(notes)))
    notes.append(f"Variants tried so far: {validate.n_variants()}")
    changelog("- Weekly session summary:\n" + "\n".join(f"  - {n}" for n in notes))
    return notes
