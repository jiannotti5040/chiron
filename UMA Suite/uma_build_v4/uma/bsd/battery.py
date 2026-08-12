# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
uma.bsd.battery — the validation the module must pass before it may report.

Vault rule, inherited from studies/famous_conjectures.py: an encoder that
cannot reproduce what is already known has no business reporting what is not.
So before uma.bsd is allowed to pin an unpublished Sha, it must reproduce
published ones -- and it must do so in a way that could FAIL.

Each entry carries LMFDB's own numeric values for the real period and L(1).
Those are floats and are therefore never used as inputs; they are used only as
CONTAINMENT TARGETS. The module's interval must contain them. If a convention
were wrong by the classic factor of 2 -- the number of real components when
Delta > 0 is exactly the place that trap is set -- the containment test fails
loudly instead of silently shifting every Sha by 4.

The battery deliberately spans the discriminating cases:
  * Delta < 0 and Delta > 0 (one vs two real components);
  * torsion 1, 2 and 5 (the |tors|^2 factor);
  * Tamagawa product 1, 2 and 5;
  * Sha = 1 and Sha = 4 (571.b1, the smallest conductor with |Sha| > 1).
A battery all of whose curves had Sha = 1 would not discriminate at all.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Tuple

from . import bsd_certificate, real_period, l_value_at_1, CONSISTENT, REFUSED, REFUTED
from .curve import Curve, Refuse
from .rig import Iv

# label, ainvs, conductor, disc, torsion, tamagawa product, Omega, L(1), Sha
BATTERY: List[Tuple] = [
    ("11.a2", (0, -1, 1, -10, -20), 11, -161051, 5, 5,
     "1.2692093042795534216887946168", "0.25384186085591068433775892335", 1),
    ("15.a1", (1, 1, 1, -2160, -39540), 15, 405, 2, 2,
     "0.70030152116630101159009041840", "0.35015076058315050579504520920", 1),
    # 37.b1 has trivial torsion: psi_3's only rational root is x = -76/3, whose
    # y-discriminant is -1/27, so the 3-division point is not even real. The
    # reduction bound stalls at 3 because the isogeny class contains Z/3.
    ("37.b1", (0, 1, 1, -1873, -31833), 37, 37, 1, 1,
     "0.72568106193615278233620554103", "0.72568106193615278233620554103", 1),
    ("571.b1", (0, -1, 1, -929, -10595), 571, -571, 1, 1,
     "0.43234125627186097023531760110", "1.7293650250874438809412704044", 4),
]


def _contains(iv: Iv, decimal: str, tol_digits: int = 20) -> bool:
    """Does the proven interval contain the published decimal, allowing for
    the published value's own truncation at the last digit?"""
    v = Fraction(decimal)
    slack = Fraction(1, 10 ** min(tol_digits, len(decimal.split(".")[-1])))
    lo, hi = iv.as_fractions()
    return lo - slack <= v <= hi + slack


def run_battery() -> Tuple[bool, List[Dict]]:
    results: List[Dict] = []
    ok = True
    for label, ainvs, N, disc, tors, tam, omega_s, l1_s, sha in BATTERY:
        row: Dict = {"label": label, "ainvs": list(ainvs)}
        try:
            E = Curve(ainvs)
            row["conductor_ok"] = (E.conductor() == N)
            row["discriminant_ok"] = (E.disc == disc)
            row["torsion_ok"] = (E.torsion_order() == tors)
            row["tamagawa_ok"] = (E.tamagawa_product() == tam)
            om = real_period(E)
            l1 = l_value_at_1(E)
            row["omega_contains_published"] = _contains(om, omega_s)
            row["L1_contains_published"] = _contains(l1, l1_s)
            row["omega_proven"] = om.decimal(22)
            row["L1_proven"] = l1.decimal(22)
            cert = bsd_certificate(ainvs, label=label)
            row["verdict"] = cert["verdict"]
            row["sha_analytic"] = cert.get("sha_analytic")
            row["sha_ok"] = (cert.get("sha_analytic") == sha)
            row["passed"] = all(row[k] for k in
                                ("conductor_ok", "discriminant_ok", "torsion_ok",
                                 "tamagawa_ok", "omega_contains_published",
                                 "L1_contains_published", "sha_ok")) and \
                row["verdict"] == CONSISTENT
        except (Refuse, ValueError, ZeroDivisionError) as e:
            row["passed"] = False
            row["error"] = f"{type(e).__name__}: {e}"
        ok = ok and bool(row.get("passed"))
        results.append(row)
    return ok, results


