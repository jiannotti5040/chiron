#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Hunt for a rank-2 curve with Sha_an > 1, then certify it exactly.

The sweep's stated weakness: all 103 certified curves enclose the square 1, so
a bug that forced the quotient to 1 would produce that table unchanged. The
fix is a curve whose answer is NOT 1, certified by the same pipeline.

Blind sweeping is a poor way to find one. Instead: a FAST FLOAT SCREEN over a
wide box proposes candidates (PARI's own approximate L''(1)/2, regulator and
period -- exactly the rounded-float route the report criticised, used here
only as a search heuristic and never as evidence), and any candidate whose
approximate quotient is far from 1 is then handed to the EXACT interval
certificate for a verdict.

Propose with floats, dispose with intervals. The float number is never
reported as a result.

Run:  venv/bin/python hunt_nontrivial_sha.py [radius] [n_cap] [seconds]
"""

from __future__ import annotations

import math
import sys
import time

import flint
from cypari2 import Pari
from flint import arb

from rank2_corpus_sweep import (DEEP_DOUBLINGS, PREC_BITS, height_ball,
                                leading_coeff, prove_saturation, real_period,
                                silverman_bound)


def float_screen(pari, E, ainvs):
    """PARI's own floating-point BSD quotient. Search heuristic only."""
    try:
        if int(pari.ellrootno(E)) != 1:
            return None
        rk = pari.ellanalyticrank(E)
        if int(rk[0]) != 2:
            return None
        # Calibrated against the exact path, which is the authority here:
        # for r = 2, ellanalyticrank's value is exactly 2x this module's
        # leading_coeff, i.e. it is L''(1) and the r! = 2 must be divided out.
        # Measured on 389.a1: 1.5186330005768536 vs 0.7593165002884268.
        # Likewise E.omega[1] is half Omega_E when disc > 0, handled below.
        L2 = float(rk[1]) / 2                 # -> L''(1)/2!
        if L2 <= 0:
            return None
        rr = pari.ellrank(E)
        if int(rr[0]) != 2 or int(rr[1]) != 2 or len(rr[3]) < 2:
            return None
        pts = pari.ellsaturation(E, [rr[3][0], rr[3][1]], 100)
        reg = float(pari.matdet(pari.ellheightmatrix(E, pts)))
        if reg <= 0:
            return None
        om = float(pari(f"ellinit({ainvs}).omega[1]"))
        disc = int(pari(f"ellinit({ainvs}).disc"))
        om_full = 2 * om if disc > 0 else om
        tors = int(pari.elltors(E)[0])
        tam = 1
        for loc in pari.ellglobalred(E)[4]:
            tam *= int(loc[3])
        return L2 * tors ** 2 / (om_full * reg * tam), pts, tors, tam
    except Exception:
        return None


def certify(pari, ainvs, E, pts, tors, tam):
    """The exact interval certificate. Returns (sha_ball, saturated, mu, mb)."""
    N = int(pari.ellglobalred(E)[0])
    L2 = leading_coeff(pari, E, N)
    if L2.contains(0):
        return None
    om = real_period(ainvs)
    if om is None:
        return None
    C = silverman_bound(ainvs)
    P, Q = pts[0], pts[1]
    hP = height_ball(pari, E, P, C, DEEP_DOUBLINGS)
    hQ = height_ball(pari, E, Q, C, DEEP_DOUBLINGS)
    hpq = height_ball(pari, E, pari.elladd(E, P, Q), C, DEEP_DOUBLINGS)
    hmq = height_ball(pari, E, pari.ellsub(E, P, Q), C, DEEP_DOUBLINGS)
    reg = hP * hQ - ((hpq - hmq) / 4) ** 2
    if reg.lower() <= 0:
        return None
    ok, mu, mb, _ = prove_saturation(pari, E, ainvs, P, Q, C, reg)
    sha = L2 * tors ** 2 / (om * reg * tam)
    return sha, ok, mu, mb, reg, N


def main() -> None:
    radius = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    n_cap = int(sys.argv[2]) if len(sys.argv) > 2 else 60_000
    budget = float(sys.argv[3]) if len(sys.argv) > 3 else 1800.0
    t0 = time.time()

    flint.ctx.prec = PREC_BITS
    pari = Pari()
    pari.allocatemem(768_000_000, silent=True)
    pari.set_real_precision_bits(PREC_BITS)

    print("Screening with floats (heuristic), certifying with intervals.")
    print(f"{'ainvs':22} {'N':>7} {'float Sha':>10} {'exact Sha_an':>26} "
          f"{'sat':>5} {'verdict':>12}")
    seen, hits, screened = set(), 0, 0
    for a1 in (0, 1):
        for a2 in (-1, 0, 1):
            for a3 in (0, 1):
                for a4 in range(-radius, radius + 1):
                    for a6 in range(-radius, radius + 1):
                        if time.time() - t0 > budget:
                            print(f"\n[budget reached] screened {screened}, "
                                  f"non-trivial found {hits}")
                            return
                        ainvs = [a1, a2, a3, a4, a6]
                        try:
                            E = pari.ellinit(ainvs)
                            if not E:
                                continue
                            if int(pari(f"ellinit({ainvs}).disc")) <= 0:
                                continue
                            N = int(pari.ellglobalred(E)[0])
                            if N in seen or N > n_cap:
                                continue
                            seen.add(N)
                            res = float_screen(pari, E, ainvs)
                            if res is None:
                                continue
                            screened += 1
                            approx, pts, tors, tam = res
                            if approx < 1.6:          # only chase non-trivial
                                continue
                            got = certify(pari, ainvs, E, pts, tors, tam)
                            if got is None:
                                continue
                            sha, ok, mu, mb, reg, N = got
                            lo, hi = float(sha.lower()), float(sha.upper())
                            ints = [k for k in range(max(0, int(lo) - 1),
                                                     int(hi) + 2) if lo <= k <= hi]
                            sq = [k for k in ints
                                  if math.isqrt(k) ** 2 == k]
                            if not ok:
                                v = "UNSATURATED"
                            elif len(ints) == 1 and sq:
                                v = f"CONSISTENT({sq[0]})"
                            elif len(ints) == 0 or (len(ints) == 1 and not sq):
                                v = "**REFUTED**"
                            else:
                                v = "inconclusive"
                            hits += 1
                            print(f"{str(ainvs):22} {N:>7} {approx:>10.4f} "
                                  f"{str(sha)[:26]:>26} {str(ok):>5} {v:>12}",
                                  flush=True)
                        except Exception:
                            continue
    print(f"\nscreened {screened} rank-2 curves, non-trivial candidates {hits}")


if __name__ == "__main__":
    main()
