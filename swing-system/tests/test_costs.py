from swing import costs


def test_buy_cost_10k():
    # STT 10 + exch 0.307 + SEBI 0.01 + stamp 1.5 + GST 18% of 0.317 = 11.874
    assert abs(costs.buy_cost(10000) - 11.87) < 0.02


def test_sell_cost_10k_includes_dp():
    # STT 10 + exch 0.307 + SEBI 0.01 + GST 0.057 + DP 15.34
    assert abs(costs.sell_cost(10000) - 25.71) < 0.02


def test_no_stamp_on_sell_and_no_dp_on_buy():
    assert costs.sell_cost(0) == costs.DP_PER_SELL
    assert costs.buy_cost(0) == 0


def test_slippage_direction():
    assert costs.fill_price(100, "buy") > 100 > costs.fill_price(100, "sell")


def test_round_trip_cost_reasonable():
    # A Rs 11,000 round trip should cost roughly 0.3%-0.5% before slippage
    rt = costs.buy_cost(11000) + costs.sell_cost(11000)
    assert 0.003 * 11000 < rt < 0.005 * 11000
