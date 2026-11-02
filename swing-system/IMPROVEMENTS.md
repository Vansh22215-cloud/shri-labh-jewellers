# IMPROVEMENTS.md - pre-registered proposals

Rules: every proposal states its reason **before** it is tested. The weekly job tests proposals with
`status: proposed`, runs the full validation gate in a sandbox, and promotes at most one per week - only if it
passes the gate AND beats the live version in most walk-forward periods AND has a higher walk-forward CAGR.
Results are written back here and in CHANGELOG.md. Recent paper trades alone never justify a change.

You (or Claude) can add a proposal by copying a block below and changing it.

```proposal
id: P1
status: rejected 2026-11-02 - P1: gate FAIL, beat live in 7/13 walk-forward periods, WF CAGR 7.13% vs live 6.79%, WF maxDD -17.35% vs -21.74%
written: 2026-11-02
reason: Quarterly results cause large overnight gaps that jump past stop-losses; skipping entries within 5 trading days before results should cut gap losses more than it costs in missed winners.
overrides: {"results_rule": "exclude"}
```
