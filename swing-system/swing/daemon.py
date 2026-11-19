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
import threading
import sys
import time
from datetime import datetime, timedelta, timezone

from .config import DATA, ROOT, get_logger, load_settings

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
    if job in ("nightly", "company", "basket") and (t.weekday() >= 5 or t.hour < 18):
        return None
    if job == "research" and (t.weekday() >= 5 or t.hour < 20):
        return None
    if job == "review" and (t.weekday() >= 5 or t.hour < 16):
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


def retry_later(job, minutes=20, max_tries=12, t=None):
    """The job could not do its work yet (e.g. prices not published): free it to run again in `minutes`."""
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
    STATE.write_text(json.dumps(st, indent=1))
    log.info("Daemon: %s will retry in %d min (attempt %d of %d)", job, minutes, tries, max_tries)


def _waiting(st, job, t):
    nb = st.get("not before " + str(key(job, t)))
    return bool(nb) and str(t)[:19] < nb


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
    if wd < 5 and t >= t.replace(hour=15, minute=40, second=0) and not st.get(key("vantage", t)):
        out.append("vantage")                      # VANTAGE INDICATOR scan of every NSE stock (today's candle: Kite)
    if wd < 5 and t >= t.replace(hour=16, minute=0, second=0) and not st.get(key("review", t)) \
            and (st.get(key("vantage", t)) or t >= t.replace(hour=16, minute=20)) and t.hour < 18:
        out.append("review")                       # owner 19 Nov: tracker + Learner + why-engine at about 4 pm
    if wd < 5 and t >= t.replace(hour=18, minute=40, second=0) and not st.get(key("nightly", t)):
        out.append("nightly")
    if wd < 5 and t >= t.replace(hour=18, minute=50, second=0) and not st.get(key("vantage2", t)) \
            and st.get(key("vantage", t)) and "nightly" not in out and not _waiting(st, "vantage2", t):
        from .vantage import due_evening
        if due_evening(f"{t:%Y-%m-%d}"):
            out.append("vantage2")                 # retry with Yahoo's candle when the 3:40 pm scan had no Kite data
    if wd < 5 and t >= t.replace(hour=18, minute=45, second=0) and not st.get(key("company", t)) \
            and (st.get(key("nightly", t)) or t >= t.replace(hour=19, minute=30)) and "nightly" not in out:
        out.append("company")
    if wd < 5 and t >= t.replace(hour=20, minute=17, second=0) and not st.get(key("research", t)) \
            and (st.get(key("nightly", t)) or t >= t.replace(hour=21, minute=30)):
        out.append("research")
    if wd < 5 and t >= t.replace(hour=19, minute=5, second=0) and not st.get(key("basket", t)) \
            and (st.get(key("nightly", t)) or t >= t.replace(hour=20, minute=0)) and "nightly" not in out:
        from .basket import due as basket_due
        if basket_due(t):
            out.append("basket")                   # monthly basket of the 20 strongest stocks (round 4, M3)
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


SCRIPTS = {"review": "run_review.py", "vantage": "run_vantage.py", "vantage2": "run_vantage.py", "scan": "run_scan.py", "nightly": "run_nightly.py", "company": "company_of_day.py", "research": "run_research.py", "weekly": "run_weekly.py", "basket": "run_basket.py"}


_JOB = {"thread": None, "name": None}


def job_running():
    th = _JOB["thread"]
    return th is not None and th.is_alive()


def run_job(job, minutes_left, background=True):
    """D114: jobs run in a background thread (one at a time) so the bot keeps answering, exit alerts keep firing
    and minute tasks keep running while a long job (nightly ~5 min, research up to ~1 hour) works."""
    if job_running() or not claim(job):
        return False
    env = dict(os.environ, SWING_CLAIMED=job,
               SWING_RESEARCH_BUDGET=str(max(10, min(120, minutes_left - 25))))

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


CODE_PATHS = ["swing-system/swing", "swing-system/scripts", "swing-system/requirements.txt",
              "swing-system/strategies", "swing-system/settings.yaml", "vantage-ai/validation/replica.py"]


def code_version(ref="HEAD"):
    """Fingerprint of the program files at a git ref (data/results commits do not change it)."""
    out = []
    for p in CODE_PATHS:
        r = subprocess.run(["git", "rev-parse", f"{ref}:{p}"], cwd=ROOT.parent, capture_output=True, text=True)
        out.append(r.stdout.strip())
    return "|".join(out)


