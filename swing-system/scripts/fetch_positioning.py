"""Download NSE participant-wise OI history (FII/DII/Pro/Client) since 2013 and build the panel."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from swing import data_prices, intel_positioning

if __name__ == "__main__":
    cal = data_prices.load("NIFTY50").index
    intel_positioning.download([d for d in cal if d >= pd.Timestamp("2013-01-01")])
    print(intel_positioning.build_panel().tail(3))
