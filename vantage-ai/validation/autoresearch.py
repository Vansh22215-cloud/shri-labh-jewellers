"""AUTO-RESEARCH: the research that runs every week on GitHub, without Claude (owner 19 Nov: "research tests ...
nobody will run the tests" -> they must run by themselves; AUTO_LAB_PROTOCOL.md is the rulebook).

Every run:
 1. rebuilds the full VANTAGE trade history (top-300 and all stocks) from the latest prices, so every new week adds
    FRESH trades nobody has looked at (signals from 20 Nov 2026 on);
 2. describes every trade by ~40 facts at its signal (lab_features.build) - stock, its history, market, sector, time;
 3. tests every possibility (auto_lab.possibilities: skip / half quantity / take-first) with the 4-step bar:
    development -> luck count -> recent years (holdout) -> year by year + random-skip placebo,
    and, once there are 150+ fresh top-300 trades, step 5: not worse on the fresh trades;
 4. a rule that clears every step and can be applied live becomes a PROPOSAL: one Telegram message to the owner
    ("/approve LAB-xxxx" or "/decline LAB-xxxx"). Nothing changes without his yes. Approved rules are re-checked on the
    fresh trades every week and flagged if they stop holding.
Outputs: swing-system/strategies/lab_rules.json (proposals/approved/declined), swing-system/journal/auto_research.md.
Never raises risk: rules can only skip, halve or reorder trades; the 1% limit and 25% cap stay."""
import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import improve as im  # noqa: E402
from improve import iv, OOS  # noqa: E402
import auto_lab as al  # noqa: E402

SW = im.SW
FRESH = pd.Timestamp("2026-11-20")       # first signal day nobody had seen when the auto-research started
FRESH_MIN = 150                          # fresh top-300 trades needed before step 5 counts
RULES_F = os.path.join(SW, "strategies", "lab_rules.json")
REPORT_F = os.path.join(SW, "journal", "auto_research.md")
WORK = os.path.join(SW, "data", "auto_research")
# facts the live system can compute at a signal exactly as the test did (market-type and results columns cannot yet)
LIVE_OK = {"turnover_cr", "from_52w_high", "ret_6m", "ret_1m", "ret_1w", "vol_surge", "atr_pct", "range_10d", "vs_200d",
           "signal_day_move", "price_rs", "up_days_10", "nifty_1m", "nifty_vs_200d", "nifty_vol_20d", "score",
           "stop_dist", "day_of_month", "setup", "weekday", "month", "sector"}


def rule_id(r):
    return "LAB-" + hashlib.sha1(r["name"].encode()).hexdigest()[:4].upper()


def _trades(data, procs=4):
    from multiprocessing import Pool
    im.BENCH, im.PARAMS = iv.nifty()["close"], {}
    tr = []
    with Pool(procs) as p:
        for r in p.imap_unordered(im._one, data, chunksize=4):
            tr += [t for t in r if "error" not in t]
    T = pd.DataFrame(tr)
    for c in ("signal", "entry_date", "exit_date"):
        T[c] = pd.to_datetime(T[c])
    return T