def token_rotated(now=None, wait_s=180, every_h=0.5):
    """Owner 17 Nov: after a bot-key change in GitHub Secrets, a running run still holds the OLD key (secrets are
    given to a run only when it starts) and Telegram answers 401. After 3 minutes of 401s, end the run so the next
    one starts with the new key - at most once every 30 minutes (a wrong key must not cause a fast restart loop;
    each new run reads the secret again, so a corrected key is picked up within ~30 minutes)."""
    from . import bot
    now = now or time.time()
    since = bot.TOKEN_REFUSED_SINCE
    if not since or now - since < wait_s or not os.environ.get("GITHUB_ACTIONS"):
        return False
    f = DATA / "token_restart.json"
    try:
        last = float(json.loads(f.read_text()).get("t"))
    except Exception:
        last = None                    # never handed over for this reason
    if last is not None and now - last < every_h * 3600:
        return False
    try:
        f.write_text(json.dumps({"t": now}))
    except Exception:
        pass
    return True


def update_waiting(start_version):
    """True if newer program code was pushed to the branch since this run started (then the run ends early and
    the next one - started automatically by keep_alive - uses the new code within minutes)."""
    branch = os.environ.get("SWING_BRANCH")
    if not branch or not os.environ.get("GITHUB_ACTIONS"):
        return False
    try:
        subprocess.run(["git", "fetch", "-q", "origin", branch], cwd=ROOT.parent, timeout=60, check=True)
        new = code_version("FETCH_HEAD")
        return bool(new.replace("|", "")) and new != start_version
    except Exception:
        return False


def self_check():
    """At start: is the picture reader working on this computer? Warn the owner once a day if not."""
    try:
        import numpy as np
        from .chart_reader import _ocr
        _ocr()(np.full((60, 200, 3), 255, dtype=np.uint8))
        log.info("Self-check: chart picture reader ready")
        return True
    except Exception as e:
        log.warning("Self-check: chart picture reader NOT working: %s %s", type(e).__name__, str(e)[:120])
        if claim_once("picture reader warning"):
            from . import telegram
            from .config import load_settings
            telegram.send(load_settings(), "⚠️ System check: the chart-picture reader could not start on GitHub "
                                           f"today ({type(e).__name__}). Text tips still work. Open a Claude "
                                           "session to fix it.", label="self-check warning")
        return False


def claim_once(name, t=None):
    t = t or now()
    st = _load()
    k = f"{name} {t:%Y-%m-%d}"
    if st.get(k):
        return False
    st[k] = now().isoformat(timespec="minutes")
    STATE.write_text(json.dumps(st, indent=1))
    return True


_last_filings = 0.0
_last_intraday = 0.0
_intraday_thread = None
_bt_thread = None


def _run_backtest():
    try:
        from .intraday_backtest import run
        txt = run()
        if txt:
            _send(txt)
            from .intraday_paper import SETUPS_F
            d = json.loads(SETUPS_F.read_text())
            log.info("Intraday setups tested on Kite history: allowed %s; %s", d.get("allowed"),
                     {k: (v.get("trades"), v.get("avg_net")) for k, v in d.get("stats", {}).items()})
    except Exception as e:
        log.warning("Daemon: intraday backtest failed: %s", type(e).__name__)


def _safe_intraday(fn):
    try:
        fn()
    except Exception as e:
        log.warning("Daemon: intraday scan failed: %s", type(e).__name__)


_VLIVE = {"proc": None, "starts": 0}


def ensure_vantage_live():
    """Keep the live VANTAGE scanner process running (restarted if it dies, at most 5 times a run)."""
    p = _VLIVE["proc"]
    if p is not None and p.poll() is None:
        return True
    if _VLIVE["starts"] >= 5:
        return False
    _VLIVE["starts"] += 1
    _VLIVE["proc"] = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "run_vantage_live.py")], cwd=ROOT)
    log.info("Daemon: VANTAGE live scanner started")
    return True


