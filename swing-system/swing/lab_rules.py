"""Rules found by the automatic research (vantage-ai/validation/autoresearch.py) and approved by the owner.
Only rules with status 'approved' in strategies/lab_rules.json act, and only in two ways: skip a VANTAGE BUY, or halve
its quantity. They can never raise risk. Facts are computed with the same code the test used (lab_features.py).
If anything fails, no rule acts (the tip goes out as it would without research rules) and the problem is logged."""
import json
import os
import sys

import numpy as np
import pandas as pd

from .config import ROOT, get_logger

log = get_logger()
RULES_F = ROOT / "strategies" / "lab_rules.json"
_CACHE = {}


def _state():
    try:
        return json.loads(RULES_F.read_text())
    except Exception:
        return {"rules": [], "runs": []}


def _save(st):
    RULES_F.parent.mkdir(parents=True, exist_ok=True)
    RULES_F.write_text(json.dumps(st, indent=1, default=str))


def approved():
    return [r for r in _state().get("rules", []) if r.get("status") == "approved" and r.get("kind") in ("skip", "half")]


def set_status(rid, status):
    """Owner's /approve LAB-x or /decline LAB-x."""
    st = _state()
    for r in st.get("rules", []):
        if r.get("id", "").upper() == str(rid).upper():
            if status == "approved" and r.get("status") not in ("proposed", "declined"):
                return f"{r['id']} is {r.get('status')} - nothing to approve."
            r["status"], r[f"{status}_on"] = status, str(pd.Timestamp.now(tz="Asia/Kolkata").date())
            _save(st)
            log.info("Research rule %s %s by the owner", r["id"], status)
            if status == "approved":
                k = r.get("kind")
                if k == "foundry-shadow":
                    return (f"✅ {r['id']} approved: ATLAS now follows this new strategy SILENTLY on live prices "
                            "(journal/foundry_shadow.md). No tips until it proves itself and you approve again.")
                if k == "foundry-tips":
                    return f"✅ {r['id']} approved: its tips start from this evening (buy at the next open), with exit alerts."
                if k == "context-order":
                    return f"✅ {r['id']} approved: VANTAGE tips now show their behaviour-group rank."
                return f"✅ {r['id']} approved: {r.get('plain', r['name'])}. It acts on VANTAGE buys from the next scan."
            return f"🚫 {r['id']} switched off: {r.get('plain', r['name'])}."
    return f"No research rule {rid}. Proposals arrive as '🔬 Research result' messages."


def _features(sym, b, day):
    vd = os.path.join(os.path.dirname(str(ROOT)), "vantage-ai", "validation")
    if vd not in sys.path:
        sys.path.insert(0, vd)
    import lab_features as lf
    from . import data_prices
    d0 = data_prices.load(sym)
    if d0 is None or len(d0) < 260:
        return None
    if "adj_close" not in d0:
        d0 = d0.assign(adj_close=d0["close"])
    f = (d0["adj_close"] / d0["close"]).fillna(1.0)
    d = pd.DataFrame({"open": d0["open"] * f, "high": d0["high"] * f, "low": d0["low"] * f, "close": d0["adj_close"],
                      "volume": d0["volume"], "raw_close": d0["close"]}).dropna()
    sig = pd.Timestamp(str(b.get("signal") or day)[:10])
    F = lf.stock_features(d)
    F = F[F.index <= sig]
    if not len(F):
        return None
    x = F.iloc[-1].to_dict()
    if "bench" not in _CACHE:
        _CACHE["bench"] = data_prices.benchmark()
    n = _CACHE["bench"]                                      # same formulas as lab_features.market()
    c = (n["close"] if "close" in n else n.iloc[:, 0])
    c = c[c.index <= sig]
    if len(c) > 200:
        x.update(nifty_1m=float(c.iloc[-1] / c.iloc[-22] - 1), nifty_vs_200d=float(c.iloc[-1] / c.iloc[-200:].mean() - 1),
                 nifty_vol_20d=float(c.pct_change().iloc[-20:].std() * np.sqrt(252)))
    close, stop = float(b.get("close") or d["raw_close"].iloc[-1]), float(b.get("stop"))
    x.update(setup=str(b.get("setup", "")), score=float(b.get("score") or 0), stop_dist=(close - stop) / close,
             weekday=sig.day_name()[:3], month=str(sig.month), day_of_month=sig.day)
    try:
        sec = pd.read_csv(ROOT / "data" / "events" / "nifty500.csv")
        x["sector"] = dict(zip(sec["Symbol"].astype(str), sec["Industry"].astype(str))).get(sym, "unknown")
    except Exception:
        x["sector"] = "unknown"
    return x


