"""Once 5-minute history is complete: the long test of the practice rules (swing/longtest.py) -> results/long_test.md
and a Telegram summary. Runs outside market hours."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import DATA
    from swing import longtest
    try:
        longtest.run(send=True)
        (DATA / "long_test_done.txt").write_text("done")
    except Exception as e:
        print("long test failed:", type(e).__name__, str(e)[:300])
        (DATA / "long_test_done.txt").write_text(f"failed: {type(e).__name__}")
    try:                                   # changed Kite files -> the private R2 bucket (when set up)
        from swing import r2
        r2.push()
    except Exception as e:
        print("R2 upload failed:", type(e).__name__)
    try:
        from swing.ci_save import save
        save("long test")
    except Exception as e:
        print("save failed:", e)
