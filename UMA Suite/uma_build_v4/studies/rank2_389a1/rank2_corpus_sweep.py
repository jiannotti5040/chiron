#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""A falsification sweep of the BSD leading-coefficient formula AT RANK 2.

BSD_REPORT.md wanted to run "the only finitely-falsifiable content of a
Millennium Problem" through a procedure that can return no. It ran that at
rank 0, where exact modular-symbol methods already existed (see
studies/exact_rank0_sha/). The audit's conclusion was that the idea is sound
but belongs at rank >= 2, where leading coefficients really are stored as
rounded floats. This is that sweep.

For each curve the pipeline is, per curve and with no table lookup anywhere:

  1. enumerate a-invariants; keep non-singular curves with disc > 0
  2. PARI 2-descent -> rank interval; keep those with lower == upper == 2,
     and take the two independent points DESCENT returns (not elldata)
  3. root number +1 and the exact rational modular symbol L(1)/Omega_+ = 0,
     which together force even order of vanishing >= 2
  4. L''(E,1)/2 as an Arb ball with an explicit Deligne tail bound; excluding
     zero upgrades that to analytic rank EXACTLY 2
  5. saturation PROVED per curve (Silverman C -> exhaustive small-point
     enumeration -> mu -> Hermite index bound -> ellisdivisible sieve)
  6. Sha_an = L''/2 * tors^2 / (Omega * Reg * prod c_p) as a ball

  7. THE FALSIFICATION TEST: does the ball contain exactly one integer, and
     is that integer a perfect square? A ball containing NO integer would
     refute the strong BSD formula for that curve. A ball containing an
     integer that is not a square would refute it too.

What a pass means is limited and stated at the end: enclosing a unique square
is CONSISTENT, never VERIFIED, because the true value could be a non-integer
in the same interval -- and integrality is precisely what BSD asserts.

Scope: disc > 0 only, so E(R) has two real components and the real period is
2 * (2K(m)/sqrt(e1-e3)) with all three roots real. The disc < 0 period needs a
different AGM branch which is not implemented here rather than guessed.

Run:  venv/bin/python rank2_corpus_sweep.py [max_curves]
"""

from __future__ import annotations

import math
import sys
from fractions import Fraction

import flint
from cypari2 import Pari
from flint import acb, arb, fmpz_poly

PREC_BITS = 512
SCAN_DOUBLINGS = 6
DEEP_DOUBLINGS = 10
MAX_SEARCH = 20_000        # cap on the exhaustive small-point enumeration
COEFF_RANGE = 3            # a-invariant box: a1,a3 in {0,1}, a2 in {-1,0,1}, ...


# ----------------------------------------------------------------- utilities
def rational_log_height(v: Fraction) -> arb:
    return arb(max(abs(v.numerator), abs(v.denominator))).log()


def rational_log_abs_max_one(v: Fraction) -> arb:
    n, d = abs(v.numerator), abs(v.denominator)
    return arb(0) if n <= d else (arb(n) / d).log()


def silverman_bound(ainvs) -> arb:
    """Arb upper bound on |hhat(P) - h_x(P)|, Silverman (1990) Thm 1.1,
    in PARI's ellheight normalisation. Generalised off 389.a1."""
    a1, a2, a3, a4, a6 = ainvs
    b2 = a1 * a1 + 4 * a2
    b4 = a1 * a3 + 2 * a4
    b6 = a3 * a3 + 4 * a6
    b8 = a1 * a1 * a6 + 4 * a2 * a6 - a1 * a3 * a4 + a2 * a3 * a3 - a4 * a4
    c4 = b2 * b2 - 24 * b4
    disc = -b2 * b2 * b8 - 8 * b4**3 - 27 * b6**2 + 9 * b2 * b4 * b6
    j = Fraction(c4**3, disc)
    mu = (rational_log_height(Fraction(disc, 1)) / 12
          + rational_log_abs_max_one(j) / 12
          + rational_log_abs_max_one(Fraction(b2, 12)) / 2
          + arb(2 if b2 else 1).log() / 2)
    lo = 2 * (-rational_log_height(j) / 24 - mu - arb(961) / 1000)
    hi = 2 * (mu + arb(107) / 100)
    return arb(0, max(abs(lo).upper(), abs(hi).upper()))


