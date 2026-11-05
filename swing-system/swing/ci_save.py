"""Saves non-personal results back to GitHub at the end of a GitHub Actions run (no Claude needed).

The workflow's own save step (on the default branch) did `git pull --rebase` with unstaged files present, which
fails, so the push was rejected and results were lost between runs. This runs first, from the branch code:
commit the fixed list of non-personal files, rebase onto the remote with --autostash (other changes kept aside),
push with retries. Trades, forwarded tips, reports and price data are never committed (they stay private).
Does nothing outside GitHub Actions."""
import logging
import os
import subprocess
import time

from .config import ROOT

log = logging.getLogger("swing.ci_save")

SAVE = ["journal/tips.csv", "journal/company_picks.csv", "validation", "strategies", "stocks", "library",
        "IMPROVEMENTS.md", "CHANGELOG.md", "settings.yaml", "ROADMAP.md", "data/universe_history.csv",
        "data/quarantine.json", "data/no_yahoo_data.json"]


def _git(*a, check=False):
    r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()[:300]}")
    return r


def save(label):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return "skipped (not on GitHub)"
    branch = os.environ.get("SWING_BRANCH") or _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    _git("config", "user.name", "swing-system-bot")
    _git("config", "user.email", "swing-system-bot@users.noreply.github.com")
    _git("add", "--", *[p for p in SAVE if (ROOT / p).exists()])
    if _git("diff", "--cached", "--quiet").returncode == 0:
        return "nothing new to save"
    _git("commit", "-m", f"swing-system: {label} {os.environ.get('GITHUB_RUN_ID', '')}".strip(), check=True)
    for attempt in range(5):
        _git("fetch", "origin", branch)
        rb = _git("rebase", "--autostash", "-X", "theirs", f"origin/{branch}")   # theirs = this run's results win
        if rb.returncode:
            _git("rebase", "--abort")
            log.warning("rebase failed (%s); retrying", rb.stderr.strip()[:200])
        else:
            p = _git("push", "origin", f"HEAD:{branch}")
            if p.returncode == 0:
                return "saved"
            log.warning("push rejected (%s); retrying", p.stderr.strip()[:200])
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("could not save results to GitHub after 5 tries")
