"""Zerodha Kite Connect - MARKET DATA ONLY (owner's choice: orders stay as tickets the owner places in the Kite app).

Owner's paid Connect app (Rs 500/month, approved - DECISIONS D92). Keys are GitHub Secrets KITE_API_KEY /
KITE_API_SECRET, passed to the run in memory only; they are never written to a file, a log or a message.

Daily login (Zerodha requires a human login every day; automated login is not allowed):
  08:45 IST the bot sends the login link -> owner logs in -> Zerodha redirects to the repo's GitHub Pages page
  kite-login.html -> it forwards to t.me/<bot>?start=kite_<request_token> -> owner taps Start -> exchange()
  swaps the one-time request token (useless without the secret) for the day's access token.
The access token is stored ENCRYPTED (key derived from the API secret) in data/private/kite_token.bin and expires
at 06:00 IST next day. No token, an expired one, or any Kite error -> no data, no tips (Kite is the only price
source; owner 20 Nov). Order placement is NOT implemented and never will be: read-only market data only.
"""
import base64
import hashlib
import io
import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from .config import PRIVATE, DATA, get_logger

log = get_logger()
API = "https://api.kite.trade"
IST = timezone(timedelta(hours=5, minutes=30))
TOKEN_F = PRIVATE / "kite_token.bin"
INSTR_F = DATA / "kite_instruments_nse.csv"
INDEX = {"NIFTY50": "NIFTY 50", "BANKNIFTY": "NIFTY BANK", "^NSEI": "NIFTY 50", "^NSEBANK": "NIFTY BANK",
         "NIFTY_FIN_SERVICE.NS": "NIFTY FIN SERVICE", "^NSEMDCP50": "NIFTY MIDCAP 50"}


def keys():
    k, s = os.environ.get("KITE_API_KEY", "").strip(), os.environ.get("KITE_API_SECRET", "").strip()
    return (k, s) if k and s else (None, None)


def configured():
    return keys()[0] is not None


def login_url():
    k, _ = keys()
    return f"https://kite.zerodha.com/connect/login?v=3&api_key={k}" if k else None


def _fernet():
    from cryptography.fernet import Fernet
    _, s = keys()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("kite-token|" + s).encode()).digest()))


def _expiry(now=None):
    now = now or datetime.now(IST)
    six = now.replace(hour=6, minute=0, second=0, microsecond=0)
    return six if now < six else six + timedelta(days=1)


def exchange(request_token):
    """One-time request token -> the day's access token (stored encrypted). Returns (ok, plain message)."""
    k, s = keys()
    if not k:
        return False, "Kite is not set up yet (the API key and secret are not in GitHub Secrets)."
    if not request_token or not request_token.isalnum() or len(request_token) > 64:
        return False, "That login link looks broken - please tap the login link again."
    checksum = hashlib.sha256((k + request_token + s).encode()).hexdigest()
    try:
        r = requests.post(f"{API}/session/token", data={"api_key": k, "request_token": request_token,
                                                         "checksum": checksum},
                          headers={"X-Kite-Version": "3"}, timeout=30)
        d = r.json()
    except Exception as e:
        return False, f"Could not reach Zerodha ({type(e).__name__}). Try the login link again."
    if r.status_code != 200 or d.get("status") != "success":
        etype, emsg = str(d.get("error_type", "")), str(d.get("message", ""))[:160]
        log.warning("Kite login refused by Zerodha: HTTP %s %s %s", r.status_code, etype, emsg)   # no secrets in these
        low = (etype + " " + emsg).lower()
        if "checksum" in low or "api_secret" in low or "api secret" in low:
            k_, s_ = keys()
            same = " It is IDENTICAL to the API key - the key was pasted into the secret." if s_ == k_ else ""
            why = ("the API SECRET in GitHub does not match your Kite app. The stored secret has "
                   f"{len(s_)} characters (Kite secrets usually have 32).{same} In GitHub -> Settings -> Secrets and "
                   "variables -> Actions, tap KITE_API_SECRET -> Update, paste the API secret (tap 'Show API secret' "
                   "on the Kite app page first; not the key), then tell me so I restart the system.")
        elif "api_key" in low or "api key" in low:
            why = "the API KEY in GitHub does not match your Kite app - update KITE_API_KEY in GitHub Secrets."
        elif "expired" in low or "invalid" in low or "token" in low:
            why = ("the login code expired or was already used (they last only a few minutes and work once). "
                   "Send /kite for a fresh link and send the code back right away.")
        else:
            why = "see Zerodha's message below."
        return False, f"❌ Zerodha did not accept the login: {why}\n(Zerodha said: {etype} {emsg})"
    tok = d["data"]["access_token"]
    save_token(tok)
    log.info("Kite: logged in for today")
    return True, "✅ Kite connected for today - live Zerodha prices are on until 6 am tomorrow."


