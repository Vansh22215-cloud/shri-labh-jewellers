"""EVERYTHING AGAIN ON KITE DATA (owner 19 Nov: "do all work again, tests, runs, each and everything, with Kite
Connect data"). Runs on GitHub (Kite keys live only there) once Kite daily history is complete.
Every input that comes from prices is rebuilt from Kite exchange candles (SWING_PRICE_SOURCE=kite); stocks Kite does
not list (delisted) keep NSE's official bhavcopy rebuilds. Every result goes to a separate folder
(swing-system/data/kite_rerun), so the Yahoo originals stay for the side-by-side comparison:
  swing-system/journal/kite_rerun.md  +  swing-system/journal/kite_rerun/*.json  (results only - no Kite prices)."""
import json
import os
import shutil
import subprocess
import sys
import time

HERE0 = os.path.dirname(os.path.abspath(__file__))
SW = os.path.join(os.path.dirname(os.path.dirname(HERE0)), "swing-system")
RUN = os.path.join(SW, "data", "kite_rerun")
OUT = os.path.join(SW, "journal", "kite_rerun")
os.makedirs(RUN, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
os.environ.update(SWING_PRICE_SOURCE="kite", ATLAS_RUN_DIR=RUN, ATLAS_FEATURES=os.path.join(RUN, "lab_features.csv.gz"),
                  ATLAS_CONTEXT_TRADES=os.path.join(RUN, "context_trades.csv.gz"))
sys.path.insert(0, HERE0)
sys.path.insert(0, SW)

STEPS = [  # (label, command run in RUN with the Kite environment, result file)
    ("market-mood calendar (13 years)", ["situation_memory.py"], "situation_memory.json"),
    ("ADD MORE trade paths", ["recycle_explore.py"], "recycle_paths.csv"),
    ("40 facts per trade", ["lab_features.py"], "lab_features.csv.gz"),
    ("luck check: stock choice vs random", ["luck_check2.py"], "luck_check2.json"),
    ("stock-choice fingerprint", ["fingerprint.py"], "fingerprint.json"),
    ("round 21 stress test (costs, slippage, missed tips)", ["improve21.py"], "improve21_results.json"),
    ("round 24 crash scenario", ["improve24.py"], "improve24_results.json"),
    ("round 25 compounding", ["improve25.py"], "improve25_results.json"),
    ("round 26 top-300 vs all stocks", ["improve26.py"], "improve26_results.json"),
    ("round 27 universe size 100-500", ["improve27.py"], "improve27_results.json"),
    ("round 28 tip order when money is short", ["improve28.py"], "improve28_results.json"),
    ("round 29 VANTAGE + live dip-buy", ["improve29.py"], "improve29_results.json"),
    ("real Zerodha costs + 20.8% tax", ["costs_real.py"], "costs_real_results.json"),
    ("NIFTY on identical terms", ["benchmark_fair.py"], "benchmark_fair_results.json"),
    ("auto-lab step 1 (230 rules, luck worlds)", ["auto_lab.py", "step1"], "auto_lab_step1.json"),
    ("auto-lab step 2 (recent years, years, placebo)", ["auto_lab.py", "step2"], "auto_lab_results.json"),
    ("context engine (behaviour, sector, company, market...)", ["-c", "import context_engine as c; c.main()"], "context_results.json"),
    ("strict behaviour groups (past only)", ["strict_groups.py"], "strict_groups_results.json"),
    ("Strategy Foundry (640 strategies)", ["foundry.py"], "foundry_results.json"),
]


def generate():
    """Trade lists from Kite prices with the same VANTAGE code: B (next open), C1 (3:20 pm), U (all stocks), DIP."""
    import pandas as pd
    import improve as im
    import autoresearch as ar
    from swing import data_prices
    from multiprocessing import Pool
    top = list(im.iv.universe(include_delisted=True))
    allx = [(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in im.all_stocks()]
    sets = {}
    for name, data, params in (("trades_FINAL.csv", top, {}), ("improve3_trades_C1.csv", top, {"entryAtClose": True}),
                               ("improve_trades_U2.csv", allx, {})):
        im.PARAMS = params
        T = ar._trades(data)
        T.to_csv(os.path.join(RUN, name), index=False)
        sets[name] = T
    shutil.copy(os.path.join(RUN, "improve_trades_U2.csv"), os.path.join(RUN, "improve_trades_U.csv"))
    sys.path.insert(0, os.path.join(SW, "validation"))
    import independent_validation as ivv
    trades = []
    with Pool(4) as p:
        for r in p.imap_unordered(ivv._one, [("DIP", s, d, m, src) for s, d, m, src in top], chunksize=4):
            trades += [t for t in r if "error" not in t]
    pd.DataFrame(trades).to_csv(os.path.join(RUN, "independent_trades_DIP.csv"), index=False)
    for f in ("improve8_results_events.csv",):                     # event dates (not prices)
        if os.path.exists(os.path.join(HERE0, f)):
            shutil.copy(os.path.join(HERE0, f), os.path.join(RUN, f))
    prov = {k: len(v) for k, v in data_prices.PROVENANCE.items()}
    nse = {k: int((T["src"] == "nse").sum()) for k, T in sets.items() if "src" in T}
    return {"trades": {k: len(v) for k, v in sets.items()}, "dip_trades": len(trades), "price_sources": prov,
            "trades_from_nse_bhavcopy_(delisted)": nse, "line": data_prices.provenance_line()}


def main():
    t0 = time.time()
    log = {"started": time.strftime("%Y-%m-%d %H:%M"), "steps": []}
    try:
        log["generate"] = generate()
    except Exception as e:
        log["generate"] = {"error": repr(e)[:300]}
    for label, cmd, out in STEPS:
        t = time.time()
        args = [sys.executable] + ([cmd[0]] if cmd[0] == "-c" else [os.path.join(HERE0, cmd[0])]) + cmd[1:]
        try:
            r = subprocess.run(args, cwd=RUN, env=os.environ.copy(), timeout=5400, capture_output=True, text=True)
            ok = r.returncode == 0 and os.path.exists(os.path.join(RUN, out))
            err = "" if ok else (r.stderr or "")[-400:]
        except Exception as e:
            ok, err = False, repr(e)[:300]
        log["steps"].append({"step": label, "ok": ok, "minutes": round((time.time() - t) / 60, 1), "error": err})
        if ok and out.endswith(".json"):
            shutil.copy(os.path.join(RUN, out), os.path.join(OUT, out))
        print(label, "OK" if ok else "FAILED", flush=True)
    log["minutes"] = round((time.time() - t0) / 60, 1)
    json.dump(log, open(os.path.join(OUT, "run_log.json"), "w"), indent=1)
    report(log)
    return log


def _get(d, *path):
    for p in path:
        if isinstance(d, dict) and p in d:
            d = d[p]
        else:
            return None
    return d


def report(log):
    """Side-by-side headline numbers, Yahoo (earlier files) vs Kite (this run)."""
    def both(f, *path):
        y, k = (json.load(open(os.path.join(d, f))) if os.path.exists(os.path.join(d, f)) else {} for d in (HERE0, OUT))
        return _get(y, *path), _get(k, *path)
    rows = [("Live setup C+A top-300, recent years (round 21 normal)", "improve21_results.json", ("holdout", "S0 normal", "C+A", "cagr")),
            ("Live setup C+A top-300, older years", "improve21_results.json", ("dev", "S0 normal", "C+A", "cagr")),
            ("Top-300, recent years (round 26)", "improve26_results.json", ("periods", "holdout fixed", "U-300")),
            ("All stocks >= Rs 2 cr, recent years (round 26)", "improve26_results.json", ("periods", "holdout fixed", "U-all")),
            ("VANTAGE + dip-buy after costs + tax, recent", "costs_real_results.json", ("VANTAGE + live dip-buy (what you receive)", "holdout Nov 2023-Nov 2026", "real costs + 20% tax", "cagr")),
            ("VANTAGE + dip-buy after costs + tax, older", "costs_real_results.json", ("VANTAGE + live dip-buy (what you receive)", "dev 2013-Oct 2023", "real costs + 20% tax", "cagr")),
            ("Crash: 10% gap one-morning loss, recent", "improve24_results.json", ("holdout", "C+A", "gap 10%", "one_day_loss_pct")),
            ("Auto-lab: rules passing step 1 / luck", "auto_lab_step1.json", ("passed_dev",)),
            ("Foundry: strategies passing development", "foundry_results.json", ("dev_survivors",)),
            ("Momentum-first order (P1), recent", "improve28_results.json", ("P1", "holdout fixed")),
            ("Strict behaviour groups DYNAMIC pass?", "strict_groups_results.json", ("DYNAMIC", "PASS"))]
    L = ["# Everything re-run on Kite data", "", f"Run started {log['started']} on GitHub, {log['minutes']} minutes.", "",
         "## Data used", ""]
    g = log.get("generate", {})
    L += [f"- {g.get('line', 'generation failed: ' + str(g.get('error')))}",
          f"- Trades rebuilt from Kite prices: {g.get('trades')}; live dip-buy trades: {g.get('dip_trades')}",
          f"- Of those, trades in delisted stocks (NSE bhavcopy, Kite does not list them): {g.get('trades_from_nse_bhavcopy_(delisted)')}",
          "", "## Every step", "", "| Step | Result | Minutes |", "|---|---|---|"]
    L += [f"| {s['step']} | {'done' if s['ok'] else 'FAILED: ' + s['error'][-120:].replace('|', '/')} | {s['minutes']} |" for s in log["steps"]]
    L += ["", "## Headline numbers: Yahoo (earlier) vs Kite (now)", "", "| What | Yahoo | Kite |", "|---|---|---|"]
    for name, f, path in rows:
        y, k = both(f, *path)
        L.append(f"| {name} | {y} | {k} |")
    L += ["", "Full Kite results: journal/kite_rerun/*.json. Any decision whose number moved by more than about a point "
              "a year is re-checked and reported to the owner before anything changes."]
    open(os.path.join(SW, "journal", "kite_rerun.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
