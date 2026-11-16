"""Run at the end of every GitHub run: start the next always-on run, so the system never stops.

Why: GitHub's free scheduler drops most scheduled runs and an outside timer (cron-job.org) can fail too. With
this, each run hands over to the next one (~1 minute gap), all day, every day, with nothing outside GitHub.
Uses only the run's own short-lived GitHub key (GITHUB_TOKEN, given by GitHub to every run, valid for that run only).
Safety: does nothing if another run is already waiting; stops itself (and tells you on Telegram) if runs keep
ending within minutes (a crash loop), so a broken update can never start hundreds of runs. Turn off with
`keep_alive: false` in settings.yaml.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests

from swing.config import DATA, load_settings

LOG = DATA / "keep_alive.json"
API = "https://api.github.com"


def failed_steps(repo, run_id, h):
    """Names of the steps of THIS run that failed (e.g. package install, the bot itself)."""
    try:
        jobs = requests.get(f"{API}/repos/{repo}/actions/runs/{run_id}/jobs", headers=h, timeout=20).json()
        return [s["name"] for j in jobs.get("jobs", []) for s in j.get("steps", [])
                if s.get("conclusion") == "failure"]
    except Exception:
        return []


def alert_failure(names):
    """D108: tell the owner once per 6 hours when a run failed, with what to do - the system must never die silently."""
    f = DATA / "failure_alert.json"
    try:
        last = json.loads(f.read_text()).get("t", 0)
    except Exception:
        last = 0
    if not names or time.time() - last < 6 * 3600:
        return False
    try:
        from swing import telegram
        telegram.send(load_settings(), "⚠️ System problem: a GitHub run failed at: " + ", ".join(names)[:300] +
                      ".\nThe system restarts itself automatically. If this message keeps coming for a day, open "
                      "GitHub → Actions → the failed run to see why (or ask Claude once).", label="system problem")
        f.write_text(json.dumps({"t": time.time()}))
        return True
    except Exception:
        return False


def main():
    if not os.environ.get("GITHUB_ACTIONS"):
        return "not on GitHub"
    if not load_settings().get("keep_alive", True):
        return "keep_alive is off in settings.yaml"
    token, repo = os.environ.get("GH_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not token or not repo:
        return "no GitHub key in this run (workflow needs the keep-alive step)"
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    alert_failure([n for n in failed_steps(repo, run_id, h) if "next run" not in n.lower()])
    # 1) another run already waiting/running? then it carries on
    for status in ("queued", "pending", "waiting", "in_progress"):
        try:
            runs = requests.get(f"{API}/repos/{repo}/actions/workflows/swing.yml/runs",
                                params={"status": status, "per_page": 10}, headers=h, timeout=20).json()
            if any(str(r.get("id")) != str(run_id) for r in runs.get("workflow_runs", [])):
                return f"another run is already {status}"
        except Exception:
            pass
    # 2) crash-loop guard: count recent hand-overs from runs that ended within minutes (a healthy run that ends
    #    early on purpose - e.g. to pick up new program code - is not counted)
    now = time.time()
    try:
        hist = [t for t in json.loads(LOG.read_text()) if now - t < 3600]
    except Exception:
        hist = []
    lasted_min = None
    try:
        info = requests.get(f"{API}/repos/{repo}/actions/runs/{run_id}", headers=h, timeout=20).json()
        from datetime import datetime
        started = datetime.fromisoformat(info["run_started_at"].replace("Z", "+00:00")).timestamp()
        lasted_min = (now - started) / 60
    except Exception:
        pass
    if lasted_min is not None and lasted_min >= 8:
        hist = []                                    # this run was healthy: reset the counter
    if len(hist) >= 4:
        try:
            from swing import telegram
            telegram.send(load_settings(), "⚠️ System check: GitHub runs keep ending within minutes, so the automatic "
                                           "restart paused itself. The next scheduled or cron-job.org run restarts it. "
                                           "Open a Claude session if this repeats.", label="system problem")
        except Exception:
            pass
        LOG.write_text(json.dumps([]))
        return "paused: 4 restarts in the last hour (crash-loop guard)"
    # 3) start the next run
    for i in range(4):
        try:
            r = requests.post(f"{API}/repos/{repo}/actions/workflows/swing.yml/dispatches", headers=h, timeout=20,
                              json={"ref": os.environ.get("GITHUB_REF_NAME", "main"), "inputs": {"task": "bot"}})
            if r.status_code == 204:
                LOG.write_text(json.dumps(hist + [now]))
                return "next run started"
            last = f"HTTP {r.status_code}"
            if r.status_code in (401, 403, 404, 422):
                break
        except Exception as e:
            last = type(e).__name__
        time.sleep(2 ** (i + 1))
    return f"could not start the next run ({last})"


if __name__ == "__main__":
    print("keep-alive:", main())
