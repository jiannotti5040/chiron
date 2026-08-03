# Head-to-head vs symbolic regression (gplearn + PySR) — live OEIS protocol

**Author: Jacob Iannotti. Licensed under Apache-2.0 (see the repository-root [LICENSE](../LICENSE)).**
Reproduce: `python3 bench_symreg_external.py --population 300 --generations 12`
(gplearn 0.4.2 / scikit-learn 1.7.2; run 2026-07-04 on the live-fetched
OEIS corpus in `oeis_corpus_cache.json`).

Same protocol as [EXTERNAL_VALIDATION.md](EXTERNAL_VALIDATION.md): both
systems see the first 12 terms of each of 24 OEIS sequences; the grade is
**exact** prediction of the next 4 terms. Primus may refuse; a regressor
always answers.

## Result

| | exact 4/4 | wrong | refused |
|---|---|---|---|
| **Primus** | **16** | **0** | 8 |
| gplearn GP | 2 | 22 | — (cannot refuse) |

gplearn's two exact hits were squares (A000290) and oblong numbers
(A002378). Everything else it answered — Fibonacci, primes, partitions,
factorials, all of it — and answered wrong. Primus answered 16 exactly,
refused 8, and was never wrong.

## What this comparison does and does not claim

It is deliberately a comparison of **contracts**, not of curve-fitting
skill. Genetic-programming regression targets approximate fit under noise;
exact integer continuation is a hostile bar for it, and a larger budget
than the time-capped run here (population 300, 12 generations) would let it
recover a few more closed forms.

## PySR — the stronger baseline (run 2026-07-12)

Reproduce: `python3 bench_pysr.py` (PySR, deterministic serial mode,
`niterations=40`, seed 0; run on the author machine 2026-07-12 against the
same cached live-OEIS corpus, now 29 rows, same 12-shown/4-graded exact
scoring, post-fix engine — commits `ff3acd0..10d6b80`).

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
order-4 recurrence that Primus now *refuses* at 12 shown terms — its
evidence rule (h ≥ p held-out terms for an order-p recurrence, adopted
2026-07-11 after the composites false stamp) demands 16 terms before an
8-parameter rule can stamp. PySR's polynomial guess happens to land exact
there. That is the trade this project chooses on purpose: the same rule
that refuses one true quarter-squares stamp is the rule that prevented a
false composites stamp. Refusal is the product.

But no budget fixes the structural difference this table isolates: a
regressor **must** return its best guess and carries no native notion of
"I cannot certify this." On sequences with no recoverable closed form
(primes, partitions, Bell, Stern, Thue–Morse, d(n), φ(n)) the best possible
regressor output is still a confident wrong answer. Primus converts every
one of those into a refusal, and everything it did stamp was externally
correct. Calibrated confidence — not recovery breadth — is the property
being sold, and it is the one the baseline structurally cannot match.

## Guess-and-prove — the same GP behind the exact gate (run 2026-07-20)

Reproduce: `python3 bench_symreg_external.py --population 300 --generations 12`
(gplearn 0.4.2 / scikit-learn 1.7.2 — the same pair as the raw-GP run above;
same cached live-OEIS corpus, fetched 2026-07-04, before this layer was
built; 29 rows, 12-shown/4-graded exact scoring).

`primus.conjecture` puts the identical regressor BEHIND the discipline
instead of against it: GP trains on 8 of the 12 shown terms, its float
constants are snapped to exact integers/rationals, and a candidate stamps
only if it reproduces all 12 shown terms exactly in rational arithmetic —
including the 4 the search never saw. A stamped expression then predicts
terms 13–16 by exact evaluation. The stochastic proposer never stamps;
only the exact verifier does.

| | exact 4/4 | wrong / stamped-wrong | refused |
|---|---|---|---|
| **Primus** | **18** | **0** | 11 |
| raw gplearn GP | 2 | 27 | — (cannot refuse) |
| **gated GP (conjecture)** | **3** | **0** | 26 |

The gate did its one job 29 times out of 29: every wrong guess the raw
regressor was forced to emit became a refusal, and **nothing stamped was
externally wrong**. The gated run even recovers one row the raw run missed
(cubes, A000578): the exact holdout check surfaces the clean candidate
from the final population where the float-fitness winner was almost-right-
and-exactly-wrong.

Honest protocol notes: (1) this is not a compute-parity comparison — the
gated run spends up to two GP fits per sequence (a constant-free phase,
then a with-constants phase) against the raw run's one; the comparison is
of CONTRACTS, not budgets. (2) With the add/sub/mul/div function set, an
everywhere-defined integer-valued closed form is necessarily polynomial,
so the gated column's exact hits are and must be the polynomial rows; its
value on this corpus is the 27-wrongs-to-0 conversion, not new recovery.
(3) The seed engine caps its polynomial family at degree 6, so guess-and-
prove does add stamping reach there (degree-7+ polynomials, gated in
`primus.conjecture`'s selftest); Chiron's uncapped polynomial family
subsumes the current function set, which its twin module discloses.
