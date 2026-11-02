from swing.strategy import position_size, trade_plan
from swing.health import sanity_check_plans


def test_risk_based_size(params):
    # 1% of 45,000 = 450 risk; 5 per share -> 90 shares (cap 112)
    assert position_size(45000, 45000, 100, 95, params) == 90


def test_position_cap_binds(params):
    # risk allows 45 shares but 25% cap = 11,250 / 1000 = 11
    assert position_size(45000, 45000, 1000, 990, params) == 11


def test_cash_limit_binds(params):
    assert position_size(45000, 2000, 100, 95, params) == 19


def test_stop_above_entry_gives_zero(params):
    assert position_size(45000, 45000, 100, 105, params) == 0


def test_plan_levels_ordered(params):
    pl = trade_plan(500, 10, params)
    assert pl["stop"] < pl["entry_low"] < pl["entry_high"] < pl["target1"] < pl["target2"]
    assert pl["stop"] == 480 and pl["target1"] == 530 and pl["target2"] == 560


def test_sanity_catches_bad_plan():
    bad = {"symbol": "X", "stop": 110, "entry_low": 100, "entry_high": 105, "target1": 120, "target2": 130,
           "qty": 5, "risk_rupees": 100, "last_close": 102}
    assert sanity_check_plans([bad], 45000)
    good = dict(bad, stop=95, risk_rupees=40)
    assert not sanity_check_plans([good], 45000)