def rebuild():
    """-> trades of both sets from today's data (top-300 point-in-time; all stocks)."""
    top = _trades(list(iv.universe(include_delisted=True)))
    allx = _trades([(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in im.all_stocks()])
    return pd.concat([top.assign(set="top300"), allx.assign(set="all")], ignore_index=True)


def prepare(X):
    X = X[(X["entry"] > X["init_stop"]) & (X["entry"] > 0)].copy()
    X["stop_dist"] = (X["entry"] - X["init_stop"]) / X["entry"]
    X["month"] = X["month"].astype(str)
    X["dev"] = X["signal"] < OOS
    X["period"] = np.where(X["signal"] < OOS, "dev", np.where(X["signal"] < FRESH, "holdout", "fresh"))
    return X


def judge(X, survivors):
    """Steps 2-5 for step-1 survivors -> list of results."""
    per = lambda k, p: X[(X["set"] == k) & (X["period"] == p)].reset_index(drop=True)
    H = {k: per(k, "holdout") for k in ("top300", "all")}
    Fr = per("top300", "fresh")
    base = {k: al.run(S, {"kind": "none"}, 15) for k, S in H.items()}
    fbase = al.run(Fr, {"kind": "none"}, 15) if len(Fr) >= FRESH_MIN else None
    T3 = X[(X["set"] == "top300") & (X["period"] != "fresh")].reset_index(drop=True)
    D3 = per("top300", "dev")
    years = sorted(T3["signal"].dt.year.unique())
    out = []
    for r in survivors:
        v = {k: al.run(S, r, 15) for k, S in H.items()}
        r["holdout"] = {k: {"cagr": round(v[k][0], 2), "maxdd": round(v[k][1], 2)} for k in H}
        r["holdout_pass"] = all(v[k][0] >= base[k][0] + 1 and v[k][1] >= base[k][1] - 2 for k in H)
        better = n = 0
        for y in years:
            Y = T3[T3["signal"].dt.year == y].reset_index(drop=True)
            if len(Y) < 50:
                continue
            n += 1
            better += al.run(Y, r, 7)[0] >= al.run(Y, {"kind": "none"}, 7)[0]
        r["years_better"] = f"{better} of {n}"
        r["years_pass"] = better >= 0.6 * n
        if r["kind"] == "skip":
            frac = float(al.rule_mask(D3, r).mean())
            g = al.run(D3, r, 7)[0]
            beaten = sum(g > al.run(D3, {"kind": "random_skip", "val": frac, "seed": s}, 7)[0] for s in range(20))
            r["placebo_beaten"], r["placebo_pass"] = f"{beaten} of 20", beaten >= 18
        else:
            r["placebo_pass"] = True
        if fbase is not None:
            fv = al.run(Fr, r, 15)
            r["fresh"] = {"cagr": round(fv[0], 2), "base": round(fbase[0], 2), "n": len(Fr)}
            r["fresh_pass"] = fv[0] >= fbase[0]
        else:
            r["fresh"], r["fresh_pass"] = {"n": len(Fr), "waiting": f"needs {FRESH_MIN}"}, None
        r["live_ok"] = r.get("col") in LIVE_OK
        r["CANDIDATE"] = bool(r["holdout_pass"] and r["years_pass"] and r["placebo_pass"] and r["fresh_pass"] is not False)
        r["id"] = rule_id(r)
        out.append(r)
    return base, fbase, out


def recheck_approved(X, state):
    """Approved rules: still not worse on the fresh trades? -> list of warnings."""
    Fr = X[(X["set"] == "top300") & (X["period"] == "fresh")].reset_index(drop=True)
    warn = []
    if len(Fr) < FRESH_MIN:
        return warn
    fb = al.run(Fr, {"kind": "none"}, 15)[0]
    for r in state["rules"]:
        if r.get("status") == "approved":
            fv = al.run(Fr, r, 15)[0]
            r["fresh_check"] = {"cagr": round(fv, 2), "base": round(fb, 2), "n": len(Fr), "on": str(pd.Timestamp.now().date())}
            if fv < fb - 1:
                warn.append(f"{r['id']} ({r['name']}) is not holding on {len(Fr)} fresh trades: {fv:.1f}% vs {fb:.1f}% a "
                            f"year without it. Send /decline {r['id']} to switch it off.")
    return warn


def load_state():
    try:
        return json.load(open(RULES_F))
    except Exception:
        return {"note": "AUTO-RESEARCH rules (vantage-ai/validation/autoresearch.py). status: proposed -> approved / "
                        "declined only by the owner (/approve, /decline). Approved rules are applied by VANTAGE.",
                "rules": [], "runs": []}


def save_state(state):
    os.makedirs(os.path.dirname(RULES_F), exist_ok=True)
    json.dump(state, open(RULES_F, "w"), indent=1, default=str)


def message(r):
    h, f = r["holdout"], r.get("fresh", {})
    if r.get("kind") == "foundry-shadow":
        return ("🧪 ATLAS designed a NEW strategy that passed every test\n\n"
                f"{r['id']}: {r['name']}\n\n"
                f"Recent years (Nov 2023+), after all costs and tax: {h['top300']['cagr']:.1f}% a year on its own "
                f"(worst fall {h['top300']['maxdd']:.0f}%); next to your current tips the account made "
                f"{h['all']['cagr']:.1f}% a year. Year by year: better in {r['years_better']}.\n"
                "Next step is a SILENT live record (no tips, no money): ATLAS follows its signals on real prices. "
                f"After 100+ live trades it asks you again before any tip is sent.\n\n/approve {r['id']} or /decline {r['id']}")
    if r.get("kind") == "foundry-tips":
        fr = r.get("fresh", {})
        return ("🧪 ATLAS strategy ready for real tips\n\n"
                f"{r['id']}: {r['name']}\n\n"
                f"Its silent live record: {fr.get('n', 0)} trades since 20 Nov 2026; on those, alone "
                f"{fr.get('alone', [0])[0]:.1f}% a year, next to your current tips {fr.get('with_current', [0])[0]:.1f}% vs "
                f"{fr.get('current', [0])[0]:.1f}% without it (after costs and tax).\n"
                "If you approve, its tips come in the evening (buy at the next open) with stop-loss, target, quantity "
                f"(1% risk) and exit alerts.\n\n/approve {r['id']} or /decline {r['id']}")
    return ("🔬 ATLAS research result - a rule passed every test\n\n"
            f"{r['id']}: {r['plain']}\n\n"
            f"Recent years (Nov 2023+): top-300 {h['top300']['cagr']:.1f}% a year, all stocks {h['all']['cagr']:.1f}% "
            f"(worst fall {h['top300']['maxdd']:.0f}% / {h['all']['maxdd']:.0f}%) - better than without it in both.\n"
            f"Older years: passed. Year by year: better in {r['years_better']}. "
            + (f"Random-skip check: beat {r['placebo_beaten']}. " if r.get("placebo_beaten") else "")
            + (f"Fresh trades since 20 Nov: {f['cagr']:.1f}% vs {f['base']:.1f}%." if "cagr" in f else
               f"Fresh trades since 20 Nov: {f.get('n', 0)} so far (checked every week).")
            + f"\n\nRisk per trade stays 1%. Reply /approve {r['id']} to use it, /decline {r['id']} to drop it.")


def plain(r):
    k, c = r["kind"], r.get("col", "")
    names = {"turnover_cr": "money traded a day (₹ cr)", "from_52w_high": "distance from the 52-week high",
             "ret_6m": "6-month return", "ret_1m": "1-month return", "ret_1w": "1-week return",
             "vol_surge": "volume vs normal", "atr_pct": "daily swing", "range_10d": "10-day range",
             "vs_200d": "distance from the 200-day average", "signal_day_move": "signal-day move",
             "price_rs": "share price (₹)", "up_days_10": "up-days in the last 10", "nifty_1m": "NIFTY 1-month return",
             "nifty_vs_200d": "NIFTY vs its 200-day average", "nifty_vol_20d": "NIFTY swing", "score": "signal score",
             "stop_dist": "stop-loss distance", "day_of_month": "day of the month"}
    nm = names.get(c, c.replace("_", " "))
    if r.get("num"):
        lo, hi = r["val"]
        rng = (f"below {hi:.4g}" if lo == -np.inf or lo < -1e300 else f"above {lo:.4g}" if hi == np.inf or hi > 1e300
               else f"between {lo:.4g} and {hi:.4g}")
        return f"{'Skip' if k == 'skip' else 'Half quantity on'} VANTAGE buys when the {nm} is {rng}"
    if k in ("prefer_high", "prefer_low"):
        return f"When money is short, take the VANTAGE buys with the {'highest' if k == 'prefer_high' else 'lowest'} {nm} first"
    return f"{'Skip' if k == 'skip' else 'Half quantity on'} VANTAGE buys when {nm} = {r.get('val')}"


def lead_rules():
    """Patterns the why-engine found in live (or proof-run) tips and confirmed in both history periods
    (strategies/why_leads.json) -> exact-bucket skip / half rules, tested with the same bar as every possibility."""
    try:
        L = json.load(open(os.path.join(SW, "strategies", "why_leads.json")))["leads"]
    except Exception:
        return []
    out, seen = [], set()
    for x in L:
        lo, hi = (float(v) for v in x["range"])
        kind = "skip" if "worse" in x["verdict"] else None
        if kind is None:            # a 'better' tail: test skipping everything outside it is too blunt - half the rest
            continue
        for k in ("skip", "half"):
            name = f"{k} {x['col']} {'' if lo == -np.inf else f'{lo:.4g}'}..{'' if hi == np.inf else f'{hi:.4g}'} (why-lead)"
            if name not in seen:
                seen.add(name)
                out.append({"kind": k, "col": x["col"], "val": [lo, hi], "num": True, "name": name, "lead": x["key"]})
    return out


def foundry_promotions(state, foundry, min_fresh=100):
    """Approved shadow strategies with 100+ fresh closed trades: still beating the NIFTY fund and adding to the live
    system on the fresh trades? -> a second proposal: send its tips (FTP-xxxx). Nothing is sent without that yes."""
    out, stats = [], {}
    known = {r["id"] for r in state["rules"]}
    for r in state["rules"]:
        if r.get("kind") != "foundry-shadow" or r.get("status") != "approved":
            continue
        foundry._E.update(foundry.entries()) if not foundry._E else None
        foundry._F.update(foundry.filters()) if not foundry._F else None
        E, F = foundry._E[r["entry"]], foundry._F[r["filter"]]
        T = foundry.trades(E if F is None else (E & F.fillna(False).astype(bool)), foundry.EXITS[r["exit"]])
        Fr, B = foundry.period(T, "fresh"), foundry.period(foundry.current_system(), "fresh")
        r["fresh"] = {"n": int(len(Fr))}
        if len(Fr) < min_fresh or not len(B):
            continue
        alone, comb, base = foundry.account(Fr, 15), foundry.account(Fr, 15, base=B), foundry.account(B, 15)
        r["fresh"].update(alone=alone, with_current=comb, current=base)
        pid = "FTP-" + r["id"][4:]
        if comb[0] >= base[0] + 1 and comb[1] >= base[1] - 2 and alone[0] > 0 and pid not in known:
            rec = {"id": pid, "name": r["name"], "kind": "foundry-tips", "status": "proposed", "parent": r["id"],
                   "entry": r["entry"], "filter": r["filter"], "exit": r["exit"],
                   "plain": f"Start sending tips for {r['id']} (its silent live record passed): {r['name']}",
                   "holdout": {"top300": {"cagr": alone[0], "maxdd": alone[1]}, "all": {"cagr": comb[0], "maxdd": comb[1]}},
                   "years_better": f"fresh {len(Fr)} trades", "fresh": r["fresh"], "proposed_on": str(pd.Timestamp.now().date())}
            state["rules"].append(rec)
            out.append(rec)
    return out, stats


def run(send=True, procs=4, luck_worlds=3):
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True)
    import lab_features as lf
    import situation_memory as sm
    T = rebuild()
    S = sm.situations()["key"]
    X = prepare(lf.build(T, S, procs=procs))
    X.to_csv(os.path.join(WORK, "features.csv.gz"), index=False)
    rules = al.possibilities(X) + lead_rules()
    base_dev, passed = al.screen(X, rules, procs=procs)
    luck = [len(al.screen(al.shuffled(X, s), [dict(r) for r in rules], procs=procs)[1]) for s in range(1, luck_worlds + 1)]
    base_h, fbase, res = judge(X, passed)
    state = load_state()
    known = {r["id"]: r for r in state["rules"]}
    new = []
    for r in res:
        r["plain"] = plain(r)
        # "take first" rules (R28: momentum order was the best near miss) are proposed only after they also hold on
        # the fresh trades (step 5 must have run and passed); they change the order advice, never the risk
        prefer_ok = r["kind"] in ("prefer_high", "prefer_low") and r.get("fresh_pass") is True
        if r["CANDIDATE"] and r["live_ok"] and (r["kind"] in ("skip", "half") or prefer_ok):
            old = known.get(r["id"])
            if old is None:
                r["status"], r["proposed_on"] = "proposed", str(pd.Timestamp.now().date())
                state["rules"].append({k: v for k, v in r.items() if k != "dev"} | {"dev": r["dev"]})
                new.append(r)
            elif old.get("status") == "proposed":
                old.update({k: r[k] for k in ("holdout", "years_better", "fresh") if k in r})
    try:   # ATLAS Context Engine (CONTEXT_PROTOCOL.md): which rule works on which kind of stock, re-learned weekly
        import context_engine as ce
        C = ce.main()
        for name, r in C["rules"].items():
            cid = "CTX-" + hashlib.sha1(name.encode()).hexdigest()[:4].upper()
            if r.get("PASS") and name.startswith("C-ORDER") and cid not in known:
                rec = {"id": cid, "name": name, "kind": "context-order", "grouping": name.split(" by ", 1)[1],
                       "status": "proposed", "proposed_on": str(pd.Timestamp.now().date()),
                       "plain": f"When money is short, take first the tips whose behaviour group has the best record ({name})",
                       "holdout": {k: {"cagr": r[k]["holdout"]["rule"][0], "maxdd": r[k]["holdout"]["rule"][1]} for k in ("top300", "all")},
                       "years_better": r["top300"]["years_better"], "fresh": {}}
                state["rules"].append(rec)
                new.append(rec)
        summary_ctx = {"matters": C["matters"], "passed": [n for n, r in C["rules"].items() if r.get("PASS")]}
    except Exception as e:
        summary_ctx = {"error": type(e).__name__}
        print("context engine failed:", type(e).__name__)
    try:   # ATLAS Strategy Foundry (FOUNDRY_PROTOCOL.md): new strategies designed from building blocks, every week
        import foundry
        Fo = foundry.main(procs=procs)
        for name in Fo["passed"]:
            fid = "FND-" + hashlib.sha1(name.encode()).hexdigest()[:4].upper()
            if fid not in known:
                r = next(x for x in Fo["all"] if x["name"] == name)
                rec = {"id": fid, "name": name, "kind": "foundry-shadow", "status": "proposed",
                       "entry": r["entry"], "filter": r["filter"], "exit": r["exit"],
                       "proposed_on": str(pd.Timestamp.now().date()),
                       "plain": f"New strategy (silent live record first, no tips): {name}",
                       "holdout": {"top300": {"cagr": r["hold_alone"][0], "maxdd": r["hold_alone"][1]},
                                   "all": {"cagr": r["hold_with_current"][0], "maxdd": r["hold_with_current"][1]}},
                       "years_better": r["years_better"], "fresh": {}}
                state["rules"].append(rec)
                new.append(rec)
        summary_fnd = {k: Fo[k] for k in ("tried", "dev_survivors", "luck_passed", "passed")}
        promos, fstats = foundry_promotions(state, foundry)
        new += promos
    except Exception as e:
        summary_fnd = {"error": type(e).__name__}
        print("foundry failed:", type(e).__name__)
    warns = recheck_approved(X, state)
    n_fresh = int(((X["set"] == "top300") & (X["period"] == "fresh")).sum())
    summary = {"on": str(pd.Timestamp.now(tz="Asia/Kolkata"))[:16], "trades": int(len(X)), "fresh_top300": n_fresh,
               "possibilities": len(rules), "passed_dev": len(passed), "luck_passes": luck,
               "candidates": [r["id"] for r in res if r["CANDIDATE"]], "new_proposals": [r["id"] for r in new],
               "context": summary_ctx, "foundry": summary_fnd, "minutes": round((time.time() - t0) / 60, 1)}
    state["runs"] = (state.get("runs", []) + [summary])[-52:]
    save_state(state)
    write_report(summary, base_dev, base_h, fbase, res, state, warns)
    if send:
        try:
            from swing import telegram
            from swing.config import load_settings
            s = load_settings()
            for r in new:
                telegram.send(s, message(r), label="research result")
            for w in warns:
                telegram.send(s, "🔬 Research check\n\n" + w, label="research result")
        except Exception as e:
            print("telegram failed:", type(e).__name__)
    print(json.dumps(summary), flush=True)
    return summary


