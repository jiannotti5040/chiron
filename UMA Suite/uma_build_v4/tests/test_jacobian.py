# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
Exact-arithmetic gates for uma.jacobian — the 2026 Jacobian-conjecture
counterexample (Alpöge announcement, Knill transcription), verified by the
suite's own rational arithmetic rather than cited.

Run with: pytest tests/test_jacobian.py -v
"""
from __future__ import annotations

from fractions import Fraction

from uma.jacobian import (ONE, P1, P2, X, Y, Z, counterexample_map,
                          jacobian_det, keller_control, mutated_control,
                          padd, pdiff, peval, pmul, ppow, pscale,
                          verify_counterexample)


# ── engine sanity: the machinery must be right before the theorem is ─────

def test_poly_mul_known_product():
    """(x + y)(x - y) = x^2 - y^2, exactly."""
    left = pmul(padd(X, Y), padd(X, pscale(Y, -1)))
    assert left == padd(ppow(X, 2), pscale(ppow(Y, 2), -1))


def test_poly_diff_power_rule():
    """d/dx x^3 y = 3 x^2 y, exactly."""
    assert pdiff(pmul(ppow(X, 3), Y), 0) == pscale(pmul(ppow(X, 2), Y), 3)


def test_poly_eval_rational_point():
    """(1+xy) at (2, 3/2, anything) = 4, exactly."""
    p = padd(ONE, pmul(X, Y))
    assert peval(p, (Fraction(2), Fraction(3, 2), Fraction(0))) == 4


def test_zero_coefficients_are_pruned():
    """x - x is the empty polynomial (canonical zero)."""
    assert padd(X, pscale(X, -1)) == {}


# ── positive + discrimination controls ───────────────────────────────────

def test_keller_control_det_exactly_one():
    """Known automorphism (x+y^2, y, z): det J = 1 identically."""
    assert keller_control() == {(0, 0, 0): Fraction(1)}


def test_mutated_map_det_not_constant():
    """One perturbed coefficient and the constancy dies: claim 1 is a
    knife-edge cancellation the machinery can distinguish, not an
    artifact that any nearby map would satisfy."""
    det = mutated_control()
    non_constant = {e: c for e, c in det.items() if e != (0, 0, 0)}
    assert non_constant, "perturbed map still had constant det — no discrimination"


# ── the counterexample itself, exactly ───────────────────────────────────

def test_det_jacobian_is_minus_two_identically():
    """Claim 1: the symbolic Jacobian determinant of the Alpöge map is the
    constant polynomial −2 — every non-constant coefficient cancels."""
    det = jacobian_det(counterexample_map())
    assert det == {(0, 0, 0): Fraction(-2)}


def test_collision_points_are_distinct():
    assert P1 != P2


def test_collision_images_exactly_equal():
    """Claim 2: F(0,0,−1/4) = F(1,−3/2,13/2), computed in Fractions."""
    F = counterexample_map()
    img1 = tuple(peval(f, P1) for f in F)
    img2 = tuple(peval(f, P2) for f in F)
    assert img1 == img2


def test_collision_image_value():
    """The shared image is exactly (−1/4, 0, 0) — pinned so a silent
    transcription change cannot slip past as 'still equal'."""
    F = counterexample_map()
    assert tuple(peval(f, P1) for f in F) == (Fraction(-1, 4), Fraction(0), Fraction(0))


def test_certificate_refutes_implication():
    """Premise (constant nonzero det) + non-injectivity ⇒ the implication
    fails for n = 3. The certificate asserts exactly that and no more."""
    cert = verify_counterexample()
    assert cert["claim_1_det_identity"]["verified"]
    assert cert["claim_2_collision"]["verified"]
    assert cert["refutes_implication"]


def test_certificate_carries_honest_status():
    """The certificate must state announcement provenance, non-peer-reviewed
    status, the open n = 2 case, and the scope caveat — the vault does not
    ship a history claim dressed as arithmetic."""
    cert = verify_counterexample()
    assert "NOT peer-reviewed" in cert["status"]
    assert "n = 2" in cert["scope"] or "n = 2" in cert["status"]
    assert "caveat" in cert and "provenance" in cert["caveat"]
    assert cert["announced"] == "2026-07-20"
