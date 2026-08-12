#!/usr/bin/env python3
"""Minimal exact-plus-ball backend for the rank-two curve 389.a1.

This is a research prototype, not a universal BSD prover.  PARI supplies
integer/rational arithmetic (descent, modular symbols, Fourier coefficients),
and python-flint/Arb supplies outward-rounded real balls for the central
second derivative.  The analytic tail bound is printed as part of the
certificate so the numerical/non-numerical boundary is inspectable.
"""

from __future__ import annotations

from importlib.metadata import version

import flint
from cypari2 import Pari
from flint import arb


AINVS = [0, 1, 1, -2, 0]
CONDUCTOR = 389
TERMS = 128
SERIES_TERMS = 257  # k = 0, ..., 256
PREC_BITS = 512


def f_second_at_one(x: arb) -> arb:
    r"""Enclose d^2/ds^2 (x^-s Gamma(s,x)) at s=1.

    We use

      F''(1) = ((EulerGamma + log(x))^2 + pi^2/6)/x
               - 2 sum_{k>=0} (-x)^k / (k! (k+1)^3).

    The series is truncated only after its terms decrease.  Its alternating
    remainder is enclosed by the first omitted term.
    """

    main = ((arb.const_euler() + x.log()) ** 2 + arb.pi() ** 2 / 6) / x

    term = arb(1)  # k = 0
    series = term
    last_k = SERIES_TERMS - 1
    for k in range(last_k):
        term *= -x * (k + 1) ** 2 / (k + 2) ** 3
        series += term

    next_term = term * -x * (last_k + 1) ** 2 / (last_k + 2) ** 3
    # Sufficient condition that all subsequent magnitudes decrease.
    assert x.upper() < arb(last_k + 2)
    remainder_radius = 2 * abs(next_term).upper()
    return main - 2 * series + arb(0, remainder_radius)


def main() -> None:
    flint.ctx.prec = PREC_BITS
    pari = Pari()
    pari.set_real_precision_bits(PREC_BITS)

    curve = pari.ellinit(AINVS)
    global_reduction = pari.ellglobalred(curve)
    conductor = int(global_reduction[0])
    root_number = int(pari.ellrootno(curve))

    # PARI's 2-descent returns unconditional lower/upper rank bounds.
    rank_record = pari.ellrank(curve)
    rank_lower = int(rank_record[0])
    rank_upper = int(rank_record[1])

    # x^+([0]-[infinity]) = L(E,1) / Omega^+ exactly in Q.
    modular_symbol_data = pari.msfromell(curve, 1)
    modular_symbol_space = modular_symbol_data[0]
    plus_symbol = modular_symbol_data[1]
    central_symbol = pari.mseval(
        modular_symbol_space, plus_symbol, pari("[oo,0]")
    )

    coefficients = [int(a) for a in pari.ellan(curve, TERMS)]
    c = 2 * arb.pi() / arb(conductor).sqrt()
    completed_sum = arb(0)
    for n, a_n in enumerate(coefficients, start=1):
        completed_sum += a_n * f_second_at_one(c * n)

    # Deligne: |a_n| <= d(n)*sqrt(n), and d(n) <= 2*sqrt(n).
    # Also F''(1,x) <= 2*exp(-x)/x^3.  Therefore the omitted
    # completed-series tail is at most the following geometric majorant.
    first_omitted = TERMS + 1
    tail_completed = (
        4
        / c**3
        * (-c * first_omitted).exp()
        / (first_omitted**2 * (1 - (-c).exp()))
    )
    completed_sum += arb(0, tail_completed.upper())

    # Lambda''(1) = 2*sum a_n F_n''(1), and when L(1)=L'(1)=0,
    # L''(1)/2 = (2*pi/sqrt(N))*sum a_n F_n''(1).
    leading_coefficient = c * completed_sum

    pari_analytic = pari.ellanalyticrank(curve)
    pari_derivative_over_factorial = pari_analytic[1] / 2

    print("RANK-TWO BACKEND PROTOTYPE")
    print(f"curve_ainvs={AINVS}")
    print(f"python-flint={version('python-flint')} FLINT={flint.__FLINT_VERSION__}")
    print(f"cypari2={version('cypari2')} embedded_PARI={pari('version()')}")
    print(f"precision_bits={PREC_BITS} q_terms={TERMS} local_series_terms={SERIES_TERMS}")
    print(f"conductor={conductor} expected={CONDUCTOR}")
    print(f"root_number={root_number}")
    print(f"descent_rank_interval=[{rank_lower},{rank_upper}]")
    print(f"descent_points={rank_record[3]}")
    print(f"central_modular_symbol={central_symbol} (exact rational)")
    print(f"completed_tail_bound={tail_completed}")
    print(f"L_second_over_2_ball={leading_coefficient}")
    print(f"L_second_over_2_excludes_zero={not leading_coefficient.contains(0)}")
    print(f"PARI_heuristic_analytic_rank={pari_analytic[0]}")
    print(f"PARI_numerical_L_second={pari_analytic[1]}")
    print(f"PARI_numerical_L_second_over_2={pari_derivative_over_factorial}")

    assert conductor == CONDUCTOR
    assert root_number == 1
    assert rank_lower == rank_upper == 2
    assert central_symbol == 0
    assert not leading_coefficient.contains(0)


if __name__ == "__main__":
    main()