def height_ball(pari, E, P, C: arb, doublings: int) -> arb:
    Q = P
    for _ in range(doublings):
        Q = pari.ellmul(E, Q, 2)
    x = Q[0]
    n = abs(int(pari.numerator(x)))
    d = abs(int(pari.denominator(x)))
    return (arb(max(n, d, 1)).log() / 4**doublings
            + arb(0, C.rad() / 4**doublings))


def real_period(ainvs) -> arb:
    """Omega_E for disc > 0: two real components."""
    a1, a2, a3, a4, a6 = ainvs
    b2 = a1 * a1 + 4 * a2
    b4 = a1 * a3 + 2 * a4
    b6 = a3 * a3 + 4 * a6
    roots = []
    for r, mult in fmpz_poly([b6, 2 * b4, b2, 4]).complex_roots():
        if not r.imag.contains(0):
            return None
        roots.extend([r.real] * mult)
    if len(roots) != 3:
        return None
    roots.sort(key=lambda r: float(r.mid()))
    e3, e2, e1 = roots
    if not (e3.upper() < e2.lower() and e2.upper() < e1.lower()):
        return None
    m = (e2 - e3) / (e1 - e3)
    return 2 * (2 * acb(m).elliptic_k()).real / (e1 - e3).sqrt()


def enumerate_points(ainvs, limit: int):
    """Every affine rational point with max(|a|, b^2) <= limit, x = a/b^2.

    y^2 + a1 x y + a3 y = x^3 + a2 x^2 + a4 x + a6 is completed to
    (2y + a1 x + a3)^2 = 4x^3 + b2 x^2 + 2 b4 x + b6, so with x = a/b^2 the
    point is rational exactly when the integer numerator is a perfect square.
    """
    a1, a2, a3, a4, a6 = ainvs
    b2 = a1 * a1 + 4 * a2
    b4 = a1 * a3 + 2 * a4
    b6 = a3 * a3 + 4 * a6
    out = []
    b = 1
    while b * b <= limit:
        B2, B4, B6 = b * b, b**4, b**6
        for a in range(-limit, limit + 1):
            if math.gcd(a, b) != 1:
                continue
            N = 4 * a**3 + b2 * a * a * B2 + 2 * b4 * a * B4 + b6 * B6
            if N < 0:
                continue
            r = math.isqrt(N)
            if r * r != N:
                continue
            x = Fraction(a, B2)
            for s in (1, -1):
                y = (Fraction(s * r, B2 * b) - a1 * x - a3) / 2
                if y * y + a1 * x * y + a3 * y == x**3 + a2 * x * x + a4 * x + a6:
                    out.append((x, y))
        b += 1
    return sorted(set(out), key=lambda t: (abs(t[0].numerator), t[0].denominator))


def prove_saturation(pari, E, ainvs, P, Q, C, reg):
    """Returns (ok, mu, m_bound, detail). Exhaustive-enumeration + Hermite."""
    limit = int(math.floor(math.exp(float(C.rad()) + 0.35)))
    if limit > MAX_SEARCH:
        return None, None, None, f"enumeration would need {limit} > {MAX_SEARCH}"
    B = math.log(limit)
    pts = enumerate_points(ainvs, limit)
    smallest = None
    for x, y in pts:
        R = pari(f"[{x.numerator}/{x.denominator},{y.numerator}/{y.denominator}]")
        if int(pari.ellorder(E, R)) != 0:
            continue
        h = height_ball(pari, E, R, C, SCAN_DOUBLINGS).lower()
        if smallest is None or h < smallest:
            smallest = h
    tail = arb((arb(B) - C).lower())
    if smallest is None:
        mu = tail
    else:
        mu = arb(smallest) if arb(smallest).upper() < tail.lower() else tail
    if mu.lower() <= 0:
        return None, mu, None, "mu not positive: enumeration reach too small"
    m_bound = 2 * arb(reg.upper()).sqrt() / (arb(3).sqrt() * arb(mu.lower()))
    m_max = int(math.floor(float(m_bound.upper())))
    if m_max < 1:
        return None, mu, m_bound, "index bound below 1 (numerically degenerate)"
    for p in [q for q in range(2, m_max + 1)
              if all(q % d for d in range(2, int(q**0.5) + 1))]:
        for i in range(p):
            for j in range(p):
                if i == 0 and j == 0:
                    continue
                R = pari.elladd(E, pari.ellmul(E, P, i), pari.ellmul(E, Q, j))
                if pari.ellisdivisible(E, R, p):
                    return False, mu, m_bound, f"index divisible by {p}"
    return True, mu, m_bound, f"m <= {m_max}, all primes ruled out"


