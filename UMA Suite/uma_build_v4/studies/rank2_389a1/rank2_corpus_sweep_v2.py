#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Rank-2 BSD falsification sweep, v2 -- same certificate, far wider reach.

v1 ran a 2-descent on every candidate, which dominated the cost. Most curves
are rank 0 or 1 and can be discarded far more cheaply:

    disc > 0  ->  new conductor  ->  root number +1  ->  L(1) = 0 exactly
              ->  ONLY THEN the expensive ellrank

Root number is nearly free and halves the field; the exact rational modular
symbol then kills every rank-0 curve, because those have L(1) != 0. What
survives is already forced to have even analytic rank >= 2.

Results are appended to results.jsonl as they are produced, so an interrupted
run keeps everything it proved.

Verdicts and their meaning are unchanged from v1 -- see README.md. Nothing is
stamped VERIFIED; enclosing a unique square is CONSISTENT.

Run:  venv/bin/python rank2_corpus_sweep_v2.py [box_radius] [max_seconds]
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from fractions import Fraction

import flint
from cypari2 import Pari
from flint import arb

from rank2_corpus_sweep import (DEEP_DOUBLINGS, PREC_BITS, height_ball,
                                leading_coeff, prove_saturation, real_period,
                                silverman_bound)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.jsonl")


