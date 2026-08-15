# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Gates for the exhaustive small-point enumeration behind every rank-2
saturation proof.

`studies/rank2_389a1/` proves a Mordell-Weil basis saturated by bounding the
index with Hermite, which needs `mu`, a proven lower bound on canonical
height. `mu` is only valid if the point enumeration is genuinely EXHAUSTIVE in
range: a missed point could be the one of small height, and every saturation
proof downstream would be void without any test failing.

The enumeration is pure Python (no PARI), so it is gated here in the ordinary
suite rather than only inside the optional backend.

The routine solves, for x = a/b^2 in lowest terms,
    (2y + a1 x + a3)^2 = 4x^3 + b2 x^2 + 2 b4 x + b6
by testing whether the integer numerator is a perfect square.
"""
from __future__ import annotations

import importlib.util
import math
import os
from fractions import Fraction

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SWEEP = os.path.join(_HERE, os.pardir, "studies", "rank2_389a1",
                      "rank2_corpus_sweep.py")


def _load_enumerate_points():
    """Import just the pure-Python enumerator, without the PARI-dependent rest."""
    if not os.path.exists(_SWEEP):
        pytest.skip("rank2 study not present")
    src = open(_SWEEP).read()
    start = src.index("def enumerate_points(")
    end = src.index("\ndef ", start + 1)
    ns: dict = {"math": math, "Fraction": Fraction}
    exec(compile(src[start:end], _SWEEP, "exec"), ns)
    return ns["enumerate_points"]


enumerate_points = _load_enumerate_points()

C389 = [0, 1, 1, -2, 0]      # y^2 + y = x^3 + x^2 - 2x, rank 2
C11 = [0, -1, 1, -10, -20]   # 11.a2, rank 0, torsion 5


def on_curve(ainvs, x: Fraction, y: Fraction) -> bool:
    a1, a2, a3, a4, a6 = ainvs
    return y * y + a1 * x * y + a3 * y == x ** 3 + a2 * x * x + a4 * x + a6


def brute_force(ainvs, limit):
    """Independent reference: sweep x = a/b^2 and solve the quadratic in y
    directly, rather than via the completed-square numerator."""
    a1, a2, a3, a4, a6 = ainvs
    found = set()
    for b in range(1, int(math.isqrt(limit)) + 1):
        for a in range(-limit, limit + 1):
            if math.gcd(a, b) != 1:
                continue
            x = Fraction(a, b * b)
            # y^2 + (a1 x + a3) y - (x^3 + a2 x^2 + a4 x + a6) = 0
            B = a1 * x + a3
            Cc = -(x ** 3 + a2 * x * x + a4 * x + a6)
            disc = B * B - 4 * Cc
            if disc < 0:
                continue
            num, den = disc.numerator, disc.denominator
            rn, rd = math.isqrt(num), math.isqrt(den)
            if rn * rn != num or rd * rd != den:
                continue
            root = Fraction(rn, rd)
            for s in (1, -1):
                y = (-B + s * root) / 2
                if on_curve(ainvs, x, y):
                    found.add((x, y))
    return found


def test_every_point_returned_is_actually_on_the_curve():
    for ainvs in (C389, C11):
        for x, y in enumerate_points(ainvs, 60):
            assert on_curve(ainvs, x, y), (ainvs, x, y)


def test_enumeration_is_exhaustive_against_an_independent_method():
    """The property `mu` depends on. A missed point invalidates every
    saturation proof, so this is checked against a differently-derived
    reference rather than against itself."""
    for ainvs in (C389, C11):
        for limit in (30, 120):
            got = set(enumerate_points(ainvs, limit))
            ref = brute_force(ainvs, limit)
            assert got == ref, (
                f"{ainvs} limit={limit}: "
                f"missed {sorted(ref - got)[:4]}, extra {sorted(got - ref)[:4]}")


def test_finds_the_known_generators_of_389a1():
    # Each verified against y^2 + y = x^3 + x^2 - 2x before being asserted:
    #   x=0  -> 0,  y(y+1)=0  -> y = 0
    #   x=1  -> 0,  y(y+1)=0  -> y = 0
    #   x=-1 -> 2,  y^2+y=2   -> y = 1
    #   x=-2 -> 0,  y(y+1)=0  -> y = 0
    #   x=3  -> 30, y^2+y=30  -> y = 5
    known = ((0, 0), (1, 0), (-1, 1), (-2, 0), (3, 5))
    for x, y in known:
        assert on_curve(C389, Fraction(x), Fraction(y)), (x, y)
    pts = set(enumerate_points(C389, 40))
    for x, y in known:
        assert (Fraction(x), Fraction(y)) in pts, (x, y)


def test_respects_the_height_bound_it_claims():
    """Nothing outside max(|a|, b^2) <= limit may be returned, or the
    'anything not found exceeds B' step of the argument is false."""
    limit = 50
    for x, y in enumerate_points(C389, limit):
        a, b2 = x.numerator, x.denominator
        assert max(abs(a), b2) <= limit, (x, y)


def test_larger_limit_is_a_superset():
    small = set(enumerate_points(C389, 25))
    large = set(enumerate_points(C389, 90))
    assert small <= large
    assert len(large) > len(small)