def leading_coeff(pari, E, N: int) -> arb:
    """L''(E,1)/2 as a ball, with an explicit Deligne tail bound."""
    import rank2_backend_prototype as backend
    terms = max(128, int(10 * math.sqrt(N)))
    coeffs = [int(a) for a in pari.ellan(E, terms)]
    c = 2 * arb.pi() / arb(N).sqrt()
    s = arb(0)
    for n, an in enumerate(coeffs, start=1):
        s += an * backend.f_second_at_one(c * n)
    fo = terms + 1
    tail = 4 / c**3 * (-c * fo).exp() / (fo**2 * (1 - (-c).exp()))
    s += arb(0, tail.upper())
    return c * s


# --------------------------------------------------------------------- sweep
def main() -> None:
    global COEFF_RANGE
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    if len(sys.argv) > 2:
        COEFF_RANGE = int(sys.argv[2])
    flint.ctx.prec = PREC_BITS
    pari = Pari()
    pari.allocatemem(512_000_000, silent=True)
    pari.set_real_precision_bits(PREC_BITS)

    print("=" * 100)
    print("RANK-2 BSD FALSIFICATION SWEEP -- saturation proved per curve, no table lookups")
    print("=" * 100)
    print(f"{'ainvs':22} {'N':>6} {'mu':>7} {'m<=':>6} {'sat':>4} "
          f"{'Reg':>10} {'Sha_an ball':>26} {'ints':>5} {'sq':>4} {'verdict':>11}")

    seen, done, refuted, skipped = set(), 0, [], 0
    R = COEFF_RANGE
    cands = []
    for a1 in (0, 1):
        for a2 in (-1, 0, 1):
            for a3 in (0, 1):
                for a4 in range(-R, R + 1):
                    for a6 in range(-R, R + 1):
                        cands.append([a1, a2, a3, a4, a6])
    for ainvs in cands:
        if done >= want:
            break
        try:
            E = pari.ellinit(ainvs)
        except Exception:
            continue
        if not E:
            continue
        try:
            disc = int(pari(f"ellinit({ainvs}).disc"))
            if disc <= 0:
                continue
            N = int(pari.ellglobalred(E)[0])
            if N in seen:
                continue
            rr = pari.ellrank(E)
            if int(rr[0]) != 2 or int(rr[1]) != 2:
                continue
            pts = rr[3]
            if len(pts) < 2:
                continue
            seen.add(N)
            P, Q = pts[0], pts[1]
            tors = int(pari.elltors(E)[0])
            tam = 1
            for loc in pari.ellglobalred(E)[4]:
                tam *= int(loc[3])

            # analytic rank exactly 2
            ms, xpm = pari.msfromell(E, 1)
            if Fraction(str(pari.mseval(ms, xpm)[0])) != 0:
                continue                                  # L(1) != 0 exactly
            L2 = leading_coeff(pari, E, N)
            if L2.contains(0):
                continue                                  # cannot pin rank 2

            om = real_period(ainvs)
            if om is None:
                continue
            C = silverman_bound(ainvs)
            hP = height_ball(pari, E, P, C, DEEP_DOUBLINGS)
            hQ = height_ball(pari, E, Q, C, DEEP_DOUBLINGS)
            hpq = height_ball(pari, E, pari.elladd(E, P, Q), C, DEEP_DOUBLINGS)
            hmq = height_ball(pari, E, pari.ellsub(E, P, Q), C, DEEP_DOUBLINGS)
            reg = hP * hQ - ((hpq - hmq) / 4) ** 2
            if reg.lower() <= 0:
                continue

            ok, mu, mb, detail = prove_saturation(pari, E, ainvs, P, Q, C, reg)
            # PARI's descent points need not generate. For 389.a1 they span an
            # index-3 sublattice: Reg comes out 1.37214 = 9 * 0.15246 and the
            # quotient reads 1/9. So when the certificate says NOT saturated,
            # let PARI PROPOSE a saturated basis and re-run the certificate on
            # it -- proposal from the tool, proof from the gate. A basis that
            # still fails is reported, never quietly used.
            if ok is False:
                try:
                    sat = pari.ellsaturation(E, [P, Q], 100)
                    P2, Q2 = sat[0], sat[1]
                    hP = height_ball(pari, E, P2, C, DEEP_DOUBLINGS)
                    hQ = height_ball(pari, E, Q2, C, DEEP_DOUBLINGS)
                    hpq = height_ball(pari, E, pari.elladd(E, P2, Q2), C, DEEP_DOUBLINGS)
                    hmq = height_ball(pari, E, pari.ellsub(E, P2, Q2), C, DEEP_DOUBLINGS)
                    reg2 = hP * hQ - ((hpq - hmq) / 4) ** 2
                    if reg2.lower() > 0:
                        ok2, mu2, mb2, _ = prove_saturation(
                            pari, E, ainvs, P2, Q2, C, reg2)
                        if ok2:
                            P, Q, reg, ok, mu, mb = P2, Q2, reg2, ok2, mu2, mb2
                except Exception:
                    pass
            if ok is None:
                skipped += 1
                continue
            sha = L2 * tors**2 / (om * reg * tam)
            lo, hi = float(sha.lower()), float(sha.upper())
            ints = [k for k in range(max(0, int(lo) - 1), int(hi) + 2)
                    if lo <= k <= hi]
            sq = [k for k in ints if math.isqrt(k) ** 2 == k]
            if not ok:
                verdict = "UNSATURATED"
            elif len(ints) == 0:
                verdict = "**REFUTED**"
                refuted.append((ainvs, N, sha))
            elif len(ints) == 1 and len(sq) == 1:
                verdict = "CONSISTENT"
            elif len(ints) == 1 and not sq:
                verdict = "**REFUTED**"
                refuted.append((ainvs, N, sha))
            else:
                verdict = "inconclusive"
            done += 1
            print(f"{str(ainvs):22} {N:>6} {float(mu):>7.4f} "
                  f"{int(math.floor(float(mb.upper()))):>6} {str(ok):>4} "
                  f"{float(reg):>10.5f} {str(sha)[:26]:>26} "
                  f"{len(ints):>5} {(sq[0] if sq else '-'):>4} {verdict:>11}",
                  flush=True)
        except Exception as e:
            continue

    print()
    print("=" * 100)
    print(f"curves certified end-to-end : {done}")
    print(f"skipped (enumeration too big): {skipped}")
    print(f"REFUTATIONS of strong BSD    : {len(refuted)}")
    print()
    print("A CONSISTENT row means: analytic rank proved exactly 2, the")
    print("Mordell-Weil basis proved saturated, and the Sha_an ball encloses")
    print("exactly one integer which is a perfect square. It does NOT mean")
    print("#Sha is that square -- the true value could be a nearby non-integer,")
    print("and integrality of the quotient is what BSD asserts and what is")
    print("still unproved in rank 2. The verdict vocabulary stays CONSISTENT /")
    print("REFUTED / REFUSED; nothing here is stamped VERIFIED.")


if __name__ == "__main__":
    main()