def main() -> None:
    radius = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 3600.0
    # Conductor cap. msfromell builds the modular symbol space of level N and
    # is NOT cheap once N reaches ~1e5, which is where a wide a-invariant box
    # lands. Capping N keeps the exact-symbol gate fast and makes the corpus
    # well defined: "every rank-2 curve of conductor <= cap found in this box".
    n_cap = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    t0 = time.time()

    flint.ctx.prec = PREC_BITS
    pari = Pari()
    pari.allocatemem(768_000_000, silent=True)
    pari.set_real_precision_bits(PREC_BITS)

    seen = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try:
                seen.add(json.loads(line)["N"])
            except Exception:
                pass

    done = refuted = unsat = skipped = 0
    tried = passed_cheap = 0
    print(f"{'ainvs':22} {'N':>7} {'mu':>7} {'m<=':>5} {'Reg':>10} "
          f"{'Sha_an':>24} {'ints':>5} {'sq':>4} {'verdict':>11}", flush=True)

    for a1 in (0, 1):
        for a2 in (-1, 0, 1):
            for a3 in (0, 1):
                for a4 in range(-radius, radius + 1):
                    for a6 in range(-radius, radius + 1):
                        if time.time() - t0 > budget:
                            print(f"\n[budget {budget:.0f}s reached]", flush=True)
                            _summary(done, refuted, unsat, skipped, tried,
                                     passed_cheap, time.time() - t0)
                            return
                        ainvs = [a1, a2, a3, a4, a6]
                        tried += 1
                        try:
                            E = pari.ellinit(ainvs)
                            if not E:
                                continue
                            if int(pari(f"ellinit({ainvs}).disc")) <= 0:
                                continue
                            N = int(pari.ellglobalred(E)[0])
                            if N in seen or N > n_cap:
                                continue
                            # --- cheap gates, in increasing cost -----------
                            if int(pari.ellrootno(E)) != 1:
                                continue
                            ms, xpm = pari.msfromell(E, 1)
                            if Fraction(str(pari.mseval(ms, xpm)[0])) != 0:
                                continue          # L(1) != 0 -> analytic rank 0
                            passed_cheap += 1
                            # --- expensive from here -----------------------
                            rr = pari.ellrank(E)
                            if int(rr[0]) != 2 or int(rr[1]) != 2:
                                continue
                            pts = rr[3]
                            if len(pts) < 2:
                                continue
                            seen.add(N)
                            P, Q = pts[0], pts[1]
                            L2 = leading_coeff(pari, E, N)
                            if L2.contains(0):
                                continue
                            om = real_period(ainvs)
                            if om is None:
                                continue
                            tors = int(pari.elltors(E)[0])
                            tam = 1
                            for loc in pari.ellglobalred(E)[4]:
                                tam *= int(loc[3])
                            C = silverman_bound(ainvs)

                            def reg_of(P, Q):
                                hP = height_ball(pari, E, P, C, DEEP_DOUBLINGS)
                                hQ = height_ball(pari, E, Q, C, DEEP_DOUBLINGS)
                                hpq = height_ball(pari, E, pari.elladd(E, P, Q),
                                                  C, DEEP_DOUBLINGS)
                                hmq = height_ball(pari, E, pari.ellsub(E, P, Q),
                                                  C, DEEP_DOUBLINGS)
                                return hP * hQ - ((hpq - hmq) / 4) ** 2

                            reg = reg_of(P, Q)
                            if reg.lower() <= 0:
                                continue
                            ok, mu, mb, _ = prove_saturation(pari, E, ainvs,
                                                             P, Q, C, reg)
                            if ok is False:
                                try:
                                    sat = pari.ellsaturation(E, [P, Q], 100)
                                    P2, Q2 = sat[0], sat[1]
                                    r2 = reg_of(P2, Q2)
                                    if r2.lower() > 0:
                                        o2, m2, b2, _ = prove_saturation(
                                            pari, E, ainvs, P2, Q2, C, r2)
                                        if o2:
                                            P, Q, reg, ok, mu, mb = (
                                                P2, Q2, r2, o2, m2, b2)
                                except Exception:
                                    pass
                            if ok is None:
                                skipped += 1
                                continue
                            sha = L2 * tors ** 2 / (om * reg * tam)
                            lo, hi = float(sha.lower()), float(sha.upper())
                            ints = [k for k in range(max(0, int(lo) - 1), int(hi) + 2)
                                    if lo <= k <= hi]
                            sq = [k for k in ints if math.isqrt(k) ** 2 == k]
                            if not ok:
                                verdict, unsat = "UNSATURATED", unsat + 1
                            elif len(ints) == 0 or (len(ints) == 1 and not sq):
                                verdict, refuted = "**REFUTED**", refuted + 1
                            elif len(ints) == 1:
                                verdict = "CONSISTENT"
                            else:
                                verdict = "inconclusive"
                            done += 1
                            row = {"ainvs": ainvs, "N": N, "mu": float(mu),
                                   "m_bound": float(mb.upper()),
                                   "saturated": bool(ok), "reg": float(reg),
                                   "sha_lo": lo, "sha_hi": hi,
                                   "n_integers": len(ints),
                                   "square": sq[0] if sq else None,
                                   "torsion": tors, "tamagawa": tam,
                                   "verdict": verdict}
                            with open(OUT, "a") as fh:
                                fh.write(json.dumps(row) + "\n")
                            print(f"{str(ainvs):22} {N:>7} {float(mu):>7.4f} "
                                  f"{int(math.floor(float(mb.upper()))):>5} "
                                  f"{float(reg):>10.5f} {str(sha)[:24]:>24} "
                                  f"{len(ints):>5} {(sq[0] if sq else '-'):>4} "
                                  f"{verdict:>11}", flush=True)
                        except Exception:
                            continue
    _summary(done, refuted, unsat, skipped, tried, passed_cheap,
             time.time() - t0)


def _summary(done, refuted, unsat, skipped, tried, cheap, elapsed):
    print()
    print("=" * 96)
    print(f"candidates examined         : {tried}")
    print(f"survived the cheap gates    : {cheap}   "
          f"(root number +1 and L(1)=0 exactly)")
    print(f"curves certified end-to-end : {done}")
    print(f"unsaturated after proposal  : {unsat}")
    print(f"skipped (enumeration too big): {skipped}")
    print(f"REFUTATIONS of strong BSD   : {refuted}")
    print(f"elapsed                     : {elapsed:.0f}s")
    print(f"rows appended to            : {OUT}")


if __name__ == "__main__":
    main()