# ── controls: the battery must be able to fail ───────────────────────────

def control_wrong_period_factor() -> bool:
    """The factor-of-2 trap, made to spring.

    E(R) has two components exactly when Delta > 0, and dropping that doubling
    is the classic silent error in a period computation. On 15.a1 (Delta > 0)
    the halved period yields Sha_an = 2 -- an integer, so an integrality test
    alone would pass it, but NOT a perfect square, so the Cassels test rejects
    it. This control asserts both halves of that: the wrong convention lands on
    exactly one integer, and that integer is caught by the square test."""
    E = Curve((1, 1, 1, -2160, -39540))
    om = real_period(E)
    half = Iv(om.lo // 2, -((-om.hi) // 2))
    l1 = l_value_at_1(E)
    from math import isqrt
    from .rig import integers_in
    bad = integers_in((l1.scale_int(E.torsion_order() ** 2)) /
                      half.scale_int(E.tamagawa_product()))
    return bad == [2] and isqrt(2) ** 2 != 2


def control_largest_root_is_used() -> bool:
    """The period formula needs the LARGEST real root of 4x^3 + b2 x^2 +
    2 b4 x + b6. A plain sign-change bisection returns the smallest when there
    are three, and still produces a plausible positive period. 15.a1 has three
    real roots; this asserts the root actually used is above the other two."""
    from .rig import largest_real_root, _sturm_chain, _roots_in
    E = Curve((1, 1, 1, -2160, -39540))
    h = [4, E.b2, 2 * E.b4, E.b6]
    chain = _sturm_chain(h)
    lo, hi = largest_real_root(h).as_fractions()
    total = _roots_in(chain, Fraction(-10 ** 6), Fraction(10 ** 6))
    below = _roots_in(chain, Fraction(-10 ** 6), lo)
    return total == 3 and below == 2


def control_additive_is_refused() -> bool:
    """A curve with additive reduction must be refused, not estimated.
    27.a1: y^2 + y = x^3 has additive reduction at 3."""
    cert = bsd_certificate((0, 0, 1, 0, 0), label="27.a3")
    return cert["verdict"] == REFUSED and "additive" in cert["reason"]


def control_rank_one_is_refused() -> bool:
    """37.a1 has rank 1, hence root number -1, hence L(1) = 0. The module must
    refuse rather than divide by an interval containing zero."""
    cert = bsd_certificate((0, 0, 1, -1, 0), label="37.a1")
    return cert["verdict"] == REFUSED and "root number" in cert["reason"]


def control_perturbed_curve_moves() -> bool:
    """Perturbing one coefficient of 11.a2 must change the answer. A gate that
    reports the same Sha for a different curve is measuring nothing."""
    base = bsd_certificate((0, -1, 1, -10, -20))
    pert = bsd_certificate((0, -1, 1, -10, -19))
    return base.get("sha_analytic") != pert.get("sha_analytic") or \
        pert["verdict"] != base["verdict"]


def control_split_test_routes_agree() -> bool:
    """The fast split/non-split test (-c6 a square mod p) must agree with the
    slow one (#E_ns(F_p) = p - 1) on every bad prime of the battery where both
    apply. A fast path that is never checked against the slow path is an
    assumption wearing an optimisation's clothes."""
    for _, ainvs, *_ in BATTERY:
        E = Curve(ainvs)
        for p in E.bad_primes():
            if p < 5 or E.reduction_type(p) == "additive":
                continue
            fast = pow(-E.c6 % p, (p - 1) // 2, p) == 1
            if p > 2000:          # the slow route is O(p^2); check where feasible
                continue
            if fast != (E._count_nonsingular(p) == p - 1):
                return False
    return True


CONTROLS = {
    "wrong_period_factor_detected": control_wrong_period_factor,
    "split_test_routes_agree": control_split_test_routes_agree,
    "largest_real_root_is_used": control_largest_root_is_used,
    "additive_reduction_refused": control_additive_is_refused,
    "rank_one_refused": control_rank_one_is_refused,
    "perturbed_curve_moves": control_perturbed_curve_moves,
}
