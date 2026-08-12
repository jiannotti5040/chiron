#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Exact, float-free analytic Sha for rank-0 curves, from modular symbols.

BSD_REPORT.md claimed that every published Sha_an -- LMFDB's included -- comes
from "dividing two floating-point numbers and rounding to the nearest
integer", and that uma/bsd was therefore the first procedure able to return
"no". This script refutes the mechanism claim directly rather than by citation.

    Sha_an = (L(1)/Omega_E) * #tors^2 / prod(c_p)

L(1)/Omega_+ is read off the exact rational modular symbol (PARI msfromell /
mseval), and torsion and the Tamagawa numbers are exact integers. No float and
no rounding appears anywhere, and a wrong value emerges NON-INTEGRAL rather
than rounding into agreement -- which is precisely the falsifiability the
report said did not exist.

Omega_E = n_c * Omega_+ with n_c = 2 when disc > 0 (E(R) has two components).
Getting that factor wrong is what makes 15.a1 and 37.b1 come out as 2 instead
of 1, and it is the normalisation caveat the audit flagged.

Run:  ../rank2_389a1/venv/bin/python exact_sha_modular_symbols.py
"""
from fractions import Fraction

from cypari2 import Pari

CURVES = (("11.a2",  [0, -1, 1, -10, -20],       1),
          ("15.a1",  [1, 1, 1, -2160, -39540],   1),
          ("37.b1",  [0, 1, 1, -1873, -31833],   1),
          ("571.b1", [0, -1, 1, -929, -10595],   4),
          ("389.a1", [0, 1, 1, -2, 0],        None))   # rank 2: L(1) = 0


def exact_sha(pari, ainvs):
    E = pari.ellinit(ainvs)
    ms, xpm = pari.msfromell(E, 1)
    L_over_omega_plus = Fraction(str(pari.mseval(ms, xpm)[0]))
    disc = int(pari(f"ellinit({ainvs}).disc"))
    n_c = 2 if disc > 0 else 1
    torsion = int(pari.elltors(E)[0])
    tamagawa = 1
    for local in pari.ellglobalred(E)[4]:
        tamagawa *= int(local[3])
    return (L_over_omega_plus * torsion ** 2 / (n_c * tamagawa),
            L_over_omega_plus, n_c, torsion, tamagawa)


def main():
    pari = Pari()
    pari.allocatemem(128_000_000, silent=True)
    print(f"{'curve':9} {'L/Om+':>7} {'n_c':>4} {'tors':>5} {'c_p':>4} "
          f"{'Sha_an':>7} {'integral':>9} {'known':>6} {'ok':>4}")
    ok_all = True
    for label, ainvs, known in CURVES:
        sha, lr, n_c, tors, tam = exact_sha(pari, ainvs)
        ok = known is None or sha == known
        ok_all &= ok
        print(f"{label:9} {str(lr):>7} {n_c:>4} {tors:>5} {tam:>4} {str(sha):>7} "
              f"{str(sha.denominator == 1):>9} "
              f"{('rank2' if known is None else known):>6} {'OK' if ok else 'NO':>4}")
    print()
    print(f"all rank-0 battery curves reproduced exactly: {ok_all}")
    assert ok_all


if __name__ == "__main__":
    main()
