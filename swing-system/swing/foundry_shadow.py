"""Strategies designed by the ATLAS Strategy Foundry, after the owner's yes (strategies/lab_rules.json):
  - foundry-shadow (first yes): followed SILENTLY every evening on real prices -> journal/foundry_shadow.md
  - foundry-tips (second yes, only after 100+ fresh trades passed): evening tips (buy at the next open) with stop-loss,
    target, quantity (1% risk) and exit alerts; every tip is recorded (data/private/foundry_tips.csv) and tracked.
Same code as the test (vantage-ai/validation/foundry.py), so live signals are the tested signals. Never raises."""
import json
import os
import sys

import numpy as np
import pandas as pd

from .config import ROOT, PRIVATE, get_logger

log = get_logger()
REPORT = ROOT / "journal" / "foundry_shadow.md"
TIPS_F = PRIVATE / "foundry_tips.csv"
COLS = ["id", "sym", "signal", "atr", "k", "R", "T", "trail", "status", "entry", "stop", "target", "exit_day", "exit_why"]


def _approved(kinds):
    try:
        st = json.loads((ROOT / "strategies" / "lab_rules.json").read_text())
    except Exception:
        return []
    return [r for r in st.get("rules", []) if r.get("kind") in kinds and r.get("status") == "approved"]


def _foundry():
    from .config import ROOT as _R                       # the real repository, whatever ROOT the rules come from
    vd = os.path.join(os.path.dirname(str(_R)), "vantage-ai", "validation")
    if vd not in sys.path:
        sys.path.insert(0, vd)
    import foundry
    foundry.load()
    if not foundry._E:
        foundry._E.update(foundry.entries())
        foundry._F.update(foundry.filters())
    return foundry


def _signal(fo, r):
    E, F = fo._E[r["entry"]], fo._F[r["filter"]]
    return E if F is None else (E & F.fillna(False).astype(bool))


def _load_tips():
    try:
        return pd.read_csv(TIPS_F, dtype=str)
    except Exception:
        return pd.DataFrame(columns=COLS)


def tip_message(r, sym, close, atr, ex, s):
    from . import safety
    k, R = ex["k"], ex.get("R")
    stop_gap = k * atr
    q = safety.size(close, close - stop_gap, s)
    plan = ("sell when it closes below its " + ex["trail"].replace("ma", "") + "-day average"
            if ex.get("trail") else f"take profit at +{R:g} x the risk" if R else "time limit") + f", at most {ex['T']} days"
    return (f"🧪 ATLAS STRATEGY {r['id']}\n\n#{sym}\n\nBUY at tomorrow's open (≈ ₹{close:,.2f} today)\n"
            f"🛑 Stop-loss: the open minus ₹{stop_gap:,.2f} (≈ ₹{close - stop_gap:,.2f})"
            + (f"\n🎯 Target: the open plus ₹{R * stop_gap:,.2f} (≈ ₹{close + R * stop_gap:,.2f})" if R else "")
            + (f"\n📦 Qty ≈ {q} shares ≈ ₹{q * close:,.0f} · max loss ≈ ₹{q * stop_gap:,.0f} (1%)" if q else "")
            + f"\nExit: {plan}. I'll send the exit alert.\n\n{r['name']}\nResearch, not advice.")


def exit_check(fo, row, ex):
    """-> (why, plain) if the open tip must be closed today, else None (checked on today's bar)."""
    p = fo.P
    s = p["syms"].index(row["sym"])
    t = p["idx"].get_loc(pd.Timestamp(row["signal"]))
    last = len(p["idx"]) - 1
    if t + 1 > last:
        return None
    e = p["O_a"][t + 1, s]
    if not np.isfinite(e):
        return None
    stop = e - ex["k"] * float(row["atr"])
    tgt = e + ex["R"] * (e - stop) if ex.get("R") else None
    held = last - (t + 1)
    lo, hi, c = p["L_a"][last, s], p["H_a"][last, s], p["C_a"][last, s]
    if lo <= stop:
        return "stop", f"🛑 Stop-loss hit (₹{stop:,.2f}) - sell now / at the next open"
    if tgt is not None and hi >= tgt:
        return "target", f"🎯 Target reached (₹{tgt:,.2f}) - sell"
    if ex.get("trail"):
        ma = p[ex["trail"] + "_a"][last, s]
        armed = True
        if ex.get("arm"):
            armed = np.nanmax(p["C_a"][t + 1:last + 1, s]) >= e * (1 + ex["arm"])
        if armed and c < ma:
            return "trail", "📉 Closed below its trailing average - sell at tomorrow's open"
    if held >= ex["T"] - 1:
        return "time", f"⌛ {ex['T']}-day time limit reached - sell at tomorrow's open"
    return None


