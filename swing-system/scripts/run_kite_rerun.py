"""Everything again on Kite data (owner 19 Nov) - daemon job after the research job, once Kite history is complete.
Runs vantage-ai/validation/kite_rerun_all.py (all trade lists rebuilt from Kite prices, every main test re-run),
saves the results (journal/kite_rerun.md + journal/kite_rerun/*.json, no prices) and tells the owner on Telegram."""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import on_github, DATA, load_settings
    from swing.daemon import claim
    if on_github() and not claim("kite_rerun"):
        print("kite_rerun: already done (skipped)")
        sys.exit(0)
    script = Path(__file__).resolve().parents[2] / "vantage-ai" / "validation" / "kite_rerun_all.py"
    r = subprocess.run([sys.executable, str(script)], timeout=6 * 3600, capture_output=True, text=True)
    print((r.stdout or "")[-3000:])
    from swing import telegram
    s = load_settings()
    if r.returncode == 0:
        (DATA / "kite_rerun").mkdir(parents=True, exist_ok=True)
        (DATA / "kite_rerun" / "done.txt").write_text("done")
        telegram.send(s, "📊 ATLAS re-ran EVERY test on Kite's exchange data (trade lists rebuilt, all rounds, lab, "
                         "behaviour groups, Foundry). Yahoo vs Kite side by side: journal/kite_rerun.md", label="research result")
    else:
        print("kite rerun failed:", (r.stderr or "")[-600:])
        telegram.send(s, "⚠️ The full re-run on Kite data stopped with an error; it will be fixed and run again. "
                         "Your tips are not affected.", label="system problem")
    try:
        from swing.ci_save import save
        save("everything re-run on Kite data")
    except Exception as e:
        print("save failed:", e)
