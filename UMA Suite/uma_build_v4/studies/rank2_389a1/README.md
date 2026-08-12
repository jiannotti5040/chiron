<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Jacob Iannotti -->

# Rank-two BSD certificate capsule — 389.a1

The audit of `docs/BSD_REPORT.md` concluded that the honest place for a new
rigorous engine is **rank 2**, not another rank-zero sweep: rank 0 and 1
analytic Sha were computed exactly years ago (LMFDB, Sage's `L_ratio()`,
Miller 2011), while rank ≥ 2 leading coefficients are still generally stored
as floating approximations. This capsule is the rank-two vertical slice.

Curve: [389.a1](https://www.lmfdb.org/EllipticCurve/Q/389/a/1), `[0,1,1,-2,0]`,
i.e. `y^2 + y = x^3 + x^2 - 2x` — the smallest-conductor rank-2 curve.

## What runs

```bash
python3.12 -m venv venv
venv/bin/python -m pip install 'python-flint==0.9.0' 'cypari2==2.2.4'
venv/bin/python rank2_backend_prototype.py       # analytic rank exactly 2
venv/bin/python rank2_bsd_quotient_prototype.py  # the quotient, saturation assumed
venv/bin/python rank2_saturation.py              # saturation PROVED + the quotient
```

`rank2_saturation.py` is the one to read; the other two are its inputs.

## Result

| Quantity | Enclosure |
|---|---|
| `L''(E,1)/2` | `[0.7593165002884267702 ± 4.30e-20]`, excludes 0 → analytic rank exactly 2 |
| `Omega` | `[4.98042512171011015064... ± 9.08e-153]` |
| `Reg(E(Q))` | `[0.15246 ± 5.21e-6]` — **saturation proved**, not assumed |
| torsion, Tamagawa | 1, 1 (exact) |
| `Sha_an` | `[1.0000 ± 3.35e-5]` — contains 1, **excludes 4** |

## The saturation gap, and how it is closed

The quotient prototype proved `P=(0,0)` and `Q=(1,0)` independent but took
the claim that they *generate* `E(Q)` from PARI's `elldata` archive. That is
provenance, not proof, and it is load-bearing: if `L = <P,Q>` has index `m`
in the Mordell–Weil group then `Reg(L) = m^2 Reg(E(Q))`, so an unproved `m`
scales the quotient by `m^2`. At `m = 2` the answer would be 4 — also a
perfect square, and it would have read as an equally satisfying result.

`rank2_saturation.py` closes it without consulting any table:

1. `C` = Silverman's bound, `|hhat(R) - h_x(R)| <= C`; here `C = 6.154021`.
2. Enumerate **every** rational point with `h_x <= B = log 5000`, exactly:
   with `x = a/b^2` in lowest terms the point is rational precisely when
   `N = 4a^3 + 4a^2 b^2 - 8a b^4 + b^6` is a perfect square (`math.isqrt`),
   and each hit is re-verified in exact rationals. 74 affine points. Anything
   not found has `h_x > B`, hence `hhat > B - C = 2.363172`.
3. So `mu = min(smallest hhat found, B - C) = 0.325462` is a proven lower
   bound on the canonical height of every non-torsion rational point.
4. Hermite in rank 2 (`gamma_2 = 2/sqrt 3`) gives `Reg(E(Q)) >= (mu/gamma_2)^2`,
   and `m^2 = Reg(L)/Reg(E(Q))`, so `m <= 2 sqrt(Reg L)/(sqrt 3 * mu) = 1.385`.
5. `m < 2`, so `m = 1`. **L is saturated**, and no prime sieve is even needed.
   (When the bound exceeds 2 the script rules out each prime `p <= m` exactly
   with `ellisdivisible` over all `(a,b) mod p`.)

Corroborated three ways: all 74 enumerated points lie in `<P,Q>` with
`|a|,|b| <= 6`; PARI's independent `ellsaturation` returns the same basis; and
the **negative control** below is caught.

## The certificate caught a real unsaturated basis in the wild

`rank2_corpus_sweep.py` runs the whole pipeline over curves found by
enumeration rather than lookup, taking the two independent points from PARI's
**2-descent output**. For 389.a1 those descent points are *not* a basis: they
span an index-3 sublattice. The certificate reported

```
[0, 1, 1, -2, 0]  N=389  m<=4  sat=False  Reg=1.37214  Sha_an=[0.11111 +/- 2.4e-6]
```

`1.37214 / 0.15246 = 9` exactly, and the quotient reads `1/9` — the `m^2 = 9`
scaling, live. It refused rather than reporting `Sha_an = 1/9` as a result.

This is worth more than the synthetic `<2P, Q>` control below: nobody
constructed it. It is what the pipeline does when handed a basis a standard
tool actually produced, and it is exactly the failure the original prototype
would have absorbed silently, because it took its basis from `elldata` and
never checked.

The sweep therefore uses **propose-then-prove**: when the certificate says not
saturated, PARI's `ellsaturation` *proposes* a basis and the certificate is
re-run on it; only a basis that passes is used. With that, 389.a1 recovers
`Reg = 0.15246` and `Sha_an = [1.0000 ± 3.35e-5]`. Proposal from the tool,
proof from the gate — the same split the vault uses everywhere else.

## The rank-2 falsification sweep

This is the experiment `BSD_REPORT.md` wanted, at the rank where it is not
already solved. Per curve: analytic rank proved exactly 2 (exact modular
symbol gives `L(1) = 0`, root number +1, and an Arb ball for `L''(1)/2`
excluding zero), saturation proved, then the test —

> **does the `Sha_an` ball contain exactly one integer, and is it a square?**

A ball containing **no** integer refutes the strong BSD formula for that
curve. A ball containing a non-square integer refutes it too. Both are
finitely checkable, and both are verdicts the rounding-to-nearest procedure
the report criticised structurally cannot return.

**Full results are in [`RESULTS.md`](RESULTS.md)**, regenerated from
`results.jsonl` by `summarize_results.py` (pure stdlib — no PARI needed to
read the results back).

As of the completed radius-14 sweep:

| | |
|---|---|
| candidates examined | 10,092 (the complete box) |
| survived the cheap gates | 68 (root number +1 **and** `L(1) = 0` exactly) |
| **curves certified end-to-end** | **103** |
| distinct conductors | 103, range **389–11467** |
| unsaturated after proposal | 0 |
| **REFUTATIONS of strong BSD** | **0** |
| widest / tightest `Sha_an` ball | 1.24e-4 / 2.33e-5 |

Two sweep drivers exist. `rank2_corpus_sweep.py` is the readable one and runs
a 2-descent per candidate. `rank2_corpus_sweep_v2.py` reorders the gates —
`disc > 0` → new conductor under a cap → root number +1 → exact modular symbol
`L(1) = 0` → *only then* `ellrank` — which is roughly 15× faster, because most
curves are rank 0 and the exact symbol discards them for the price of one
rational. The conductor cap matters: `msfromell` builds the modular symbol
space of level `N` and stops being cheap around `N ~ 1e5`, which is where a
wide a-invariant box lands.

**Zero refutations.** Which is the expected outcome — BSD is not expected to
be false — and the point is that a refutation was *available* and did not
occur. `CONSISTENT` never becomes `VERIFIED`: enclosing the single square 1
does not prove `#Sha = 1`, because the true value could be a non-integer in
the same ball, and integrality is what BSD asserts.

## Negative control

The same machinery is run on `<2P, Q>`, which is index 2 by construction. It
reports `NOT SATURATED — 1P+0Q is divisible by 2`, and the regulator ratio
comes out `[4.000 ± 2.07e-4]`, exactly the predicted `2^2`. A certificate that
cannot say no proves nothing, so this control is part of the run and the
script asserts it fails.

## Dependency ledger

**Unconditional here** (exact rational or outward-rounded interval arithmetic):
torsion, Tamagawa product, conductor, Fourier coefficients; the exhaustive
small-point enumeration and hence `mu`; the Hermite index bound; the
`ellisdivisible` sieve.

**Theorem-dependent:** Silverman (1990) Thm 1.1 for `C`; modularity and the
functional equation for the L-series; Hermite's constant `gamma_2 = 2/sqrt 3`.

**Trusted software, not replayed by an independent checker:** PARI's 2-descent
for rank exactly 2 (`ellrank` → `[2,2]`, which the index argument *requires* —
comparing two rank-2 lattices is meaningless otherwise), `elltors`,
`ellglobalred`, `ellisdivisible`; FLINT/Arb outward rounding.

**NOT established: BSD for this curve.** `Sha_an` enclosing the single square
1 does *not* prove `#Sha = 1`. The enclosure is equally satisfied by a nearby
non-integer, and integrality of the quotient is exactly what BSD asserts and
what remains unproved in rank 2. The verdict vocabulary is `CONSISTENT`, never
`VERIFIED`.

## Licensing

The scripts here are Apache-2.0 like the rest of the vault. They are **not**
self-contained: they import `cypari2` (PARI, GPL-2.0-or-later) and
`python-flint` (MIT, wrapping FLINT/Arb LGPL-3.0), and `cysignals` is LGPL-3.0.
Nothing from those projects is vendored into this repository — `requirements.txt`
names them and the venv is gitignored — so the vault's own licensing is
unchanged. Anyone redistributing a *combined* artifact (a wheel or image with
PARI inside) inherits the GPL obligation; this capsule deliberately does not
produce one.

## Provenance

`rank2_backend_prototype.py` and `rank2_bsd_quotient_prototype.py` came from
the 2026-08-10 independent audit run and are unmodified. `rank2_saturation.py`
was written 2026-08-11 to close the gap the second of those names in its own
docstring.
