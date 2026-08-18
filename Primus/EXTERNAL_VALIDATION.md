# External validation — live OEIS run

**Author: Jacob Iannotti. Licensed under Apache-2.0 (see the repository-root [LICENSE](../LICENSE)).**
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

## Addendum, 2026-07-05 (v0.5.0): the Apéry release and the deep tier

The next boundary fell the same way the last one did — and paid for itself
in repairs. Extending the exact solver to degree-3 coefficients reached the
**Apéry numbers** (A005259, the ζ(3) irrationality sequence), with the
**Franel numbers** (A000172) as the blind probe needing only deeper
evidence, not the new degree. Both verify with their classical recurrences
on live-fetched terms; **Bell numbers still refuse with 24 shown terms**,
because no amount of evidence should buy a stamp for a rule that does not
exist.

The attempt exposed three latent defects, each now fixed and each bigger
than Apéry: (1) the numeric front door floated every input term, silently
corrupting integers beyond 2⁵³ before any exact solver saw them; (2) an
ambiguous nullspace (dimension > 1) let the solver pick an arbitrary
mixture-rule — uniqueness is now a refusal condition in both engines;
(3) holdout refits reused full-surface precision, which for fast-growing
sequences quantized every prefix residual to zero. The holdout safety net
caught all three before any false stamp — but the fixes moved the honesty
into the solvers themselves, where it belongs.

**Battery standing: 28 sequences — 20 verified (all externally correct),
0 false stamps, 7 honest refusals, 1 conservative unstamp.** The deep tier
(24 shown / 4 graded, marked per-sequence) is documented in the corpus
provenance: parameter-rich rules cannot even form candidates on 12 terms;
demanding more evidence for more parameters is MDL's appetite as protocol.

## Addendum, 2026-07-07 (v0.5.1): a third falsify-and-repair (companion Pell)

Extending the live battery with 7 post-development probes (list fixed before
grading) surfaced another false stamp — and it fell exactly like repunits did.
**A002203 (companion Pell / Pell-Lucas)** was stamped VERIFIED with a float
`holonomic_r1_p2` rule predicting 551612, where OEIS gives 551614. Root cause: on
integer surfaces the float/SVD holonomic path can overfit (6 free parameters),
score a shorter description than the true order-2 linear recurrence, and clear
the prefix-holdout it happens to match within the shown window. The production
engine (`../Chiron/chiron.py`) did **not** have the defect — it classifies
companion Pell as the exact linear recurrence — so the seed had again silently
drifted behind the monolith, on a surface the drift set did not yet cover.

Fixed in `src/primus/engine.py`: when any candidate reproduces the integer
surface exactly in integer arithmetic, the non-exact holonomic path is dropped
from selection, so an exact rule can never be masked by a float overfit. The
surface is now in both the seed/Chiron differential and the external battery.
The extended battery stands at **35 sequences — 25 verified (all externally
correct), 0 false stamps, 9 refusals, 1 conservative unstamp.** As before, the
claim is stronger for having been falsified and repaired in the open.

> **Re-run 2026-08-03 — the verified count is now 24, not 25.**
> `python3 oeis_live.py --cache oeis_corpus_extended_2026-07-07.json` today
> reports `n=35 · VERIFIED+correct: 24 · declined: 9 · recovered-unstamped: 2 ·
> false confidence: 0 · PASS`. One sequence that was stamped at v0.5.1 now
> recovers its rule but declines to stamp it. The engine moved **toward**
> refusal, which is the safe direction and needs no repair — but the 25 above is
> a dated figure, not the current one, and is left in place because this file is
> a chronological record. The invariant is unchanged: zero false stamps in both
> runs.
>
> **Which corpus produces which number.** `oeis_live.py` defaults to
> `oeis_corpus_cache.json` (**29** sequences → 20 verified / 7 declined / 2
> unstamped), which is what the gate battery and `docs/BATTERIES.md` report.
> The **35**-sequence figure requires the `--cache` flag above. Both are live-
> graded against oeis.org; neither is a superset claim about the other.

## 2026-07-11 — the first full keyword:core sweep: 3 false stamps. RESOLVED same night.

**Status: RESOLVED.** All three defects were fixed at root within hours
(commits `ff3acd0`/`5f619da`: prefix-exactness in the holdout refit, held-out
evidence scaled to model capacity — h ≥ p for order-p recurrences — and an
exact-Fraction multiplicative_ratio path), ported to Chiron the same night,
locked into the drift set (42/42) and the stress suite (55/55). The re-run
sweep on the same 109 live sequences: **44 verified — all externally correct,
0 false stamps, 63 honest declines, 2 conservative unstamps**
(`oeis_sweep_2026-07-12_fixed.log`). The repair cost zero correct external
stamps at this protocol, and A001147 moved from false-stamp to exactly
verified. Bonus finding: the fix exposed Thue-Morse's old cached stamp as the
same coincidence class (lucky-right), now an honest refusal.

The original report is preserved unedited below.

