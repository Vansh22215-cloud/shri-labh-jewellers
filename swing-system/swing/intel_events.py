"""Market EVENT calendar (ROADMAP I5).

Only dates that are certain are hard-coded (no guessing):
  * Union Budget days (incl. interim/full budgets after elections)
  * General-election result days
  * Monthly NSE F&O expiry (last Thursday up to Aug 2025, last Tuesday from Sep 2025; computed, and replaced by the
    real expiry from the F&O bhavcopy when available; exchange holidays may shift it a day earlier)
Upcoming events the system cannot compute (RBI policy, US Fed, CPI) can be added by hand to
data/events/manual_events.csv (columns: date,event). Shown in reports; used only in pre-registered tests.
"""
from datetime import date, timedelta

import pandas as pd

from .config import EVENTS

BUDGET = ["2013-02-28", "2014-02-17", "2014-07-10", "2015-02-28", "2016-02-29", "2017-02-01", "2018-02-01",
          "2019-02-01", "2019-07-05", "2020-02-01", "2021-02-01", "2022-02-01", "2023-02-01", "2024-02-01",
          "2024-07-23", "2025-02-01", "2026-02-01"]
ELECTION_RESULTS = ["2014-05-16", "2019-05-23", "2024-06-04"]
MANUAL = EVENTS / "manual_events.csv"


def monthly_expiry(y, m):
    last = (date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)) - timedelta(days=1)
    wd = 3 if date(y, m, 1) < date(2025, 9, 1) else 1     # Thursday until Aug 2025, then Tuesday
    while last.weekday() != wd:
        last -= timedelta(days=1)
    return last


def calendar(start="2013-01-01", end=None):
    end = pd.Timestamp(end or date.today() + timedelta(days=120))
    rows = [{"date": pd.Timestamp(d), "event": "Union Budget"} for d in BUDGET]
    rows += [{"date": pd.Timestamp(d), "event": "Election results"} for d in ELECTION_RESULTS]
    for p in pd.period_range(start, end, freq="M"):
        rows.append({"date": pd.Timestamp(monthly_expiry(p.year, p.month)), "event": "Monthly F&O expiry"})
    if MANUAL.exists():
        m = pd.read_csv(MANUAL, parse_dates=["date"])
        rows += m.to_dict("records")
    cal = pd.DataFrame(rows)
    return cal[(cal["date"] >= pd.Timestamp(start)) & (cal["date"] <= end)].sort_values("date")


def big_event_days_ahead(trading_days, days_before=2, kinds=("Union Budget", "Election results")):
    """bool Series over trading_days: True on the `days_before` trading days BEFORE a big event (and the event day)."""
    idx = pd.DatetimeIndex(trading_days)
    flag = pd.Series(False, index=idx)
    for d in calendar(str(idx[0].date()), str(idx[-1].date()))[lambda x: x["event"].isin(kinds)]["date"]:
        pos = idx.searchsorted(d)
        for k in range(max(0, pos - days_before), min(len(idx), pos + 1)):
            flag.iloc[k] = True
    return flag


def upcoming(n_days=30):
    cal = calendar(str(date.today()), str(date.today() + timedelta(days=n_days)))
    return cal.to_dict("records")


def line():
    u = upcoming()
    if not u:
        return ""
    return "Upcoming events: " + "; ".join(f"{pd.Timestamp(e['date']):%d %b} {e['event']}" for e in u[:4])