def _hits(r, x):
    v = x.get(r.get("col"))
    if v is None or (isinstance(v, float) and v != v):
        return False
    if r.get("num"):
        lo, hi = (float(z) for z in r["val"])
        return lo <= float(v) < hi
    return str(v) == str(r.get("val"))


def decision(sym, b, day):
    """-> (None | 'skip' | 'half', rule id). Skip wins over half. Never raises."""
    rules = approved()
    if not rules:
        return None, ""
    key = (sym, str(b.get("signal") or day)[:10], str(b.get("setup")))
    if key in _CACHE:
        return _CACHE[key]
    out = (None, "")
    try:
        x = _features(sym, b, day)
        if x is not None:
            for kind in ("skip", "half"):
                hit = [r for r in rules if r["kind"] == kind and _hits(r, x)]
                if hit:
                    out = (kind, hit[0]["id"])
                    break
    except Exception as e:
        log.warning("research rules could not be checked for a signal: %s", type(e).__name__)
    _CACHE[key] = out
    return out


def context_line(sym, b, day, group_only=False):
    """Approved context-order rule (ATLAS Context Engine) -> one message line with the stock's behaviour group and its
    rank, so the owner takes higher-ranked tips first when money is short. '' when none is approved or on any error."""
    rules = [r for r in _state().get("rules", []) if r.get("status") == "approved" and r.get("kind") == "context-order"]
    if group_only:
        rules = [{"_group_only": True}]
    if not rules:
        return ""
    try:
        M = json.loads((ROOT / "strategies" / "context_model.json").read_text())
        vd = os.path.join(os.path.dirname(str(ROOT)), "vantage-ai", "validation")
        if vd not in sys.path:
            sys.path.insert(0, vd)
        import context_engine as ce
        from . import data_prices
        d0 = data_prices.load(sym)
        f = (d0["adj_close"] / d0["close"]).fillna(1.0) if "adj_close" in d0 else 1.0
        d = pd.DataFrame({"open": d0["open"] * f, "close": d0.get("adj_close", d0["close"])}).dropna()
        sig = pd.Timestamp(str(b.get("signal") or day)[:10])
        B = ce.behaviour(d)
        B = B[B.index <= sig].iloc[-1].to_dict()
        x = _features(sym, b, day) or {}
        B.update({k: x.get(k) for k in ("atr_pct", "from_52w_high", "ret_6m")})
        B["log_turnover"] = float(np.log10(max(float(x.get("turnover_cr") or 0.01), 0.01)))
        z = np.array([(float(B[k]) - M["mu"][k]) / (M["sd"][k] or 1) for k in M["features"]]).clip(-4, 4)
        g = "B" + str(int(np.argmin(((np.array(M["centres"]) - z) ** 2).sum(axis=1))))
        name = rules[0].get("grouping", "behaviour10")
        if rules[0].get("_group_only"):
            return g
        key = g if name == "behaviour10" else f"{g}~{b.get('setup', '')}"
        sc = M["scores"].get(name, {})
        if key not in sc:
            return ""
        rank = 1 + sum(v > sc[key] for v in sc.values())
        return (f"\n🧭 ATLAS context: behaviour group {g} ranks {rank} of {len(sc)} (past {sc[key] * 100:+.1f}% a trade) - "
                f"when money is short, take higher-ranked tips first ({rules[0]['id']})")
    except Exception as e:
        log.warning("context line failed: %s", type(e).__name__)
        return ""


def behaviour_group(sym, b, day):
    """The stock's discovered behaviour group (B0..B9) at the signal, '' if unknown (used by the why-engine)."""
    return context_line(sym, b, day, group_only=True)
