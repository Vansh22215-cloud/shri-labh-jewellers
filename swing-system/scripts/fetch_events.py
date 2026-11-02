"""Download results dates (past + next) for the current Nifty 500 / universe. Cached, polite."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing import data_nse
from swing.fundamentals import earnings_dates

if __name__ == "__main__":
    syms = list(data_nse.nifty500_list()["Symbol"].dropna())
    ok = 0
    for i, s in enumerate(syms):
        if earnings_dates(s):
            ok += 1
        if i % 50 == 0:
            print(i, ok, flush=True)
    print("done", ok, "of", len(syms))
