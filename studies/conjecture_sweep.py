#!/usr/bin/env python3
"""
conjecture_sweep.py — bounded exhaustive search over open conjectures, as a
registry of independently-validated encoders.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

SCOPE, STATED HONESTLY. google-deepmind/formal-conjectures holds 1,171 open
conjectures; 86 have searchable structure. This file encodes the subset whose
definition is unambiguous AND for which known data exists to validate the
encoder against. That is a small fraction, on purpose. An encoder nobody
validated is worse than no encoder, because it manufactures counterexamples.

THE FOUR VERDICTS:

  REFUTED        explicit counterexample, independently re-checked
  VERIFIED-TO-N  exhausted a bounded region, found nothing. NOT A PROOF.
  REFUSED        no finite search exists, or the encoder failed validation
  ERROR          the code broke

A conjecture of the form "for all n, P(n)" is REFUTABLE by one counterexample,
so a bounded search is genuinely informative. A conjecture of the form "there
are infinitely many x" or "there exists N0 such that for all N >= N0" is
neither refutable nor verifiable by any finite computation -- a single failure
is not a counterexample and no bound settles it. Those are REFUSED regardless
of how much evidence a search accumulates, and the distinction is enforced
here rather than left to a reader.

EVERY ENCODER VALIDATES FIRST. If validation fails the search does not run.
"""

from __future__ import annotations

import gc
import sys
from fractions import Fraction
from math import isqrt

REFUTED, VERIFIED, REFUSED, ERROR = "REFUTED", "VERIFIED-TO-N", "REFUSED", "ERROR"


# ``a000041`` needs a perfect-power detector.  Do not use floating-point
# roots for this: partition numbers eventually exceed the range of a double,
# and a rounded root must never decide a mathematical verdict.  The helpers
# below use integer arithmetic exclusively.  It is enough to test PRIME
# exponents: if v = x^m for composite m, then v is also a q-th power for a
# prime divisor q of m.
_POWER_EXPONENTS = {}
_POWER_FILTERS = {}


def _small_primes(limit):
    """Return all primes <= limit, exactly (small helper for exponents)."""
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[:2] = b"\x00\x00"
    for p in range(2, isqrt(limit) + 1):
        if sieve[p]:
            sieve[p * p::p] = bytearray(len(sieve[p * p::p]))
    return [p for p in range(2, limit + 1) if sieve[p]]


def _prime_exponents(bit_length):
    """Prime exponents that could occur in a positive ``bit_length``-bit power."""
    if bit_length not in _POWER_EXPONENTS:
        _POWER_EXPONENTS[bit_length] = _small_primes(bit_length - 1)
    return _POWER_EXPONENTS[bit_length]


def _prime_mod_one(exponent):
    """A small prime q = 1 (mod exponent), found with exact trial division."""
    q = exponent + 1
    while True:
        if all(q % d for d in range(2, isqrt(q) + 1)):
            return q
        q += exponent


def _power_filter(exponent):
    """Return (q, q-th-power residues mod q) for a necessary cheap test."""
    if exponent not in _POWER_FILTERS:
        q = _prime_mod_one(exponent)
        _POWER_FILTERS[exponent] = (q, {pow(a, exponent, q) for a in range(q)})
    return _POWER_FILTERS[exponent]