def minute_tasks(t=None):
    """Small things checked every minute: Kite login prompt/reminder, instant alerts, the 2-week paper review."""
    import html as _html
    t = t or now()
    wd = t.weekday() < 5
    try:   # audit 17 Nov: no silent failures - heartbeat / recovery notice, kill-switch notice, outbox, safety stop
        from . import monitor
        _s = load_settings()
        monitor.heartbeat(t)
        monitor.kill_switch_watch(_s)
        monitor.housekeeping(_s)
        monitor.daily_status(t)
        monitor.weekly_health(t)
        if t.hour >= 20 and claim_once("local backup", t):          # daily local backup, last 14 days kept
            from . import archive
            _p, _n, _bad = archive.local_backup()
            log.info("Local backup: %d files%s", _n, f", {len(_bad)} damaged left out" if _bad else "")
    except Exception as e:
        log.warning("Daemon: monitor failed: %s", type(e).__name__)
    try:   # D120: VANTAGE INDICATOR live scan of every NSE stock during market hours (own process)
        if wd and 9 * 60 + 20 <= t.hour * 60 + t.minute < 15 * 60 + 30 and load_settings().get("vantage_live", True):
            ensure_vantage_live()
    except Exception as e:
        log.warning("Daemon: VANTAGE live start failed: %s", type(e).__name__)
    try:
        from . import kite
        if wd and kite.configured() and not kite.logged_in():
            if t >= t.replace(hour=8, minute=45, second=0) and t.hour < 15 and claim_once("kite login prompt", t):
                _send(f"🔑 <b>Log in to Kite for today</b>\n<a href=\"{_html.escape(kite.login_url())}\">Tap here to log in</a> - "
                      "then tap <b>Start</b> when Telegram opens. Live Zerodha prices for alerts and updates until 6 am "
                      "tomorrow. (Until then I use Yahoo prices.)", label="kite login")
            elif t >= t.replace(hour=9, minute=30, second=0) and t.hour < 15 and claim_once("kite login reminder", t):
                _send(f"⏰ Reminder: not logged in to Kite yet - alerts are using slower Yahoo prices. "
                      f"<a href=\"{_html.escape(kite.login_url())}\">Log in</a>", label="kite login")
            elif t >= t.replace(hour=11, minute=0, second=0) and t.hour < 14 and claim_once("kite login reminder 2", t):
                _send(f"⏰ Still not logged in to Kite. Log in any time - scanning starts the moment you do (intraday "
                      f"tips until 2:30 pm; evening tips come anyway). <a href=\"{_html.escape(kite.login_url())}\">"
                      f"Log in</a>", label="kite login")
    except Exception as e:
        log.warning("Daemon: kite login prompt failed: %s", type(e).__name__)
    try:   # one-off owner request: re-send deleted tips - does nothing once done
        from . import oneoff_resend
        oneoff_resend.maybe_run(t)
    except Exception as e:
        log.warning("Daemon: one-off re-send failed: %s", type(e).__name__)
    try:   # one-off owner request (picks with Kite data) - does nothing once done
        from . import oneoff_picks
        oneoff_picks.maybe_run(t)
    except Exception as e:
        log.warning("Daemon: one-off request failed: %s", type(e).__name__)
    try:   # 9:00 am morning brief: filings, results due, insider trades for the followed stocks
        if wd and t >= t.replace(hour=9, minute=0, second=0) and t.hour < 12 and claim_once("morning brief", t):
            from . import nse_filings
            seen_f = DATA / "filings_seen.json"
            msg = nse_filings.morning_brief()
            _, seen = nse_filings.new_filings(set())          # everything up to now counts as seen
            seen_f.write_text(json.dumps(sorted(seen)[-3000:]))
            if msg:
                _send(msg)
    except Exception as e:
        log.warning("Daemon: morning brief failed: %s", type(e).__name__)
    try:   # new important filings of followed stocks, 9:00-18:00, checked every 15 minutes
        global _last_filings
        if wd and 9 <= t.hour < 18 and time.time() - _last_filings > 900 and _load().get(f"morning brief {t:%Y-%m-%d}"):
            _last_filings = time.time()
            from . import nse_filings
            seen_f = DATA / "filings_seen.json"
            seen = set(json.loads(seen_f.read_text())) if seen_f.exists() else set()
            lines, seen = nse_filings.new_filings(seen)
            seen_f.write_text(json.dumps(sorted(seen)[-3000:]))
            if lines:
                _send("📢 <b>NEW FILING</b> for a stock you follow\n\n" + "\n".join(lines[:8]) +
                      "\n\n<i>Research, not advice.</i>")
    except Exception as e:
        log.warning("Daemon: filings check failed: %s", type(e).__name__)
    engine_on = False
    try:   # the LIVE MARKET ENGINE: whole-market scanning 09:14-15:30 in a background thread (D95)
        from . import live_engine
        engine_on = live_engine.ensure_running(pd_now(t).tz_localize(None) if pd_now(t).tzinfo else pd_now(t))
    except Exception as e:
        log.warning("Daemon: live engine failed to start: %s", type(e).__name__)
    try:   # intraday PAPER trading (no tips): every 5 minutes 09:35-15:25
        global _last_intraday
        m = t.hour * 60 + t.minute
        if wd and not engine_on and 9 * 60 + 35 <= m <= 15 * 60 + 25 and time.time() - _last_intraday > 290:
            _last_intraday = time.time()
            global _intraday_thread
            if _intraday_thread is None or not _intraday_thread.is_alive():   # runs beside the bot, never blocks it
                import threading
                from . import intraday_paper
                _intraday_thread = threading.Thread(target=_safe_intraday, args=(intraday_paper.step,), daemon=True)
                _intraday_thread.start()
    except Exception as e:
        log.warning("Daemon: intraday paper failed: %s", type(e).__name__)
    try:   # weekly test of the intraday setups on Kite history, after the close (needs today's Kite login)
        global _bt_thread
        from . import kite
        from .intraday_paper import SETUPS_F
        age = (time.time() - SETUPS_F.stat().st_mtime) / 86400 if SETUPS_F.exists() else 99
        try:
            from .setups import RULES_VERSION
            if json.loads(SETUPS_F.read_text()).get("rules_version") != RULES_VERSION:
                age = 99                     # the rules changed: test them again tonight
        except Exception:
            age = 99
        if wd and t.hour * 60 + t.minute >= 15 * 60 + 45 and t.hour < 23 and age >= 6.5 and kite.logged_in() \
                and (_bt_thread is None or not _bt_thread.is_alive()) and claim_once("intraday backtest", t):
            import threading
            _bt_thread = threading.Thread(target=_run_backtest, daemon=True)
            _bt_thread.start()
    except Exception as e:
        log.warning("Daemon: intraday backtest start failed: %s", type(e).__name__)
    try:
        from . import alerts
        if alerts.market_open(pd_now(t)):
            alerts.check()
    except Exception as e:
        log.warning("Daemon: alerts failed: %s", type(e).__name__)
    try:
        from . import risk
        start = _load().get("tickets_start")
        if not start and risk.TICKETS_F.exists():
            st = _load()
            st["tickets_start"] = f"{t:%Y-%m-%d}"
            STATE.write_text(json.dumps(st, indent=1))
        elif start and (t.date() - datetime.fromisoformat(start).date()).days >= 14 and t.hour >= 19 \
                and not _load().get("paper review sent"):
            txt = risk.paper_review(start)
            try:
                from .intraday_paper import week_line
                txt = (txt or "") + "\n\n" + week_line()
            except Exception:
                pass
            if txt:
                _send(txt + "\n\nReply here if you want live orders later (needs a static IP, see DECISIONS). "
                            "<i>Research, not advice.</i>")
            st = _load()
            st["paper review sent"] = f"{t:%Y-%m-%d}"
            STATE.write_text(json.dumps(st, indent=1))
    except Exception as e:
        log.warning("Daemon: paper review failed: %s", type(e).__name__)


