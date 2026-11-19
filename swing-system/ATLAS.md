# ATLAS - map of the system (19 Nov 2026)

ATLAS = the owner's goal: a system that **finds, analyses, tests, challenges, recommends, tracks, learns, evolves,
manages capital and improves itself**, while protecting capital. It is read-only towards Kite and never places,
modifies or cancels an order. The owner places every order himself.

| ATLAS part | What it does | Where |
|---|---|---|
| **Find** (Finder) | VANTAGE live scan, 3:20 pm close call, 3:40 pm close scan, ADD MORE; live engine (dip-buy, breakout, intraday, F&O) | `swing/vantage.py`, `swing/live_engine.py`, `swing/daemon.py` |
| **Analyse** | Company record ("X of Y past signals won"), likely-win %, results week, market type | `swing/vantage.py`, `vantage-ai/validation/company_record.json` |
| **Test** | Pre-registered rounds: development before Nov 2023, holdout after; account simulation ₹51k, 1% risk | `vantage-ai/validation/IMPROVE*` (rounds 1-24), `experiments.json` |
| **Test everything** (AUTO-LAB) | Describes all 36,387 past trades by 40 facts (stock, its history, market, sector, results, time), builds every rule from them (230 in run 1) and tests each: older years, luck worlds, recent years, year by year, random-skip placebo. Only a 4-step pass goes to the owner | `vantage-ai/validation/auto_lab.py`, `lab_features.py`, `AUTO_LAB_*` |
| **Research without Claude** | Every Friday night on GitHub: rebuild all trades from new prices, all facts, all possibilities, 4 steps + fresh trades since 20 Nov 2026; a full pass -> Telegram proposal; `/approve LAB-x` makes VANTAGE apply it (skip or half only) | `vantage-ai/validation/autoresearch.py`, `swing/lab_rules.py`, `strategies/lab_rules.json`, `journal/auto_research.md` |
| **Challenge** | Luck checks, fingerprint, prosecutor tests (round 23), crash scenario (round 24), beliefs + daily question | `luck_check*.json`, `fingerprint`, `beliefs.json`, `swing/learning.py` |
| **Recommend** | Telegram tips with stop-loss and 1%-risk quantity; no repeats across channels | `swing/telegram.py`, `swing/registry.py`, `swing/safety.py` |
| **Track** | Every idea ever produced, sent or not, one table | `swing/tracker.py` -> `journal/all_tips.csv/.md`; `swing/scorecard.py` |
| **Remember** | Append-only hash-chained idea history | `swing/ledger.py` -> `journal/ledger.jsonl` |
| **Learn** (Learner) | Situations, mistakes (codes), lessons with evidence levels, expectation bands, opportunity cost, market memory, missed movers | `swing/learning.py` -> `journal/learning.md`, `learning_queue.csv` |
| **Evolve** | Ranked research queue weighted by which kinds of ideas pass; 7-stage promotion; strategy registry | `swing/research_queue.py` -> `journal/research_queue.md`; `strategies/registry.json` |
| **Manage capital** | 1% risk per trade, 25% cap per stock, kill switch, portfolio risk weekly (needs capital set) | `swing/safety.py`, `learning.portfolio_risk` |
| **Improve itself** | Nightly: split re-scale -> scorecard -> tracker -> Learner (+ ledger, research queue) -> shadow records; weekly learning message | `scripts/run_nightly.py`, `scripts/run_weekly.py` |

## Rules that never change automatically
- No order is ever placed, changed or cancelled. Kite is read-only. Keys live only in GitHub Secrets.
- The 1% risk limit is never raised by the system.
- A live change needs a passed pre-registered test **and** the owner's yes. The Learner and research queue only *suggest*.
- History is never deleted: the ledger is append-only and checked every night.
- Personal money data (capital, holdings, /bought) never goes to git; the portfolio-risk line is Telegram only.

## Not built (on purpose)
- Genetic "alpha genome" search: 78 tests on one holdout already; a search would find luck.
- Multi-strategy capital brain: VANTAGE is the only proven stock-choice edge.
- Automatic trading: forbidden by the owner.
