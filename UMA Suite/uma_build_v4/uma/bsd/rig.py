# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
uma.bsd.rig — rigorous real arithmetic in exact integers. No floats.

WHY THIS EXISTS. The Birch--Swinnerton-Dyer prediction is a statement about
real numbers (a period, an L-value) that is *asserted to be rational* -- in
fact to be a positive integer, and in fact a perfect square. Every published
computation of that integer, including every entry in the LMFDB, obtains it
by dividing two floating-point numbers and rounding to the nearest integer.
The rounding step is where the exactness is lost, and it is unrecoverable:
a float quotient of 3.9999999 and one of 4.0000001 are reported identically.

This module refuses that step. A real quantity is represented as a CLOSED
INTERVAL with dyadic rational endpoints, held as a pair of integers scaled by
2^-PREC. Every operation rounds OUTWARD, so the interval provably contains the
true value at every stage. Nothing is ever rounded to a nearest value.

The consequence is the whole point of the module: an interval either pins a
rational uniquely or it does not, and "it does not" is a first-class answer.

Contract, per vault convention: every function returns an interval that
CONTAINS the true value. If it cannot, it raises. It never returns a
best guess.
"""
from __future__ import annotations

from fractions import Fraction
from math import isqrt

# Working precision, in bits. Every endpoint is an integer multiple of 2^-PREC.
PREC = 320
SCALE = 1 << PREC


def _floor_div(a: int, b: int) -> int:
    """Floor division that is correct for negative numerators."""
    return a // b


def _ceil_div(a: int, b: int) -> int:
    return -((-a) // b)


class Iv:
    """A closed interval [lo/2^PREC, hi/2^PREC] guaranteed to contain its value.

    Endpoints are plain Python ints (scaled). All arithmetic rounds outward,
    so containment is an invariant of every operation.
    """

    __slots__ = ("lo", "hi")

    def __init__(self, lo: int, hi: int):
        if hi < lo:
            raise ValueError("empty interval")
        self.lo = lo
        self.hi = hi

    # ── constructors ────────────────────────────────────────────────────
    @staticmethod
    def exact(q) -> "Iv":
        """The tightest interval containing an exact rational."""
        q = Fraction(q)
        n, d = q.numerator, q.denominator
        return Iv(_floor_div(n * SCALE, d), _ceil_div(n * SCALE, d))

    @staticmethod
    def zero() -> "Iv":
        return Iv(0, 0)

    # ── inspection ──────────────────────────────────────────────────────
    def width(self) -> Fraction:
        return Fraction(self.hi - self.lo, SCALE)

    def as_fractions(self):
        return Fraction(self.lo, SCALE), Fraction(self.hi, SCALE)

    def contains_zero(self) -> bool:
        return self.lo <= 0 <= self.hi

    def is_positive(self) -> bool:
        """True only if the whole interval is strictly positive -- i.e. the
        true value is PROVABLY positive, not merely observed to be."""
        return self.lo > 0

    def __repr__(self) -> str:
        lo, hi = self.as_fractions()
        return f"Iv[{float(lo):.18g}, {float(hi):.18g}]"

    def decimal(self, digits: int = 24) -> str:
        """Decimal digits that are COMMON to both endpoints -- i.e. digits
        that are proven, not printed. Truncated at the first disagreement."""
        lo, hi = self.as_fractions()
        s_lo = _fixed_decimal(lo, digits)
        s_hi = _fixed_decimal(hi, digits)
        out = []
        for a, b in zip(s_lo, s_hi):
            if a != b:
                break
            out.append(a)
        return "".join(out) + "..."

    # ── arithmetic (all outward-rounding) ───────────────────────────────
    def __neg__(self) -> "Iv":
        return Iv(-self.hi, -self.lo)

    def __add__(self, o: "Iv") -> "Iv":
        return Iv(self.lo + o.lo, self.hi + o.hi)

    def __sub__(self, o: "Iv") -> "Iv":
        return Iv(self.lo - o.hi, self.hi - o.lo)

    def __mul__(self, o: "Iv") -> "Iv":
        c = (self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi)
        return Iv(_floor_div(min(c), SCALE), _ceil_div(max(c), SCALE))

    def scale_int(self, k: int) -> "Iv":
        """Multiply by an exact integer -- no rounding needed."""
        return Iv(self.lo * k, self.hi * k) if k >= 0 else Iv(self.hi * k, self.lo * k)

    def __truediv__(self, o: "Iv") -> "Iv":
        if o.contains_zero():
            raise ZeroDivisionError("interval divisor straddles zero -- refuse")
        c = []
        for num in (self.lo, self.hi):
            for den in (o.lo, o.hi):
                c.append((_floor_div(num * SCALE, den), _ceil_div(num * SCALE, den)))
        return Iv(min(x[0] for x in c), max(x[1] for x in c))

    def sqrt(self) -> "Iv":
        """Outward-rounded square root. Requires a provably non-negative
        interval; a straddling interval is a refusal, not a clamp."""
        if self.lo < 0:
            raise ValueError("sqrt of an interval that may be negative -- refuse")
        lo = isqrt(self.lo * SCALE)
        h = self.hi * SCALE
        hi = isqrt(h)
        if hi * hi < h:
            hi += 1
        return Iv(lo, hi)


# ── decimal rendering of an exact rational, truncated toward zero ────────
def _fixed_decimal(q: Fraction, digits: int) -> str:
    neg = q < 0
    q = -q if neg else q
    whole = q.numerator // q.denominator
    rem = q - whole
    frac = (rem.numerator * 10 ** digits) // rem.denominator
    return ("-" if neg else "") + f"{whole}.{frac:0{digits}d}"


# ── constants: proven enclosures, not literals trusted to be exact ───────
# 60 decimal digits of pi. The interval is [truncate, truncate + 10^-59],
# which contains pi because the digits shown are correct and truncation
# only ever loses value from below.
_PI_DIGITS = "3.14159265358979323846264338327950288419716939937510582097494"
_PI_DEN = 10 ** (len(_PI_DIGITS) - 2)
_PI_LO_Q = Fraction(int(_PI_DIGITS.replace(".", "")), _PI_DEN)
_PI_HI_Q = _PI_LO_Q + Fraction(1, _PI_DEN)
PI = Iv(_floor_div(_PI_LO_Q.numerator * SCALE, _PI_LO_Q.denominator),
        _ceil_div(_PI_HI_Q.numerator * SCALE, _PI_HI_Q.denominator))


def exp_pos(x: Iv, terms: int = 400) -> Iv:
    """e^x for a provably positive x, as an enclosure.

    Truncated Taylor series with an explicit remainder bound: for x < n+1 the
    tail after n terms is at most (x^n/n!) * 1/(1 - x/(n+1)). Both the partial
    sum and the bound are computed in interval arithmetic, so the returned
    interval contains e^x for every point of x.
    """
    if x.lo < 0:
        raise ValueError("exp_pos requires x >= 0")
    xh = Fraction(x.hi, SCALE)
    if xh >= terms:
        raise ValueError("exp series bound violated -- increase terms or reduce x")
    total = Iv.exact(1)
    term = Iv.exact(1)
    for k in range(1, terms):
        term = term * x / Iv.exact(k)
        total = total + term
    # remainder bound, using the largest point of x
    ratio = xh / terms
    if ratio >= 1:
        raise ValueError("exp remainder bound not applicable")
    tail_hi = Fraction(term.hi, SCALE) * (1 / (1 - ratio))
    if tail_hi < 0:
        raise ValueError("exp remainder bound negative")
    bound = Iv.exact(tail_hi)
    return Iv(total.lo, (total + bound).hi)


def exp_neg(x: Iv, terms: int = 400) -> Iv:
    """e^-x for a provably positive x."""
    return Iv.exact(1) / exp_pos(x, terms)


def agm(a: Iv, b: Iv, iters: int = 60) -> Iv:
    """Arithmetic-geometric mean of two provably positive intervals.

    AGM is monotone non-decreasing in each argument on the positive reals, so
    iterating the interval recursion yields an interval containing AGM(a, b)
    for every point of the inputs. The iteration is stopped when the endpoints
    stop moving; it converges quadratically.
    """
    if not (a.is_positive() and b.is_positive()):
        raise ValueError("agm requires provably positive arguments")
    for _ in range(iters):
        an = Iv(a.lo + b.lo, a.hi + b.hi)
        an = Iv(_floor_div(an.lo, 2), _ceil_div(an.hi, 2))
        bn = (a * b).sqrt()
        if an.lo == a.lo and an.hi == a.hi and bn.lo == b.lo and bn.hi == b.hi:
            break
        a, b = an, bn
    return Iv(min(a.lo, b.lo), max(a.hi, b.hi))


def _poly_eval(coeffs, q: Fraction) -> Fraction:
    v = Fraction(0)
    for c in coeffs:
        v = v * q + c
    return v


def _poly_div_rem(a, b):
    """Remainder of a / b for dense coefficient lists over Q, highest first."""
    a = [Fraction(c) for c in a]
    b = [Fraction(c) for c in b]
    while len(a) >= len(b) and any(c != 0 for c in a):
        if a[0] == 0:
            a = a[1:]
            continue
        f = a[0] / b[0]
        shift = len(a) - len(b)
        for i, c in enumerate(b):
            a[i] -= f * c
        a = a[1:] if shift >= 0 else a
        if shift == 0:
            break
    a = [c for c in a]
    while a and a[0] == 0:
        a = a[1:]
    return a if a else [Fraction(0)]


def _sturm_chain(coeffs):
    """Sturm chain of a squarefree integer polynomial, over Q."""
    p0 = [Fraction(c) for c in coeffs]
    p1 = [Fraction(len(coeffs) - 1 - i) * c for i, c in enumerate(p0[:-1])]
    chain = [p0, p1]
    while len(chain[-1]) > 1 or chain[-1][0] != 0:
        r = _poly_div_rem(chain[-2], chain[-1])
        r = [-c for c in r]
        if len(r) == 1 and r[0] == 0:
            break
        chain.append(r)
    return chain


def _sign_variations(chain, x: Fraction) -> int:
    signs = []
    for p in chain:
        v = _poly_eval(p, x)
        if v != 0:
            signs.append(1 if v > 0 else -1)
    return sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])


def _roots_in(chain, a: Fraction, b: Fraction) -> int:
    """Number of DISTINCT real roots in (a, b], exactly, by Sturm's theorem."""
    return _sign_variations(chain, a) - _sign_variations(chain, b)


