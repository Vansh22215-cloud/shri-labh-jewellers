"""SAFETY CORE (audit 17 Nov 2026) - every NEW trade recommendation passes here. Exits are never blocked.

Principle (owner): "I would rather miss 100 profitable opportunities than receive one dangerously incorrect
recommendation." So a new tip is sent only when ALL of these hold:
  1. kill switch OFF (settings.yaml kill_switch)                     - owner's emergency stop
  2. no EMERGENCY latched (data/safety.json)                          - set by monitors (stale data, corrupt store,
                                                                         invalid calculations, repeated failures);
                                                                         cleared ONLY by integrity_check() passing
  3. capital and risk limits EXPLICITLY configured in settings.yaml   - never a guessed capital
  4. the tip's own numbers are valid (finite, positive, stop on the right side, quantity >= 1, money at risk within
     the per-trade limit, order value within the per-order limit)
  5. portfolio limits: open positions, total money at risk on open tips, losing-streak cooldown
Every refusal is logged with its reason and kept in data/private/skipped_signals.csv (audit trail).
"""
import json
import math

import pandas as pd

from .config import DATA, PRIVATE, ROOT, get_logger

log = get_logger()
STATE_F = DATA / "safety.json"
SKIPPED_F = PRIVATE / "skipped_signals.csv"
# money at risk each strategy may use at most (% of capital): lower-ranked strategies can never use up the room the
# strongest one (the dip-buy, which comes only on market dips) needs
STRATEGY_CAP = {"AI": 3.0, "RCP": 4.0, "DS": 2.0, "INTRADAY": 2.0, "FNO": 3.0}
DEFAULT_LIMITS = {"risk_per_trade_pct": 1.0, "max_order_pct": 25.0, "max_open_positions": 15, "max_open_risk_pct": 10.0, "loss_streak_pause": 8,
                  "loss_streak_cooldown_days": 3}


# ----------------------------------------------------------------------------- state
def _state():
    try:
        return json.loads(STATE_F.read_text())
    except Exception:
        return {}


def _save(s):
    tmp = STATE_F.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1, default=str))
    tmp.replace(STATE_F)


def _now():
    return pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)


def _notify(text):
    try:
        from . import telegram
        from .config import load_settings
        telegram.send_reliable(load_settings(), text, label="system problem")
    except Exception:
        pass


def emergency(reason, notify=True):
    """Latch an emergency: no new tips until integrity_check() passes. Exit monitoring continues."""
    s = _state()
    if s.get("emergency"):
        return False
    s["emergency"] = {"reason": str(reason)[:300], "since": str(_now())[:16]}
    s.setdefault("history", []).append({"on": str(_now())[:16], "reason": str(reason)[:300]})
    s["history"] = s["history"][-100:]
    _save(s)
    log.warning("SAFETY: emergency latched - %s", reason)
    if notify:
        _notify(f"🛑 SAFETY STOP: new trade tips are paused.\nReason: {reason}\nExit alerts for open tips keep "
                "working. Tips resume automatically only after the system's integrity check passes.")
    return True


def emergency_active():
    return _state().get("emergency")


def integrity_check(settings=None):
    """-> (ok, problems). Only a passing check may clear a latched emergency."""
    from .config import load_settings
    probs = []
    s = settings or load_settings()
    ok_cfg, why = configured(s)
    if not ok_cfg:
        probs.append(why)
    try:
        from .live_engine import load_tips
        load_tips()
    except Exception as e:
        probs.append(f"tip store unreadable ({type(e).__name__})")
    try:
        from . import data_prices
        n = data_prices.load("NIFTY50")
        if n is None or not len(n) or not math.isfinite(float(n["close"].iloc[-1])):
            probs.append("Nifty price history missing or invalid")
        elif (_now().normalize() - n.index[-1].normalize()).days > 6:
            probs.append(f"Nifty prices are stale (last {n.index[-1].date()})")
    except Exception as e:
        probs.append(f"price data unreadable ({type(e).__name__})")
    return (not probs), probs


