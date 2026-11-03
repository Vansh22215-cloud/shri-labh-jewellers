"""Download quarterly reported EPS (with report dates) for the current Nifty 500 from Yahoo (for CANSLIM)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing import data_nse
from swing.fundamentals import eps_history

if __name__ == "__main__":
    syms = list(data_nse.nifty500_list()["Symbol"].dropna())
    ok = sum(1 for s in syms if len(eps_history(s)) >= 5)
    print("done", ok, "of", len(syms))
