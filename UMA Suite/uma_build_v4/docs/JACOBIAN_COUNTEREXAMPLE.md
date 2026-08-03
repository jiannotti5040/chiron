# The 2026 Jacobian-conjecture counterexample, verified by this suite's own arithmetic

**Author: Jacob Iannotti. Licensed under Apache-2.0 (see the repository-root LICENSE).**
**Epistemic status: the verification machinery and the two arithmetic claims below are implemented-and-tested (`uma/jacobian/`, `tests/test_jacobian.py`, 12 gates). The surrounding history is reported, not certified.**

## What happened

On **2026-07-20**, Levent Alpöge announced on X — construction attributed
to **Claude Fable 5**, prompted mid-World-Cup-final by a friend — an
explicit polynomial map **C³ → C³** with **constant nonzero Jacobian
determinant** that is **not injective**: a counterexample to the Jacobian
conjecture in its det-nonzero-constant formulation, open since Keller
(1939). By adjoining identity coordinates the failure extends to every
**n ≥ 3**; **n = 2 remains open**. As of **2026-07-21** there is **no
peer-reviewed write-up**; the working copies are the primary thread, its
Wolfram Alpha checks, and Oliver Knill's transcription with Mathematica
verification code (quantumcalculus.org), which is the source of the
polynomials verified here.

## The map (Knill transcription)

```
u = (1+xy)³·z + y²·(1+xy)·(4+3xy)
v = y + 3x·(1+xy)²·z + 3x·y²·(4+3xy)
w = 2x − 3x²y − x³z
```

## What `uma.jacobian` verifies — in exact rational arithmetic, no CAS

| # | Claim | Method | Result |
|---|---|---|---|
| 1 | **det J(F) = −2 as a polynomial identity** | symbolic cofactor determinant over ℚ (sparse exponent-dict polynomials, `Fraction` coefficients); every non-constant coefficient cancels exactly | **VERIFIED** |
| 2 | **F(0, 0, −1/4) = F(1, −3/2, 13/2) = (−1/4, 0, 0)**, two distinct rational points, one image | exact `Fraction` evaluation | **VERIFIED** |

Claim 1 is the conjecture's hypothesis; claim 2 denies injectivity, hence
invertibility. Together they refute the implication for n = 3. Both
collision points are real and rational, so no complex arithmetic is even
needed to exhibit the failure.

Controls (the machinery must discriminate, not merely agree): the known
elementary automorphism `(x + y², y, z)` yields **det J = 1** identically
(positive control), and perturbing a single coefficient of `w` (2x → 3x)
destroys the constancy of the determinant (discrimination control) — the
identity in claim 1 is a knife-edge cancellation, not something nearby
maps satisfy.

## What this suite does NOT claim

- It does not certify the **provenance** of the construction (Alpöge's
  thread and its attribution to Fable 5 are reported as announced).
- It does not touch **n = 2**, which this map leaves open.
- It does not substitute for **peer review**; the official record still
  awaits an expert write-up. If the transcription itself contained an
  error, these gates verify the transcribed map — which is, regardless of
  history, a genuine counterexample in its own right: the two checks above
  stand on their own arithmetic.

That last sentence is the point of doing this inside UMA: whatever the
eventual paper says, **a polynomial map with constant determinant −2 and
a verified two-point collision exists and is checked here exactly** —
zero floats, zero network, zero trust in anyone else's algebra.

## Reproduce

```
cd uma_build_v4
python3 -m pytest tests/test_jacobian.py -v     # 12 gates
python3 -m uma.jacobian                          # the certificate, as JSON
```

## Sources (as consulted 2026-07-21)

- Alpöge announcement: x.com/__alpoge__/status/2079028340955197566 (2026-07-20)
- Transcription + Mathematica check: quantumcalculus.org/jacobian-conjecture-solution/ (Oliver Knill, 2026-07-20)
- Context/coverage: explainx.ai blog (2026-07-20, "Did Fable 5 Disprove the Jacobian Conjecture?"); alexisgallagher.com/posts/2026/jacobianfun/ (claims an infinite family, n preimages for every n ≥ 3 — reported, not verified here)

## Relation to the rest of UMA

UMA's dynamics documents use Jacobians in the analytic sense (flux
Jacobians, linearized drift). This module is the suite's first pure-
algebra member and follows the vault discipline end to end: exact
arithmetic on the stamping path, controls that can fail, refusal to
certify beyond what was computed.
