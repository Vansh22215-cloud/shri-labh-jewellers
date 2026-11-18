# Round 24 results (19 Nov 2026): crash scenario

Pre-registration: IMPROVE24_PREREGISTRATION.md. Script: improve24.py. Numbers: improve24_results.json.
₹51,000 account, 1% risk, 25% cap, 15 random orders (median). Crash on the day the most trades were open.

| Period / setup | Market gap | Loss that morning | Yearly growth (no crash -> crash) | Worst fall |
|---|---|---|---|---|
| Holdout, live setup (C+A) | 5% | 7.4% | 18.8% -> 17.8% | -19% |
| Holdout, live setup (C+A) | 10% | 14.8% | 18.8% -> 14.5% | -19% |
| Holdout, live setup (C+A) | 20% | 29.6% | 18.8% -> 7.2% | -19% |
| Development, live setup | 10% | 15.0% | 20.5% -> 20.5% | -16% |
| Development, live setup | 20% | 29.9% | 20.5% -> 19.0% | -19% |

Verdict: **survives** (pre-registered bar: growth positive, falls no deeper than 40%, for the 10% gap).

What it means in plain words:
- The account is about 99% invested in 18-32 stocks most of the time. A crash morning hits all of them at once.
- The 1% stop-loss rule does NOT protect against a gap: prices open below the stops. A 10% market gap costs about
  15% of the account (about ₹7,600 of ₹51,000) in one morning; a 2020-style 20% gap about 30% (about ₹15,000).
- The system still makes money over the years after such a day (recent years +14.5% a year with a 10% crash).
- Important caveat found: the "worst fall" in all rounds is measured when trades close. The fall marked at daily
  prices is deeper (here the one-morning loss of 15-30% does not show in the worst-fall column). Added to the
  beliefs register as a known blind spot; the live Learner's portfolio-risk line shows the real number weekly.
- No rule change: cutting the invested share would cut growth every normal year (round 10 already failed).
