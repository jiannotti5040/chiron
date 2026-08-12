#!/usr/bin/env python3
"""A self-contained saturation certificate for the rank-two basis of 389.a1.

This closes the gap `rank2_bsd_quotient_prototype.py` names in its own header:
it proves (0,0) and (1,0) are INDEPENDENT, but not that they GENERATE E(Q).
If L = <P,Q> sits at index m in the Mordell-Weil group then

    Reg(L) = m^2 * Reg(E(Q)),

so an unproved m multiplies the BSD quotient by m^2 and "Sha_an = 1" means
nothing: m = 2 alone would put the quotient at 4, which is also a square and
would read as an equally happy answer. The prototype sourced the basis from
PARI's elldata archive, which is provenance, not proof.

The argument needs no external table:

  1. C is Silverman's bound, |hhat(R) - h_x(R)| <= C for every R.
  2. Enumerate EVERY rational point with h_x <= B, exactly: with x = a/b^2 in
     lowest terms the point is rational precisely when
     N = 4a^3 + 4a^2 b^2 - 8a b^4 + b^6 is a perfect square. Anything NOT
     found therefore has h_x > B, hence hhat > B - C.
  3. mu = min(smallest hhat found, B - C) is then a proven lower bound on the
     canonical height of every non-torsion rational point.
  4. Hermite in rank 2 (gamma_2 = 2/sqrt 3) gives Reg(E(Q)) >= (mu/gamma_2)^2,
     and m^2 = Reg(L)/Reg(E(Q)), so  m <= 2 sqrt(Reg L) / (sqrt 3 * mu).
  5. If that is < 2 then m = 1 outright; otherwise each prime p <= m is ruled
     out exactly with ellisdivisible.

Every real quantity is an Arb ball and every rounding is taken in the
direction that weakens the conclusion.

Run:  ./venv/bin/python rank2_saturation.py
"""

from __future__ import annotations

import math
from fractions import Fraction

import flint
from cypari2 import Pari
from flint import arb

import rank2_backend_prototype as analytic
from rank2_bsd_quotient_prototype import (
    canonical_height_ball,
    real_period_ball,
    silverman_height_difference_bound,
)

SEARCH_H = 5000        # enumerate h_x <= log(SEARCH_H)
SCAN_DOUBLINGS = 6     # cheap scan heights; error is C/4^n


def scan_height_lower_bound(pari, curve, point, C: arb) -> arb:
    """Rigorous LOWER bound for hhat(point), cheaply."""
    multiple = point
    for _ in range(SCAN_DOUBLINGS):
        multiple = pari.ellmul(curve, multiple, 2)
    x = multiple[0]
    num = abs(int(pari.numerator(x)))
    den = abs(int(pari.denominator(x)))
    approx = arb(max(num, den, 1)).log() / 4**SCAN_DOUBLINGS
    return approx + arb(0, C.rad() / 4**SCAN_DOUBLINGS)


def enumerate_small_points(limit: int):
    """Every affine rational point with max(|a|, b^2) <= limit, x = a/b^2.

    On an integral Weierstrass model every rational point has x = a/b^2 and
    y = c/b^3 with gcd(a,b) = 1, so this sweep is exhaustive in range. Each
    hit is re-verified against the curve equation in exact rationals, so
    there are no false positives either.
    """
    found = set()
    b = 1
    while b * b <= limit:
        b2 = b * b
        b4 = b2 * b2
        b6 = b4 * b2
        for a in range(-limit, limit + 1):
            if math.gcd(a, b) != 1:
                continue
            N = 4 * a**3 + 4 * a * a * b2 - 8 * a * b4 + b6
            if N < 0:
                continue
            r = math.isqrt(N)
            if r * r != N:
                continue
            x = Fraction(a, b2)
            for sign in (1, -1):
                y = (Fraction(sign * r, b2 * b) - 1) / 2
                if y * y + y == x**3 + x * x - 2 * x:
                    found.add((x, y))
        b += 1
    return sorted(found, key=lambda t: (abs(t[0].numerator), t[0].denominator))


def pari_point(pari, x: Fraction, y: Fraction):
    return pari(f"[{x.numerator}/{x.denominator},{y.numerator}/{y.denominator}]")