def save_token(tok, now=None):
    blob = json.dumps({"t": tok, "exp": _expiry(now).isoformat()}).encode()
    TOKEN_F.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_F.write_bytes(_fernet().encrypt(blob))


def token(now=None):
    if not configured() or not TOKEN_F.exists():
        return None
    try:
        d = json.loads(_fernet().decrypt(TOKEN_F.read_bytes()))
        if datetime.fromisoformat(d["exp"]) <= (now or datetime.now(IST)):
            return None
        return d["t"]
    except Exception:
        return None


def logged_in(now=None):
    return token(now) is not None


# SAFETY (audit 17 Nov): this system is a manual trade-finder. The Kite client may ONLY read market data. Any other
# endpoint (orders, GTT, holdings, positions, margins, funds, profile) is refused before a request is made.
READ_ONLY_PREFIXES = ("/quote", "/instruments")


def _get(path, params=None, timeout=20):
    if not str(path).startswith(READ_ONLY_PREFIXES):
        raise PermissionError(f"Kite endpoint not allowed (read-only market data only): {str(path)[:40]}")
    k, _ = keys()
    t = token()
    if not t:
        raise RuntimeError("not logged in")
    r = requests.get(f"{API}{path}", params=params, timeout=timeout,
                     headers={"X-Kite-Version": "3", "Authorization": f"token {k}:{t}"})
    if r.status_code == 403:
        try:
            etype = r.json().get("error_type", "")
        except Exception:
            etype = ""
        if etype and etype != "TokenException":     # e.g. a data permission: the login itself is still fine
            raise PermissionError(f"Kite refused this data ({etype})")
        try:
            TOKEN_F.unlink()           # token rejected (expired / logged out): stop using it
        except Exception:
            pass
        raise RuntimeError("session expired")
    r.raise_for_status()
    return r


def _instrument(sym):
    s = INDEX.get(sym, sym)
    return f"NSE:{s}"


