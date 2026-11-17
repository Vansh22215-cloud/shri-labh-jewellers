"""Round 6 (IMPROVE6_PREREGISTRATION.md)."""
import json
import sys
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
from improve import iv, HERE, stats, split, frame  # noqa: E402

T = frame(f"{HERE}/trades_FINAL.csv")
n = iv.nifty()["close"]
weak = (n < n.rolling(200).mean())
T["weak"] = T["signal"].map(weak).fillna(False).astype(bool)
bd, bh = split(T)
out = {"baseline": {"dev": stats(bd), "holdout": stats(bh)}}
for k, drop in (("G1", T["weak"]), ("G2", T["weak"] & T["setup"].isin(["Breakout", "RCP"]))):
    V = T[~drop]
    vd, vh = split(V)
    sd, sh = stats(vd), stats(vh)
    b = out["baseline"]
    ok = (sh["exp"] > b["holdout"]["exp"] and sh["win"] >= b["holdout"]["win"] and sh["n"] >= 0.7 * b["holdout"]["n"]
          and sd["exp"] > b["dev"]["exp"] and sd["dd_1pct"] >= b["dev"]["dd_1pct"] and sh["dd_1pct"] >= b["holdout"]["dd_1pct"])
    out[k] = {"PASS": bool(ok), "dev": sd, "holdout": sh}
json.dump(out, open(f"{HERE}/improve6_results.json", "w"), indent=1)
print(json.dumps(out, indent=1))
