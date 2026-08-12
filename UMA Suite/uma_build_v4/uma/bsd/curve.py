# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
uma.bsd.curve — exact integer arithmetic on an elliptic curve over Q.

Everything in this file is an exact integer computation. No approximation, no
table lookup, no external CAS. Where an invariant cannot be determined exactly
by the methods implemented here, the function RAISES Refuse rather than
guessing -- the refusals are load-bearing, and the domain of the module is
defined by exactly where they stop.

DOMAIN. Semistable curves in a minimal Weierstrass model. Semistability
(every bad prime has multiplicative, not additive, reduction) is what makes
three separate things exact at once:

  * the conductor is the radical of the discriminant;
  * every Tamagawa number is v_p(Delta) or gcd(2, v_p(Delta));
  * the sign of the functional equation is (-1)^(1 + #split-multiplicative
    primes), because the local root number at a good prime is +1 and at a
    multiplicative prime is -1 (split) or +1 (non-split).

Outside semistability all three require the wild part of Tate's algorithm and
local root numbers at 2 and 3. Those are not implemented, so those curves are
refused. That is a smaller claim honestly made, not a larger one guessed at.
"""
from __future__ import annotations

from math import gcd, isqrt
from typing import Dict, List, Tuple


class Refuse(Exception):
    """Raised where exactness is not attainable by the methods here.

    Per vault convention a refusal is a result, not a failure. Callers turn it
    into a REFUSED verdict with the reason attached; nothing downstream is
    permitted to substitute an estimate."""


GOOD, SPLIT, NONSPLIT, ADDITIVE = "good", "split_multiplicative", "nonsplit_multiplicative", "additive"


def _factor(n: int) -> Dict[int, int]:
    """Trial-division factorisation. Exact; refuses rather than probabilistic
    fallback if a large cofactor survives."""
    n = abs(n)
    out: Dict[int, int] = {}
    d = 2
    while d * d <= n and d < 200_000:
        while n % d == 0:
            out[d] = out.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        if d * d > n or _is_probable_prime(n):
            out[n] = out.get(n, 0) + 1
        else:
            raise Refuse(f"discriminant has an unfactored cofactor {n}")
    return out


_FACTOR_CACHE: Dict[int, Dict[int, int]] = {}


# psi_k is the smallest composite that is a strong pseudoprime to all of the
# first k prime bases, so deterministic Miller-Rabin over those k bases is
# correct for every n < psi_k and WRONG at psi_k itself. Jaeschke (1993) for
# k <= 8, Sorenson-Webster (arXiv:1509.00864) for k = 9..13.
#
# The bound is derived from the witness list rather than written beside it.
# Written separately they desynchronised: twelve bases were paired with the
# thirteen-base bound, so psi_12 = 399165290221 * 798330580441 was reported
# prime -- below the bound this routine claimed to decide. Deriving the bound
# makes that class of defect unrepresentable. Kept in step with the identical
# table in Primus/src/primus/certify.py; tests/test_bsd.py cross-checks them.
_MR_PSI = {
    1: 2_047,
    2: 1_373_653,
    3: 25_326_001,
    4: 3_215_031_751,
    5: 2_152_302_898_747,
    6: 3_474_749_660_383,
    7: 341_550_071_728_321,
    8: 341_550_071_728_321,
    9: 3_825_123_056_546_413_051,
    10: 3_825_123_056_546_413_051,
    11: 3_825_123_056_546_413_051,
    12: 318_665_857_834_031_151_167_461,
    13: 3_317_044_064_679_887_385_961_981,
}
_MR_WITNESSES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
_MR_DETERMINISTIC_BOUND = _MR_PSI[len(_MR_WITNESSES)]


def _is_probable_prime(n: int) -> bool:
    """Deterministic Miller-Rabin below _MR_DETERMINISTIC_BOUND (the same bound
    and witness list Primus uses for its primality claim kind). Above that this
    returns False, which makes _factor refuse -- deliberately, since a probable
    prime is not a proof."""
    if n < 2:
        return False
    for p in _MR_WITNESSES:
        if n % p == 0:
            return n == p
    if n >= _MR_DETERMINISTIC_BOUND:
        return False
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in _MR_WITNESSES:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


class Curve:
    """y^2 + a1 x y + a3 y = x^3 + a2 x^2 + a4 x + a6, with a_i in Z."""

    def __init__(self, ainvs: Tuple[int, int, int, int, int]):
        self.a1, self.a2, self.a3, self.a4, self.a6 = (int(a) for a in ainvs)
        a1, a2, a3, a4, a6 = self.a1, self.a2, self.a3, self.a4, self.a6
        self.b2 = a1 * a1 + 4 * a2
        self.b4 = 2 * a4 + a1 * a3
        self.b6 = a3 * a3 + 4 * a6
        self.b8 = a1 * a1 * a6 + 4 * a2 * a6 - a1 * a3 * a4 + a2 * a3 * a3 - a4 * a4
        self.c4 = self.b2 * self.b2 - 24 * self.b4
        self.c6 = -self.b2 ** 3 + 36 * self.b2 * self.b4 - 216 * self.b6
        self.disc = (-self.b2 * self.b2 * self.b8 - 8 * self.b4 ** 3
                     - 27 * self.b6 * self.b6 + 9 * self.b2 * self.b4 * self.b6)
        if self.disc == 0:
            raise Refuse("singular curve: discriminant is zero")
        self._facts = None
        self._red: Dict[int, str] = {}
        # the defining identity -- a free internal consistency gate
        assert self.c4 ** 3 - self.c6 ** 2 == 1728 * self.disc

    def __repr__(self) -> str:
        return f"Curve({[self.a1, self.a2, self.a3, self.a4, self.a6]})"

    @property
    def ainvs(self):
        return (self.a1, self.a2, self.a3, self.a4, self.a6)

    def disc_factors(self) -> Dict[int, int]:
        """Factorisation of the discriminant, computed once per curve."""
        if self._facts is None:
            self._facts = _factor(self.disc)
        return self._facts

    # ── minimality ──────────────────────────────────────────────────────
    def certify_minimal(self) -> Dict[int, str]:
        """Prove the model is minimal at every prime, or refuse.

        A non-minimal model at p forces v_p(Delta) >= 12, since Delta scales by
        u^12 under an admissible change of variables. So v_p(Delta) < 12 is a
        SUFFICIENT proof of minimality at p and needs no case analysis. Where
        v_p(Delta) >= 12 and p >= 5, non-minimality is equivalent to
        p^4 | c4 and p^6 | c6. At p = 2, 3 with v_p(Delta) >= 12 the test is
        Kraus's, which is not implemented -- refuse.
        """
        proof: Dict[int, str] = {}
        for p, v in self.disc_factors().items():
            if v < 12:
                proof[p] = f"v_{p}(Delta) = {v} < 12"
            elif p >= 5:
                if self.c4 % p ** 4 == 0 and self.c6 % p ** 6 == 0:
                    raise Refuse(f"model is NOT minimal at {p}")
                proof[p] = f"v_{p}(Delta) = {v}, but p^4 does not divide c4 or p^6 does not divide c6"
            else:
                raise Refuse(f"minimality at p = {p} with v_p(Delta) = {v} needs Kraus's test")
        return proof

    # ── reduction ───────────────────────────────────────────────────────
    def bad_primes(self) -> List[int]:
        return sorted(self.disc_factors())

    def reduction_type(self, p: int) -> str:
        if p in self._red:
            return self._red[p]
        if self.disc % p != 0:
            t = GOOD
        elif self.c4 % p != 0:
            t = SPLIT if self._is_split(p) else NONSPLIT
        else:
            t = ADDITIVE
        self._red[p] = t
        return t

    def _is_split(self, p: int) -> bool:
        """Split iff the node's tangent slopes are rational over F_p.

        For p >= 5 the slopes are rational exactly when -c6 is a square mod
        F_p, decided by one Euler-criterion exponentiation. At p = 2 and 3 that
        shortcut needs care, so those two primes -- and only those two -- are
        settled by direct point counting: multiplicative reduction gives
        #E_ns(F_p) = p - 1 when split and p + 1 when non-split.

        Both routes are exact. The battery asserts they AGREE wherever both
        apply, so the fast path is checked against the slow one rather than
        trusted."""
        if p >= 5:
            return pow(-self.c6 % p, (p - 1) // 2, p) == 1
        return self._count_nonsingular(p) == p - 1

    def _count_nonsingular(self, p: int) -> int:
        a1, a2, a3, a4, a6 = self.ainvs
        n = 1  # the point at infinity is always non-singular
        for x in range(p):
            for y in range(p):
                f = (y * y + a1 * x * y + a3 * y - x ** 3 - a2 * x * x - a4 * x - a6) % p
                if f:
                    continue
                # singular iff both partials vanish
                fx = (-3 * x * x - 2 * a2 * x - a4 + a1 * y) % p
                fy = (2 * y + a1 * x + a3) % p
                if fx == 0 and fy == 0:
                    continue
                n += 1
        return n

    def is_semistable(self) -> bool:
        return all(self.reduction_type(p) != ADDITIVE for p in self.bad_primes())

    def require_semistable(self) -> None:
        bad = [p for p in self.bad_primes() if self.reduction_type(p) == ADDITIVE]
        if bad:
            raise Refuse(f"additive reduction at {bad}: outside the implemented domain")

    def conductor(self) -> int:
        """For a semistable curve the conductor is the radical of Delta."""
        self.require_semistable()
        n = 1
        for p in self.bad_primes():
            n *= p
        return n

    # ── Tamagawa numbers ────────────────────────────────────────────────
    def tamagawa(self, p: int) -> int:
        """c_p, exactly, for a semistable curve in a minimal model.

        Good reduction gives 1. Multiplicative reduction is Kodaira type I_n
        with n = v_p(Delta); the component group is Z/n when split, and when
        non-split only its 2-torsion survives Frobenius, giving gcd(2, n)."""
        t = self.reduction_type(p)
        if t == GOOD:
            return 1
        if t == ADDITIVE:
            raise Refuse(f"Tamagawa number at additive prime {p} not implemented")
        n = self.disc_factors()[p]
        return n if t == SPLIT else gcd(2, n)

    def tamagawa_product(self) -> int:
        self.require_semistable()
        prod = 1
        for p in self.bad_primes():
            prod *= self.tamagawa(p)
        return prod

    # ── root number ─────────────────────────────────────────────────────
    def root_number(self) -> int:
        """The sign of the functional equation, exactly, for semistable E.

        eps = w_inf * prod_p w_p with w_inf = -1, w_p = +1 at good primes,
        w_p = -1 at split multiplicative primes and +1 at non-split ones.
        Hence eps = (-1)^(1 + #split). Rank parity predicts rank = 0 mod 2
        exactly when eps = +1."""
        self.require_semistable()
        splits = sum(1 for p in self.bad_primes() if self.reduction_type(p) == SPLIT)
        return -1 if (1 + splits) % 2 else 1

    # ── Frobenius traces ────────────────────────────────────────────────
    def ap(self, p: int) -> int:
        """a_p, exactly.

        Good p, odd: complete the square. y^2 + (a1 x + a3) y = g(x) has
        1 + chi(D(x)) solutions in y for D(x) = (a1 x + a3)^2 + 4 g(x), so
        #E(F_p) = p + 1 + sum_x chi(D(x)) and a_p = -sum_x chi(D(x)).
        Good p = 2: counted directly. Bad p: +1 / -1 / 0 by reduction type."""
        t = self.reduction_type(p)
        if t == SPLIT:
            return 1
        if t == NONSPLIT:
            return -1
        if t == ADDITIVE:
            return 0
        if p == 2:
            return 3 - self._count_nonsingular(2)
        a1, a2, a3, a4, a6 = self.ainvs
        s = 0
        e = (p - 1) // 2
        for x in range(p):
            d = ((a1 * x + a3) ** 2 + 4 * (x ** 3 + a2 * x * x + a4 * x + a6)) % p
            if d == 0:
                continue
            s += 1 if pow(d, e, p) == 1 else -1
        return -s

    def an_upto(self, limit: int) -> List[int]:
        """a_1 .. a_limit by Hecke multiplicativity. Exact integers.

        a_{p^{k+1}} = a_p a_{p^k} - p a_{p^{k-1}} at good p, a_{p^k} = a_p^k at
        bad p, and a_{mn} = a_m a_n for coprime m, n."""
        a = [0] * (limit + 1)
        if limit >= 1:
            a[1] = 1
        sieve = bytearray([1]) * (limit + 1)
        sieve[0:2] = b"\x00\x00"
        for i in range(2, isqrt(limit) + 1):
            if sieve[i]:
                sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
        primes = [i for i in range(2, limit + 1) if sieve[i]]
        ap = {p: self.ap(p) for p in primes}
        good = {p: (self.disc % p != 0) for p in primes}
        for p in primes:
            pk, prev, cur = p, 1, ap[p]
            a[p] = cur
            while pk * p <= limit:
                pk *= p
                nxt = ap[p] * cur - (p * prev if good[p] else 0)
                a[pk] = nxt
                prev, cur = cur, nxt
        # multiplicative extension
        for n in range(2, limit + 1):
            if sieve[n]:
                continue
            # split n as p^k * m with gcd(p, m) = 1
            p = next(q for q in primes if n % q == 0)
            pk = p
            while n % (pk * p) == 0:
                pk *= p
            m = n // pk
            if m > 1:
                a[n] = a[pk] * a[m]
        return a

    # ── torsion ─────────────────────────────────────────────────────────
    def torsion_order(self, primes_used: int = 20) -> int:
        """|E(Q)_tors|, exactly, by an EXHAUSTIVE search over a proven range.

        Work on the integral model E' : Y^2 = X^3 + b2 X^2 + 8 b4 X + 16 b6,
        isomorphic to E over Q by (x, y) -> (4x, 8y + 4 a1 x + 4 a3), so the
        torsion subgroups agree. Nagell-Lutz: every torsion point of E' has
        INTEGER coordinates and Y^2 divides disc(E'). Hence

            0 <= f(X) = Y^2 <= |disc|,

        which confines X to a range that is computed, not assumed:
          * all real roots of f lie within Fujiwara's bound R, and f < 0 below
            the smallest root, so X >= -R;
          * f increases past R, so doubling from R finds an X_hi beyond which
            f(X) > |disc|.
        Enumerating [-R, X_hi] is therefore COMPLETE -- no torsion point can
        escape it. Each integral point's order is then decided exactly by the
        group law (Mazur bounds the order by 16, and a non-integral multiple
        proves infinite order by Nagell-Lutz again).

        A reduction-theoretic upper bound is computed as an INDEPENDENT
        cross-check: E(Q)_tors injects into E(F_p) at good odd p, so the order
        must divide gcd_p #E(F_p). It is not used to derive the answer -- that
        bound stalls at the largest torsion in the isogeny class, since
        #E(F_p) is an isogeny invariant. Disagreement is a refusal.
        """
        order = 1 + len(self._integral_torsion_points())
        g = 0
        used, p = 0, 3
        while used < primes_used and p < 10 ** 6:
            if self.disc % p != 0:
                cnt = p + 1 - self.ap(p)
                g = cnt if g == 0 else gcd(g, cnt)
                used += 1
            p += 2
            while not _is_probable_prime(p):
                p += 2
        if g and g % order:
            raise Refuse(f"torsion {order} does not divide the reduction bound {g}")
        return order

    def _torsion_search_range(self):
        """The proven X-range of the exhaustive torsion search: (low, high)."""
        A2, A4, A6 = self.b2, 8 * self.b4, 16 * self.b6
        disc = (-4 * A2 ** 3 * A6 + A2 * A2 * A4 * A4 + 18 * A2 * A4 * A6
                - 4 * A4 ** 3 - 27 * A6 * A6)
        if disc == 0:
            raise Refuse("integral model is singular")
        B = abs(disc)

        def f(X):
            return X ** 3 + A2 * X * X + A4 * X + A6

        # Fujiwara: every root r satisfies |r| <= 2 max(|A2|, |A4|^1/2, |A6|^1/3)
        def iroot(n, k):
            r = int(round(abs(n) ** (1.0 / k))) + 2
            while r ** k > abs(n):
                r -= 1
            return r + 1

        R = 2 * max(abs(A2), iroot(A4, 2), iroot(A6, 3), 1)
        hi = R
        while f(hi) <= B:
            hi *= 2
        return -R, hi, B, (A2, A4, A6)

    def _integral_torsion_points(self):
        low, high, B, (A2, A4, A6) = self._torsion_search_range()
        if high - low > 5_000_000:
            raise Refuse(f"proven torsion search range has {high - low} points: too large")
        out = []
        for X in range(low, high + 1):
            rhs = X ** 3 + A2 * X * X + A4 * X + A6
            if rhs < 0 or rhs > B:
                continue
            Y = isqrt(rhs)
            if Y * Y != rhs:
                continue
            for YY in ({Y, -Y} if Y else {0}):
                if self._order_of((X, YY), A2, A4, A6):
                    out.append((X, YY))
        return out

    @staticmethod
    def _add(P, Q, A2, A4, A6):
        """Group law on Y^2 = X^3 + A2 X^2 + A4 X + A6 over Q, exact."""
        from fractions import Fraction
        if P is None:
            return Q
        if Q is None:
            return P
        x1, y1 = Fraction(P[0]), Fraction(P[1])
        x2, y2 = Fraction(Q[0]), Fraction(Q[1])
        if x1 == x2 and y1 == -y2:
            return None
        if P == Q:
            if y1 == 0:
                return None
            lam = (3 * x1 * x1 + 2 * A2 * x1 + A4) / (2 * y1)
        else:
            lam = (y2 - y1) / (x2 - x1)
        x3 = lam * lam - A2 - x1 - x2
        y3 = lam * (x1 - x3) - y1
        if x3.denominator != 1 or y3.denominator != 1:
            return (x3, y3)
        return (int(x3), int(y3))

    def _order_of(self, P, A2, A4, A6, cap: int = 16):
        """Order of P if at most cap (Mazur: torsion order is at most 16),
        else 0. Non-integral coordinates appearing mid-way prove infinite
        order by Nagell-Lutz."""
        Q = P
        for k in range(1, cap + 1):
            if Q is None:
                return k
            if not isinstance(Q[0], int):
                return 0
            Q = self._add(Q, P, A2, A4, A6)
        return 0