def certify_saturation(pari, E, basis, C, mu, label, verbose=True):
    """Index bound + exact prime sieve for the lattice spanned by `basis`.

    Returns (saturated: bool, detail: str).
    """
    P, Q = basis
    hP = canonical_height_ball(pari, E, P, C)
    hQ = canonical_height_ball(pari, E, Q, C)
    hPQ = canonical_height_ball(pari, E, pari.elladd(E, P, Q), C)
    hPmQ = canonical_height_ball(pari, E, pari.ellsub(E, P, Q), C)
    pairing = (hPQ - hPmQ) / 4
    reg = hP * hQ - pairing**2
    if reg.lower() <= 0:
        return False, "basis is not independent (regulator ball contains 0)", reg

    m_bound = (2 * arb(reg.upper()).sqrt()
               / (arb(3).sqrt() * arb(mu.lower())))
    m_max = int(math.floor(float(m_bound.upper())))
    if verbose:
        print(f"  [{label}] Reg = {reg}")
        print(f"  [{label}] index bound m <= {float(m_bound.upper()):.6f} -> m <= {m_max}")

    if m_max < 2:
        if verbose:
            print(f"  [{label}] no prime index is possible; m = 1 directly")
        return True, "m = 1 from the height bound alone", reg

    primes = [p for p in range(2, m_max + 1)
              if all(p % d for d in range(2, int(p**0.5) + 1))]
    if verbose:
        print(f"  [{label}] primes still to rule out: {primes}")
    for p in primes:
        for a in range(p):
            for b in range(p):
                if a == 0 and b == 0:
                    continue
                R = pari.elladd(E, pari.ellmul(E, P, a), pari.ellmul(E, Q, b))
                if pari.ellisdivisible(E, R, p):
                    return (False,
                            f"{a}P+{b}Q is divisible by {p}: index is a multiple of {p}",
                            reg)
        if verbose:
            print(f"  [{label}] p={p}: no (a,b) mod p is p-divisible -> p-saturated")
    return True, f"every prime <= {m_max} ruled out exactly", reg