def pd_now(t):
    import pandas as pd
    return pd.Timestamp(t)


def _send(text, label="system notice"):
    from . import telegram
    from .config import load_settings
    telegram.send(load_settings(), text, html=True, label=label)


def run():
    from .bot import poll_once
    start = time.time()
    left = lambda: MAX_MIN - (time.time() - start) / 60
    answered = 0
    last_track = 0.0
    start_version = code_version()
    last_update_check = time.time()
    self_check()
    while left() > 2:
        if time.time() - last_update_check > 600:     # new program code pushed? hand over to a fresh run
            last_update_check = time.time()
            if update_waiting(start_version):
                if job_running():     # never cut a job in half: hand over once it has finished
                    last_update_check = time.time() - 540
                else:
                    log.info("Daemon: newer program code found - ending this run so the next one uses it")
                    break
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
        if token_rotated() and not job_running():
            log.info("Daemon: Telegram refuses the bot key (rotated?) - ending this run so the next one loads the "
                     "current GitHub Secret")
            break
        minute_tasks()
        if not job_running():
            for job in due():
                if job == "research" and left() < 30:
                    continue                       # not enough time left: the next run does it
                if run_job(job, left()):
                    break                          # one job at a time; the next starts when it has finished
        time.sleep(60 if left() > 3 else 5)
    if job_running():                              # let a running job finish before this run ends
        log.info("Daemon: waiting for %s to finish before ending", _JOB["name"])
        _JOB["thread"].join(timeout=max(60, (MAX_MIN + 20 - (time.time() - start) / 60) * 60))
    try:
        from .ci_save import save
        save("daemon run")
    except Exception as e:
        log.warning("Daemon: final save failed: %s", e)
    return answered
