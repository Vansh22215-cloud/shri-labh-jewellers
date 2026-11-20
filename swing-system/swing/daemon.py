"""ATLAS always-on run on GitHub (rebuilt 20 Nov 2026). One GitHub run lives ~5 h 15 min; when it ends the next one
starts by itself (scripts/keep_alive.py). Every minute:
  - answers Telegram (/kite, /capital, /stop, /resume, /status, /tips, /strategies, /test, /learn);
  - 8:45 am weekdays: the Kite login link (Zerodha needs one human login a day), reminders at 9:05 and 9:30;
  - 9:08 am - 3:32 pm weekdays, when logged in: the LIVE FEED - live candles of every NSE stock at 1/3/5/10/15/
    30/60 minutes + the day candle, the approved strategies on every closed candle, exit alerts (swing/tips.py);
  - 3:45 pm: a short status of the day (feed, candles, tips, exits);
  - outside market hours, when logged in: the Kite history download in ~10-minute chunks (scripts/run_candles.py)
    until everything Kite has is downloaded, then the daily top-up;
  - Saturday 10:30 am: the Learner report of every tested strategy;
  - 6:30 pm daily: Company of the Quarter - reads ~150 companies' NSE filings; one pick per calendar quarter;
  - 9:30 pm: a private backup of your records to your Telegram (only if they changed);
  - once, after this rebuild: removes the old system's data from GitHub's cache (Yahoo prices etc.).
Jobs run one at a time in the background, so the bot keeps answering while a job works."""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

from .config import DATA, PRIVATE, ROOT, get_logger, load_settings

log = get_logger()
IST = timezone(timedelta(hours=5, minutes=30))
STATE = DATA / "jobs_done.json"
MAX_MIN = float(os.environ.get("SWING_DAEMON_MINUTES", 315))
SCRIPTS = {"candles": "run_candles.py", "learner": "run_learner.py", "test": "run_test.py", "company": "run_company.py"}
TEST_QUEUE = DATA / "test_queue.json"         # strategies the owner asked to test (/test NAME)


def now():
    return datetime.now(IST)


def _load():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def _write(st):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1))
    tmp.replace(STATE)


def market_minutes(t):
    return t.weekday() < 5 and 8 * 60 + 45 <= t.hour * 60 + t.minute <= 15 * 60 + 50


def key(job, t=None):
    t = t or now()
    if job == "test":
        return None                                # every request runs (queue), nothing recorded
    if job == "candles" and market_minutes(t):
        return None                                # never during market hours (live scanning first)
    if job == "learner" and (t.weekday() != 5 or t.hour * 60 + t.minute < 10 * 60 + 30):
        return None
    if job == "company" and (market_minutes(t) or t.hour * 60 + t.minute < 18 * 60 + 30):
        return None                                # company of the quarter: filings read each evening, pick at 6:30 pm
    return f"{job} {t:%Y-%m-%d}"


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
    cut = (now() - timedelta(days=10)).strftime("%Y-%m-%d")
    for old in [x for x in st if x[-10:] < cut]:
        st.pop(old, None)
    _write(st)
    return True


def claim_once(name, t=None):
    t = t or now()
    st = _load()
    k = f"{name} {t:%Y-%m-%d}"
    if st.get(k):
        return False
    st[k] = now().isoformat(timespec="minutes")
    _write(st)
    return True


def retry_later(job, minutes=20, max_tries=12, t=None):
    """The job has more to do: free it to run again in `minutes`."""
    t = t or now()
    k = key(job, t)
    if k is None:
        return
    st = _load()
    tries = int(st.get("tries " + k, 0)) + 1
    st["tries " + k] = tries
    if tries < max_tries:
        st.pop(k, None)
        st["not before " + k] = str(t + timedelta(minutes=minutes))[:19]
    _write(st)


def _waiting(st, job, t):
    nb = st.get("not before " + str(key(job, t)))
    return bool(nb) and str(t)[:19] < nb


def due(t=None):
    t = t or now()
    st = _load()
    out = []
    if key("learner", t) and not st.get(key("learner", t)):
        out.append("learner")
    try:
        q = json.loads(TEST_QUEUE.read_text()) if TEST_QUEUE.exists() else []
        if q and not market_minutes(t):           # tests run outside market hours (the live feed comes first)
            from .candles import complete
            from .strategy import load_all
            S = load_all()
            if any(n not in S or complete(S[n].interval) for n in q):
                out.append("test")                 # ... and only once that interval's Kite history is complete
    except Exception:
        pass
    if key("company", t) and not st.get(key("company", t)) and not out:
        out.append("company")
    if key("candles", t) and not st.get(key("candles", t)) and not _waiting(st, "candles", t) and not out:
        try:
            from . import kite
            if kite.logged_in():
                out.append("candles")
        except Exception:
            pass
    return out


