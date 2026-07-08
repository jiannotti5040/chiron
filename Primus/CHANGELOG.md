# Changelog — primus-intelligence

All notable changes to the installable seed. Dates are UTC.

## 0.5.1 — 2026-07-07

**A live false stamp on the seed, caught by an extended external OEIS probe and
repaired at the root — the repunit story a third time.**

- **Fix (stamping path).** On an integer surface, when any candidate reproduces
  the data EXACTLY in integer arithmetic, the non-exact (float/SVD) holonomic
  path is no longer allowed to mask it. Found live on OEIS **A002203** (companion
  Pell): the seed scored a 6-parameter float `holonomic_r1_p2` overfit shorter
  than the true order-2 linear recurrence, cleared the prefix-holdout it happened
  to match, and stamped VERIFIED while predicting 551612 instead of 551614.
  Chiron was already correct (exact `linear_recurrence_order2`); the seed had
  silently drifted behind it.
- **Guard.** A002203 added to the seed/Chiron differential (`drift_check.py`) and
  to the external OEIS battery, closing the blind spot permanently.
- Full battery green after the fix: 48 stress · 27 certify · 13 fuzz · 10 MCP ·
  internal benchmark (zero false confidence) · live-OEIS extended 25 verified / 0
  false · drift GREEN (companion Pell now covered) · Chiron selftest.

## 0.5.0 — 2026-07-05

**The Apéry release: degree-3 P-recursion, the deep-evidence tier, and
three engine repairs the attempt forced.**

- Exact P-recursive solver extended to polynomial coefficients of degree 3
  (`max_pdeg` 2 → 3, seed and Chiron in step — no ledger debt). The Apéry
  numbers (A005259, the ζ(3) irrationality sequence) now verify with their
  classical recurrence; Franel numbers (A000172) verify as the blind probe
  that needed only deeper evidence, not the new degree.
- **Deep-evidence protocol tier** in `oeis_live.py`: sequences marked
  `protocol: "deep"` are graded at 24 shown / 4 held out. This is MDL's
  appetite made into protocol — a (2,3) rule has 12 unknowns and cannot
  even FORM a candidate on 12 terms, and its holdout refit needs 18-term
  prefixes to be unambiguous. Bell numbers ride the tier as the control:
  24 terms of evidence still buy a refusal, because Bell is not P-recursive.
- Repairs forced by the attempt (each a latent defect beyond Apéry):
  1. **Exact integers now ride past the float front door.**
     `collapse_numeric` floated every term on entry, silently corrupting
     integers beyond 2⁵³ — Apéry's 29-digit terms died before any exact
     solver saw them. Python-int inputs are preserved end-to-end
     (`_exact_int_view`), and integral-looking floats are trusted only
     below 2⁵³.
  2. **Nullspace uniqueness is now a refusal condition** (seed and Chiron).
     A solution space of dimension > 1 means the data admits multiple rules
     of the class; any basis vector is an arbitrary mixture that reproduces
     the shown terms yet predicts noise. Ambiguity refuses.
  3. **Holdout refits judge the prefix at the prefix's own scale.** Reusing
     full-surface precision let a tail-dominated tolerance (~10²⁶ for
     Apéry) quantize every prefix residual to zero, handing the refit to a
     one-parameter constant.
- Live-OEIS battery now 28 sequences: **20 verified, all externally
  correct; 0 false stamps; 7 honest refusals; 1 conservative unstamp.**

## 0.4.0 — 2026-07-04

**The capability edge the live-OEIS run identified is closed.** New exact
P-recursive solver (`_cand_holonomic_exact`): recurrences with polynomial
coefficients, order ≤ 2, degree ≤ 2, found by exact Fraction nullspace —
no SVD, no thresholds — with exact reproduction of every shown term
required before a candidate exists, and exact-arithmetic prediction after.

- Motzkin (A001006) now VERIFIED with the classical recurrence
  (n+4)M(n+2) = (2n+5)M(n+1) + 3(n+1)M(n), recovered from 12 terms.
- Large Schröder numbers (A006318), fetched live from OEIS *after* the
  solver was written, verified on first contact — a genuine out-of-
  development probe.
