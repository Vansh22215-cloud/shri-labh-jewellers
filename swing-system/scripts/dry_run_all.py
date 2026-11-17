"""Practice run of every daily job, start to finish, on a COPY of the system: nothing reaches Telegram (messages go to
the copy's data/private/dry_run_messages.txt), nothing is saved to GitHub, and the real data is not touched.
Usage: python3 scripts/dry_run_all.py [work_dir]"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOBS = [("run_scan.py", {}), ("run_vantage.py", {"SWING_CLAIMED": "vantage2"}), ("run_nightly.py", {}),
        ("company_of_day.py", {}), ("run_basket.py", {}), ("run_research.py", {}), ("run_weekly.py", {})]


def main():
    work = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/swing_dry_run")
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    env = dict(os.environ, SWING_DRY_RUN="1", TELEGRAM_BOT_TOKEN="123456:dry-run", TELEGRAM_CHAT_ID="dry-run")
    env.pop("GITHUB_ACTIONS", None)
    out = work / "data" / "private" / "dry_run_messages.txt"
    rows = []
    for job, extra in JOBS:
        before = out.read_text(encoding="utf-8").count("----- ") if out.exists() else 0
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, str(work / "scripts" / job)], cwd=work, env=dict(env, **extra),
                               capture_output=True,
                               text=True, timeout=3600)
            code, tail = r.returncode, (r.stdout + r.stderr).strip().splitlines()[-3:]
        except subprocess.TimeoutExpired:
            code, tail = "timeout", []
        after = out.read_text(encoding="utf-8").count("----- ") if out.exists() else 0
        rows.append((job, code, round(time.time() - t0), after - before, tail))
        print(f"{job:22s} exit={code} {rows[-1][2]:5d}s messages={after - before}", flush=True)
        for line in tail:
            print("    ", line[:200], flush=True)
    bad = [r for r in rows if r[1] != 0]
    print("ALL JOBS OK" if not bad else f"{len(bad)} job(s) failed: {[r[0] for r in bad]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
