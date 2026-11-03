import pandas as pd

from swing import intel_fno


def test_summary_pcr_maxpain_and_levels():
    rows = []
    for k, ce, pe in [(90, 10, 500), (100, 300, 300), (110, 800, 20)]:
        rows.append({"TckrSymb": "X", "FinInstrmTp": "STO", "XpryDt": "2026-11-23", "StrkPric": k, "OptnTp": "CE",
                     "OpnIntrst": ce, "ChngInOpnIntrst": 0, "ClsPric": 1, "PrvsClsgPric": 1, "UndrlygPric": 100})
        rows.append({"TckrSymb": "X", "FinInstrmTp": "STO", "XpryDt": "2026-11-23", "StrkPric": k, "OptnTp": "PE",
                     "OpnIntrst": pe, "ChngInOpnIntrst": 0, "ClsPric": 1, "PrvsClsgPric": 1, "UndrlygPric": 100})
    rows.append({"TckrSymb": "X", "FinInstrmTp": "STF", "XpryDt": "2026-11-23", "StrkPric": 0, "OptnTp": None,
                 "OpnIntrst": 1000, "ChngInOpnIntrst": 100, "ClsPric": 102, "PrvsClsgPric": 100, "UndrlygPric": 101})
    s = intel_fno.summarise(pd.DataFrame(rows)).set_index("symbol").loc["X"]
    assert s["max_call_oi_strike"] == 110 and s["max_put_oi_strike"] == 90
    assert abs(s["pcr"] - 820 / 1110) < 1e-9
    assert s["max_pain"] == 100
    assert s["opt_expiry"] == "2026-11-23"
