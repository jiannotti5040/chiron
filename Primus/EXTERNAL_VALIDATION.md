# External validation — live OEIS run

**Author: Jacob Iannotti. Licensed under PolyForm Noncommercial 1.0.0 (see the repository-root [LICENSE.md](../LICENSE.md)).**
Reproduce: `python3 oeis_live.py` (cached live snapshot) or `python3 oeis_live.py --live` (re-fetch from oeis.org).

The internal benchmark grades the engine on sequences it generated for
itself. This run removes that self-reference: **all terms were fetched live
from oeis.org on 2026-07-04** (per-sequence b-files), the engine saw the
first 12 terms of each sequence, and it was graded on exact prediction of
the next 4 terms it had never seen. Corpus: 24 canonical sequences spanning
the engine's declared hypothesis classes *and* famously non-closed-form
sequences where refusal is the correct behavior. The list was fixed before
any sequence was run.

## Headline finding: the external run caught a real false verification

On its first execution, the harness found what ~5,070 internal cases never
surfaced. **A002275 (repunits)** — a true order-2 recurrence,
a(n) = 11·a(n−1) − 10·a(n−2) — was stamped VERIFIED, yet predicted
111111112740 where OEIS says 111111111111.

Two compounding defects in the seed engine:

1. `lstsq` recovered the recurrence coefficients in float64 and never
   snapped them to exact rationals; iterating the recurrence compounds the
   error geometrically.
2. The held-out check used a **1e-6 relative tolerance** — at a(n) ≈ 10¹⁰
   that forgives errors of ~10⁴ — despite documentation promising exact
   equality.

Both are now fixed in `src/primus/engine.py`: integer surfaces get exact
rational coefficient refinement (Fraction arithmetic, drift-free integer
prediction), and holdout verification on integer surfaces demands exact
integer equality, with float predictions above 2⁵³ refused rather than
trusted. All 48 legacy stress tests and the internal benchmark still pass.

Two honest observations follow. *First*, the production engine
(`../Chiron/chiron.py`) did **not** have this defect — it recovers and
predicts repunits exactly. The "clean auditable seed" had silently drifted
behind the monolith, which is precisely the risk of maintaining multiple
copies of one engine. *Second*, this is what external validation is for:
the zero-false-confidence claim survived thousands of self-generated cases
and fell on the 24th externally-sourced one. The claim is now stronger
because it was falsified and repaired, not because it was defended.

## Results after the fix (zero false verifications)

Protocol: engine sees terms 1–12, graded on exact prediction of terms 13–16
against OEIS ground truth.

| Grade | Count | Sequences |
|---|---|---|
| **VERIFIED + externally correct** | **16 / 24** | Fibonacci, Lucas, Pell, Tribonacci, Jacobsthal, 2ⁿ, 3ⁿ, squares, cubes, triangular, oblong, factorials, repunits, Catalan, central binomial, quarter-squares |
| **VERIFIED + externally wrong (false confidence)** | **0 / 24** | — |
| recovered but conservatively unstamped | 1 | Thue–Morse (periodic guess happened to match; engine refused the stamp — correct) |
| declined (refusal) | 7 | primes, partitions, Bell, d(n), φ(n), Stern, Motzkin |

Notes on the refusals — the honest miss list:

- **Primes, partitions, Bell, d(n), φ(n), Stern**: outside the declared
  hypothesis classes; refusal is the designed behavior and every refusal was
  externally correct (the engine's tentative continuations were indeed
  wrong, and it did not stamp them).
- **Motzkin (A001006)** was the interesting boundary miss: P-recursive of
  order 2, one step beyond the then-current holonomic family. **Addendum,
  same day (v0.4.0):** the edge is closed. An exact-rational P-recursion
  solver (Fraction nullspace, no floats, exact reproduction required)
  recovers Motzkin's classical recurrence
  `(n+4)·M(n+2) = (2n+5)·M(n+1) + 3(n+1)·M(n)` from 12 terms and verifies
  it on the held-out OEIS values. As a fresh out-of-development probe, the
  large Schröder numbers (A006318) were then fetched live and verified on
  first contact. Bell numbers still refuse — they are not P-recursive, and
  the control holding is as important as the recoveries. The battery now
  stands at **18 / 25 verified, 0 false stamps, 6 honest refusals**.
- **Quarter-squares verified** via `holonomic_r2_p1` — a boundary probe the
  engine passed.

## What this does and does not show

It shows: on externally-sourced data the engine either proves its rule by
exact prediction of unseen terms or refuses, with zero false stamps, and
its refusals fall exactly where its documentation says they should. It
does **not** show novelty of the recovered rules (they are rediscoveries of
classified structure) and it is a 24-sequence curated battery, not the full
OEIS. `oeis_live.py --live --keyword-core` runs the same protocol over the
full ~180-sequence keyword:core corpus on any machine with network access —
that is the natural next escalation, and the harness ships ready for it.

## Head-to-head: symbolic-regression baseline

See `bench_symreg_external.py` (gplearn, runnable offline once installed)
and `bench_pysr.py` (PySR harness; runs wherever PySR/Julia is installed).
Results recorded in [SYMREG_RESULTS.md](SYMREG_RESULTS.md) when run.
