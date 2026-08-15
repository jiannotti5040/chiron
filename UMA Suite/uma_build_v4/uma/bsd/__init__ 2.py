# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
uma.bsd — the Birch--Swinnerton-Dyer prediction, pinned exactly or refused.

WHAT THIS MODULE IS FOR. BSD is a Millennium Problem and nothing here proves
it. But BSD is unusual among the seven: it has *finite refutable content*. For
a single elliptic curve E/Q of analytic rank 0, the strong form of the
conjecture asserts

        Sha_an(E) := L(E,1) * |E(Q)_tors|^2 / (Omega_E * prod_p c_p)

is the order of the Tate-Shafarevich group. Two consequences of that sentence
are checkable on one curve, in finite time:

    (i)  Sha_an(E) is a positive INTEGER;
    (ii) it is a perfect SQUARE, because the Cassels-Tate pairing on a finite
         Sha is alternating and non-degenerate.

Either failing on any single curve refutes BSD outright. That is the shape of
obligation the vault's own conjecture triage exists to find -- and BSD is
absent from all 3,195 statements it classified. This module closes that gap.

WHY EXACTNESS IS THE WHOLE POINT. L(E,1) and Omega_E are transcendental-looking
reals; their RATIO is asserted rational. Every published value of Sha_an --
LMFDB's included -- is a float quotient rounded to the nearest integer. The
rounding is exactly where the falsification test is destroyed: it maps a
hypothetical 3.9999 and a lawful 4.0000 to the same answer, so a genuine
counterexample would be silently rounded into agreement. No amount of extra
precision fixes this, because rounding-to-nearest is not a proof at any
precision.

Here, instead, L(1) and Omega are computed as INTERVALS with dyadic rational
endpoints and outward rounding (uma.bsd.rig), so the quotient is an interval
that provably contains the true value. Then:

    * the interval contains no positive integer      -> BSD REFUTED
    * it contains integers but no perfect square     -> BSD REFUTED
    * it contains exactly one integer, and it is m^2 -> CONSISTENT, pinned m^2
    * it contains several integers                   -> REFUSED (raise PREC)

Nothing is ever rounded to a nearest value, and "consistent" is never written
up as "verified": pinning Sha_an for one curve is not a proof of BSD for that
curve, only an exact statement of what BSD predicts there.

DOMAIN. Semistable E/Q in a minimal model with root number +1 and an L(1)
enclosure provably bounded away from zero (hence analytic rank exactly 0).
Everything outside is refused; see uma.bsd.curve for why each boundary is
where it is.

    from uma.bsd import bsd_certificate
    cert = bsd_certificate((0, -1, 1, -929, -10595))    # 571.b1
    cert["verdict"], cert["sha_analytic"]                # CONSISTENT, 4

    python3 -m uma.bsd                                   # certificates as JSON
