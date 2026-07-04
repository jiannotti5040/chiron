# Changelog — primus-intelligence

All notable changes to the installable seed. Dates are UTC.

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
