from datetime import date

from swing import options_check as oc
from tests.test_tipcheck import EQ

import pandas as pd
EQ2 = pd.concat([EQ, pd.DataFrame({"SYMBOL": ["BOSCHLTD"], "NAME OF COMPANY": ["Bosch Limited"]})])
MSG = "📈📉 BOSCHLTD\n🖲 NOV 49000 PE AT 1000-1020\n✅ Target-1200-1270-1350-1500\n⛔️ Stoploss-800 (15 Min CB)\n✨ Lot Size-25"


def test_parse_option_channel_format():
    o = oc.parse_option(MSG, EQ2)
    assert o["symbol"] == "BOSCHLTD" and o["kind"] == "PE" and o["strike"] == 49000 and o["month"] == 11
    assert (o["entry_low"], o["entry_high"], o["stop"], o["lot"]) == (1000, 1020, 800, 25)
    assert o["targets"] == [1200, 1270, 1350, 1500]


def test_black_scholes_put_call_parity_and_iv_roundtrip():
    s, k, t, v = 100, 100, 0.1, 0.3
    c, p = oc.bs(s, k, t, v, "CE"), oc.bs(s, k, t, v, "PE")
    import math
    assert abs((c - p) - (s - k * math.exp(-oc.R * t))) < 1e-6
    assert abs(oc.implied_vol(p, s, k, t, "PE") - v) < 1e-4


def test_monthly_expiry_last_tuesday():
    assert oc.monthly_expiry(2026, 11) == date(2026, 11, 24)
    assert oc.monthly_expiry(2026, 12) == date(2026, 12, 29)


def test_not_an_option_tip():
    assert oc.parse_option("BUY TATASTEEL 150 SL 145 TGT 160", EQ2) is None