The live sweep was expanded from the curated battery to the OEIS
`keyword:core` corpus fetched live (109 sequences graded after the search API
stopped serving pages at start=110; the pager now retries with backoff and
grades the honest partial — that fetch-path hardening was itself found by this
run, first live contact). Protocol: engine sees 12 terms, graded on exact
prediction of the next 4. Raw log: `oeis_sweep_2026-07-11_109seq.log`.

Result: **44 verified-correct · 3 VERIFIED+WRONG · 61 honest declines · 1
conservative unstamp.** The three false stamps, each a distinct root cause:

| Sequence | Stamped as | Predicted vs expected | Suspected root cause |
|---|---|---|---|
| A000002 Kolakoski | `periodic_3` | `[1,2,2,1]` vs `[1,1,2,1]` | periodic family's verification hole on short surfaces |
| A001147 odd double factorial | `multiplicative_ratio` | `…876, …417` vs `…875, …375` (last digits) | float precision leaking past 2^53 in the ratio path — the repunit defect class, different family |
| A002808 composites | `linear_recurrence_order4` | `[22,24,26,27]` vs `[22,24,25,26]` | order-4 evidence margin too loose at 12 shown terms |

At 12 shown terms the honest behaviour for all three was **refusal**. The fix
work (per playbook: root cause, never a widened tolerance; exact arithmetic on
every stamping path; port to Chiron; drift + full battery) is tracked in the
repo's issues. The cached battery and all internal suites remain green; the
sections above this one predate tonight's finding.

## Head-to-head: symbolic-regression baseline

See `bench_symreg_external.py` (gplearn, runnable offline once installed)
and `bench_pysr.py` (PySR harness; runs wherever PySR/Julia is installed).
Results recorded in [SYMREG_RESULTS.md](SYMREG_RESULTS.md) when run.

## 2026-08-11 — two false-verification classes, found by external audit

Neither of these was caught by the internal battery, and both were live in the
shipped tree. An independent audit of `UMA Suite/uma_build_v4/docs/BSD_REPORT.md`
surfaced the first and pointed at the second; the second was confirmed
reachable here. Both are now gated.

| Defect | What it stamped | Root cause | Gate added |
|---|---|---|---|
| **Primality witness/bound desync** | `certify("318665857834031151167461 is prime")` → **VERIFIED**, on a composite | twelve Miller–Rabin witnesses (2…37) paired with the *thirteen*-witness bound 3.317e24. The Sorenson–Webster ψ₁₂ counterexample `399165290221 × 798330580441` sits **below** the range the gate claimed to decide | bound now **derived** from the witness list via a machine-checked ψ table, so the pair cannot desync; 5 gates in `certify._selftest`, incl. one asserting every tabulated ψₖ really does fool its own k bases |
| **Tolerance fit read as proof** | `collapse([1.0 + 1e-9*n])` → `"VERIFIED generator 'constant' … EXACTLY predicts all 6 held-out terms … That is proof it captured the law"`, for a strictly *increasing* sequence | the repunit fix demanded exact equality on **integer** surfaces and left real ones on a `1e-6·(|a|+1)` tolerance. Chiron's float fallback independently carried `"verified": True` after a tolerance fit | `verified = (hits == h) and int_surface`; real surfaces fall through to the candidate wording with hits still reported. 5 gates in `test_invariant_engine.py`; Chiron's fallback now emits `verified: False, tolerance_fit: True` |

The first is the sharper lesson: the arithmetic was correct, the witness loop
was correct, and every existing primality gate passed. What was wrong was a
*constant written twice*. Deriving it was the fix; adding base 41 alone would
have left the same defect class one edit away.

Negative controls, because a gate that cannot fail proves nothing:
reintroducing the original witness/bound pair fails exactly three of the new
gates, and the drifting-float sequence is stamped again if `and int_surface`
is removed.

Neither defect had reached a stored certificate: all 571 artifacts under
`Chiron/artifacts/` were scanned and none carries a primality claim, so no
quarantine was required.

Battery after both fixes, unchanged where it should be:
`primus selftest` GREEN · certify **40/40** (was 35) · engine stress **60/60**
(was 55) · fuzz 16/16 · MCP 11/11 · drift 42/42 GREEN · `oeis_live` n=29,
**20 verified, 0 false confidence** (identical to before — no recall lost) ·
Chiron 12/12 · monolith 61/61 through the fold.

### Addendum, same day — a false REFUTATION, found by dogfooding

Found by running `certify` on my own working notes, which is what the Chiron
skill says to do and what had not been done. Two of my claims came back
REFUTED. One was genuine sloppiness on my part (a rounded product written as
an exact equality). The other was the gate inventing an error:

| Input | Extracted as | Stamped | Truth |
|---|---|---|---|
| `2 * 3 / 6 = 1` | `3 / 6 = 1` | REFUTED | **true** |
| `1 + 2 + 3 = 6` | `2 + 3 = 6` | REFUTED | **true** |
| `10 * 4 / 8 = 5` | `4 / 8 = 5` | REFUTED | **true** |
| `3825123056546413051 = 149491 * 747451 * 34233211` | drops the third factor | REFUTED | **true** |

