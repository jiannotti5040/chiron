# When an AI hands you a proof, what checks the arithmetic?

**Author: Jacob Iannotti. Apache-2.0 (see [../LICENSE.md](../LICENSE.md)).**

In one week of July 2026, two long-open mathematical conjectures were
refuted by counterexamples that AI systems produced:

| Conjecture | Open since | Announced | Produced with |
|---|---|---|---|
| **Jacobian conjecture** (n ≥ 3) | 1939 (Keller) | 2026-07-20, Levent Alpöge | Claude Fable 5 |
| **Goemans' unsplittable-flow cost conjecture** (Dinitz–Garg–Goemans) | ~1990s | 2026-07, Dmitry Rybin | GPT-5.6 Pro |

Both were announced ahead of peer review. Both are short enough to state on
a napkin and hard enough that specialists missed them for decades. This is
now a recurring situation, not a novelty: **a machine produces a claim, and
somebody has to decide whether the arithmetic is actually real.**

That decision is what this project is for. Below is what the licensed
engine's arithmetic checked, what it reproduced independently, and — the
part that matters — **what it refused to certify.**

Everything here is an *output*. No engine source appears on this page; the
gates named are reproducible by any license holder with the commands given.

---

## 1. The Jacobian counterexample — 12 gates

The conjecture: a polynomial map with constant non-zero Jacobian
determinant must be invertible. The counterexample is a map **C³ → C³**:

```
u = (1+xy)³·z + y²·(1+xy)·(4+3xy)
v = y + 3x·(1+xy)²·z + 3x·y²·(4+3xy)
w = 2x − 3x²y − x³z
```

Verified in exact rational arithmetic — sparse polynomials over ℚ with
`Fraction` coefficients, no computer-algebra system, no floats:

| # | Claim | Result |
|---|---|---|
| 1 | **det J(F) = −2** as a polynomial identity (every non-constant coefficient cancels exactly) | **VERIFIED** |
| 2 | **F(0, 0, −1/4) = F(1, −3/2, 13/2) = (−1/4, 0, 0)** — two distinct rational points, one image | **VERIFIED** |

Claim 1 is the conjecture's hypothesis; claim 2 denies injectivity. Together
they refute the implication for n = 3, and via identity coordinates for every
n ≥ 3.

**Controls that can fail** (a gate that cannot fail proves nothing): the
known elementary automorphism `(x + y², y, z)` returns det J = 1 identically
(positive control), and perturbing one coefficient of `w` (2x → 3x) destroys
the determinant's constancy (discrimination control). The identity is a
knife-edge cancellation, not a property of nearby maps.

---

## 2. The Dinitz–Garg–Goemans cost counterexample — 15 gates

The theorem of Dinitz, Garg and Goemans is not in dispute: any fractional
single-source flow can be re-routed as an **unsplittable** flow — each demand
sent entirely along one path — while exceeding each arc's capacity by at most
`d_max`, the largest demand. Goemans then **conjectured** this could always
be done **without increasing the cost.**

The counterexample is a 7-node, 9-arc network. Each of its three terminals
has exactly two possible routes, so the unsplittable routing space has
exactly `2³ = 8` members — **small enough to enumerate completely.** That is
the difference between sampling and proving.

| # | Claim | Result |
|---|---|---|
| 1 | The fractional flow is **feasible** — conserves at every interior node, meets every demand exactly | **VERIFIED** |
| 2 | Its cost is **58** | **VERIFIED** |
| 3 | Every unsplittable routing within the DGG congestion allowance costs **at least 60** (all 8 enumerated; 4 are admissible) | **VERIFIED** |
| 4 | Therefore Goemans' cost conjecture is **false** for this instance | **REFUTED** |

Exact integers throughout. No LP solver, no floats, no network.

### Independent corroboration

The instance was reconstructed from a published 3-parameter family at
`(b, m, g) = (10, 5, 1)`. Three numbers *not used in the reconstruction* then
matched the separately-reported instance exactly — the congestion thresholds
on the spine arcs:

| arc | capacity | + d_max (15) | independently reported |
|---|---|---|---|
| s→u | 24 | **39** | 39 |
| u→v | 14 | **29** | 29 |
| v→w | 9 | **24** | 24 |

### A disagreement the engine resolved rather than papered over

Two public accounts of this counterexample disagreed on its cost: one said
**58**, the family's own convention gives **290**. Neither is wrong —
290 = 58 × 5, and the refutation is invariant under positive cost scaling.
The apparent contradiction was a normalisation, not an error. Both accounts
describe one counterexample. That reconciliation is asserted as a gate, so it
cannot silently rot.

### The whole family, not one lucky instance

Every admissible `(b, m, g)` with `b ≤ 25` — **456 instances** — was
enumerated exhaustively. All 456 refute:

```
admissible_instances_checked : 456
instances_refuting           : 456
all_refute                   : True
```

**Controls that can fail:** inadmissible parameters raise rather than
silently verifying; a perturbed capacity is detected as an infeasible flow;
and with all costs set to zero the verifier reports `refuted: False` —
because nothing is then more expensive than the fractional flow. The
refutation depends on the congestion allowance, not on convenient accounting.

---

## 3. What was **refused** — the part that makes the rest worth reading

Neither module certifies:

- **Provenance.** That Fable 5 or GPT-5.6 Pro produced these constructions is
  *reported*, not verified. The arithmetic stands regardless of who wrote it.
- **The plane case (n = 2)** of the Jacobian conjecture, which this map leaves
  entirely open.
- **Minimality** of either counterexample.
- **The Dinitz–Garg–Goemans theorem itself**, which is untouched — only
  Goemans' *cost* conjecture is refuted.
- **Peer review.** As of 2026-07-23 neither result has a peer-reviewed
  write-up. These gates check arithmetic, not consensus.

That list is not a disclaimer bolted on at the end. It is the product. An
engine that stamps everything tells you nothing; the stamps above are worth
something precisely because these five things did not get one.

---

## Why this is the honest demo

The public [`eval/`](../eval/) proves the headline property on 34 OEIS
sequences — a fair test, but a small-stakes one. This page is the same
discipline applied where the stakes are visible: **two claims the world was
actively arguing about, checked in exact arithmetic within days, with the
boundary of the check stated plainly.**

If an AI system in your workflow produces a structured result that can be
checked exactly, this is the shape of the answer you get: a verdict, the
method, and an explicit line around what was *not* established.

## Reproduce

Both modules ship in the licensed vault's UMA suite:

```
cd uma_build_v4
python3 -m pytest tests/test_jacobian.py -v   # 12 gates
python3 -m pytest tests/test_dgg.py -v        # 15 gates
python3 -m uma.jacobian                        # certificate, JSON
python3 -m uma.dgg                             # certificate, JSON
python3 -m pytest -q -m "not slow"             # 151 passed, whole suite
```

Counts as of the 2026-07-23 run; every figure on this page is reconciled in
[`BATTERIES.md`](BATTERIES.md), which wins any disagreement.

## Sources (consulted 2026-07-21 / 2026-07-23)

- Jacobian: Alpöge announcement (X, 2026-07-20); Oliver Knill transcription with Mathematica check, quantumcalculus.org; digestions by Terence Tao and Secret Blogging Seminar (2026-07-20/21)
- DGG: Dmitry Rybin announcement (X, July 2026); 3-parameter generalisation by Hensen Juang (X); technical write-up at mathlab.drummerduck.com; background theorem Dinitz, Garg & Goemans, *Combinatorica* (1999)