def write_report(summary, base_dev, base_h, fbase, res, state, warns):
    L = [f"# Automatic research ({summary['on']} IST)", "",
         "Runs every week on GitHub by itself (vantage-ai/validation/autoresearch.py, rulebook AUTO_LAB_PROTOCOL.md).",
         "", f"- Trades rebuilt from today's prices: {summary['trades']:,} (fresh top-300 trades since 20 Nov 2026: "
         f"{summary['fresh_top300']}; step 5 starts at {FRESH_MIN})",
         f"- Possibilities tested: {summary['possibilities']}; passed the older years: {summary['passed_dev']}; "
         f"passed in luck worlds (facts shuffled): {summary['luck_passes']}",
         f"- Passed every step: {len(summary['candidates'])}; new proposals sent to the owner: {len(summary['new_proposals'])}",
         f"- Current system, recent years: top-300 {base_h['top300'][0]:.1f}% a year, all stocks {base_h['all'][0]:.1f}%",
         "", "## Step-1 survivors and their later steps", "",
         "| Rule | Recent top-300 | Recent all | Years | Placebo | Fresh | Live-ready | Verdict |", "|---|---|---|---|---|---|---|---|"]
    for r in res:
        f = r.get("fresh", {})
        fr = f"{f['cagr']:.1f}% vs {f['base']:.1f}%" if "cagr" in f else f.get("waiting", "-")
        L.append(f"| {r['id']} {r['plain']} | {r['holdout']['top300']['cagr']:.1f}% | {r['holdout']['all']['cagr']:.1f}% | "
                 f"{r['years_better']} | {r.get('placebo_beaten', '-')} | "
                 f"{fr} | "
                 f"{'yes' if r['live_ok'] else 'no'} | {'PASS' if r['CANDIDATE'] else 'fail'} |")
    if not res:
        L.append("| none | | | | | | | |")
    L += ["", "## Rules and their status (strategies/lab_rules.json)"]
    L += [f"- {r['id']} [{r.get('status')}] {r.get('plain', r['name'])}" for r in state["rules"]] or ["- none yet"]
    L += [f"- ⚠️ {w}" for w in warns]
    L += ["", "## Earlier runs"] + [f"- {x['on']}: {x['possibilities']} tested, {x['passed_dev']} passed step 1, "
                                    f"{len(x['candidates'])} passed all, {x['minutes']} min" for x in state["runs"][-8:]]
    os.makedirs(os.path.dirname(REPORT_F), exist_ok=True)
    open(REPORT_F, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    run(send="--send" in sys.argv)