_JOB = {"thread": None, "name": None}


def job_running():
    th = _JOB["thread"]
    return th is not None and th.is_alive()


def run_job(job, minutes_left, background=True):
    if job_running() or not claim(job):
        return False
    env = dict(os.environ, SWING_CLAIMED=job)

    def _go():
        log.info("Daemon: running %s", job)
        try:
            subprocess.run([sys.executable, str(ROOT / "scripts" / SCRIPTS[job])], cwd=ROOT, env=env,
                           timeout=max(60, (minutes_left - 5) * 60))
        except Exception as e:
            log.warning("Daemon: %s failed: %s", job, type(e).__name__)
        log.info("Daemon: %s finished", job)

    if not background:
        _go()
        return True
    th = threading.Thread(target=_go, daemon=True)
    _JOB.update(thread=th, name=job)
    th.start()
    return True


# ----------------------------------------------------------------------------- live feed
_FEED = {"feed": None, "day": None, "starts": 0}


def feed_window(t):
    return t.weekday() < 5 and 9 * 60 + 8 <= t.hour * 60 + t.minute <= 15 * 60 + 32


def ensure_feed(t=None):
    """Keep the live feed running in market hours while logged in (restarted if it stops, at most 6 times a day)."""
    from . import kite
    t = t or now()
    f = _FEED["feed"]
    if _FEED["day"] != t.date():
        _FEED.update(day=t.date(), starts=0)
    if not feed_window(t):
        return False
    if f is not None and f.alive():
        return True
    if not kite.logged_in():
        if t.hour * 60 + t.minute >= 9 * 60 + 20:
            kite.report_unavailable(load_settings(), "Live scanning", why="Kite is not logged in")
        return False
    if _FEED["starts"] >= 6:
        return False
    _FEED["starts"] += 1
    try:
        from .live_feed import LiveFeed
        from .tips import Scanner
        _FEED["feed"] = LiveFeed(on_close=Scanner().on_close).start()
        return True
    except Exception as e:
        log.warning("Daemon: live feed failed to start: %s", type(e).__name__)
        return False


def day_status(t):
    """3:45 pm: what the live system did today (always sent - the owner sees it is working)."""
    from . import tips
    f = _FEED["feed"]
    st = f.status() if f is not None else None
    T = tips.load_tips()
    today = T[T["signal"].dt.date == t.date()] if len(T) else T
    closed = T[T["exit_time"].notna() & (T["exit_time"].dt.date == t.date())] if len(T) else T
    live = load_settings().get("live_strategies") or []
    L = [f"🩺 ATLAS today ({t:%a %d %b})"]
    if st:
        L.append(f"Live feed (Kite): {st['instruments']:,} stocks/indices, {st['ticks']:,} price updates, candles built "
                 f"for {st['stocks_with_candles']:,}.")
    else:
        L.append("Live feed: did not run today (no Kite login?).")
    L.append(f"Live strategies: {', '.join(live) if live else 'none yet - waiting for your first strategy'}.")
    L.append(f"Tips sent: {len(today)}; closed today: {len(closed)}"
             + (f" ({(closed['net_pct'] > 0).sum()} in profit)" if len(closed) else "") + ".")
    return "\n".join(L)