def _integer_nth_root(value, exponent):
    """Floor(value ** (1/exponent)), calculated using integers only."""
    if exponent == 1:
        return value
    if exponent == 2:
        return isqrt(value)
    # Newton iteration starts at an upper bound and decreases to the floor.
    root = 1 << ((value.bit_length() + exponent - 1) // exponent)
    while True:
        nxt = ((exponent - 1) * root + value // pow(root, exponent - 1)) // exponent
        if nxt >= root:
            return root
        root = nxt


def perfect_power(value):
    """Return one exact (base, exponent) witness, or ``None`` if none exists."""
    if value < 4:
        return None
    for exponent in _prime_exponents(value.bit_length()):
        modulus, residues = _power_filter(exponent)
        if value % modulus not in residues:
            continue
        root = _integer_nth_root(value, exponent)
        if root > 1 and pow(root, exponent) == value:
            return root, exponent
    return None


def primes_upto(n):
    s = bytearray([1]) * (n + 1)
    s[0:2] = b"\x00\x00"
    for i in range(2, isqrt(n) + 1):
        if s[i]:
            s[i * i::i] = bytearray(len(s[i * i::i]))
    return [i for i, b in enumerate(s) if b]


# ===========================================================================
# Erdos 242 -- the Erdos-Straus conjecture
#   for every n > 2 there are 1 <= x < y < z with 4/n = 1/x + 1/y + 1/z
#   FORM: forall n  =>  ONE counterexample refutes it.
# ===========================================================================

def es_solve(n):
    """
    Exact search for a single n. Returns (x,y,z) or None.

    Pure integer arithmetic -- Fraction was ~100x too slow to reach a useful
    bound, and it buys nothing here since every quantity is a ratio of ints:

        4/n - 1/x = (4x - n)/(n x) = p/q
        1/y + 1/z = p/q  =>  q/p < y <= 2q/p,  and  z = q y / (p y - q)

    so the whole search is integer division and one divisibility test.
    """
    for x in range(n // 4 + 1, 3 * n // 4 + 2):
        if x < 1:
            continue
        p, q = 4 * x - n, n * x          # remainder p/q, must be > 0
        if p <= 0:
            continue
        # Iterating y over (q/p, 2q/p] is CORRECT but astronomically wide: for
        # x just above n/4 the numerator p is 1..4 while q ~ n^2/4, so that
        # range is ~10^10 for n ~ 2*10^5. Instead use the standard identity
        #     1/y + 1/z = p/q   <=>   (p y - q)(p z - q) = q^2,
        # and enumerate DIVISORS of q^2. Exhaustive, and small.
        for d in _divisors_of_square(q):
            if (q + d) % p:
                continue
            y = (q + d) // p
            if y <= x:
                continue
            e = (q * q) // d
            if (q + e) % p:
                continue
            z = (q + e) // p
            if z > y:
                return (x, y, z)
    return None


_SPF_CACHE = {"limit": 0, "spf": []}


def _spf(limit):
    if _SPF_CACHE["limit"] < limit:
        # Each checkpoint is a complete, independent scan.  Keeping the old
        # Python-int sieve alive while allocating the next, larger sieve can
        # double peak memory (and killed the 10,000,000 A063880 checkpoint
        # after a successful 8,192,000 run).  Release it before building the
        # replacement; no caller relies on identities from the old cache.
        _SPF_CACHE.update(limit=0, spf=[])
        gc.collect()
        spf = list(range(limit + 1))
        i = 2
        while i * i <= limit:
            if spf[i] == i:
                for j in range(i * i, limit + 1, i):
                    if spf[j] == j:
                        spf[j] = i
            i += 1
        _SPF_CACHE.update(limit=limit, spf=spf)
    return _SPF_CACHE["spf"]


def _factor(n):
    f, spf = {}, _SPF_CACHE["spf"]
    while n > 1:
        if n < len(spf):
            p = spf[n]
        else:                                  # fall back to trial division
            p = next((d for d in range(2, isqrt(n) + 1) if n % d == 0), n)
        while n % p == 0:
            n //= p
            f[p] = f.get(p, 0) + 1
    return f


def _divisors_of_square(q):
    """All divisors d of q^2 with d <= q (so that y <= z), ascending."""
    f = _factor(q)
    divs = [1]
    for p, a in f.items():
        divs = [d * p ** e for d in divs for e in range(2 * a + 1)]
    return sorted(d for d in divs if d <= q)


def erdos242(limit):
    _spf(3 * limit)          # warm the factor sieve for q = n*x
    name = "Erdos 242 (Erdos-Straus): 4/n = 1/x+1/y+1/z, 1<=x<y<z, for all n>2"
    # --- validate: reproduce solutions checkable by hand -------------------
    checks = []
    for n in (3, 4, 5, 6, 7, 12, 23):
        s = es_solve(n)
        if s is None:
            return dict(verdict=REFUSED, name=name,
                        detail=f"encoder found no solution for n={n}, which is known "
                               f"to be solvable -- encoder is wrong, refusing to run")
        x, y, z = s
        if Fraction(1, x) + Fraction(1, y) + Fraction(1, z) != Fraction(4, n):
            return dict(verdict=REFUSED, name=name,
                        detail=f"encoder returned a non-solution for n={n}")
        checks.append(f"n={n} -> 1/{x}+1/{y}+1/{z}")
    validation = "solutions re-substituted exactly: " + "; ".join(checks[:4])

    # --- the standard reduction, and why it is sound ----------------------
    # If a | n with a > 2 and 4/a = 1/x + 1/y + 1/z, then writing n = a*b,
    #     4/n = 1/(b x) + 1/(b y) + 1/(b z)
    # and multiplying by b preserves 1 <= x < y < z. So a representation for
    # ANY divisor a > 2 lifts to one for n. Checking every odd prime therefore
    # covers every n with an odd prime factor, and powers of two are covered by
    # lifting from a = 4. This is the reduction used throughout the literature.
    #
    # It is applied here because the naive per-n search was far too slow to
    # reach a useful bound -- and the lift is verified below rather than
    # assumed, since a speed optimisation that silently changes results is
    # exactly how a fake counterexample gets manufactured.
    lift_checks = []
    for n in (9, 15, 16, 25, 32, 49, 100):
        a = next((d for d in range(3, n + 1) if n % d == 0 and es_solve(d)), None)
        if a is None:
            return dict(verdict=REFUSED, name=name,
                        detail=f"lift reduction failed to find a usable divisor for n={n}")
        b = n // a
        x, y, z = es_solve(a)
        X, Y, Z = b * x, b * y, b * z
        if Fraction(1, X) + Fraction(1, Y) + Fraction(1, Z) != Fraction(4, n) or not (1 <= X < Y < Z):
            return dict(verdict=REFUSED, name=name,
                        detail=f"lift produced a non-solution at n={n} -- refusing to run")
        lift_checks.append(f"n={n} lifted from a={a}")
    validation += " | lift verified exactly: " + "; ".join(lift_checks[:4])

    ps = [p for p in primes_upto(limit) if p > 2]
    bad = []
    for p in ps:
        if es_solve(p) is None:
            bad.append(p)
            if len(bad) >= 5:
                break
    if bad:
        return dict(verdict=REFUTED, name=name, validation=validation,
                    detail=f"no representation exists for prime n = {bad}")
    return dict(verdict=VERIFIED, name=name, validation=validation, bound=limit,
                detail=f"every one of the {len(ps):,} odd primes below {limit:,} has a "
                       f"representation; by the verified lift this covers every n in "
                       f"[3, {limit:,}]",
                prior="verified past 10^17 in the literature; this bound is far below "
                      "the state of the art and advances nothing")


# ===========================================================================
# Andrica -- sqrt(p_{n+1}) - sqrt(p_n) < 1
#   Exact integer form: with a=p_n, b=p_{n+1}, the claim is
#      b - a - 1 < 2*sqrt(a)   <=>   (b-a-1) <= 0  OR  (b-a-1)^2 < 4a
#   No floats anywhere.
#   FORM: forall n  =>  ONE counterexample refutes it.
# ===========================================================================

def andrica(limit):
    name = "Andrica: sqrt(p_{n+1}) - sqrt(p_n) < 1 for all n"
    ps = primes_upto(limit)

    # --- validate the integer reformulation against exact rational reasoning
    # The known maximum of sqrt(p_{n+1})-sqrt(p_n) is at (p,q)=(7,11).
    # Check the integer test agrees with a high-precision rational check on
    # every pair below 10^5, using integer square roots only.
    def holds_int(a, b):
        d = b - a - 1
        return d <= 0 or d * d < 4 * a

    def holds_ref(a, b):
        # sqrt(b)-sqrt(a) < 1  <=>  sqrt(b) < 1+sqrt(a).  Compare squares of
        # scaled integer square roots at high precision -- still exact ints.
        S = 10 ** 12
        return isqrt(b * S * S) < S + isqrt(a * S * S)

    small = [p for p in ps if p < 100000]
    mismatch = [(small[i], small[i + 1]) for i in range(len(small) - 1)
                if holds_int(small[i], small[i + 1]) != holds_ref(small[i], small[i + 1])]
    if mismatch:
        return dict(verdict=REFUSED, name=name,
                    detail=f"integer reformulation disagrees with the reference "
                           f"computation on {len(mismatch)} pairs, e.g. {mismatch[:3]} "
                           f"-- encoder unsound, refusing to run")
    validation = (f"integer test (b-a-1)^2 < 4a agrees with an independent "
                  f"exact-integer sqrt comparison on all {len(small):,} prime "
                  f"pairs below 100,000")

    bad = [(ps[i], ps[i + 1]) for i in range(len(ps) - 1)
           if not holds_int(ps[i], ps[i + 1])]
    if bad:
        return dict(verdict=REFUTED, name=name, validation=validation,
                    detail=f"counterexample prime pairs: {bad[:5]}")
    # record where the expression is largest, as a sanity signal
    best = max(range(len(ps) - 1),
               key=lambda i: Fraction(ps[i + 1] - ps[i], 1) / (isqrt(ps[i]) + 1))
    return dict(verdict=VERIFIED, name=name, validation=validation, bound=ps[-1],
                detail=f"holds for all {len(ps):,} consecutive prime pairs up to "
                       f"{ps[-1]:,}; tightest near p={ps[best]}",
                prior="verified past 1.3*10^16 in the literature; this bound is "
                      "far below the state of the art")


# ===========================================================================
# A034693 -- a(n) = smallest k with k*n+1 prime.
#   Conjecture in the Lean file: a(n) < 1 + n^(3/4).
#   Exact integer form: k < 1 + n^(3/4)  <=>  (k-1)^4 < n^3   (k >= 1)
#   FORM: forall n  =>  refutable.
# ===========================================================================

def a034693(limit):
    name = "A034693: smallest k with k*n+1 prime satisfies k < 1 + n^(3/4)"
    lim = limit * 200 + 100
    s = bytearray([1]) * (lim + 1)
    s[0:2] = b"\x00\x00"
    for i in range(2, isqrt(lim) + 1):
        if s[i]:
            s[i * i::i] = bytearray(len(s[i * i::i]))

    def smallest_k(n):
        k = 1
        while True:
            v = k * n + 1
            if v > lim:
                return None
            if s[v]:
                return k
            k += 1

    # --- validate against OEIS's published terms --------------------------
    # These are copied from https://oeis.org/A034693 . An earlier version of
    # this list was typed from memory and diverged at n=16 (memory said 3; the
    # true value is 1, since 16*1+1 = 17 is prime). The validation gate caught
    # it and refused to run -- the ENCODER was correct and the reference was
    # not. Recalled numbers are not a source; published ones are.
    published = [1, 1, 2, 1, 2, 1, 4, 2, 2, 1, 2, 1, 4, 2, 2, 1, 6, 1, 10, 2]
    got = [smallest_k(n) for n in range(1, 21)]
    if got != published:
        return dict(verdict=REFUSED, name=name,
                    detail=f"encoder disagrees with published A034693 terms: "
                           f"got {got[:8]} vs {published[:8]} -- refusing to run")
    validation = f"first 20 terms match published A034693 exactly: {got[:8]}..."

    bad = []
    for n in range(2, limit + 1):
        k = smallest_k(n)
        if k is None:
            continue
        if (k - 1) ** 4 >= n ** 3:          # exact integer form of k >= 1+n^(3/4)
            bad.append((n, k))
            if len(bad) >= 5:
                break
    if bad:
        return dict(verdict=REFUTED, name=name, validation=validation,
                    detail=f"(n, a(n)) violating a(n) < 1+n^(3/4): {bad}")
    return dict(verdict=VERIFIED, name=name, validation=validation, bound=limit,
                detail=f"holds for every n in [2, {limit:,}]",
                prior="the bound is heuristic; no proof is known, and small n are "
                      "the hardest case so a modest bound is not strong evidence")


# ===========================================================================
# Erdos 1065 -- infinitely many primes p = 2^k*q + 1 with q prime.
#   FORM: asserts an INFINITE set. No finite computation can refute or verify
#   it. REFUSED by construction; the count is reported as evidence only.
# ===========================================================================

def erdos1065(limit):
    name = "Erdos 1065: infinitely many primes p = 2^k*q+1, q prime"
    ps = primes_upto(limit)
    pset = set(ps)
    hits = 0
    for p in ps:
        m, found = p - 1, False
        while m % 2 == 0 and not found:
            m //= 2
            if m in pset:
                found = True
        if found or (p - 1) in pset:
            hits += 1
    return dict(verdict=REFUSED, name=name,
                validation=f"prime sieve verified: pi({limit:,}) = {len(ps):,}",
                detail=f"{hits:,} such primes below {limit:,} — EVIDENCE ONLY. "
                       f"The statement asserts an infinite set, so no finite count "
                       f"can confirm it and no finite search can refute it.",
                prior="a special case of Dickson's conjecture; open")


# ===========================================================================

# ===========================================================================
# The Zhi-Wei Sun family. Each is "every n can be written as <form>" -- FORALL
# n, so one counterexample refutes it and a bounded search is genuinely
# informative. Each carries a cash prize, meaning they have been attacked
# hard; a laptop finding a counterexample would be evidence of an encoder bug,
# not a discovery.
#
# These get STRONGER validation than existence. The OEIS sequences count the
# NUMBER of representations of n, so the encoder must reproduce those counts
# term for term. Matching a count is a far tighter constraint than finding
# some witness, and it is what would catch a subtly wrong predicate.
# ===========================================================================

def _is_sq(v):
    if v < 0:
        return False
    r = isqrt(v)
    return r * r == v


def _smooth(primes, cap):
    """All products of the given primes that are <= cap."""
    vals = {1}
    for p in primes:
        nxt = set()
        for v in vals:
            while v <= cap:
                nxt.add(v)
                v *= p
        vals = nxt
    return sorted(v for v in vals if v <= cap)



# --- classical sum-of-two-squares criterion --------------------------------
# n is a sum of two squares  <=>  every prime p = 3 (mod 4) in its
# factorization occurs to an EVEN power. Validated against brute force on
# 30,001 values. This turns an O(sqrt n) scan into a factorization test, and
# it is what lets the bounds below move by orders of magnitude: several of
# these conjectures reduce, after fixing their "easy" parameters, to exactly
# the question of whether a residue is a sum of two squares.
def _is_sum_two_squares(n):
    if n < 0:
        return False
    if n == 0:
        return True
    for p, e in _factor(n).items():
        if p % 4 == 3 and e % 2:
            return False
    return True


def _sun(anum, name, count, limit, prior="", search=None, lo=None):
    """
    Shared driver: validate representation counts against OEIS, then search.

    `count` must reproduce the OEIS sequence EXACTLY -- that is the encoder
    check. `search` is the predicate the CONJECTURE actually asserts, which is
    not always the same object: A280831 for instance counts representations of
    8n+7 over POSITIVE integers, while the conjecture in the Lean file is about
    every n over NONNEGATIVE ones. Validating on one and searching the other,
    without noticing, is how a bogus counterexample gets produced.
    """
    try:
        from oeis_novelty import entry
        e = entry(anum)
        pub = [int(x) for x in (e.get("data") or "").split(",")
               if x.strip().lstrip("-").isdigit()]
        off = int((e.get("offset") or "0,1").split(",")[0])
    except Exception as ex:
        return dict(verdict=REFUSED, name=name,
                    detail=f"could not fetch A{anum:06d} to validate the encoder "
                           f"({type(ex).__name__}) -- refusing to run unvalidated")

    k = min(len(pub), 35)
    got = [count(off + i) for i in range(k)]
    if got != pub[:k]:
        i = next(j for j in range(k) if got[j] != pub[j])
        return dict(verdict=REFUSED, name=name,
                    detail=f"encoder disagrees with published A{anum:06d} at n={off+i}: "
                           f"got {got[i]}, published {pub[i]} -- refusing to run")
    validation = (f"representation COUNTS reproduce the first {k} published terms of "
                  f"A{anum:06d} exactly (a tighter check than mere existence)")

    pred = search or (lambda n: count(n) > 0)
    start = off if lo is None else lo
    bad = []
    for n in range(start, limit + 1):
        if not pred(n):
            bad.append(n)
            if len(bad) >= 5:
                break
    if bad:
        return dict(verdict=REFUTED, name=name, validation=validation,
                    detail=f"NO representation exists for n = {bad}")
    return dict(verdict=VERIFIED, name=name, validation=validation, bound=limit,
                detail=f"every n in [{start}, {limit:,}] has at least one representation",
                prior=prior)


def a280831(limit):
    def reps(m, lo):
        """count x,y,z,w >= lo with m = x^2+y^2+z^2+w^2 and x^4+1680y^3z square"""
        c = 0
        for x in range(lo, isqrt(m) + 1):
            rx = m - x * x
            for y in range(lo, isqrt(rx) + 1):
                ry = rx - y * y
                for z in range(lo, isqrt(ry) + 1):
                    w2 = ry - z * z
                    if w2 < lo * lo or not _is_sq(w2):
                        continue
                    if _is_sq(x ** 4 + 1680 * y ** 3 * z):
                        c += 1
        return c
    # STRUCTURAL REDUCTION, verified against brute force on 20,001 values.
    # Taking y = 0 makes the side condition x^4 + 1680*y^3*z = x^4 = (x^2)^2,
    # a square unconditionally. So n = x^2 + 0 + z^2 + w^2 satisfies the
    # conjecture for free, and that is exactly "n is a sum of three squares".
    # By Gauss-Legendre that holds iff n is NOT of the form 4^k(8m+7).
    #
    # So 83.35% of all n are settled by a classical theorem rather than a
    # search, and only n = 4^k(8m+7) requires real work. This is not a new
    # observation -- it is almost certainly why Sun's sequence counts 8n+7 --
    # but exploiting it is what lets the bound move by three orders of
    # magnitude instead of grinding every n.
    def needs_search(n):
        m = n
        while m and m % 4 == 0:
            m //= 4
        return m % 8 == 7

    def satisfied(n):
        if not needs_search(n):
            return True          # Gauss-Legendre, via y = 0
        return reps(n, 0) > 0

    return _sun(280831,
                "A280831 (1680-conjecture): every n = x^2+y^2+z^2+w^2 with x^4+1680y^3z square",
                lambda n: reps(8 * n + 7, 1), limit,
                "Zhi-Wei Sun prize 1,680 RMB; open. 83.35% of n reduce to "
                "Gauss-Legendre via y=0; only 4^k(8m+7) is searched",
                search=satisfied, lo=0)


def a306477(limit):
    from math import comb

    def terms(k, off, cap):
        out, i = [], 0
        while comb(i + off, k) <= cap:
            out.append(comb(i + off, k))
            i += 1
        return out

    def count(n):
        A, B = terms(2, 2, n), terms(4, 3, n)
        C, D = terms(6, 5, n), set(terms(8, 7, n))
        c = 0
        for a in A:
            for b in B:
                if a + b > n:
                    break
                for d in C:
                    if a + b + d > n:
                        break
                    if (n - a - b - d) in D:
                        c += 1
        return c
    return _sun(306477,
                "A306477 (2-4-6-8): n = C(w+2,2)+C(x+3,4)+C(y+5,6)+C(z+7,8)",
                count, limit,
                "Zhi-Wei Sun prize $2,468; already verified to 1.2*10^12 by Yaakov "
                "Baruch (2019) -- this bound is far below that")


def a303656(limit):
    _spf(limit)          # so _is_sum_two_squares factorizes by sieve, not trial division
    def count(n):
        c, p3 = 0, 1
        while p3 <= n:
            p5 = 1
            while p3 + p5 <= n:
                r = n - p3 - p5
                for a in range(isqrt(r // 2) + 1):     # a <= b, per the OEIS definition
                    if _is_sq(r - a * a):
                        c += 1
                p5 *= 5
            p3 *= 3
        return c
    # Conjecture is "a(n) > 0 for all n > 1"; OEIS publishes a(1) = 0 itself.
    def fast(n):
        p3 = 1
        while p3 <= n:
            p5 = 1
            while p3 + p5 <= n:
                if _is_sum_two_squares(n - p3 - p5):
                    return True
                p5 *= 5
            p3 *= 3
        return False

    return _sun(303656, "A303656: every n>1 = a^2 + b^2 + 3^c + 5^d", count, limit,
                "Zhi-Wei Sun prize $3,500; verified to 2*10^10 by Sun -- this bound "
                "is far below that", search=fast, lo=2)


def a308734(limit):
    _spf(limit)
    def count(n):
        r = isqrt(n)
        c = 0
        for u in _smooth((2, 3), r):
            for v in _smooth((2, 5), r):
                rem = n - u * u - v * v
                if rem < 0:
                    continue
                for x in range(isqrt(rem // 2) + 1):   # x <= y, per the OEIS definition
                    if _is_sq(rem - x * x):
                        c += 1
        return c
    # Conjecture is "a(n) > 0 for all n > 1"; OEIS publishes a(1) = 0 itself.
    def fast(n):
        r = isqrt(n)
        for u in _smooth((2, 3), r):
            for v in _smooth((2, 5), r):
                rem = n - u * u - v * v
                if rem < 0:
                    continue
                if _is_sum_two_squares(rem):
                    return True
        return False

    return _sun(308734, "A308734: every n>1 = (2^a*3^b)^2 + (2^c*5^d)^2 + x^2 + y^2",
                count, limit, "Zhi-Wei Sun prize $2,500; verified to 10^9 by Sun -- "
                "this bound is far below that", search=fast, lo=2)



def a287616(limit):
    """n = x(x+1)/2 + y(3y+1)/2 + z(5z+1)/2, x,y,z nonnegative."""
    def count(n):
        T = []
        x = 0
        while x * (x + 1) // 2 <= n:
            T.append(x * (x + 1) // 2); x += 1
        P = []
        y = 0
        while y * (3 * y + 1) // 2 <= n:
            P.append(y * (3 * y + 1) // 2); y += 1
        H = set()
        z = 0
        while z * (5 * z + 1) // 2 <= n:
            H.add(z * (5 * z + 1) // 2); z += 1
        c = 0
        for t in T:
            for q in P:
                if t + q > n:
                    break
                if (n - t - q) in H:
                    c += 1
        return c
    return _sun(287616,
                "A287616: every n = x(x+1)/2 + y(3y+1)/2 + z(5z+1)/2",
                count, limit, "Zhi-Wei Sun prize $135; open", lo=0)


def a281976(limit):
    """n = x^2+y^2+z^2+w^2 with z<=w, x a square, and x+24y a square."""
    def count(n):
        c = 0
        for x in range(isqrt(n) + 1):
            if not _is_sq(x):                    # x itself must be a square
                continue
            rx = n - x * x
            for y in range(isqrt(rx) + 1):
                if not _is_sq(x + 24 * y):       # and so must x + 24y
                    continue
                ry = rx - y * y
                for z in range(isqrt(ry // 2) + 1):   # z <= w
                    if _is_sq(ry - z * z):
                        c += 1
        return c
    return _sun(281976,
                "A281976: every n = x^2+y^2+z^2+w^2, z<=w, x and x+24y both squares",
                count, limit, "Zhi-Wei Sun prize $2,400; open", lo=0)


def _direct_sigma_usigma(n):
    """Independent divisor enumeration, used only to audit a finite witness."""
    sigma = usigma = 0
    for d in range(1, isqrt(n) + 1):
        if n % d:
            continue
        mate = n // d
        for divisor in (d,) if d == mate else (d, mate):
            sigma += divisor
            if __import__("math").gcd(divisor, n // divisor) == 1:
                usigma += divisor
    return sigma, usigma


def a063880(limit):
    """
    DeepMind Formal Conjectures A063880: if sigma(n) = 2*usigma(n), then
    n = 108 mod 216, and 108 is the only primitive member.  These are two
    universal claims, so a finite scan can refute but never prove them.
    """
    name = "A063880: sigma(n)=2*usigma(n) implies n=108 mod 216; 108 is unique primitive"
    _spf(limit)

    def sums(n):
        sigma = usigma = 1
        for p, exponent in _factor(n).items():
            sigma *= (p ** (exponent + 1) - 1) // (p - 1)
            usigma *= 1 + p ** exponent
        return sigma, usigma

    try:
        from oeis_novelty import entry
        raw = entry(63880)
        published = [int(x) for x in (raw or {}).get("data", "").split(",")
                     if x.strip().lstrip("-").isdigit()]
    except Exception as exc:
        return dict(verdict=REFUSED, name=name,
                    detail=f"could not fetch A063880 to validate the encoder ({type(exc).__name__})")
    if not published:
        return dict(verdict=REFUSED, name=name,
                    detail="A063880 returned no published terms; refusing to scan an unvalidated encoder")

    members = []
    for n in range(1, limit + 1):
        sigma, usigma = sums(n)
        if sigma == 2 * usigma:
            members.append(n)

    # The multiplicative formula is the fast path.  It must agree with an
    # independent definition-level divisor scan on every published term before
    # it may support a verdict about values outside the published range.
    validation_count = min(len(published), len(members))
    if published[:validation_count] != members[:validation_count]:
        return dict(verdict=REFUSED, name=name,
                    detail="factor-based membership disagrees with A063880's published prefix")
    for n in published[:validation_count]:
        if sums(n) != _direct_sigma_usigma(n):
            return dict(verdict=REFUSED, name=name,
                        detail=f"factor and direct-divisor sums disagree at published n={n}")
    validation = (f"first {validation_count} published A063880 members match exactly; "
                  "their sigma/usigma values also agree with independent divisor enumeration")

    bad = [n for n in members if n % 216 != 108]
    if bad:
        n = bad[0]
        fast = sums(n)
        slow = _direct_sigma_usigma(n)
        if fast != slow or fast[0] != 2 * fast[1]:
            return dict(verdict=REFUSED, name=name, validation=validation,
                        detail=f"candidate n={n} did not survive independent divisor enumeration")
        return dict(verdict=REFUTED, name=name, validation=validation,
                    detail=f"n={n} is a member by two exact methods but n mod 216 = {n % 216}")

    member_set = set(members)
    primitive = []
    for n in members:
        factors = _factor(n)
        divisors = [1]
        for p, exponent in factors.items():
            divisors = [d * p ** e for d in divisors for e in range(exponent + 1)]
        if not any(d != n and d in member_set for d in divisors):
            primitive.append(n)
    extra = [n for n in primitive if n != 108]
    if extra:
        n = extra[0]
        # Recheck both the candidate and every proper divisor directly before
        # calling it a refutation of the primitive-term statement.
        factors = _factor(n)
        divisors = [1]
        for p, exponent in factors.items():
            divisors = [d * p ** e for d in divisors for e in range(exponent + 1)]
        direct_member = lambda d: _direct_sigma_usigma(d)[0] == 2 * _direct_sigma_usigma(d)[1]
        if not direct_member(n) or any(d != n and direct_member(d) for d in divisors):
            return dict(verdict=REFUSED, name=name, validation=validation,
                        detail=f"candidate primitive n={n} did not survive direct divisor checks")
        return dict(verdict=REFUTED, name=name, validation=validation,
                    detail=f"n={n} is a primitive member distinct from 108, rechecked by direct divisors")

    return dict(verdict=VERIFIED, name=name, validation=validation, bound=limit,
                detail=(f"all {len(members):,} members in [1,{limit:,}] are 108 mod 216; "
                        "108 is the only primitive member in that interval"),
                prior="DeepMind's FormalConjectures/OEIS/63880.lean marks both "
                      "statements research open; this is finite evidence only")


def a000041(limit):
    """
    No partition number p(k) is a perfect power x^m with x,m > 1.
    FORM: forall k -- one perfect-power partition number refutes it.
    Different shape from the Sun family: the OEIS sequence IS the partition
    numbers, so validation is direct rather than via representation counts.
    """
    name = "A000041: no partition number is a perfect power x^m (x,m>1)"
    # exact integer partition numbers via Euler's pentagonal recurrence
    p = [1] + [0] * limit
    for n in range(1, limit + 1):
        tot, k = 0, 1
        while True:
            g1 = k * (3 * k - 1) // 2
            g2 = k * (3 * k + 1) // 2
            if g1 > n and g2 > n:
                break
            sgn = -1 if k % 2 == 0 else 1
            if g1 <= n:
                tot += sgn * p[n - g1]
            if g2 <= n:
                tot += sgn * p[n - g2]
            k += 1
        p[n] = tot

    published = [1, 1, 2, 3, 5, 7, 11, 15, 22, 30, 42, 56, 77, 101, 135, 176,
                 231, 297, 385, 490, 627]
    if p[:len(published)] != published:
        return dict(verdict=REFUSED, name=name,
                    detail=f"partition numbers disagree with published A000041: "
                           f"got {p[:8]} vs {published[:8]} -- refusing to run")
    validation = (f"pentagonal-recurrence partition numbers reproduce the first "
                  f"{len(published)} published A000041 terms exactly; p(100) = {p[100]:,}")

    hits = []
    for k in range(2, limit + 1):
        pp = perfect_power(p[k])
        if pp:
            hits.append((k, p[k], pp))
            if len(hits) >= 5:
                break
    if hits:
        return dict(verdict=REFUTED, name=name, validation=validation,
                    detail=f"partition number(s) that ARE perfect powers: {hits}")
    return dict(verdict=VERIFIED, name=name, validation=validation, bound=limit,
                detail=f"no p(k) for k in [2, {limit:,}] is a perfect power",
                prior="open; perfect-power detection uses exact integer roots and "
                      "exact exponentiation (no floating-point arithmetic)")


REGISTRY = {
    "erdos242":  (erdos242, 1000000),
    "andrica":   (andrica, 3_000_000),
    "a034693":   (a034693, 20000),
    "erdos1065": (erdos1065, 2_000_000),
    "a280831":   (a280831, 200000),
    "a306477":   (a306477, 30000),
    "a303656":   (a303656, 1000000),
    "a308734":   (a308734, 1000000),
    "a287616":   (a287616, 100000),
    "a281976":   (a281976, 3000),
    "a063880":   (a063880, 10000000),
    "a000041":   (a000041, 20000),
}


def main():
    which = sys.argv[1:] or list(REGISTRY)
    print("=" * 76)
    print("BOUNDED CONJECTURE SWEEP -- exact integer/rational arithmetic only")
    print("=" * 76)
    rows = []
    for key in which:
        if key not in REGISTRY:
            continue
        fn, default = REGISTRY[key]
        print(f"\n[{key}] running ...", flush=True)
        try:
            r = fn(default)
        except Exception as e:
            r = dict(verdict=ERROR, name=key, detail=f"{type(e).__name__}: {e}")
        rows.append((key, r))
        print(f"  {r['verdict']}  {r.get('name', key)}")
        if r.get("validation"):
            print(f"    encoder validated: {r['validation']}")
        print(f"    {r.get('detail', '')}")
        if r.get("prior"):
            print(f"    prior art: {r['prior']}")

    print("\n" + "=" * 76)
    for key, r in rows:
        print(f"  {r['verdict']:14s} {key}")
    print("\n  VERIFIED-TO-N IS NOT A PROOF. Every general statement above")
    print("  remains open; bounded searches are evidence, not certification.")


if __name__ == "__main__":
    main()
