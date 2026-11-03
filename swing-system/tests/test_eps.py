import pandas as pd

from swing import fundamentals as fu


def test_eps_growth_point_in_time(tmp_path, monkeypatch):
    monkeypatch.setattr(fu, "EPS", tmp_path)
    pd.DataFrame({"date": ["2023-01-20", "2023-04-20", "2023-07-20", "2023-10-20", "2024-01-20"],
                  "eps": [10, 11, 12, 13, 15]}).to_csv(tmp_path / "X.csv", index=False)
    days = pd.bdate_range("2024-01-15", "2024-01-31")
    g = fu.eps_growth_panel(["X"], days)["X"]
    assert pd.isna(g[pd.Timestamp("2024-01-19")])            # report not known yet
    assert abs(g[pd.Timestamp("2024-01-22")] - 0.5) < 1e-9     # 15 vs 10 a year earlier, known the day after
