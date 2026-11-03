from swing import risk_score


def test_calm_liquid_uptrend_is_low_risk():
    s, why = risk_score.score(1.5, 500, True, True, None, 5, validated=True)
    assert s == 1 and risk_score.label(s) == "LOW"


def test_everything_bad_caps_at_10():
    s, why = risk_score.score(8, 5, False, False, 2, 30, validated=False)
    assert s == 10 and len(why) >= 6


def test_unvalidated_adds_three():
    a, _ = risk_score.score(1.5, 500, True, True, None, 5, validated=True)
    b, _ = risk_score.score(1.5, 500, True, True, None, 5, validated=False)
    assert b - a == 2 and b == 3