def largest_real_root(coeffs, iters: int = PREC + 16) -> Iv:
    """Enclosure of the LARGEST real root of a squarefree integer polynomial.

    coeffs is [c_d, ..., c_1, c_0] with c_d > 0.

    Plain sign-change bisection is WRONG here and quietly so: on a cubic with
    three real roots it converges to whichever root the midpoint sequence
    happens to bracket, which is generally the smallest. The period formula
    needs specifically the largest, and using the wrong one still produces a
    plausible positive number -- the failure is invisible downstream.

    So the bisection is driven by an exact ROOT COUNT rather than a sign: at
    each step Sturm's theorem says how many distinct real roots lie in
    (mid, hi], and the bracket moves right whenever that count is nonzero.
    Every evaluation is exact rational arithmetic, so the count is exact and
    the returned bracket provably contains the largest real root and no other.
    """
    if coeffs[0] <= 0:
        raise ValueError("leading coefficient must be positive")
    bound = 1 + max(abs(c) for c in coeffs[1:]) // coeffs[0] + 1
    chain = _sturm_chain(coeffs)
    lo, hi = Fraction(-bound), Fraction(bound)
    if _roots_in(chain, lo, hi) < 1:
        raise ValueError("no real root in the Cauchy bracket -- refuse")
    for _ in range(iters):
        mid = (lo + hi) / 2
        if _roots_in(chain, mid, hi) >= 1:
            lo = mid
        else:
            hi = mid
    return Iv(_floor_div(lo.numerator * SCALE, lo.denominator),
              _ceil_div(hi.numerator * SCALE, hi.denominator))


def integers_in(iv: Iv):
    """Every integer contained in the interval. The heart of exactification:
    if this returns exactly one value, the real quantity is pinned to it
    PROVIDED it is an integer at all. If it returns none, the quantity is
    provably not an integer."""
    lo, hi = iv.as_fractions()
    a = _ceil_div(lo.numerator, lo.denominator)
    b = _floor_div(hi.numerator, hi.denominator)
    return list(range(a, b + 1))
