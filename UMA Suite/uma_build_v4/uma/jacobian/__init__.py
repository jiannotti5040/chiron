# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
uma.jacobian — exact verification of the 2026 Jacobian-conjecture counterexample.

WHAT THIS MODULE IS. On 2026-07-20 Levent Alpöge announced (X thread,
Claude-Fable-5-assisted) an explicit polynomial map C³ → C³ with constant
nonzero Jacobian determinant that is NOT injective — a counterexample to
the Jacobian conjecture in its det-nonzero-constant formulation for n = 3
(and, by adjoining identity coordinates, all n ≥ 3; n = 2 remains open).
The explicit polynomials verified here are as transcribed by Oliver Knill
(Harvard, quantumcalculus.org, 2026-07-20), who published Mathematica
verification code alongside them.

WHAT THIS MODULE PROVES — and all it proves. In exact rational arithmetic
(Fractions; no floats, no numerics, no external CAS), it verifies two
claims about the explicit map F = (u, v, w):

  1. det J(F) = −2 as a POLYNOMIAL IDENTITY — the symbolic determinant of
     the 3×3 Jacobian collapses to the constant −2; every non-constant
     coefficient cancels exactly.
  2. F(0, 0, −1/4) = F(1, −3/2, 13/2) = (−1/4, 0, 0) — two distinct
     rational points with exactly equal images.

(1) says F satisfies the conjecture's hypothesis; (2) says F is not
injective, hence not an automorphism. Together they refute the implication
for this map. This module does NOT verify: the provenance of the
construction, the n = 2 case, peer-reviewed status (there is none as of
2026-07-21), or any claim beyond the arithmetic of the map as stated.
Epistemic status per vault convention: the verification machinery and the
two claims above are implemented-and-tested; the surrounding history is
reported, not certified.

The polynomial engine is deliberately tiny, dependency-free, and exact:
sparse exponent-dict polynomials over Q. It exists so this result is
checked by the vault's own arithmetic rather than cited on faith.

    from uma.jacobian import verify_counterexample
    cert = verify_counterexample()
    assert cert["refutes_implication"]

    python3 -m uma.jacobian          # print the certificate
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, Tuple

Poly = Dict[Tuple[int, int, int], Fraction]

ANNOUNCED = "2026-07-20"
ANNOUNCER = "Levent Alpöge (X thread; construction attributed to Claude Fable 5)"
TRANSCRIPTION = ("Oliver Knill, quantumcalculus.org/jacobian-conjecture-solution/ "
                 "(2026-07-20, with Mathematica verification code)")
STATUS = ("announced + independently arithmetic-checked; NOT peer-reviewed "
          "as of 2026-07-21; n = 2 remains open")


# ── exact sparse polynomial arithmetic over Q ────────────────────────────

def pmul(a: Poly, b: Poly) -> Poly:
    out: Poly = {}
    for ea, ca in a.items():
        for eb, cb in b.items():
            e = (ea[0] + eb[0], ea[1] + eb[1], ea[2] + eb[2])
            out[e] = out.get(e, Fraction(0)) + ca * cb
    return {e: c for e, c in out.items() if c != 0}


def padd(*ps: Poly) -> Poly:
    out: Poly = {}
    for p in ps:
        for e, c in p.items():
            out[e] = out.get(e, Fraction(0)) + c
    return {e: c for e, c in out.items() if c != 0}


def pscale(p: Poly, k) -> Poly:
    k = Fraction(k)
    return {e: c * k for e, c in p.items() if c * k != 0}


def ppow(p: Poly, n: int) -> Poly:
    r: Poly = {(0, 0, 0): Fraction(1)}
    for _ in range(n):
        r = pmul(r, p)
    return r


def pdiff(p: Poly, var: int) -> Poly:
    out: Poly = {}
    for e, c in p.items():
        if e[var] > 0:
            e2 = list(e)
            e2[var] -= 1
            out[tuple(e2)] = out.get(tuple(e2), Fraction(0)) + c * e[var]
    return {e: c for e, c in out.items() if c != 0}


def peval(p: Poly, pt) -> Fraction:
    s = Fraction(0)
    for (ex, ey, ez), c in p.items():
        s += c * pt[0] ** ex * pt[1] ** ey * pt[2] ** ez
    return s


def det3(m) -> Poly:
    """Symbolic determinant of a 3×3 polynomial matrix (cofactor expansion)."""
    return padd(
        pmul(m[0][0], padd(pmul(m[1][1], m[2][2]), pscale(pmul(m[1][2], m[2][1]), -1))),
        pscale(pmul(m[0][1], padd(pmul(m[1][0], m[2][2]), pscale(pmul(m[1][2], m[2][0]), -1))), -1),
        pmul(m[0][2], padd(pmul(m[1][0], m[2][1]), pscale(pmul(m[1][1], m[2][0]), -1))),
    )


