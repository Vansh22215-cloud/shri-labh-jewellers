"""ATLAS IMMUTABLE MARKET MEMORY: an append-only, hash-chained ledger of every idea's history.
Every evening, each idea tracked by swing/tracker.py whose state changed (new, bought/skipped, stop/target hit,
closed, result moved by 1+ point) gets ONE new line in journal/ledger.jsonl. Lines are never edited or deleted: each
carries the hash of the previous line, so any rewrite of the past is detectable (verify()). The file is saved to GitHub,
whose history is itself permanent. Market ideas only - no owner money, quantities or holdings."""
import hashlib
import json

import pandas as pd

from .config import ROOT, get_logger

log = get_logger()
LEDGER = ROOT / "journal" / "ledger.jsonl"
KEEP = ["source", "type", "sent", "date", "symbol", "status", "why", "entry", "exit", "result_pct", "mistake"]


def _hash(prev, body):
    return hashlib.sha256((prev + json.dumps(body, sort_keys=True, default=str)).encode()).hexdigest()


def _last():
    """-> (last hash, {idea key: last recorded state})."""
    prev, state = "genesis", {}
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            if not line.strip():
                continue
            x = json.loads(line)
            prev = x["hash"]
            state[x["key"]] = x["state"]
    return prev, state


def _key(r):
    return f"{r.get('source')}|{r.get('symbol')}|{str(r.get('date'))[:10]}|{r.get('type')}"


def _clean(v):
    if isinstance(v, float):
        return None if v != v else round(v, 2)
    return None if v is None or str(v) == "nan" else v


def append(R, today=None):
    """-> number of lines appended for ideas whose state changed."""
    today = today or str(pd.Timestamp.now(tz="Asia/Kolkata").date())
    prev, state = _last()
    lines = []
    for r in R.to_dict("records"):
        st = {k: _clean(r.get(k)) for k in KEEP if k in r}
        k = _key(r)
        old = state.get(k)
        moved = old is None or old.get("status") != st.get("status") or old.get("why") != st.get("why") or \
            abs((st.get("result_pct") or 0) - (old.get("result_pct") or 0)) >= 1
        if not moved:
            continue
        body = {"day": today, "key": k, "state": st}
        h = _hash(prev, body)
        lines.append(json.dumps(dict(body, prev=prev, hash=h), sort_keys=True, default=str))
        prev = h
    if lines:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return len(lines)


def verify():
    """-> (ok, lines checked). False if any line was edited, removed or reordered."""
    prev, n = "genesis", 0
    if not LEDGER.exists():
        return True, 0
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        x = json.loads(line)
        body = {"day": x["day"], "key": x["key"], "state": x["state"]}
        if x["prev"] != prev or x["hash"] != _hash(prev, body):
            return False, n
        prev, n = x["hash"], n + 1
    return True, n