def try_clear(settings=None):
    """Called by the daemon: if an emergency is latched and the integrity check now passes, resume (and say so)."""
    s = _state()
    em = s.get("emergency")
    if not em:
        return False
    ok, probs = integrity_check(settings)
    if not ok:
        return False
    s["emergency"] = None
    _save(s)
    log.info("SAFETY: integrity check passed - emergency cleared")
    _notify(f"✅ Integrity check passed - new trade tips resumed. (The stop was: {em.get('reason')})")
    return True


# ----------------------------------------------------------------------------- configuration
def configured(settings):
    """Capital and risk limits must be set EXPLICITLY in settings.yaml (no default is ever assumed)."""
    try:
        import yaml
        raw = yaml.safe_load((ROOT / "settings.yaml").read_text(encoding="utf-8")) or {}
    except Exception:
        return False, "settings.yaml unreadable"
    cap = raw.get("capital")
    rl = raw.get("risk_limits") or {}
    if not isinstance(cap, (int, float)) or cap <= 0:
        return False, "capital is not set in settings.yaml"
    if not isinstance(rl.get("risk_per_trade_pct"), (int, float)) or not 0 < rl["risk_per_trade_pct"] <= 5:
        return False, "risk_limits.risk_per_trade_pct is not set (0-5%) in settings.yaml"
    return True, ""


def limits(settings):
    rl = dict(DEFAULT_LIMITS)
    rl.update({k: v for k, v in (settings.get("risk_limits") or {}).items() if v is not None})
    rl.setdefault("max_order_pct", 25.0)
    return rl


def size(entry, stop, settings, risk_pct=None):
    """Quantity so that a stop-out loses at most risk_per_trade_pct of capital and the order is within
    max_order_pct of capital. 0 when it cannot be sized safely."""
    try:
        cap = float(settings["capital"])
        L = limits(settings)
        rp = min(float(risk_pct if risk_pct is not None else L["risk_per_trade_pct"]), float(L["risk_per_trade_pct"]))
        per = abs(float(entry) - float(stop))
        if not (math.isfinite(per) and per > 0 and float(entry) > 0):
            return 0
        q = min(cap * rp / 100 / per, cap * float(L["max_order_pct"]) / 100 / float(entry))
        return max(0, int(math.floor(q)))
    except Exception:
        return 0


# ----------------------------------------------------------------------------- per-tip validation
def validate(row, settings):
    """-> (ok, reason) for one tip's numbers."""
    try:
        e, sl = float(row["entry"]), float(row["stop"])
        qty = float(row.get("qty") or 0)
    except Exception:
        return False, "entry / stop / quantity not numbers"
    if not all(math.isfinite(x) for x in (e, sl, qty)):
        return False, "non-finite price or quantity"
    if e <= 0 or sl <= 0:
        return False, "non-positive price"
    buy = str(row.get("side", "buy")) == "buy"
    if (buy and sl >= e) or (not buy and sl <= e):
        return False, "stop-loss on the wrong side of the entry"
    if abs(e - sl) / e > 0.5:
        return False, "stop-loss more than 50% away from the entry"
    if str(row.get("type")) == "FNO":
        try:
            if not (float(row.get("premium") or 0) > 0 and float(row.get("lot") or 0) > 0):
                return False, "option premium / lot size missing"
        except Exception:
            return False, "option premium / lot size invalid"
        return True, ""
    if qty < 1:
        return False, "quantity below 1"
    L = limits(settings)
    cap = float(settings["capital"])
    at_risk = qty * abs(e - sl)
    if at_risk > cap * float(L["risk_per_trade_pct"]) / 100 * 1.01:
        return False, f"money at risk Rs {at_risk:,.0f} above the per-trade limit"
    if qty * e > cap * float(L["max_order_pct"]) / 100 * 1.01:
        return False, "order value above the per-order limit"
    tg = [x for x in str(row.get("targets", "") or "").split("/") if x and x != "nan"]
    for x in tg:
        try:
            t = float(x)
        except Exception:
            return False, "target not a number"
        if (buy and t <= e) or (not buy and t >= e):
            return False, "target on the wrong side of the entry"
    return True, ""


