# ATLAS - permanent mission (locked by the owner, 19 Nov 2026)

**ATLAS - Your Autonomous Trading Intelligence.** An intelligent, self-improving quantitative research system that
discovers market opportunities, develops its own trading strategies, rigorously tests them, learns from every
outcome and identifies the best opportunities for the owner's capital. VANTAGE is its indicator.

## The principle that never changes
**Profit is the objective. Capital protection is the constraint. Evidence is the authority. Continuous improvement
is the engine.** No system can guarantee profits or remove losses. ATLAS maximises the chance of strong,
sustainable, risk-adjusted returns, and never chases impressive-looking returns that could destroy capital.

## What ATLAS must do, and where it lives today
| Mission | Built | Where |
|---|---|---|
| **Discover** patterns, opportunities, new strategies | VANTAGE + live engine scans; weekly automatic research (230+ possibilities); discovered decision tree | `swing/vantage.py`, `swing/live_engine.py`, `vantage-ai/validation/autoresearch.py` |
| **Understand** which strategy works for which stock / sector / market / behaviour | Context engine: behaviour groups found by ATLAS, company, sector, market, setup and combinations, compared walk-forward | `vantage-ai/validation/context_engine.py`, `strict_groups.py` |
| **Experiment** - create, combine, challenge | Auto-lab possibilities, why-engine leads, prosecutor tests, beliefs register | `auto_lab.py`, `swing/why_engine.py`, `beliefs.json` |
| **Validate** on unseen data, after all costs, realistic execution | Pre-registration, development / holdout / fresh trades from 20 Nov 2026, luck worlds, placebo, verified Zerodha charges + 20.8% tax | `AUTO_LAB_PROTOCOL.md`, `costs_real.py`, `INVESTIGATION_19NOV.md` |
| **Select** by expected return, probability, risk, uncertainty | 3:22 pm ATLAS brief: ranked opportunities with evidence, avoid list, "No trade today" | `swing/brief.py` |
| **Protect** capital | 1% risk per trade, 25% cap, kill switch, daily-loss stop, top-300 only, weekly money-at-risk and crash test | `swing/safety.py`, `learning.portfolio_risk`, round 24 |
| **Learn** from every win, loss, miss, wrong prediction | Tracker, Learner, why-engine, missed movers, ledger | `swing/tracker.py`, `swing/learning.py`, `swing/why_engine.py`, `swing/ledger.py` |
| **Evolve** - improve, discover, retire | Strategy registry with 7 stages, research queue, weekly proposals, re-checks of approved rules | `strategies/registry.json`, `swing/research_queue.py`, `swing/lab_rules.py` |
| **Compound** | `/capital` monthly (sizing follows the account), round 25 | `swing/bot.py` |

## Rules ATLAS can never break
- It never places, changes or cancels an order. Kite is read-only. Keys stay in GitHub Secrets.
- It never raises the 1% risk per trade or the 25% cap, and never switches off a safety stop.
- A live change needs a test that passed its pre-written bar **and** the owner's yes.
- It never deletes history (append-only ledger) and never hides a failure: every test result is recorded, passed or not.
- When the evidence does not justify a trade, it says so: **"No trade today."**
