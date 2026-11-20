"""Saturday: the Learner report of every strategy that has a Kite test (results/learner/<name>.md) + a short
Telegram summary. The Learner only reports and suggests - it never changes a strategy or a setting."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import on_github, load_settings, DATA
    from swing.daemon import claim
    if on_github() and not claim("learner"):
        sys.exit(0)
    from swing import learner, telegram
    from swing.strategy import load_all
    lines = []
    for name in load_all():
        if (DATA / "tests" / f"{name}.parquet").exists():
            a = learner.analyse(name)
            learner.report(name)
            t, lv = a.get("test", {}), a.get("live", {})
            lines.append(f"• {name}: test {t.get('win_pct', '-')}% won ({t.get('trades', 0):,}), live "
                         f"{lv.get('win_pct', '-')}% ({lv.get('trades', 0)}); ideas: {len(a.get('ideas', []))}")
    if lines:
        telegram.send(load_settings(), "🧠 Weekly Learner\n" + "\n".join(lines) + "\n/learn NAME for details.", label="learner")
    try:
        from swing.ci_save import save
        save("learner")
    except Exception as e:
        print("save failed:", e)
