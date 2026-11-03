"""Download NSE delivery data for every trading day (first time ~45 min; later only new days)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from swing import data_delivery, data_prices

if __name__ == "__main__":
    cal = data_prices.load("NIFTY50").index
    data_delivery.download([d for d in cal if d >= pd.Timestamp("2012-09-01")])
    w = data_delivery.build_panel()
    print("panel", w.shape)
