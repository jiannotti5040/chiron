#!/usr/bin/env python3
"""Conditional rank-two BSD quotient ball for 389.a1.

The leading coefficient, period, and height matrix are enclosed with Arb.
The final quotient is conditional only on the stated Mordell-Weil basis claim:
that (0,0) and (1,0) form a saturated Z-basis modulo torsion.  The script
checks independence but does not yet emit a self-contained saturation proof.
"""

from __future__ import annotations

from fractions import Fraction

import flint
from cypari2 import Pari
from flint import acb, arb, fmpz_poly

import rank2_backend_prototype as analytic


HEIGHT_DOUBLINGS = 10


def rational_log_height(value: Fraction) -> arb:
    return arb(max(abs(value.numerator), abs(value.denominator))).log()


def rational_ball(value: Fraction) -> arb:
    return arb(value.numerator) / value.denominator


def rational_log_abs_max_one(value: Fraction) -> arb:
    numerator = abs(value.numerator)
    denominator = abs(value.denominator)
    if numerator <= denominator:
        return arb(0)
    return (arb(numerator) / denominator).log()


def silverman_height_difference_bound() -> arb:
    """Rigorous Arb upper bound for Sage's Silverman/Bremner formula."""

    a1, a2, a3, a4, a6 = analytic.AINVS
    b2 = a1 * a1 + 4 * a2
    b4 = a1 * a3 + 2 * a4
    b6 = a3 * a3 + 4 * a6
    b8 = a1 * a1 * a6 + 4 * a2 * a6 - a1 * a3 * a4 + a2 * a3 * a3 - a4 * a4
    c4 = b2 * b2 - 24 * b4
    discriminant = -b2 * b2 * b8 - 8 * b4**3 - 27 * b6**2 + 9 * b2 * b4 * b6
    j = Fraction(c4**3, discriminant)
    b2_over_12 = Fraction(b2, 12)
    two_star = 2 if b2 else 1

    mu = (
        rational_log_height(Fraction(discriminant, 1)) / 12
        + rational_log_abs_max_one(j) / 12
        + rational_log_abs_max_one(b2_over_12) / 2
        + arb(two_star).log() / 2
    )
    lower = 2 * (-rational_log_height(j) / 24 - mu - rational_ball(Fraction(961, 1000)))
    upper = 2 * (mu + rational_ball(Fraction(107, 100)))
    lower_abs = abs(lower)
    upper_abs = abs(upper)
    if lower_abs.lower() > upper_abs.upper():
        bound = lower_abs
    elif upper_abs.lower() > lower_abs.upper():
        bound = upper_abs
    else:
        bound = lower_abs.union(upper_abs)
    return arb(0, bound.upper())


def canonical_height_ball(pari: Pari, curve, point, bound: arb) -> arb:
    """Enclose hhat(P) using h_x(2^n P)/4^n and Silverman's bound."""

    multiple = point
    for _ in range(HEIGHT_DOUBLINGS):
        multiple = pari.ellmul(curve, multiple, 2)
    x = multiple[0]
    numerator = abs(int(pari.numerator(x)))
    denominator = abs(int(pari.denominator(x)))
    approximation = arb(max(numerator, denominator)).log() / 4**HEIGHT_DOUBLINGS
    return approximation + arb(0, bound.rad() / 4**HEIGHT_DOUBLINGS)


def real_period_ball() -> arb:
    """Enclose the BSD real period (both real components) using AGM K."""

    a1, a2, a3, a4, a6 = analytic.AINVS
    b2 = a1 * a1 + 4 * a2
    b4 = a1 * a3 + 2 * a4
    b6 = a3 * a3 + 4 * a6
    # (2y+a1*x+a3)^2 = 4*x^3+b2*x^2+2*b4*x+b6.
    polynomial = fmpz_poly([b6, 2 * b4, b2, 4])
    roots = []
    for root, multiplicity in polynomial.complex_roots():
        assert root.imag.contains(0)
        roots.extend([root.real] * multiplicity)
    roots.sort(key=lambda root: float(root.mid()))
    e3, e2, e1 = roots
    assert e3.upper() < e2.lower() and e2.upper() < e1.lower()
    parameter = (e2 - e3) / (e1 - e3)
    connected_period = (2 * acb(parameter).elliptic_k()).real / (e1 - e3).sqrt()
    # discriminant 389 > 0, hence E(R) has two components.
    return 2 * connected_period


def main() -> None:
    flint.ctx.prec = analytic.PREC_BITS
    pari = Pari()
    pari.allocatemem(64_000_000, silent=True)
    pari.set_real_precision_bits(analytic.PREC_BITS)
    curve = pari.ellinit(analytic.AINVS)

    # Reuse the analytic proof stage directly.
    coefficients = [int(a) for a in pari.ellan(curve, analytic.TERMS)]
    c = 2 * arb.pi() / arb(analytic.CONDUCTOR).sqrt()
    completed_sum = arb(0)
    for n, a_n in enumerate(coefficients, start=1):
        completed_sum += a_n * analytic.f_second_at_one(c * n)
    first_omitted = analytic.TERMS + 1
    tail_completed = (
        4
        / c**3
        * (-c * first_omitted).exp()
        / (first_omitted**2 * (1 - (-c).exp()))
    )
    completed_sum += arb(0, tail_completed.upper())
    leading_coefficient = c * completed_sum

    point_p = pari("[0,0]")
    point_q = pari("[1,0]")
    point_plus = pari.elladd(curve, point_p, point_q)
    point_minus = pari.ellsub(curve, point_p, point_q)
    height_difference_bound = silverman_height_difference_bound()
    height_p = canonical_height_ball(pari, curve, point_p, height_difference_bound)
    height_q = canonical_height_ball(pari, curve, point_q, height_difference_bound)
    height_plus = canonical_height_ball(pari, curve, point_plus, height_difference_bound)
    height_minus = canonical_height_ball(pari, curve, point_minus, height_difference_bound)
    pairing_pq = (height_plus - height_minus) / 4
    regulator = height_p * height_q - pairing_pq**2

    real_period = real_period_ball()
    torsion_order = int(pari.elltors(curve)[0])
    tamagawa_product = int(pari.ellglobalred(curve)[2])
    sha_quotient = (
        leading_coefficient
        * torsion_order**2
        / (real_period * regulator * tamagawa_product)
    )

    print("RANK-TWO BSD QUOTIENT PROTOTYPE")
    print("basis_claim=[(0,0),(1,0)] (saturation externally sourced; not proved here)")
    print(f"height_difference_bound={height_difference_bound}")
    print(f"height_doublings={HEIGHT_DOUBLINGS}")
    print(f"height_P={height_p}")
    print(f"height_Q={height_q}")
    print(f"pairing_PQ={pairing_pq}")
    print(f"regulator_ball={regulator}")
    print(f"real_period_ball={real_period}")
    print(f"torsion_order={torsion_order}")
    print(f"tamagawa_product={tamagawa_product}")
    print(f"L_second_over_2_ball={leading_coefficient}")
    print(f"conditional_Sha_ball={sha_quotient}")
    print(f"conditional_Sha_contains_1={sha_quotient.contains(1)}")

    assert regulator.lower() > 0
    assert torsion_order == 1
    assert tamagawa_product == 1
    assert sha_quotient.contains(1)
    assert sha_quotient.lower() > rational_ball(Fraction(99, 100))
    assert sha_quotient.upper() < rational_ball(Fraction(101, 100))


if __name__ == "__main__":
    main()
