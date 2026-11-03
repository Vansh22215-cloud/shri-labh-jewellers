import pandas as pd

from swing import tipcheck

EQ = pd.DataFrame({"SYMBOL": ["TATASTEEL", "RELIANCE", "HDFCBANK", "M&M", "SBIN", "21STCENMGM"],
                   "NAME OF COMPANY": ["Tata Steel Limited", "Reliance Industries Limited", "HDFC Bank Limited",
                                       "Mahindra & Mahindra Limited", "State Bank of India", "21st Century Management"]})


def test_parse_classic_channel_format():
    t = tipcheck.parse("🔥 BUY TATASTEEL @ 150-152 SL 145 TGT 158/165 🎯", EQ)
    assert t["symbol"] == "TATASTEEL" and t["side"] == "buy"
    assert (t["entry_low"], t["entry_high"]) == (150, 152)
    assert t["stop"] == 145 and t["targets"] == [158, 165]


def test_parse_intraday_sentence():
    t = tipcheck.parse("Intraday call: Buy RELIANCE above 1310, stoploss 1295, target 1335", EQ)
    assert t["symbol"] == "RELIANCE" and t["horizon"] == "intraday"
    assert t["entry_low"] == 1310 and t["stop"] == 1295 and t["targets"] == [1335]


def test_parse_hashtag_cmp_multiple_targets():
    t = tipcheck.parse("#HDFCBANK cmp 1,720 buy for target 1800 1850 sl 1680 (swing)", EQ)
    assert t["symbol"] == "HDFCBANK" and t["entry_low"] == 1720 and t["stop"] == 1680
    assert t["targets"] == [1800, 1850]


def test_parse_company_name_and_sell():
    t = tipcheck.parse("Sell State Bank of India below 800 sl 815 tgt 780", EQ)
    assert t["symbol"] == "SBIN" and t["side"] == "sell" and t["stop"] == 815


def test_parse_no_symbol():
    assert tipcheck.parse("Market will rally tomorrow!!", EQ)["symbol"] is None


def test_base_rate_simple_path():
    idx = pd.bdate_range("2020-01-01", periods=400)
    c = pd.Series(100.0, index=idx)
    df = pd.DataFrame({"close": c, "high": c * 1.03, "low": c * 0.995})
    win, loss, neither, n = tipcheck.base_rate(df, 0.02, 0.02, 3)
    assert win > 0.99 and loss == 0       # high always reaches +2%, low never -2%


def test_cmp_without_number_means_market_price():
    t = tipcheck.parse("Jackpot call! Buy SBIN cmp for target 1100 multibagger", EQ)
    assert t["symbol"] == "SBIN" and t["entry_low"] is None and t["targets"] == [1100]


def test_symbol_starting_with_digit():
    t = tipcheck.parse("BUY 21STCENMGM 55 sl 50 tgt 70", EQ)
    assert t["symbol"] == "21STCENMGM" and t["entry_low"] == 55 and t["stop"] == 50
