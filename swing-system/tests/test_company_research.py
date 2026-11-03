from swing.company_research import analyse


def _snap(ni=100, ocf=130, debt=50):
    y = lambda rev, ni_, ta, sh: {"published_assumed": "2025-06-01", "revenue": rev, "net_income": ni_, "ebit": ni_ * 1.4,
                                  "total_assets": ta, "current_liabilities": 200, "equity": 600, "debt": debt, "ocf": ocf,
                                  "capex": -40, "interest": 10, "gross_profit": rev * 0.4, "current_assets": 400, "shares": sh}
    return {"symbol": "X", "name": "X Ltd", "ok": True, "pe": 20, "pb": 3, "insider_pct": 0.55, "v": 2,
            "annual": {"2022-03-31": y(800, 60, 1000, 100), "2023-03-31": y(900, 80, 1050, 100), "2024-03-31": y(1000, ni, 1100, 100)}}


def test_good_company_scores_high_without_flags():
    a = analyse(_snap())
    assert not a["flags"] and a["score"] >= 60 and a["fscore"] >= 5


def test_loss_maker_flagged():
    a = analyse(_snap(ni=-10, ocf=-5))
    assert "loss-making in the latest year" in a["flags"] and "operating cash flow negative" in a["flags"]
