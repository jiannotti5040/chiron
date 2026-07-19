# Agent instructions — Jacob's Portfolio Vault (Chiron / Primus)

Any agent working in this repository: read `docs/SOP.md` first. It is the
operating manual; this file is only the gate summary.

## The one inviolable law

**Zero false verifications.** A change that makes any engine stamp something it
cannot exactly prove is wrong, even if every benchmark number improves. Refusal
is a feature. When forced to choose between recall and honesty, choose honesty
— the project's entire value is that its `verified` stamp is never allowed to
lie and stand.

## Before you claim anything works

Run the gate battery; all green before any commit that touches an engine or the
gate. From the repo root:

```
python3 Chiron/chiron.py selftest        # CHIRON core (12/12)
python3 Chiron/stress_test.py            # invariant-operation probes (23/23)
cd Primus
python3 test_invariant_engine.py         # stress gates (55/55)
python3 test_certify_fuzz.py             # adversarial certify gates (13/13)
python3 test_mcp_server.py               # MCP protocol gates (10/10)
python3 benchmark.py                     # internal proving run
python3 oeis_live.py                     # EXTERNAL validation (cached corpus)
python3 drift_check.py                   # seed vs Chiron differential
cd "../Chiron Monolith"
python3 chiron_monolith.py --smoke       # folded core engines (5/5)
```

A failing gate is information, not an obstacle: find the root cause. Never
widen a tolerance or mute a gate to get green.

## Hard rules

- Exact arithmetic only on the stamping path: Fractions and exact integer
  equality; float predictions past 2^53 are refused, not trusted.
- Edit sources of truth only (see `docs/SOP.md`). Never hand-edit
  `Chiron Monolith/chiron_monolith.py` — regenerate it:
  `cd "Chiron Monolith" && python3 build_monolith.py`, then re-run `--smoke`.
- Seed/Chiron divergence must be ledgered in `Primus/drift_check.py`
  (`SEED_AHEAD_LEDGER`) with a dated entry, or the build fails — by design.
- Do not build new layers, dashboards, folds, or copies of the engine. The
  vault grows outward (users, external validation, exactness), not inward.
- Never `git add -A` at the vault root: `Jacob Dylan Iannotti/` is deliberately
  untracked and contains an embedded git repo.
- Label epistemic status plainly: implemented-and-tested, prototype, or theory.
  Overclaiming is the one style error this project cannot afford — including in
  READMEs, sales copy, and commit messages.