- Bell numbers still refuse (they are not P-recursive) — the control holds.
- Live-OEIS battery is now 18 / 25 verified, all externally correct,
  zero false stamps, 6 honest refusals.
- The rank-1 exclusion keeps canonical families canonical: a polynomial
  multiple of a constant-coefficient recurrence is rejected (without it,
  Fibonacci could be dressed up as holonomic — caught by the 48-gate
  stress suite before shipping).
- The drift detector did its first real job: the new capability turned the
  build RED as SEED-ONLY until ledgered with a dated reason. Later the same
  day the margin fix was ported into Chiron (whose holonomic solver was
  already exact — the original ledger text misdiagnosed it as float/SVD;
  only its rows ≥ unknowns+2 margin blocked holdout verification), Motzkin
  and Schröder verify in both engines, and the ledger is empty again. The
  full loop — RED, written reason, repair, cleared — took one afternoon.

## 0.3.0 — 2026-07-04

**Certificate layer (schema `primus.certificate/1` → `/2`; contract now
written down in [SCHEMA.md](SCHEMA.md)):**

- New checkable claim kinds: primality/compositeness (deterministic
  Miller–Rabin below the proven witness bound, REFUSED above it), binomial
  coefficients, gcd/lcm, modular arithmetic, date arithmetic (days
  after/before, days between; exact calendar math), sums/totals/averages of
  listed numbers, power claims (`2^10 = 1024`, bounded), and reversed
  arithmetic (`91 = 7 × 13`).
- New certificate fields: `coverage` (fraction of input actually checked —
  read it before trusting a pass), `claims_capped`, `input.truncated`,
  per-claim `span`, `attestation.kind`.
- Adversarial hardening, verified by a new 13-gate fuzz suite
  (`test_certify_fuzz.py`): input truncation at 100k chars, 200-claim cap,
  4,096-digit integer bound (refused, not computed), 256-term per-claim
  sequence bound (fixes a real DoS the fuzzer found: a 20k-integer flood
  became one giant collapse call), digit-run clamping + anchor-windowed
  regex scanning (fixes a second real finding: quadratic scan cost on
  '='-free operand soup).
- Honest attestation language: the certificate hash is labeled what it is —
  a tamper-evident hash, not an unforgeable signature.

**Engine (the float purge):**

- Polynomial recovery on integer surfaces now uses exact Newton
  finite-difference arithmetic (no `polyfit` on the stamping path);
  predictions are exact Python ints valid far beyond 2⁵³.
- Geometric recovery on integer surfaces now uses exact rational ratio
  detection (no log-space regression); handles negative ratios, which the
  float path structurally could not.
- These close the same defect class as 0.1.0's repunit fix (float drift
  passing a tolerance, then compounding).

**Differential testing:** `drift_check.py` runs a 33-surface battery
through both this seed and `../Chiron/chiron.py`; contradictions (both
stamp, different predictions) and unledgered seed-only stamps fail the
build. Wired into CI.

**Packaging:** LICENSE.md now ships inside every wheel/sdist (the PolyForm
notice must travel with the code); CI runs a 3.9/3.13 × Ubuntu/Windows
matrix; tag-triggered PyPI release workflow (trusted publishing) added.

## 0.2.0 — 2026-07-04

- `primus-mcp`: dependency-free MCP stdio server exposing `certify` and
  `collapse` as agent tools; 10-gate live-subprocess handshake test.
- `__version__` reads package metadata — pyproject is the single source of
  version truth.

## 0.1.0 — 2026-07-04

- First packaging of the seed: `primus.engine` (moved from
  `invariant_engine.py`, which remains as a full compatibility shim),
  `primus.certify`, `primus` CLI (`collapse`, `certify --gate`, `selftest`).
- Engine fix found by the first live-OEIS external validation run:
  recurrence coefficients snapped to exact rationals; held-out verification
  demands exact integer equality on integer surfaces (the repunit
  false-verification, A002275). Details in
  [EXTERNAL_VALIDATION.md](EXTERNAL_VALIDATION.md).