# ----------------------------------------------------------------------------- portfolio limits
def portfolio_check(row, settings, tips=None):
    from .live_engine import load_tips
    t = load_tips() if tips is None else tips
    L = limits(settings)
    cap = float(settings["capital"])
    if not len(t):
        return True, ""
    op = t[t["status"].astype(str) == "open"]
    if len(op) >= int(L["max_open_positions"]):
        return False, f"{len(op)} tips already open (limit {L['max_open_positions']})"
    risk = 0.0
    for _, r in op.iterrows():
        try:
            if str(r["type"]) == "FNO":
                risk += float(r.get("premium") or 0) * float(r.get("lot") or 0) * float(r.get("qty") or 1)
            else:
                risk += float(r["qty"]) * abs(float(r["entry"]) - float(r["stop"]))
        except Exception:
            continue
    try:
        new = (float(row.get("premium") or 0) * float(row.get("lot") or 0) * float(row.get("qty") or 1)
               if str(row.get("type")) == "FNO" else float(row["qty"]) * abs(float(row["entry"]) - float(row["stop"])))
    except Exception:
        new = 0.0
    fam = lambda r: ("INTRADAY" if str(r.get("type")) == "INTRADAY" else "FNO" if str(r.get("type")) == "FNO"
                     else "DS" if str(r.get("setup", "")).startswith("DS") else str(r.get("setup", "")))
    caps = dict(STRATEGY_CAP, **(L.get("strategy_max_open_risk_pct") or {}))
    k = fam(row)
    if k in caps:
        used = 0.0
        for _, r in op.iterrows():
            if fam(r) != k:
                continue
            try:
                used += (float(r.get("premium") or 0) * float(r.get("lot") or 0) * float(r.get("qty") or 1)
                         if str(r["type"]) == "FNO" else float(r["qty"]) * abs(float(r["entry"]) - float(r["stop"])))
            except Exception:
                continue
        if used + new > cap * float(caps[k]) / 100:
            return False, f"{k} tips already use their share of risk ({caps[k]}% of capital)"
    if risk + new > cap * float(L["max_open_risk_pct"]) / 100:
        return False, (f"total money at risk on open tips would be Rs {risk + new:,.0f} "
                       f"(limit {L['max_open_risk_pct']}% of capital)")
    if "result_pct" in t:      # losing-streak cooldown (closed tips, most recent first)
        cl = t[t["result_pct"].notna()].sort_values("closed_at")
        streak = 0
        for v in cl["result_pct"].iloc[::-1]:
            if v < 0:
                streak += 1
            else:
                break
        if streak >= int(L["loss_streak_pause"]):
            last = pd.to_datetime(cl["closed_at"].iloc[-1], errors="coerce")
            if pd.notna(last) and (_now() - last).days < int(L["loss_streak_cooldown_days"]):
                return False, f"{streak} losing tips in a row - cooldown until {(last + pd.Timedelta(days=int(L['loss_streak_cooldown_days']))).date()}"
    return True, ""


# ----------------------------------------------------------------------------- the gate
def check_new_entry(row, settings):
    """-> (ok, reason). The ONE gate every new trade recommendation passes."""
    if settings.get("kill_switch"):
        return False, "kill switch is ON (settings.yaml)"
    em = emergency_active()
    if em:
        return False, f"safety stop active since {em.get('since')}: {em.get('reason')}"
    ok, why = configured(settings)
    if not ok:
        return False, why
    ok, why = validate(row, settings)
    if not ok:
        return False, f"invalid tip ({why})"
    ok, why = portfolio_check(row, settings)
    if not ok:
        return False, why
    return True, ""


def record_skip(row, reason):
    try:
        rec = {"time": str(_now())[:16], "type": row.get("type"), "symbol": row.get("symbol"),
               "setup": row.get("setup"), "entry": row.get("entry"), "stop": row.get("stop"), "qty": row.get("qty"),
               "reason": str(reason)[:200]}
        pd.DataFrame([rec]).to_csv(SKIPPED_F, mode="a", header=not SKIPPED_F.exists(), index=False)
    except Exception:
        pass
