"""ONE-TIME SETUP: download all data, check it, run the full backtest/validation,
test pending proposals, and produce the first daily report. Takes 1-3 hours (includes the ~550-strategy search).
Safe to re-run (everything is cached)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swing import data_nse, health, update, universe, validation_report, weekly, nightly
from swing.fundamentals import earnings_dates
from swing.config import load_settings

if __name__ == "__main__":
    print("1/5 Downloading prices and official NSE data (slow the first time)...")
    print(update.refresh(first_time=not (Path(__file__).parent.parent / "data" / "universe_history.csv").exists()))
    print("2/5 Checking data quality against NSE official prices...")
    syms = sorted(set(universe.load_history()["symbol"]) | set(data_nse.nifty500_list()["Symbol"].dropna()))
    q = health.build_quarantine(syms)
    print(f"   {len(q)} stocks quarantined")
    print("3/5 Downloading results dates...")
    for s in data_nse.nifty500_list()["Symbol"].dropna():
        earnings_dates(s)
    print("4/5 Backtest + validation gate (and weekly improvement session)...")
    res, _, table = validation_report.run(load_settings()["live_strategy"])
    print(table.to_string())
    print("GATE", "PASSED" if res["gate"]["passed"] else "FAILED")
    for n in weekly.run():
        print("  ", n)
    print("5/5 First daily report...")
    print(nightly.main())
