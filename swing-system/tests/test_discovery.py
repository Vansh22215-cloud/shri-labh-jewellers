import numpy as np
import pandas as pd

from swing import discovery as d


def test_generate_never_repeats_and_mixes_families():
    a = d.generate(200, [], 1)
    keys = [c["key"] for c in a]
    assert len(keys) == len(set(keys))
    b = d.generate(200, keys, 2)
    assert not set(keys) & {c["key"] for c in b}
    for c in a:
        fams = [d.family_of(x) for x in c["blocks"]]
        assert len(set(fams)) == len(fams) and c["hold"] in (5, 10, 20)


def test_evaluate_finds_a_planted_edge():
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2013-01-01", "2026-06-30")
    n_s = 40
    P = pd.DataFrame({"date": np.repeat(dates, n_s), "sym": np.tile([f"S{i}" for i in range(n_s)], len(dates))})
    for f in d.RANK_FEATS:
        P[f] = rng.random(len(P))
    for f in ("sqz", "n_up200", "n_rsi2", "breadth", "d200", "hi52", "dn_days"):
        P[f] = rng.random(len(P))
    base = rng.normal(0.002, 0.03, len(P))
    X = P.groupby("date")[list(d.RANK_FEATS)].rank(pct=True)
    edge = (X["rsi2"] < 0.2) & (X["hi52"] > 0.8)
    for k in ("fwd5", "fwd", "fwd20"):
        P[k] = base + np.where(edge, 0.03, 0.0)
    order = np.lexsort((P["date"].values, P["sym"].values))
    prev = np.full(len(P), -1)
    so = P["sym"].values[order]
    same = np.r_[False, so[1:] == so[:-1]]
    prev[order[1:]] = np.where(same[1:], order[:-1], -1)
    dm = {h: P.groupby("date")[f"fwd{h}" if h != 10 else "fwd"].transform("mean").values for h in (5, 10, 20)}
    good = {"blocks": ["hi52_high", "rsi2_low"], "hold": 10, "key": "x"}
    bad = {"blocks": ["r5_low", "vol20_high"], "hold": 10, "key": "y"}
    res = d.evaluate(P, X, [good, bad], prev, pd.to_datetime(P["date"]), dm)
    assert [c["key"] for c, _, _ in res] == ["x"]
