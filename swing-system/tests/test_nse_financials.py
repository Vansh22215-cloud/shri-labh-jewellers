"""Company financials from NSE filings (owner 20 Nov). Offline: tiny XBRL files and a fake NSE session."""
import json

import pandas as pd

from swing import nse_financials as nf

HEAD = ('<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
        'xmlns:f="http://www.bseindia.com/xbrl/fin" xmlns:xbrldi="http://xbrl.org/2006/xbrldi">')


def ctx(cid, start=None, end=None, inst=None, seg=False):
    p = f"<xbrli:instant>{inst}</xbrli:instant>" if inst else f"<xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate>"
    s = "<xbrli:scenario><xbrldi:explicitMember dimension='x'>m</xbrldi:explicitMember></xbrli:scenario>" if seg else ""
    return f'<xbrli:context id="{cid}"><xbrli:entity/><xbrli:period>{p}</xbrli:period>{s}</xbrli:context>'


def fact(name, ref, v):
    return f'<f:{name} contextRef="{ref}">{v}</f:{name}>'


FACTS = (fact("DateOfStartOfReportingPeriod", "OneD", "2026-01-01") + fact("DateOfEndOfReportingPeriod", "OneD", "2026-03-31")
         + fact("DateOfStartOfReportingPeriod", "FourD", "2025-04-01") + fact("DateOfEndOfReportingPeriod", "FourD", "2026-03-31")
         + fact("RevenueFromOperations", "OneD", "250") + fact("RevenueFromOperations", "FourD", "1000")
         + fact("RevenueFromOperations", "SegD", "400") + fact("ProfitLossForPeriod", "FourD", "100")
         + fact("ProfitBeforeTax", "FourD", "130") + fact("FinanceCosts", "FourD", "10")
         + fact("CashFlowsFromUsedInOperatingActivities", "FourD", "120")
         + fact("PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", "FourD", "30")
         + fact("Assets", "OneI", "2000") + fact("Equity", "OneI", "800") + fact("CurrentLiabilities", "OneI", "300")
         + fact("BorrowingsNoncurrent", "OneI", "150") + fact("BorrowingsCurrent", "OneI", "50")
         + fact("Assets", "PY_I", "1500") + fact("PaidUpValueOfEquityShareCapital", "FourD", "50")
         + fact("FaceValueOfEquityShareCapital", "FourD", "1"))
FY = (pd.Timestamp("2025-04-01"), pd.Timestamp("2026-03-31"))


def test_parse_full_year_and_year_end():
    x = HEAD + ctx("OneD", "2026-01-01", "2026-03-31") + ctx("FourD", "2025-04-01", "2026-03-31") \
        + ctx("SegD", "2025-04-01", "2026-03-31", seg=True) + ctx("OneI", inst="2026-03-31") \
        + ctx("PY_I", inst="2025-03-31") + FACTS + "</xbrli:xbrl>"
    r = nf.parse_xbrl(x, *FY)
    assert r["revenue"] == 1000 and r["net_income"] == 100 and r["total_assets"] == 2000   # not the quarter/segment/last year
    row = nf._row(r, *FY, pd.Timestamp("2026-04-20"), "consolidated")
    assert row["debt"] == 200 and row["ebit"] == 140 and row["capex"] == -30 and row["shares"] == 50
    assert row["published_assumed"] == "2026-04-20" and row["source"] == "NSE filing"


def test_parse_trusts_filing_dates_over_wrong_contexts():
    # older NSE files label the full-year context with the quarter's dates, or leave contexts undefined
    wrong = HEAD + ctx("OneD", "2026-01-01", "2026-03-31") + ctx("FourD", "2026-01-01", "2026-03-31") \
        + ctx("OneI", inst="2026-03-31") + FACTS + "</xbrli:xbrl>"
    assert nf.parse_xbrl(wrong, *FY)["revenue"] == 1000
    undefined = HEAD + ctx("X", "2026-01-01", "2026-03-31", seg=True) + FACTS + "</xbrli:xbrl>"
    r = nf.parse_xbrl(undefined, *FY)
    assert r["revenue"] == 1000 and r["total_assets"] == 2000


def test_missing_fields_stay_none():
    r = nf.parse_xbrl(HEAD + ctx("FourD", "2025-04-01", "2026-03-31") + fact("RevenueFromOperations", "FourD", "5")
                      + "</xbrli:xbrl>", *FY)
    assert r["revenue"] == 5 and r["equity"] is None and r["ocf"] is None
