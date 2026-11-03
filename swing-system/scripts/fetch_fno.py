"""Download NSE F&O end-of-day history (UDiFF format, from 2024-07-08)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from swing import data_prices, intel_fno

if __name__ == "__main__":
    cal = data_prices.load("NIFTY50").index
    intel_fno.download([d for d in cal if d >= pd.Timestamp("2024-07-08")])
    print("done")
