# Round 14: the champions' rules that our development data supports (written 18 Nov 2026, BEFORE the holdout was looked at)
## Source rules
- **O'Neil and Minervini:** buy the strongest leaders, and breakouts on heavy volume.
- **Minervini:** tight bases.
- **Qullamaggie, Turtles and Weinstein:** trend exits.

## Development-only exploration (`champions_explore.py`)
- **Leaders (6-month strength rank ≥ 95%):** trend trades earned +11.0% vs +6.3–8.3% (all stocks) and +5.5% vs +2.6–4.7% (top-300).
- **Breakout volume ≥ 3× its 50-day average:** +6.8% vs +4.7–6.5% (all stocks) and +5.4% vs +2.2–4.2% (top-300).
- **Tight bases did NOT help on NSE** (the tightest were worst), so they are not tested.

Strength was already rejected as a FILTER in round 1 (F2). Here it is tested only as the ORDER in which signals take the limited money.

## Rules
| ID | Rule |
|---|---|
| S1 Leaders first | Signals entering on the same day take cash in order of 6-month strength rank, strongest first (unknown rank = 0.5) instead of random. Nothing is skipped by rule. |
| S2 Volume breakouts | Breakout signals are taken only when the signal-day volume is ≥ 3× its 50-day average. Other types are unchanged. |
| S3 | S1 + S2 |

## Test
- The ₹45,000 account simulation (`improve10.sim` logic).
- **S1:** ties broken at random, median of 15 runs.
- **S2:** random order, median of 15 runs.
- Both trade sets, development and holdout.

## PASS, per rule
In BOTH periods and BOTH sets:
1. yearly growth ≥ today + 1.0 point, and
2. the worst fall is no more than 2.0 points deeper.

## After the test
Nothing is applied without the owner's yes.