def main() -> None:
    flint.ctx.prec = analytic.PREC_BITS
    pari = Pari()
    pari.allocatemem(256_000_000, silent=True)
    pari.set_real_precision_bits(analytic.PREC_BITS)
    E = pari.ellinit(analytic.AINVS)

    print("=" * 74)
    print("SATURATION CERTIFICATE -- 389.a1, claimed basis P=(0,0) Q=(1,0)")
    print("=" * 74)

    # --- prerequisites the index argument genuinely needs -----------------
    rank_rec = pari.ellrank(E)
    rank_lo, rank_hi = int(rank_rec[0]), int(rank_rec[1])
    print(f"  2-descent rank interval          : [{rank_lo},{rank_hi}]")
    assert rank_lo == rank_hi == 2, (
        "the index argument compares two rank-2 lattices; without rank "
        "exactly 2 the comparison is meaningless")
    torsion = int(pari.elltors(E)[0])
    print(f"  torsion order (exact)            : {torsion}")
    assert torsion == 1, "the argument below assumes trivial torsion"

    C = silverman_height_difference_bound()
    print(f"  Silverman bound C                : {float(C.rad()):.6f}"
          f"   [Silverman 1990, Thm 1.1]")

    # --- step 2/3: exhaustive enumeration -> mu ---------------------------
    B = math.log(SEARCH_H)
    pts = enumerate_small_points(SEARCH_H)
    print(f"  enumeration reach                : h_x <= log {SEARCH_H} = {B:.6f}")
    print(f"  affine rational points found     : {len(pts)}")

    min_h, argmin = None, None
    for x, y in pts:
        R = pari_point(pari, x, y)
        if int(pari.ellorder(E, R)) != 0:
            continue                                   # torsion, excluded
        h_lo = scan_height_lower_bound(pari, E, R, C).lower()
        if min_h is None or h_lo < min_h:
            min_h, argmin = h_lo, (x, y)
    smallest = arb(min_h)
    tail_lo = arb((arb(B) - C).lower())     # unenumerated points exceed this
    mu = smallest if smallest.upper() < tail_lo.lower() else tail_lo
    print(f"  smallest hhat among them         : {float(smallest):.6f}"
          f"   at ({argmin[0]}, {argmin[1]})")
    print(f"  unenumerated points exceed B - C : {float(tail_lo):.6f}")
    print(f"  => mu, proven lower bound on hhat: {float(mu):.6f}")
    assert mu.lower() > 0

    P, Q = pari("[0,0]"), pari("[1,0]")

    # --- step 4/5: the certificate ----------------------------------------
    print()
    ok, detail, reg_L = certify_saturation(pari, E, (P, Q), C, mu, "claimed")
    print(f"  VERDICT: {'SATURATED' if ok else 'NOT SATURATED'} -- {detail}")
    assert ok

    # --- corroboration 1: every small point lies in <P,Q> -----------------
    outside = []
    for x, y in pts:
        R = pari_point(pari, x, y)
        hit = False
        for a in range(-6, 7):
            for b in range(-6, 7):
                cand = pari.elladd(E, pari.ellmul(E, P, a), pari.ellmul(E, Q, b))
                if str(cand) == str(R):
                    hit = True
                    break
            if hit:
                break
        if not hit:
            outside.append((x, y))
    print(f"  small points expressible in <P,Q>: {len(pts) - len(outside)}/{len(pts)}"
          f"   (|a|,|b| <= 6)")
    if outside:
        print(f"    NOT matched (widen the window, or a real problem): {outside[:4]}")

    # --- corroboration 2: PARI's own routine ------------------------------
    print(f"  PARI ellsaturation(...,100)      : {pari.ellsaturation(E, [P, Q], 100)}")

    # --- NEGATIVE CONTROL: a lattice we KNOW is index 2 -------------------
    print()
    print("=" * 74)
    print("NEGATIVE CONTROL -- the same machinery on <2P, Q>, index 2 by")
    print("construction. A certificate that cannot say no proves nothing.")
    print("=" * 74)
    twoP = pari.ellmul(E, P, 2)
    ok2, detail2, reg2 = certify_saturation(pari, E, (twoP, Q), C, mu, "control")
    print(f"  VERDICT: {'SATURATED' if ok2 else 'NOT SATURATED'} -- {detail2}")
    assert not ok2, "the control was NOT detected -- the certificate is vacuous"
    ratio = reg2 / reg_L
    print(f"  Reg(control)/Reg(claimed) = {ratio}  (expected exactly 4 = 2^2)")
    assert ratio.contains(4)

    # --- the quotient, no longer conditional on saturation ----------------
    coeffs = [int(a) for a in pari.ellan(E, analytic.TERMS)]
    c = 2 * arb.pi() / arb(analytic.CONDUCTOR).sqrt()
    s = arb(0)
    for n, a_n in enumerate(coeffs, start=1):
        s += a_n * analytic.f_second_at_one(c * n)
    fo = analytic.TERMS + 1
    s += arb(0, (4 / c**3 * (-c * fo).exp() / (fo**2 * (1 - (-c).exp()))).upper())
    leading = c * s
    omega = real_period_ball()
    tam = int(pari.ellglobalred(E)[2])
    sha = leading * torsion**2 / (omega * reg_L * tam)

    print()
    print("=" * 74)
    print("BSD QUOTIENT FOR 389.a1, SATURATION NOW PROVED")
    print("=" * 74)
    print(f"  L''(E,1)/2  = {leading}")
    print(f"  Omega       = {str(omega)[:60]}...")
    print(f"  Reg(E(Q))   = {reg_L}")
    print(f"  torsion     = {torsion}     Tamagawa = {tam}")
    print(f"  Sha_an      = {sha}")
    print(f"  contains 1  : {sha.contains(1)}")
    print(f"  excludes 4  : {not sha.contains(4)}   <- the index-2 alternative,")
    print(f"                now excluded by proof rather than by trusting a table")
    assert sha.contains(1) and not sha.contains(4)

    print()
    print("=" * 74)
    print("WHAT THIS DOES AND DOES NOT ESTABLISH")
    print("=" * 74)
    print("  Unconditional here (exact rational / interval arithmetic):")
    print("    - torsion, Tamagawa product, conductor, Fourier coefficients")
    print("    - exhaustive small-point enumeration, hence mu")
    print("    - the Hermite index bound and the ellisdivisible sieve")
    print("    - every real quantity as an outward-rounded Arb ball")
    print("  Theorem-dependent:")
    print("    - Silverman (1990) Thm 1.1 for C")
    print("    - modularity + the functional equation for the L-series")
    print("    - Hermite's constant gamma_2 = 2/sqrt(3)")
    print("  Trusted software (not replayed by an independent checker):")
    print("    - PARI's 2-descent for rank exactly 2, elltors, ellglobalred,")
    print("      ellisdivisible; FLINT/Arb outward rounding")
    print("  NOT established:")
    print("    - BSD for this curve. Sha_an enclosing the single square 1 does")
    print("      NOT prove #Sha = 1: the enclosure would also be satisfied by a")
    print("      nearby non-integer, and integrality of the quotient is exactly")
    print("      what BSD asserts and what remains unproved in rank 2.")


if __name__ == "__main__":
    main()
