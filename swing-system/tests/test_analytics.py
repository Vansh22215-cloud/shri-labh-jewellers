def test_tax_only_on_positive_years():
    from swing.analytics import STCG
    gains = [1000, -500]
    taxes = [max(0, g) * STCG for g in gains]
    assert taxes == [200.0, 0.0]
