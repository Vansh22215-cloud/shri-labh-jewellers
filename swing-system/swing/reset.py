"""One-time clean start on GitHub after the rebuild (owner 20 Nov: "remove all other things... delete Yahoo data").
Runs once (data/reset_v3.done), on GitHub only:
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
FLAG = DATA / "reset_v3.done"
KEEP_DATA = {"candles", "private", "company", "bot_offset.txt", "keep_alive.json", "token_restart.json",
             "failure_alert.json", "reset_v3.done", "live", "jobs_done.json", "tests", "test_queue.json"}
KEEP_PRIVATE = {"kite_token.bin", "outbox.jsonl", "tips.csv"}


def _size(p):
    try:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
    except Exception:
        return 0


def _rm(p):
    shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)


def maybe_run(force=False):
    if FLAG.exists() or not (on_github() or force):
        return None
    freed, removed = 0, 0
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
        if p.name not in KEEP_DATA:
            freed += _size(p)
            _rm(p)
    for p in list(PRIVATE.iterdir()):                  # owner 20 Nov: delete the old personal records too
        if p.name not in KEEP_PRIVATE:
            freed += _size(p)
            _rm(p)
            removed += 1
    FLAG.write_text("done")
    msg = (f"🧹 ATLAS clean start: the old system's data was deleted from GitHub's storage ({freed / 1e9:.2f} GB: "
           f"Yahoo prices, NSE rebuilds, delisted stocks, old research, old company financials, {removed} old personal "
           "record file(s) - old tips, VANTAGE signals, trades). Kept: Kite candles and your Kite login.")
    log.info("Reset: %.2f GB removed", freed / 1e9)
    try:
        from . import telegram
        telegram.send(load_settings(), msg, label="system status")
    except Exception:
        pass
    return {"freed_gb": round(freed / 1e9, 2), "removed": removed}