# ----------------------------------------------------------------------------- minute tasks
def minute_tasks(t=None):
    import html as _html
    t = t or now()
    wd = t.weekday() < 5
    s = load_settings()
    try:
        from . import telegram
        telegram.flush_outbox(s)
    except Exception as e:
        log.warning("Daemon: outbox failed: %s", type(e).__name__)
    try:
        from . import reset
        reset.maybe_run()
    except Exception as e:
        log.warning("Daemon: reset failed: %s", type(e).__name__)
    try:
        from . import kite
        if wd and kite.configured() and not kite.logged_in() and t.hour < 15:
            link = f"<a href=\"{_html.escape(kite.login_url())}\">Tap here to log in</a>"
            if t >= t.replace(hour=8, minute=45, second=0) and claim_once("kite login prompt", t):
                _send(f"🔑 <b>Log in to Kite for today</b>\n{link} - then tap <b>Start</b> when Telegram opens. "
                      "Live scanning of every stock starts at 9:15 am; history downloads run after 3:50 pm.", "kite login")
            elif t >= t.replace(hour=9, minute=5, second=0) and claim_once("kite login reminder", t):
                _send(f"⏰ Not logged in to Kite yet - no live candles, no tips until you do. {link}", "kite login")
            elif t >= t.replace(hour=9, minute=30, second=0) and claim_once("kite login reminder 2", t):
                _send(f"⏰ Still not logged in to Kite - live scanning is off. {link}", "kite login")
    except Exception as e:
        log.warning("Daemon: kite login prompt failed: %s", type(e).__name__)
    try:
        ensure_feed(t)
    except Exception as e:
        log.warning("Daemon: feed check failed: %s", type(e).__name__)
    try:
        if wd and t.hour * 60 + t.minute >= 15 * 60 + 45 and t.hour < 20 and claim_once("day status", t):
            _send(day_status(t), "system status", html=False)
    except Exception as e:
        log.warning("Daemon: day status failed: %s", type(e).__name__)
    try:
        if t.hour * 60 + t.minute >= 21 * 60 + 30 and claim_once("backup", t):
            from . import backup
            backup.send_if_changed(s)
    except Exception as e:
        log.warning("Daemon: backup failed: %s", type(e).__name__)


def _send(text, label="system status", html=True):
    from . import telegram
    telegram.send(load_settings(), text, html=html, label=label)


# ----------------------------------------------------------------------------- hand-over
CODE_PATHS = ["swing-system/swing", "swing-system/scripts", "swing-system/requirements.txt", "swing-system/settings.yaml"]


def code_version(ref="HEAD"):
    out = []
    for p in CODE_PATHS:
        r = subprocess.run(["git", "rev-parse", f"{ref}:{p}"], cwd=ROOT.parent, capture_output=True, text=True)
        out.append(r.stdout.strip())
    return "|".join(out)


def update_waiting(start_version):
    branch = os.environ.get("SWING_BRANCH")
    if not branch or not os.environ.get("GITHUB_ACTIONS"):
        return False
    try:
        subprocess.run(["git", "fetch", "-q", "origin", branch], cwd=ROOT.parent, timeout=60, check=True)
        new = code_version("FETCH_HEAD")
        return bool(new.replace("|", "")) and new != start_version
    except Exception:
        return False


def token_rotated(now_s=None, wait_s=180, every_h=0.5):
    """Telegram refuses the bot key for 3 minutes (rotated in GitHub Secrets): end the run so the next one starts
    with the new key - at most once every 30 minutes."""
    from . import bot
    now_s = now_s or time.time()
    since = bot.TOKEN_REFUSED_SINCE
    if not since or now_s - since < wait_s or not os.environ.get("GITHUB_ACTIONS"):
        return False
    f = DATA / "token_restart.json"
    try:
        last = float(json.loads(f.read_text()).get("t"))
    except Exception:
        last = None
    if last is not None and now_s - last < every_h * 3600:
        return False
    try:
        f.write_text(json.dumps({"t": now_s}))
    except Exception:
        pass
    return True


def run():
    from .bot import poll_once
    start = time.time()
    left = lambda: MAX_MIN - (time.time() - start) / 60
    answered = 0
    start_version = code_version()
    last_update_check = time.time()
    while left() > 2:
        if time.time() - last_update_check > 600:     # new program code pushed? hand over (not during live scanning)
            last_update_check = time.time()
            if not feed_window(now()) and update_waiting(start_version):
                if job_running():
                    last_update_check = time.time() - 540
                else:
                    log.info("Daemon: newer program code found - ending this run so the next one uses it")
                    break
        try:
            answered += poll_once()
        except Exception as e:
            log.warning("Daemon: bot poll failed: %s", type(e).__name__)
        if token_rotated() and not job_running():
            break
        minute_tasks()
        if not job_running():
            for job in due():
                if run_job(job, left()):
                    break
        time.sleep(20 if left() > 3 else 5)
    f = _FEED["feed"]
    if f is not None:
        try:
            f.builder.save()
            f.stop()
        except Exception:
            pass
    if job_running():
        _JOB["thread"].join(timeout=max(60, (MAX_MIN + 20 - (time.time() - start) / 60) * 60))
    try:
        from .ci_save import save
        save("daemon run")
    except Exception as e:
        log.warning("Daemon: final save failed: %s", e)
    return answered
