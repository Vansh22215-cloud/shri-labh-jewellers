from datetime import date

import pandas as pd

from swing import intel_events as ev


def test_expiry_rule_change():
    assert ev.monthly_expiry(2024, 10) == date(2024, 10, 31)     # last Thursday
    assert ev.monthly_expiry(2026, 11) == date(2026, 11, 24)     # last Tuesday (real one may move for holidays)


def test_big_event_flag_marks_two_days_before():
    days = pd.bdate_range("2024-01-25", "2024-02-06")
    f = ev.big_event_days_ahead(days, 2)
    assert f[pd.Timestamp("2024-01-30")] and f[pd.Timestamp("2024-01-31")] and f[pd.Timestamp("2024-02-01")]
    assert not f[pd.Timestamp("2024-01-29")] and not f[pd.Timestamp("2024-02-02")]