def run(send=True):
    shadows = _approved(("foundry-shadow", "foundry-tips"))
    if not shadows:
        return 0
    try:
        from .config import load_settings
        from . import telegram
        s = load_settings()
        fo = _foundry()
        L = [f"# ATLAS Foundry strategies - live record ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y})", "",
             "Signals since 20 Nov 2026, followed with the tested rules (same code as the test).", ""]
        tips = _load_tips()
        last_day = fo.P["idx"][-1]
        for r in shadows:
            ex = fo.EXITS[r["exit"]]
            sig = _signal(fo, r)
            T = fo.period(fo.trades(sig, ex), "fresh")
            first = sig & ~sig.shift(1, fill_value=False)
            n_sig = int(first.loc[first.index >= fo.FRESH].values.sum())
            net = T["exit"] / T["entry"] - 1 - 0.0075 if len(T) else pd.Series(dtype=float)
            L.append(f"- **{r['id']}** [{r['kind']}] {r['name']}: {n_sig} signals, {len(T)} closed"
                     + (f" - won {(net > 0).mean() * 100:.0f}%, average {net.mean() * 100:+.2f}% a trade after ~0.75% costs"
                        if len(T) else ""))
            if r["kind"] != "foundry-tips":
                continue
            # new tips: today's signals (entry tomorrow's open) - never while the kill switch / safety stop is on
            from . import safety
            blocked = bool(s.get("kill_switch")) or safety.emergency_active()
            today = first.iloc[-1] if not blocked else first.iloc[-1] & False
            for sym in today.index[today.values]:
                key = (r["id"], sym, str(last_day.date()))
                if ((tips["id"] == key[0]) & (tips["sym"] == key[1]) & (tips["signal"] == key[2])).any():
                    continue
                from . import registry
                held = registry.open_stocks().get(str(sym))
                if held and s.get("no_repeat_tips", True):
                    registry.record_suppressed(sym, f"ATLAS strategy {r['id']}", held, key[2])
                    continue                                          # D139: already an open tip elsewhere
                si = fo.P["syms"].index(sym)
                atr, close = float(fo.P["atr_a"][-1, si]), float(fo.P["C_a"][-1, si])
                from . import safety as _sf
                if _sf.size(close, close - ex["k"] * atr, s) < 1:
                    continue                                          # one share would break the 1% limit: no tip
                row = {"id": r["id"], "sym": sym, "signal": key[2], "atr": f"{atr:.4f}", "k": ex["k"], "R": ex.get("R", ""),
                       "T": ex["T"], "trail": ex.get("trail", ""), "status": "open"}
                tips = pd.concat([tips, pd.DataFrame([row]).astype(str)], ignore_index=True)
                tips.to_csv(TIPS_F, index=False)                     # record first ...
                if send:
                    telegram.send_reliable(s, tip_message(r, sym, close, atr, ex, s), label="trade tip")
            # exits for open tips of this strategy
            for i in tips.index[(tips["id"] == r["id"]) & (tips["status"] == "open")]:
                hit = exit_check(fo, tips.loc[i], ex)
                if hit:
                    tips.loc[i, ["status", "exit_day", "exit_why"]] = ["closed", str(last_day.date()), hit[0]]
                    tips.to_csv(TIPS_F, index=False)
                    if send:
                        telegram.send_reliable(s, f"🧪 ATLAS STRATEGY {r['id']} - EXIT\n\n#{tips.loc[i, 'sym']}\n\n{hit[1]}",
                                               label="exit alert")
        from .data_prices import provenance_line
        L += ["", "**" + provenance_line() + "**"]
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(L) + "\n")
        return len(shadows)
    except Exception as e:
        log.warning("foundry strategies failed: %s", type(e).__name__)
        return 0
