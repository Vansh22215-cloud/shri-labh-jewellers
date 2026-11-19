"""4:00 pm EVENING REVIEW (owner 19 Nov: "I want this around 4"): right after the close, every tip is tracked, the
Learner and the why-engine run, and the results are saved to GitHub. Today's closing prices come from Kite (logged
in) or Yahoo's 5-minute data. The 6:40 pm nightly job runs the same steps again with the official day prices
(final numbers); this early review never sends tips."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402


def tracked_symbols():
    from swing.config import ROOT, PRIVATE
    syms = set()
    for f, col in ((ROOT / "journal" / "all_tips.csv", "symbol"), (PRIVATE / "vantage_signals.csv", "sym"),
                   (PRIVATE / "live_tips.csv", "symbol"), (PRIVATE / "vantage_rejected.csv", "symbol"),
                   (PRIVATE / "suppressed_repeats.csv", "symbol"), (PRIVATE / "foundry_tips.csv", "sym")):
        try:
            syms |= set(pd.read_csv(f, dtype=str)[col].dropna().astype(str))
        except Exception:
            pass
    return sorted(syms)


def todays_closes(syms, day):
    """Add today's bar where it is missing: Kite quotes first (exact after 3:30 pm), else Yahoo 5-minute data."""
    from swing import data_prices, kite
    day = pd.Timestamp(day).normalize()
    try:
        data_prices.update(syms)
    except Exception as e:
        print("price update failed:", type(e).__name__)
    need = [s for s in syms if (lambda d: d is not None and len(d) and d.index[-1] < day)(data_prices.load(s))]
    n_kite = 0
    if need:
        try:
            if kite.logged_in():
                q = kite.quotes(need)
                for s, v in q.items():
                    d = data_prices.load(s)
                    if d is None or not v.get("last") or not v.get("volume"):
                        continue
                    row = pd.DataFrame({"open": [v["open"]], "high": [max(v["high"], v["last"])],
                                        "low": [min(v["low"], v["last"])], "close": [v["last"]], "adj_close": [v["last"]],
                                        "volume": [float(v["volume"])], "dividends": [0.0], "splits": [0.0]},
                                       index=pd.DatetimeIndex([day], name="date"))
                    data_prices.save(s, pd.concat([d, row]))
                    n_kite += 1
        except Exception as e:
            print("kite closes failed:", type(e).__name__)
        rest = [s for s in need if (lambda d: d is not None and len(d) and d.index[-1] < day)(data_prices.load(s))]
        if rest:
            try:
                data_prices.patch_missing_day_batch(rest, day)
            except Exception as e:
                print("yahoo 5-minute patch failed:", type(e).__name__)
    print(f"review prices: {len(syms)} stocks, {len(need)} lacked today's bar, {n_kite} filled from Kite")


def main():
    from swing.daemon import now
    t = now()
    todays_closes(tracked_symbols(), t.date())
    for name, fn in (("scorecard", lambda: __import__("swing.scorecard", fromlist=["x"]).run()),
                     ("tracker", lambda: __import__("swing.tracker", fromlist=["x"]).run()),
                     ("learner", lambda: __import__("swing.learning", fromlist=["x"]).run()),
                     ("why-engine", lambda: __import__("swing.why_engine", fromlist=["x"]).run())):
        try:
            fn()
        except Exception as e:
            print(f"{name} failed:", e)
    try:
        from swing.ci_save import save
        save("evening review (4 pm)")
    except Exception as e:
        print("save failed:", e)


if __name__ == "__main__":
    from swing.config import on_github
    from swing.daemon import claim
    if on_github() and not claim("review"):
        print("review: already done (skipped)")
        sys.exit(0)
    main()
