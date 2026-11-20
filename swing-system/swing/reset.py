"""One-time clean start on GitHub after the rebuild (owner 20 Nov: "remove all other things... delete Yahoo data").
Runs once (data/reset_v2.done), on GitHub only:
  - DELETES from the private cache: Yahoo prices, NSE bhavcopy rebuilds, delisted-stock files, old research data,
    old candle files built from quotes, old job state - everything of the old system;
  - KEEPS: Kite candles already downloaded (moved into data/candles), the Kite login pass, the Telegram message
    position (so old messages are not answered again), NSE company filings, the keep-alive record;
  - your OLD personal records (old tips, VANTAGE signals, trades, forwarded tips) are NOT deleted: they are moved
    to data/private/old_system/ and stay in your private backups - say the word and they are deleted too.
Then one Telegram message says what was done."""
import json
import shutil

from .config import DATA, PRIVATE, get_logger, load_settings, on_github

log = get_logger()
FLAG = DATA / "reset_v2.done"
KEEP_DATA = {"candles", "private", "fundamentals", "bot_offset.txt", "keep_alive.json", "token_restart.json",
             "failure_alert.json", "reset_v2.done", "live", "jobs_done.json", "tests", "test_queue.json"}
KEEP_PRIVATE = {"kite_token.bin", "outbox.jsonl", "tips.csv", "old_system"}


def _size(p):
    try:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
    except Exception:
        return 0


def maybe_run(force=False):
    if FLAG.exists() or not (on_github() or force):
        return None
    freed, moved = 0, 0
    old_kc = DATA / "kite_candles"                     # Kite intraday candles downloaded by the old job: keep them
    if old_kc.exists():
        new = DATA / "candles"
        new.mkdir(parents=True, exist_ok=True)
        for iv in [p for p in old_kc.iterdir() if p.is_dir()]:
            dst = new / iv.name
            dst.mkdir(exist_ok=True)
            for f in iv.glob("*.parquet"):
                if not (dst / f.name).exists():
                    shutil.move(str(f), str(dst / f.name))
        try:
            st_old = json.loads((old_kc / "state.json").read_text())
            sf = new / "state.json"
            st = json.loads(sf.read_text()) if sf.exists() else {}
            for k, v in st_old.items():
                st.setdefault(k, v)
            sf.write_text(json.dumps(st))
        except Exception:
            pass
    old_jobs = DATA / "jobs_done.json"
    if old_jobs.exists():
        try:
            st = json.loads(old_jobs.read_text())
            if any(k.startswith(("nightly", "vantage", "scan")) for k in st):
                old_jobs.unlink()                      # the old system's job record: start fresh
        except Exception:
            pass
    for p in list(DATA.iterdir()):
        if p.name in KEEP_DATA:
            continue
        freed += _size(p)
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    fund = DATA / "fundamentals"
    if fund.exists():
        for p in fund.iterdir():
            if p.name == "nse_xbrl":
                continue
            try:
                if p.suffix == ".json" and json.loads(p.read_text()).get("v") == 3:
                    continue                           # NSE-filing snapshots stay
            except Exception:
                pass
            freed += _size(p)
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    old = PRIVATE / "old_system"
    for p in list(PRIVATE.iterdir()):
        if p.name in KEEP_PRIVATE:
            continue
        old.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(old / p.name))
        moved += 1
    FLAG.write_text("done")
    msg = (f"🧹 ATLAS clean start: the old system's data was removed from GitHub's storage ({freed / 1e9:.2f} GB: "
           f"Yahoo prices, NSE rebuilds, delisted stocks, old research). Kite candles and your Kite login were kept. "
           f"{moved} old personal record file(s) (old tips, VANTAGE signals, trades) were moved aside, not deleted - "
           "tell me if you want them deleted too.")
    log.info("Reset: %.2f GB removed, %d private files moved aside", freed / 1e9, moved)
    try:
        from . import telegram
        telegram.send(load_settings(), msg, label="system status")
    except Exception:
        pass
    return {"freed_gb": round(freed / 1e9, 2), "moved": moved}
