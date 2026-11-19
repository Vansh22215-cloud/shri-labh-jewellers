"""Each company's own past VANTAGE record (owner 18 Nov: 'Note : X of X past Vantage signals won').
Same replica + data handling as round 1's all-stock run (improve.all_stocks: adjusted prices, every stock with
>= 520 days, no top-300 limit). Stocks already in improve_trades_U.csv are reused; the rest are run here.
python3 company_record.py -> company_record.json {SYMBOL: [signals, wins]}"""
import json
import sys
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import iv, HERE, COST  # noqa: E402


def main():
    U = pd.read_csv(f"{HERE}/improve_trades_U.csv", usecols=["sym", "entry", "exit"])
    done = set(U["sym"])
    im.BENCH, im.PARAMS = iv.nifty()["close"], {}
    jobs = [(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in im.all_stocks() if s not in done]
    tr = []
    with Pool(4) as p:
        for r in p.imap_unordered(im._one, jobs, chunksize=4):
            tr += [t for t in r if "error" not in t]
    N = pd.DataFrame(tr)
    A = pd.concat([U, N[["sym", "entry", "exit"]]] if len(N) else [U], ignore_index=True)
    A["win"] = (A["exit"] / A["entry"] - 1 - COST) > 0
    rec = {s: [int(len(g)), int(g["win"].sum())] for s, g in A.groupby("sym")}
    tested = sorted(done | {j[0] for j in jobs})
    for s in tested:
        rec.setdefault(s, [0, 0])                      # tested, never signalled
    json.dump(rec, open(f"{HERE}/company_record.json", "w"), indent=0, sort_keys=True)
    print(len(jobs), "new stocks run,", len(N), "new trades,", len(rec), "companies in the record")


if __name__ == "__main__":
    main()
