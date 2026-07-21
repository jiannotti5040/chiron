# Head-to-head vs symbolic regression — the outputs, honestly

**Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0 (see [LICENSE.md](../LICENSE.md)).**

This page ships the **outputs** of the licensed battery's symbolic-regression
comparison, the same way [`../eval/`](../eval/) ships the engine's frozen OEIS
predictions: the benchmark scripts (`bench_pysr.py`,
`bench_symreg_external.py`) and the engine run with the licensed vault, but
zero-false is a property of outputs, and outputs can be published with their
provenance. Every number below has been produced by at least two real runs on
their listed dates — including a fresh reproduction on 2026-07-21 under newer
library versions, which matched the original runs exactly.

## Protocol

Same as the external validation: both systems see the **first 12 terms** of
each of 29 live-fetched OEIS sequences (corpus fetched 2026-07-04, before the
newest engine layer existed); the grade is **exact** prediction of the next 4
terms. Primus may refuse; a regressor structurally always answers.

## Primus vs PySR

Original run 2026-07-12 (PySR deterministic serial, `niterations=40`, seed 0);
**reproduced 2026-07-21** (pysr 1.5.10) — identical counts both times:

| | exact 4/4 | wrong | refused |
|---|---|---|---|
| **Primus** | **18** | **0** | 11 |
| PySR | 5 | 24 | — (cannot refuse) |

PySR's five exact hits are precisely the polynomial-expressible rows:
triangular numbers, squares, cubes, oblong, and quarter-squares. Everything
non-polynomial — Fibonacci, Lucas, Pell, Catalan, Motzkin, Schröder,
factorials, repunits, powers of 2 and 3 — it answered with a confident
closed-form equation, and answered wrong, 24 times. Primus stamped 18
exactly, refused 11, and was never wrong.

One honest footnote in PySR's favor: quarter-squares (A002620) is a true
order-4 recurrence that Primus *refuses* at 12 shown terms — its evidence
rule (h ≥ p held-out terms for a p-parameter rule, adopted 2026-07-11 after
an external run caught a false composites stamp) demands more evidence before
an 8-parameter rule can stamp. PySR's polynomial guess happens to land exact
there. That is the trade this project chooses on purpose: the same rule that
refuses one true quarter-squares stamp is the rule that prevented a false
composites stamp. Refusal is the product.

## Primus vs raw GP vs the same GP behind the exact gate

Original run 2026-07-20 (gplearn 0.4.2 / scikit-learn 1.7.2);
**reproduced 2026-07-21** (gplearn 0.4.3 / scikit-learn 1.9.0,
`--population 300 --generations 12`) — identical counts both times:

| | exact 4/4 | wrong / stamped-wrong | refused |
|---|---|---|---|
| **Primus** | **18** | **0** | 11 |
| raw gplearn GP | 2 | 27 | — (cannot refuse) |
| **gated GP** (`primus.conjecture`) | **3** | **0** | 26 |

The third row is the same stochastic regressor placed **behind** the
discipline instead of against it: GP proposes, float constants are snapped to
exact rationals, and a candidate stamps only if it reproduces all 12 shown
terms exactly — including 4 the search never saw. The gate did its one job 29
times out of 29: every wrong guess the raw regressor was forced to emit
became a refusal, and **nothing stamped was externally wrong**.

## What this comparison does and does not claim

It is a comparison of **contracts**, not curve-fitting skill or compute
budgets (the gated run spends up to two GP fits per sequence against the raw
run's one). A regressor targets approximate fit and must return its best
guess; on sequences with no recoverable closed form (primes, partitions,
Bell, Thue–Morse, d(n), φ(n)) the best possible regressor output is still a
confident wrong answer. Primus converts every one of those into a refusal.
Calibrated confidence — not recovery breadth — is the property being sold,
and it is the one a regressor structurally cannot match.

## Reproduce it

With a license: `python3 bench_pysr.py` and
`python3 bench_symreg_external.py --population 300 --generations 12` in the
vault's `Primus/`, against the same cached corpus. Without a license, the
outputs-based check you can run today is [`../eval/`](../eval/) — including
[`challenge.py`](../eval/challenge.py) on sequences **you** choose.