`_RE_ARITH` matches a binary `a op b = c` and its lookbehind rejects only a
preceding *digit*, not a preceding *operator* — so any chained expression had
a fragment lifted out and judged. The kernel evaluates one binary operation
and cannot know the precedence of the rest, so chains are now **REFUSED**
rather than decided on a fragment (`_chain_fragment`).

This matters as much as the false VERIFIED above: per the project's own rule,
a gate that invents errors is worth no more than one that misses them, and
this one would refute correct arithmetic in any prose that chains operations.

5 gates added; plain binary arithmetic, the reversed form, the product form,
and negative operands are all regression-guarded. Certify **45/45** (was 40).

Note: the `mcp__primus__certify` MCP tool still shows the old behaviour — it
runs the published 0.9.0 package in a separate process, not `src/`. It will
pick the fix up at the next release.

## 2026-08-18 — the grounded layer verified across units. RESOLVED same day.

Issue #3 was opened on 2026-08-15 against 0.9.0 and left open. It was still
live on `main` three days later, and it is the plainest false-verification
class this project has shipped: **three claims whose digits matched a supplied
fact while the thing being counted did not.**

Reproduce against 0.9.0 or any commit up to `df8597f`:

```python
from primus.grounded import check_text
check_text("Revenue was $4.2M.", {"Revenue": {"value": 4200000, "unit": "vehicles"}})
check_text("Readiness was 74%.", {"Readiness": {"value": 74}})
check_text("Species was 2.",     {"specie":    {"value": 2}})
```

All three returned `VERIFIED`, with the reason `exact match against the
supplied fact`. A dollar figure confirmed a vehicle count; a percentage
confirmed a bare number; a claim about *species* was answered by a fact about
*specie*.

| Defect | Root cause | Repair |
|---|---|---|
| **Currency dropped before comparison** | `$` was stripped off the *value* token (`"$4.2M"`) and never recorded anywhere, so a dollar claim arrived carrying no unit at all | the currency is read from the value and becomes the claim's semantic unit |
| **Magnitude scaling erased the unit** | `_scaled()` folded `M`/`thousand` into the number and then returned the unit slot as `None` — so any claim with a magnitude suffix lost whatever unit it had | `_measure()` returns `(value, semantic_unit, conflict)`; a magnitude scales the number and is *not* a unit, and the semantic unit survives the scaling |
| **Unit mismatch checked only when both sides had one** | the guard read `if a_unit and f_unit and a_unit != f_unit`, so every one-sided pairing fell through to a digit comparison | units must be **equal**, and "no unit" is a unit that matches only "no unit" |
| **Subject normalisation was not injective** | a trailing-`s` fold mapped `species → specie`, merging two distinct words — the exact thing the function's own docstring said must never happen | nothing is stemmed. The fold survives only as a *hint* in the refusal text, which now names the nearest supplied subject |

A bounded property sweep over the unit pairings — the same shape as the
certify kernel sweep — found the class was **wider than the three reported
cases: 10 of 30 pairings verified off the diagonal.** Fixing the three named
cases without the sweep would have left seven live.

The lesson is not that a gate was missing. `grounded.py` had a 20-gate
selftest, and `bin/chiron test --full` ran it, and it was green through all
ten leaks. The gates asked whether the *values* matched and never asked
whether the *units* did. A green battery is evidence about the questions it
asks, and this one had a question-shaped hole in it.

Negative control, because a gate that cannot fail proves nothing: the new
`test_grounded_units.py` was written **fail-first** against the unrepaired
tree and reported `5/12 passed`, naming all three reported cases plus the
seven unreported pairings. Against the repaired tree it reports `12/12`, and
`grounded.py`'s own selftest went 20/20 with its plural-folding gate
**inverted** — it had asserted the defect (`"plural and possessive fold to the
same key"`) and now asserts the invariant (`"distinct subjects never fold
together"`).

Reproduced against the **shipped wheel**, installed in a clean virtualenv
outside the repository: 0 false verifications, with refusals that say why
(`units differ: claim in 'usd', fact in 'vehicles'`).

Both gates now run in `ci.yml` on every push, not only in the release
battery — the narrower true gap, since the grounded layer was previously
checked only at release time.

Battery after the fix, unchanged where it should be: `chiron test --full`
**61/61** · parity **138 gates** identical through both incarnations · certify
property sweep PASS (4,116 claims, 0 false VERIFIED) · engine server 48/48 ·
fuzz 16/16 · engine stress 60/60 · MCP 11/11 · drift 42/42 GREEN · `oeis_live`
n=29, **20 verified, 0 false confidence** — no recall lost.

Issue #2 (the primality pseudoprime above) was **already repaired** by the
2026-08-11 work and was verified fixed on the same pass; it had simply been
left open.
