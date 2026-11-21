"""After the long test: the strategy search (swing/strategy_search.py) -> results/strategy_search.md, the winners
switched on in data/practice_params.json and a Telegram summary. Runs outside market hours. A failure is NOT
counted as done: the error goes to results/strategy_search_error.md and the search is tried again, at most 3 times."""
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import DATA, RESULTS
    from swing import strategy_search
    att_f = DATA / "strategy_search_attempts.txt"
    n = int(att_f.read_text() or 0) + 1 if att_f.exists() else 1
    att_f.write_text(str(n))
    try:
        strategy_search.run(send=True)
        (DATA / "strategy_search_done.txt").write_text("done")
        (RESULTS / "strategy_search_error.md").unlink(missing_ok=True)
    except Exception as e:
        tb = traceback.format_exc()
        print("strategy search failed:", type(e).__name__, str(e)[:300])
        (RESULTS / "strategy_search_error.md").write_text(f"# Strategy search failed (attempt {n})\n\n```\n{tb[-6000:]}\n```\n")
        if n >= 3:
            (DATA / "strategy_search_done.txt").write_text(f"gave up after {n} attempts: {type(e).__name__}")
    try:
        from swing.ci_save import save
        save("strategy search")
    except Exception as e:
        print("save failed:", e)
