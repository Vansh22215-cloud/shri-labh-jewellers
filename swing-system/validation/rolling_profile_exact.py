"""EXACT port of 'Rolling Candle Profile with Buy/Sell Signals (Zeiierman)' - research use only.

Original: (c) Zeiierman, licensed CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/).
This Python port is a derivative used for non-commercial testing and is shared under the same licence.

Ported with the script's DEFAULT inputs: EMA(21) anchor, chart timeframe (Manual, empty = no intrabar data, so the
single-candle branch is used), localisation width 0.01, wick influence 0.85, brightness 3.0, dominance 0.25,
minimum 7 coloured bands, 6-bar spacing. The pasted source ended inside the SELL condition; the final step is taken
from the author's description: BUY = buyPress AND >= 7 coloured bands AND close above a RISING anchor, fresh (not
true on the previous bar), >= 6 bars since the previous BUY; SELL mirrored.
Usage: python validation/rolling_profile_exact.py daily|hourly price|hybrid|volume
"""
import sys

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
sys.path.insert(0, f"{ROOT}/validation")
import rolling_profile_research as base  # noqa: E402
from swing.rolling_profile import signals  # noqa: E402,F401  (the live code IS the tested code)


if __name__ == "__main__":
    base.main(sys.argv[1] if len(sys.argv) > 1 else "daily", sys.argv[2] if len(sys.argv) > 2 else "price",
              sig=signals, tag="EXACT_")
