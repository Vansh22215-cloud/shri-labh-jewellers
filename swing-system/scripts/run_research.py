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
