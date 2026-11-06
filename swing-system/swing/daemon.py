"""Keeps the system running on its own clock inside ONE GitHub Actions run.

Why: GitHub's free scheduler drops many scheduled runs (on 2026-11-04 only 1 of ~12 hourly runs fired), so
"one GitHub run per job" missed the morning scans. Now whenever ANY run starts (a scheduled one that does fire,
or the owner's one tap on "Run workflow"), it stays alive for up to ~5 hours 15 minutes and does every job on
time by itself:
  * answers Telegram (forwarded tips, /bought, /sold) every minute
  * hourly market scans 10:20-15:20 IST on weekdays
  * evening trades + company of the day 18:40 IST, research 20:17 IST, weekly check Saturday 10:17 IST
When it ends, the next queued run (GitHub keeps one waiting in the same group) starts and carries on.
Each job is claimed in data/jobs_done.json so nothing runs twice when a delayed scheduled run also arrives.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from .config import DATA, ROOT, get_logger

log = get_logger()
IST = timezone(timedelta(hours=5, minutes=30))
STATE = DATA / "jobs_done.json"
MAX_MIN = float(os.environ.get("SWING_DAEMON_MINUTES", 315))
SCAN_SLOTS = [(10, 20), (11, 20), (12, 20), (13, 20), (14, 20), (15, 20)]


def now():
    return datetime.now(IST)


def _load():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def claim(job, t=None):
    """Mark a job instance as done; False if it was already done (so the caller skips it)."""
    if os.environ.get("SWING_CLAIMED") == job:
        return True
    k = key(job, t)
    if k is None:
        return True
    st = _load()
    if st.get(k):
        return False
    st[k] = now().isoformat(timespec="minutes")
    for old in [x for x in st if x[-10:] < (now() - timedelta(days=10)).strftime("%Y-%m-%d")]:
        st.pop(old, None)
    STATE.write_text(json.dumps(st, indent=1))
    return True


def key(job, t=None):
    t = t or now()
    if job == "scan":
        slot = current_scan_slot(t)
        return None if slot is None else f"scan {slot:%H:%M} {t:%Y-%m-%d}"
    # a manual run outside the job's own time is not recorded (so it never blocks the real evening run)
    if job in ("nightly", "company") and (t.weekday() >= 5 or t.hour < 18):
        return None
    if job == "research" and (t.weekday() >= 5 or t.hour < 20):
        return None
    if job == "weekly" and (t.weekday() != 5 or t.hour < 10):
        return None
    return f"{job} {t:%Y-%m-%d}"


def failed(job, t=None, max_tries=3):
    """The job ran but did not finish its work (e.g. Telegram did not take the message): free it so the always-on
    run tries again a few minutes later - at most max_tries times a day, so a lasting problem cannot spam."""
    k = key(job, t)
    if k is None:
        return
    st = _load()
    tries = int(st.get("tries " + k, 0)) + 1
    st["tries " + k] = tries
    if tries < max_tries:
        st.pop(k, None)
    STATE.write_text(json.dumps(st, indent=1))
    log.warning("Daemon: %s did not complete (attempt %d of %d)", job, tries, max_tries)


def current_scan_slot(t):
    if t.weekday() >= 5:
        return None
    best = None
    for h, m in SCAN_SLOTS:
        s = t.replace(hour=h, minute=m, second=0, microsecond=0)
        if s <= t < s + timedelta(minutes=55):
            best = s
    return best


def due(t=None):
    t = t or now()
    st = _load()
    out = []
    if current_scan_slot(t) is not None and not st.get(key("scan", t)):
        out.append("scan")
    wd = t.weekday()
    if wd < 5 and t >= t.replace(hour=18, minute=40, second=0) and not st.get(key("nightly", t)):
        out.append("nightly")
    if wd < 5 and t >= t.replace(hour=18, minute=45, second=0) and not st.get(key("company", t)) \
            and (st.get(key("nightly", t)) or t >= t.replace(hour=19, minute=30)) and "nightly" not in out:
        out.append("company")
    if wd < 5 and t >= t.replace(hour=20, minute=17, second=0) and not st.get(key("research", t)) \
            and (st.get(key("nightly", t)) or t >= t.replace(hour=21, minute=30)):
        out.append("research")
    if wd == 5 and t >= t.replace(hour=10, minute=17, second=0) and not st.get(key("weekly", t)):
        out.append("weekly")
    return out


def jobs_today_line(t=None):
    """One line for the evening message: which of today's hourly scans ran."""
    t = t or now()
    st = _load()
    day = f"{t:%Y-%m-%d}"
    done = [f"{h}:{m:02d}" for h, m in SCAN_SLOTS if st.get(f"scan {h:02d}:{m:02d} {day}")]
    missed = [f"{h}:{m:02d}" for h, m in SCAN_SLOTS if not st.get(f"scan {h:02d}:{m:02d} {day}")]
    if t.weekday() >= 5:
        return "🩺 System: weekend, no market scans."
    if not missed:
        return f"🩺 System: all {len(SCAN_SLOTS)} market scans ran today."
    return (f"🩺 System: {len(done)} of {len(SCAN_SLOTS)} market scans ran today"
            + (f" (missed {', '.join(missed)} - GitHub did not start a run in time)" if missed else "") + ".")


SCRIPTS = {"scan": "run_scan.py", "nightly": "run_nightly.py", "company": "company_of_day.py", "research": "run_research.py", "weekly": "run_weekly.py"}


def run_job(job, minutes_left):
    if not claim(job):
        return
    env = dict(os.environ, SWING_CLAIMED=job,
               SWING_RESEARCH_BUDGET=str(max(10, min(120, minutes_left - 25))))
    log.info("Daemon: running %s", job)
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts" / SCRIPTS[job])], cwd=ROOT, env=env,
                       timeout=max(60, (minutes_left - 5) * 60))
    except Exception as e:
        log.warning("Daemon: %s failed: %s", job, type(e).__name__)


def run():
    from .bot import poll_once
    start = time.time()
    left = lambda: MAX_MIN - (time.time() - start) / 60
    answered = 0
    last_track = 0.0
    while left() > 2:
        if time.time() - last_track > 1800:    # forwarded calls: alert the owner when one is right / wrong
            last_track = time.time()
            for name, fn in (("views", "swing.market_views:track"), ("stock tips", "swing.tipcheck:update_and_notify")):
                try:
                    mod, f = fn.split(":")
                    getattr(__import__(mod, fromlist=[f]), f)()
                except Exception as e:
                    log.warning("Daemon: tracking %s failed: %s", name, type(e).__name__)
        try:
            answered += poll_once()
        except Exception as e:
            log.warning("Daemon: bot poll failed: %s", type(e).__name__)
        for job in due():
            if job == "research" and left() < 30:
                continue                       # not enough time left: the next run does it
            run_job(job, left())
        time.sleep(60 if left() > 3 else 5)
    try:
        from .ci_save import save
        save("daemon run")
    except Exception as e:
        log.warning("Daemon: final save failed: %s", e)
    return answered
