"""Once 5-minute history is complete: the long test of the practice rules (swing/longtest.py) -> results/long_test.md
and a Telegram summary. Runs outside market hours. A failure is NOT counted as done: the full error goes to
results/long_test_error.md (readable at once) and the test is tried again, at most 3 times."""
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import DATA, RESULTS
    from swing import longtest
    att_f = DATA / "long_test_attempts_v2.txt"
    n = int(att_f.read_text() or 0) + 1 if att_f.exists() else 1
    att_f.write_text(str(n))
    try:
        longtest.run(send=True)
        (DATA / "long_test_done_v2.txt").write_text("done")
        (RESULTS / "long_test_error.md").unlink(missing_ok=True)
    except Exception as e:
        tb = traceback.format_exc()
        print("long test failed:", type(e).__name__, str(e)[:300])
        (RESULTS / "long_test_error.md").write_text(f"# Long test failed (attempt {n})\n\n```\n{tb[-6000:]}\n```\n")
        if n >= 3:
            (DATA / "long_test_done_v2.txt").write_text(f"gave up after {n} attempts: {type(e).__name__}")
    try:
        from swing.ci_save import save
        save("long test")
    except Exception as e:
        print("save failed:", e)