"""
from __future__ import annotations

from fractions import Fraction
from math import isqrt
from typing import Dict, Optional, Sequence

from .curve import Curve, Refuse, SPLIT, NONSPLIT, GOOD, ADDITIVE
from . import rig
from .rig import Iv

CONSISTENT, REFUTED, REFUSED = "CONSISTENT", "REFUTED", "REFUSED"

__all__ = ["Curve", "Refuse", "bsd_certificate", "real_period", "l_value_at_1",
           "sha_analytic_interval", "CONSISTENT", "REFUTED", "REFUSED"]


# ── the real period ──────────────────────────────────────────────────────

def real_period(E: Curve) -> Iv:
    """Omega_E = integral over E(R) of |dx / (2y + a1 x + a3)|, as an enclosure.

    Derivation, uniform in the sign of the discriminant. Completing the square
    gives Y^2 = h(x) = 4x^3 + b2 x^2 + 2 b4 x + b6 with Y = 2y + a1 x + a3, so
    the integrand is dx/Y. Let e1 be the largest real root of h. Substituting
    x = e1 + 1/u^2 on the unbounded branch turns

        2 * int_{e1}^{inf} dx / sqrt(h(x))

    into 2 * int_0^inf du / sqrt(1 + P u^2 + Q u^4), with

        P = 3 e1 + b2/4,      Q = h'(e1)/4 = 3 e1^2 + (b2 e1 + b4)/2,

    and Q > 0 in both cases -- Q = (e1-e2)(e1-e3) is a product of positives
    when the roots are real and equals |e1 - e2|^2 when e2, e3 are conjugate.
    Then u -> 1/t and Gauss's lemniscatic substitution w = t - sqrt(Q)/t give

        int_0^inf dt / sqrt(t^4 + P t^2 + Q) = pi / AGM(2 Q^(1/4),
                                                        sqrt(2 sqrt(Q) + P)),

    valid for BOTH signs of the discriminant, which is why no complex AGM is
    needed anywhere. Finally E(R) has two components exactly when Delta > 0,
    and the two components have equal period, so Omega doubles there.

    The one input that is not a rational is e1, and it enters only as a
    bisection bracket whose every sign test is exact integer arithmetic.
    """
    h = [4, E.b2, 2 * E.b4, E.b6]
    e1 = rig.largest_real_root(h)
    P = e1.scale_int(3) + Iv.exact(Fraction(E.b2, 4))
    Q = (e1 * e1).scale_int(3) + (e1.scale_int(E.b2) + Iv.exact(E.b4)) / Iv.exact(2)
    if not Q.is_positive():
        raise Refuse("Q not provably positive -- period enclosure refused")
    sQ = Q.sqrt()
    A = sQ.sqrt().scale_int(2)
    Barg = sQ.scale_int(2) + P
    if not Barg.is_positive():
        raise Refuse("2 sqrt(Q) + P not provably positive -- period refused")
    B = Barg.sqrt()
    omega_inf = (rig.PI / rig.agm(A, B)).scale_int(2)
    return omega_inf.scale_int(2) if E.disc > 0 else omega_inf


# ── the L-value ──────────────────────────────────────────────────────────

def l_value_at_1(E: Curve, terms: Optional[int] = None) -> Iv:
    """L(E, 1) as an enclosure, for a semistable curve with root number +1.

    From Lambda(s) = (sqrt(N)/2pi)^s Gamma(s) L(s) and Lambda(s) = eps
    Lambda(2-s), splitting the Mellin integral at y = 1 gives

        L(E,1) = (1 + eps) * sum_{n>=1} (a_n / n) exp(-2 pi n / sqrt(N)).

    The tail is bounded rigorously rather than assumed negligible:
    |a_n| <= d(n) sqrt(n) <= 2 n, so |a_n / n| <= 2 and the tail after T terms
    is at most 2 * sum_{n>T} 2 q^n = 4 q^(T+1) / (1 - q) with q = e^(-2pi/sqrt N).
    That bound is added to the interval on BOTH sides, so the result contains
    L(E,1) unconditionally on the truncation.
    """
    E.require_semistable()
    if E.root_number() != 1:
        raise Refuse("root number is -1: L(E,1) = 0 and Sha_an is not defined by this formula")
    N = E.conductor()
    sqrtN = Iv.exact(N).sqrt()
    c = rig.PI.scale_int(2) / sqrtN                 # 2 pi / sqrt(N)
    q = rig.exp_neg(c)
    if terms is None:
        # Choose T so the tail bound sits far below any plausible pinning need.
        # q = exp(-2 pi / sqrt N), so q^T < 10^-60 as soon as
        # T > 60 ln(10) sqrt(N) / (2 pi) ~= 21.99 sqrt(N). Computed in integers:
        # iterating a Fraction here would double its denominator every step.
        terms = 22 * isqrt(N) + 64
    a = E.an_upto(terms)
    total = Iv.zero()
    qn = Iv.exact(1)
    for n in range(1, terms + 1):
        qn = qn * q
        if a[n]:
            total = total + (qn.scale_int(a[n]) / Iv.exact(n))
    tail = (qn * q).scale_int(4) / (Iv.exact(1) - q)
    if tail.lo < 0:
        raise Refuse("tail bound not provably positive")
    body = total.scale_int(2)
    slack = tail.hi
    return Iv(body.lo - slack, body.hi + slack)


# ── the prediction ───────────────────────────────────────────────────────

def sha_analytic_interval(E: Curve, torsion: Optional[int] = None,
                          tamagawa: Optional[int] = None) -> Dict:
    """The BSD-predicted |Sha| as an interval, with its exact ingredients.

    torsion / tamagawa may be supplied. They are then CROSS-CHECKED against
    what this module computes: agreement is recorded, disagreement is a
    refusal. A supplied value never overrides a computed one."""
    E.require_semistable()
    minimality = E.certify_minimal()
    N = E.conductor()
    eps = E.root_number()
    if eps != 1:
        raise Refuse("root number is -1: analytic rank is odd, L(E,1) = 0, "
                     "and this module's rank-0 formula does not apply")
    t_comp = E.torsion_order()
    c_comp = E.tamagawa_product()
    if torsion is not None and torsion != t_comp:
        raise Refuse(f"torsion disagreement: computed {t_comp}, supplied {torsion}")
    if tamagawa is not None and tamagawa != c_comp:
        raise Refuse(f"Tamagawa disagreement: computed {c_comp}, supplied {tamagawa}")
    omega = real_period(E)
    L1 = l_value_at_1(E)
    if not L1.is_positive():
        raise Refuse("L(E,1) enclosure is not provably nonzero: analytic rank not proven 0")
    sha = (L1.scale_int(t_comp * t_comp)) / (omega.scale_int(c_comp))
    return {
        "conductor": N,
        "discriminant": E.disc,
        "minimality_proof": {str(k): v for k, v in minimality.items()},
        "reduction": {str(p): E.reduction_type(p) for p in E.bad_primes()},
        "root_number": eps,
        "torsion_order": t_comp,
        "tamagawa_product": c_comp,
        "omega": omega,
        "L1": L1,
        "sha_interval": sha,
    }


def bsd_certificate(ainvs: Sequence[int], torsion: Optional[int] = None,
                    tamagawa: Optional[int] = None, label: str = "") -> Dict:
    """The full verdict for one curve. Never asserts more than was proven."""
    cert: Dict = {"schema": "uma.bsd/1", "label": label, "ainvs": list(ainvs)}
    try:
        E = Curve(tuple(ainvs))
        d = sha_analytic_interval(E, torsion, tamagawa)
    except Refuse as e:
        cert.update(verdict=REFUSED, reason=str(e))
        return cert
    except (ValueError, ZeroDivisionError) as e:
        cert.update(verdict=REFUSED, reason=f"enclosure failed: {e}")
        return cert

    sha = d["sha_interval"]
    cands = rig.integers_in(sha)
    positive = [m for m in cands if m > 0]
    squares = [m for m in positive if isqrt(m) ** 2 == m]

    cert.update({
        "conductor": d["conductor"],
        "discriminant": d["discriminant"],
        "minimality_proof": d["minimality_proof"],
        "reduction": d["reduction"],
        "root_number": d["root_number"],
        "torsion_order": d["torsion_order"],
        "tamagawa_product": d["tamagawa_product"],
        "omega_proven_digits": d["omega"].decimal(),
        "L1_proven_digits": d["L1"].decimal(),
        "sha_proven_digits": sha.decimal(),
        "sha_enclosure_width": f"{float(sha.width()):.3e}",
        "integers_in_enclosure": cands,
    })

    if not positive:
        cert.update(
            verdict=REFUTED,
            reason=("the BSD-predicted |Sha| is provably not a positive integer: "
                    "its enclosure contains no positive integer"),
            sha_analytic=None)
    elif not squares:
        cert.update(
            verdict=REFUTED,
            reason=("the BSD-predicted |Sha| is provably not a perfect square "
                    "integer, contradicting the Cassels-Tate pairing"),
            sha_analytic=None)
    elif len(cands) > 1:
        cert.update(
            verdict=REFUSED,
            reason=f"enclosure admits {len(cands)} integers {cands}: not pinned, raise rig.PREC",
            sha_analytic=None)
    else:
        cert.update(
            verdict=CONSISTENT,
            sha_analytic=squares[0],
            sha_sqrt=isqrt(squares[0]),
            reason=("the enclosure admits exactly one integer and it is a perfect "
                    "square; BSD's prediction here is pinned without rounding"),
            scope=("this pins what BSD PREDICTS for this curve; it is not a proof "
                   "of BSD for this curve, and no interval computation could be"))
    return cert


def main() -> int:
    import json
    from .battery import BATTERY, run_battery
    ok, results = run_battery()
    print(json.dumps({"battery_passed": ok, "curves": results}, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
