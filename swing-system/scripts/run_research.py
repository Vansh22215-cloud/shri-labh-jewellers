"""Daily research session (GitHub Actions, weekdays 20:17 IST): test as many pre-registered ideas from
IMPROVEMENTS.md as fit in the time budget (research_minutes_budget, default 120 min on GitHub, else
research_ideas_per_run ideas), refresh the market-regime study, send a Telegram summary, save results."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swing import research, telegram, weekly  # noqa: E402
from swing.config import load_settings

if __name__ == "__main__":
    from swing.config import on_github
    from swing.daemon import claim
    if on_github() and not claim("research"):
        print("research: already done (skipped)")
        sys.exit(0)
    s = load_settings()
    notes = []
    kite_ready = False
    try:   # owner 19-20 Nov: research only on STRICT Kite data. The downloads run in their own job ('kite_download',
        from swing import kite_daily          # 6:55 pm); here: wait until Kite history is complete, then re-check
        kite_ready = kite_daily.coverage() >= 0.9
        if kite_ready:
            from swing.config import DATA as _D
            flag = _D / "kite_daily" / "recheck_done.txt"
            import datetime as _dt
            kite_daily.coverage_report()
            if not flag.exists() or _dt.date.today().weekday() == 4:
                kite_daily.audit()                                   # Kite vs Yahoo, verification only
            if not flag.exists():
                import subprocess
                rc = Path(__file__).resolve().parents[2] / "vantage-ai" / "validation" / "kite_recheck.py"
                r = subprocess.run([sys.executable, str(rc)], timeout=5400, capture_output=True, text=True)
                if r.returncode == 0:
                    flag.write_text(str(_dt.date.today()))
                else:
                    print("kite re-check failed:", (r.stderr or "")[-300:].replace("\n", " | "))
        else:
            print("research: Kite history not complete yet - no price-based research tonight (strict Kite rule)")
    except Exception as e:
        print("kite check skipped:", type(e).__name__)
    if not kite_ready:
        sys.exit(0)
    try:   # AUTO-RESEARCH (owner 19 Nov: research must keep running without Claude) - once a week, Friday night
        import subprocess, datetime as _dt
        from swing.config import DATA
        last_f = DATA / "auto_research" / "last_run.txt"
        last = _dt.date.fromisoformat(last_f.read_text().strip()) if last_f.exists() else _dt.date(2000, 1, 1)
        today = _dt.date.today()
        due = (today - last).days >= 6 and (today.weekday() == 4 or (today - last).days >= 9)
        if due and s.get("auto_research", True):
            ar = Path(__file__).resolve().parents[2] / "vantage-ai" / "validation" / "autoresearch.py"
            import os as _os
            env = dict(_os.environ, SWING_PRICE_SOURCE="kite_strict") if kite_ready else None   # strict Kite once complete
            r = subprocess.run([sys.executable, str(ar), "--send"], timeout=3600, capture_output=True, text=True, env=env)
            print("auto-research:", (r.stdout or "").strip().splitlines()[-1:] or r.returncode)
            if r.returncode == 0:
                last_f.parent.mkdir(parents=True, exist_ok=True)
                last_f.write_text(str(today))
            else:
                print("auto-research failed:", (r.stderr or "")[-300:].replace("\n", " | "))
                telegram.send(s, "⚠️ The weekly automatic research could not run tonight (it tries again within a few days). "
                                 "Your tips are not affected.", label="system problem")
    except Exception as e:
        print("auto-research skipped:", type(e).__name__)
    from swing.idea_factory import top_up
    n_per_run = int(s.get("research_ideas_per_run", 2))
    top_up(min_open=n_per_run + 2, n_new=n_per_run + 2)   # make sure ideas written on EARLIER runs are waiting
    todo = [p for p in weekly.parse_proposals() if p.get("status") == "proposed" and p.get("written", "") < str(__import__("datetime").date.today())]
    if not todo:   # first run of the day: only ideas dated before today are tested (reason on record first)
        todo = [p for p in weekly.parse_proposals() if p.get("status") == "proposed"][:0]
    import os, time
    t0 = time.time()
    on_gh = os.environ.get("GITHUB_ACTIONS") == "true"
    budget = float(os.environ.get("SWING_RESEARCH_BUDGET") or s.get("research_minutes_budget", 120)) * 60 if on_gh else None
    tested, results = 0, []
    for prop in todo:
        if budget is None and tested >= n_per_run:
            break
        if budget is not None and time.time() - t0 > budget:
            break
        try:
            line = weekly.test_proposal(prop, load_settings(), s["live_strategy"])
        except Exception as e:
            line = f"{prop.get('id')}: test crashed ({e}) - skipped"
        tested += 1
        results.append(line)
        if line.startswith("PROMOTED"):
            notes.append(line)
            notes.append("🎉 Upgrade adopted - tomorrow's trades use the improved rules.")
            break
    rejected = [r for r in results if not r.startswith("PROMOTED")]
    notes.append(f"Tested {tested} ideas in {(time.time() - t0) / 60:.0f} min: "
                 f"{sum(r.startswith('PROMOTED') for r in results)} adopted, {len(rejected)} rejected")
    notes += rejected[:8]
    if len(rejected) > 8:
        notes.append(f"... and {len(rejected) - 8} more rejected (full list in IMPROVEMENTS.md)")
    if not todo:
        notes.append("No idea old enough to test yet (new ideas are written today and tested next run).")
    k = 80 if on_gh else n_per_run + 2                     # keep a big queue written today for the next runs
    new = top_up(min_open=k, n_new=k)
    if new:
        notes.append(f"{len(new)} new ideas written for the next runs" + (": " + "; ".join(new) if len(new) <= 3 else ""))
    research.run()
    notes.append(research.today_line())
    queued = len([p for p in weekly.parse_proposals() if p.get("status") == "proposed"])
    from swing.idea_factory import combo_ideas, family_ideas
    total = len(family_ideas()) + len(combo_ideas())
    msg = ("🔬 Daily research\n" + "\n".join(f"• {n}" for n in notes) +
           f"\n{queued} ideas queued; {total} candidate ideas in the library in all.")[:3900]
    from swing.config import public_print
    public_print(msg, "research message")
    adopted = [r for r in results if r.startswith("PROMOTED")]
    try:   # remember the day's numbers for the Saturday summary
        import json
        from swing.config import DATA
        f = DATA / "research_week.json"
        log_ = json.loads(f.read_text()) if f.exists() else {}
        log_[str(__import__("datetime").date.today())] = {"tested": tested, "adopted": len(adopted),
                                                            "adopted_lines": adopted[:2]}
        f.write_text(json.dumps(dict(sorted(log_.items())[-30:]), indent=1))
    except Exception as e:
        print("research log failed:", e)
    if adopted:   # owner: research is messaged only when it actually changes the tips
        print(telegram.send(load_settings(), "🎉 Strategy upgrade adopted tonight\n" + "\n".join(adopted[:2]) +
                            "\nFrom tomorrow, the tips use the improved rules (tested on 13 years, holdout untouched)."
                            "\nResearch, not advice.", label="research upgrade"))
    else:
        print("research: nothing adopted - no Telegram message (summary goes in Saturday's weekly)")
    try:   # on GitHub: keep the results for the next run (no Claude needed)
        from swing.ci_save import save
        print("save:", save("research run"))
    except Exception as e:
        print("saving results failed:", e)