def quotes(symbols):
    """{symbol: {'last','open','high','low','prev'}} for NSE stocks / indices, or {} on any problem."""
    if not symbols or not logged_in():
        return {}
    out = {}
    syms = list(dict.fromkeys(symbols))
    fails = 0
    for i in range(0, len(syms), 500):
        chunk = syms[i:i + 500]
        data = None
        for attempt in range(2):          # audit 17 Nov: Kite allows 1 quote request per second - pace + retry once
            _pace()
            try:
                r = _get("/quote", params=[("i", _instrument(s)) for s in chunk])   # full quote: incl. volume
                data = r.json().get("data", {})
                break
            except RuntimeError:
                raise_expired = not logged_in()
                if raise_expired:
                    break
            except Exception as e:
                log.debug("Kite quote chunk failed (%s), attempt %d", type(e).__name__, attempt + 1)
        if data is None:
            fails += 1
            continue
        try:
            for s in chunk:
                q = data.get(_instrument(s))
                if not q or not q.get("last_price"):
                    continue                  # audit: one malformed instrument must not wipe out every quote
                try:
                    if not float(q["last_price"]) > 0:
                        continue
                except Exception:
                    continue
                o = q.get("ohlc", {})
                out[s] = {"last": float(q["last_price"]), "open": float(o.get("open") or q["last_price"]),
                          "high": float(o.get("high") or q["last_price"]), "low": float(o.get("low") or q["last_price"]),
                          "prev": float(o.get("close") or q["last_price"]),
                          "volume": float(q.get("volume") or 0),
                          "value_cr": float(q.get("volume") or 0) * float(q["last_price"]) / 1e7 if q.get("volume") else None,
                          # D103 order flow: total pending buy / sell quantity and the top-5 bid/ask book
                          "buy_qty": float(q.get("buy_quantity") or 0), "sell_qty": float(q.get("sell_quantity") or 0),
                          "bid5": sum(float(x.get("quantity") or 0) for x in (q.get("depth") or {}).get("buy", [])),
                          "ask5": sum(float(x.get("quantity") or 0) for x in (q.get("depth") or {}).get("sell", []))}
        except Exception as e:
            fails += 1
            log.debug("Kite quote parse failed: %s", type(e).__name__)
    if fails:
        log.warning("Kite quotes: %d of %d batch(es) failed - those stocks are skipped this round",
                    fails, (len(syms) + 499) // 500)
    return out


_LAST_QUOTE = {"t": 0.0}


def _pace(min_gap=1.05):
    """Never more than one quote request per second (Kite's documented limit)."""
    import time as _t
    with _PACE_LOCK:
        wait = _LAST_QUOTE["t"] + min_gap - _t.time()
        if wait > 0:
            _t.sleep(wait)
        _LAST_QUOTE["t"] = _t.time()


import threading as _threading  # noqa: E402
_PACE_LOCK = _threading.Lock()


def instruments():
    """NSE instrument list (symbol -> instrument_token), refreshed once a day."""
    if INSTR_F.exists() and (datetime.now().timestamp() - INSTR_F.stat().st_mtime) < 20 * 3600:
        return pd.read_csv(INSTR_F)
    r = _get("/instruments/NSE", timeout=60)
    df = pd.read_csv(io.StringIO(r.text))[["instrument_token", "tradingsymbol", "name", "segment", "instrument_type",
                                           "lot_size", "tick_size"]]
    df.to_csv(INSTR_F, index=False)
    return df


def equity_symbols():
    """Every NSE stock Kite lists today (EQ instruments, normal series - no -BE/-SM/bond/ETF-units suffixes)."""
    try:
        ins = instruments()
    except Exception:
        return []
    if "instrument_type" not in ins.columns:
        try:
            INSTR_F.unlink()
            ins = instruments()
        except Exception:
            return []
    e = ins[(ins["segment"] == "NSE") & (ins["instrument_type"] == "EQ")]
    e = e[~e["tradingsymbol"].astype(str).str.contains("-") & e["name"].notna()]
    return sorted(set(e["tradingsymbol"].astype(str)))


def historical(sym, interval="5minute", days=30):
    """OHLCV bars from Kite (interval: minute, 5minute, 15minute, 60minute, day), or None."""
    if not logged_in():
        return None
    try:
        ins = instruments()
        name = INDEX.get(sym, sym)
        row = ins[ins["tradingsymbol"] == name]
        if not len(row):
            return None
        tok = int(row["instrument_token"].iloc[0])
        to = datetime.now(IST)
        fr = to - timedelta(days=days)
        r = _get(f"/instruments/historical/{tok}/{interval}",
                 params={"from": fr.strftime("%Y-%m-%d %H:%M:%S"), "to": to.strftime("%Y-%m-%d %H:%M:%S")}, timeout=60)
        c = r.json()["data"]["candles"]
        df = pd.DataFrame(c, columns=["date", "open", "high", "low", "close", "volume"] + (["oi"] if c and len(c[0]) > 6 else []))
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        log.warning("Kite history %s failed (%s)", sym, type(e).__name__)
        return None


def live_prices(symbols):
    """Live prices from Kite ONLY (owner 19 Nov: no Yahoo fallback for live tips or alerts). -> ({sym: quote}, source).
    Missing Kite quotes stay missing: the caller sends no tip / alert for those stocks."""
    q = quotes(symbols)
    if not q:
        return {}, "unavailable"
    return q, "Zerodha"


UNAVAIL_F = None   # set below (data/kite_unavailable.json)


def report_unavailable(settings, what, why="Kite data unavailable (not logged in, expired or no data)"):
    """Once a day per job: tell the owner that no tip / alert was produced because Kite data is missing."""
    import json as _j
    f = UNAVAIL_F
    today = datetime.now(IST).strftime("%Y-%m-%d")
    try:
        st = _j.loads(f.read_text())
    except Exception:
        st = {}
    if st.get(what) == today:
        return False
    st[what] = today
    try:
        f.write_text(_j.dumps(st))
    except Exception:
        pass
    log.warning("%s: %s - no tips from it", what, why)
    try:
        from . import telegram
        telegram.send(settings, f"⚠️ {why}.\n{what}: NO tips or alerts were made from other data.\n"
                                "Log in with /kite - it resumes by itself once Kite data is back.", label="system problem")
    except Exception:
        pass
    return True


from .config import DATA as _DATA  # noqa: E402
UNAVAIL_F = _DATA / "kite_unavailable.json"