def jacobian_det(F) -> Poly:
    """Symbolic det of the Jacobian of a polynomial map F = (u, v, w)."""
    return det3([[pdiff(f, i) for i in range(3)] for f in F])


# ── the map, exactly as transcribed ──────────────────────────────────────
X: Poly = {(1, 0, 0): Fraction(1)}
Y: Poly = {(0, 1, 0): Fraction(1)}
Z: Poly = {(0, 0, 1): Fraction(1)}
ONE: Poly = {(0, 0, 0): Fraction(1)}
_XY = pmul(X, Y)
_1XY = padd(ONE, _XY)                                   # 1 + xy
_4_3XY = padd(pscale(ONE, 4), pscale(_XY, 3))           # 4 + 3xy


def counterexample_map() -> Tuple[Poly, Poly, Poly]:
    """The Alpöge map (Knill transcription):
       u = (1+xy)^3 z + y^2 (1+xy)(4+3xy)
       v = y + 3x(1+xy)^2 z + 3x y^2 (4+3xy)
       w = 2x − 3x^2 y − x^3 z
    """
    u = padd(pmul(ppow(_1XY, 3), Z),
             pmul(pmul(ppow(Y, 2), _1XY), _4_3XY))
    v = padd(Y,
             pscale(pmul(pmul(X, ppow(_1XY, 2)), Z), 3),
             pscale(pmul(pmul(X, ppow(Y, 2)), _4_3XY), 3))
    w = padd(pscale(X, 2),
             pscale(pmul(ppow(X, 2), Y), -3),
             pscale(pmul(ppow(X, 3), Z), -1))
    return u, v, w


# the announced collision: two distinct rational points, one image
P1 = (Fraction(0), Fraction(0), Fraction(-1, 4))
P2 = (Fraction(1), Fraction(-3, 2), Fraction(13, 2))


def verify_counterexample() -> Dict:
    """Exactly check both claims; return an honest certificate dict.

    Never asserts more than the arithmetic shows. If either claim failed,
    the certificate would say so — there is no code path that reports a
    refutation without both exact checks passing.
    """
    F = counterexample_map()
    det = jacobian_det(F)
    det_is_minus_2 = det == {(0, 0, 0): Fraction(-2)}

    img1 = tuple(peval(f, P1) for f in F)
    img2 = tuple(peval(f, P2) for f in F)
    collision = (P1 != P2) and (img1 == img2)

    return {
        "schema": "uma.jacobian/1",
        "map": {
            "u": "(1+xy)^3 z + y^2 (1+xy)(4+3xy)",
            "v": "y + 3x(1+xy)^2 z + 3x y^2 (4+3xy)",
            "w": "2x - 3x^2 y - x^3 z",
        },
        "claim_1_det_identity": {
            "statement": "det J(F) = -2 as a polynomial identity",
            "verified": det_is_minus_2,
            "method": "symbolic cofactor determinant over Q; exact cancellation",
        },
        "claim_2_collision": {
            "statement": "F(0,0,-1/4) = F(1,-3/2,13/2), distinct points",
            "verified": collision,
            "image": [str(v) for v in img1],
            "method": "exact Fraction evaluation",
        },
        "refutes_implication": det_is_minus_2 and collision,
        "scope": ("constant nonzero Jacobian determinant does NOT imply "
                  "injectivity for polynomial maps in dimension 3; via "
                  "identity coordinates the failure extends to all n >= 3; "
                  "n = 2 is untouched by this map"),
        "announced": ANNOUNCED,
        "announcer": ANNOUNCER,
        "transcription": TRANSCRIPTION,
        "status": STATUS,
        "caveat": ("this certificate verifies the arithmetic of the stated "
                   "map only — not the announcement's provenance, not the "
                   "n = 2 case, and not community acceptance"),
    }


# ── controls: the machinery must discriminate, not just agree ────────────

def keller_control() -> Poly:
    """A known elementary automorphism (x + y^2, y, z): det J must be
    exactly 1. Positive control for the determinant machinery."""
    return jacobian_det((padd(X, ppow(Y, 2)), Y, Z))


def mutated_control() -> Poly:
    """The counterexample with one coefficient perturbed (w's 2x -> 3x):
    det J must NOT be constant. Discrimination control — the identity in
    claim 1 is a knife-edge cancellation, not an artifact."""
    u, v, _ = counterexample_map()
    w_bad = padd(pscale(X, 3),
                 pscale(pmul(ppow(X, 2), Y), -3),
                 pscale(pmul(ppow(X, 3), Z), -1))
    return jacobian_det((u, v, w_bad))


def main() -> int:
    import json
    cert = verify_counterexample()
    print(json.dumps(cert, indent=2, default=str))
    return 0 if cert["refutes_implication"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
