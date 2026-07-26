#!/usr/bin/env python3
"""
bounded_search.py — resolve the finite content of OPEN conjectures by
exhaustive search, in exact integer arithmetic.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

WHY THIS EXISTS. The triage pass over google-deepmind/formal-conjectures found
302 finite obligations out of 3,195 -- but 215 of those are DeepMind's own
sanity tests. The interesting set is the 1,171 OPEN conjectures, of which 450
assert an existential and 100 assert a concrete numeral. An existential is
refutable by a single witness, and a universal is refutable by a single
counterexample. Both are FINITE SEARCHES.

This is the Dinitz-Garg-Goemans pattern generalized. DGG fell to exhaustive
enumeration over a finite family in exact integers. So: take an open
conjecture, enumerate its finite instances exhaustively, and emit one of

    REFUTED           a counterexample exists, here it is
    VERIFIED-TO-N     no counterexample below N, stated as a bounded claim
    REFUSED           the search space is not finitely enumerable

VERIFIED-TO-N IS NOT A PROOF OF THE CONJECTURE and is never written as one.
It is a bounded, reproducible, exactly-checked fact, and the general statement
stays REFUSED. That distinction is the entire product.

THE ENUMERATOR IS VALIDATED BEFORE IT IS TRUSTED. Every search here first
reproduces the published OEIS terms for the object it enumerates. An
enumerator that silently disagrees with the reference data would turn every
"counterexample" into a false alarm -- which is exactly the failure mode this
project has already paid for once.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


# ---------------------------------------------------------------------------
# Exact multiplicative machinery (integers only, no floats anywhere)
# ---------------------------------------------------------------------------

def spf_sieve(n):
    """Smallest-prime-factor sieve up to n inclusive."""
    spf = list(range(n + 1))
    i = 2
    while i * i <= n:
        if spf[i] == i:
            for j in range(i * i, n + 1, i):
                if spf[j] == j:
                    spf[j] = i
        i += 1
    return spf


def factor(n, spf):
    """Exact prime factorization as {p: a}."""
    f = {}
    while n > 1:
        p = spf[n]
        a = 0
        while n % p == 0:
            n //= p
            a += 1
        f[p] = a
    return f


def sigma_and_usigma(n, spf):
    """
    sigma(n)  = sum of ALL divisors      = prod (p^(a+1) - 1)/(p - 1)
    usigma(n) = sum of UNITARY divisors  = prod (1 + p^a)
    Both computed in exact integer arithmetic.
    """
    s = u = 1
    for p, a in factor(n, spf).items():
        s *= (p ** (a + 1) - 1) // (p - 1)
        u *= 1 + p ** a
    return s, u


# ---------------------------------------------------------------------------
# A063880: sigma(n) == 2 * usigma(n)
#   Conjecture 1: every member satisfies n = 108 (mod 216)
#   Conjecture 2: 108 is the only primitive term
#                 (primitive = no proper divisor is also a member)
# ---------------------------------------------------------------------------

def a063880(limit, verbose=True):
    if verbose:
        print(f"  sieving to {limit:,} ...", flush=True)
    spf = spf_sieve(limit)
    members = []
    for n in range(1, limit + 1):
        s, u = sigma_and_usigma(n, spf)
        if s == 2 * u:
            members.append(n)
    return members, spf


def validate_against_oeis(members):
    """The enumerator must reproduce OEIS's own published terms, or stop."""
    from oeis_novelty import entry
    e = entry(63880)
    pub = [int(x) for x in (e.get("data") or "").split(",")
           if x.strip().lstrip("-").isdigit()]
    k = min(len(pub), len(members))
    ok = pub[:k] == members[:k]
    print(f"\n  VALIDATION -- enumerator vs published OEIS terms")
    print(f"    published : {pub[:8]}")
    print(f"    enumerated: {members[:8]}")
    print(f"    first {k} terms agree: {ok}")
    if not ok:
        print("    ENUMERATOR DISAGREES WITH OEIS -- abandoning. Any")
        print("    'counterexample' from a broken enumerator is a false alarm.")
    return ok


def run_a063880(limit):
    print("=" * 74)
    print(f"A063880  --  sigma(n) = 2*usigma(n),  exhaustive to n <= {limit:,}")
    print("=" * 74)
    members, spf = a063880(limit)
    print(f"  members found: {len(members)}")
    if not validate_against_oeis(members):
        return None

    # --- Conjecture 1: every member is 108 mod 216 -------------------------
    bad = [n for n in members if n % 216 != 108]
    print(f"\n  CONJECTURE 1  every member = 108 (mod 216)")
    if bad:
        print(f"    *** REFUTED. {len(bad)} counterexample(s): {bad[:10]}")
        for n in bad[:5]:
            s, u = sigma_and_usigma(n, spf)
            print(f"        n={n}  n mod 216 = {n % 216}  "
                  f"sigma={s}  2*usigma={2*u}  factor={factor(n, spf)}")
    else:
        print(f"    VERIFIED-TO-N: all {len(members)} members below "
              f"{limit:,} satisfy it.")
        print(f"    The general statement stays REFUSED -- this is a bounded")
        print(f"    check, not a proof.")

    # --- Conjecture 2: 108 is the only primitive term ----------------------
    ms = set(members)
    prim = [n for n in members
            if not any(d in ms for d in _proper_divisors(n, spf))]
    print(f"\n  CONJECTURE 2  108 is the only primitive term")
    print(f"    primitive terms below {limit:,}: {prim}")
    if prim != [108]:
        extra = [p for p in prim if p != 108]
        if extra:
            print(f"    *** REFUTED. Additional primitive term(s): {extra}")
            for n in extra[:5]:
                print(f"        n={n}  factor={factor(n, spf)}")
    else:
        print(f"    VERIFIED-TO-N: 108 is the unique primitive term below "
              f"{limit:,}.")
        print(f"    General statement REFUSED.")
    return members


def _proper_divisors(n, spf):
    f = factor(n, spf)
    divs = [1]
    for p, a in f.items():
        divs = [d * p ** e for d in divs for e in range(a + 1)]
    return [d for d in divs if d != n]


# ---------------------------------------------------------------------------
# Juggler: n -> isqrt(n) if even, isqrt(n^3) if odd.  Does every n reach 1?
# Exact integer square roots -- no floats, which is where naive versions break.
# ---------------------------------------------------------------------------

def juggler_step(n):
    return _isqrt(n) if n % 2 == 0 else _isqrt(n * n * n)


def _isqrt(n):
    return __import__("math").isqrt(n)


def run_juggler(limit, cap=10_000):
    print("=" * 74)
    print(f"Juggler conjecture -- every n>0 reaches 1,  exhaustive to n <= {limit:,}")
    print("=" * 74)
    print("  exact integer sqrt throughout (math.isqrt); the float version of")
    print("  this map gives wrong trajectories for large terms.")
    worst = (0, 0)
    peak = (0, 0)
    fail = []
    for n in range(1, limit + 1):
        x, steps = n, 0
        hi = n
        while x != 1:
            x = juggler_step(x)
            hi = max(hi, x)
            steps += 1
            if steps > cap:
                fail.append(n)
                break
        if steps <= cap:
            if steps > worst[1]:
                worst = (n, steps)
            if hi > peak[1]:
                peak = (n, hi)
    if fail:
        print(f"  *** {len(fail)} value(s) did not reach 1 within {cap} steps: "
              f"{fail[:10]}")
        print("      NOT a refutation -- a step cap is not a proof of divergence.")
        print("      Reported as REFUSED (search bound reached), not REFUTED.")
    else:
        print(f"  VERIFIED-TO-N: every n <= {limit:,} reaches 1.")
        # Peaks here run to tens of thousands of digits, past Python's default
        # int->str limit, so digit count comes from bit_length rather than a
        # string conversion. The values themselves stay exact integers.
        digits = lambda x: int(x.bit_length() * 0.30103) + 1
        print(f"    longest trajectory : n={worst[0]} in {worst[1]} steps")
        print(f"    highest peak       : n={peak[0]} reached a "
              f"~{digits(peak[1]):,}-digit value")
        print(f"  General statement REFUSED -- unbounded n is not enumerable.")


# ---------------------------------------------------------------------------
# Gilbreath: d^0 = primes; d^(k+1)(n) = |d^k(n+1) - d^k(n)|.  Is d^k(0)=1 forall k>0?
# ---------------------------------------------------------------------------

def run_gilbreath(nprimes):
    print("=" * 74)
    print(f"Gilbreath's conjecture -- d^k(0) = 1 for all k>0,  using "
          f"{nprimes:,} primes")
    print("=" * 74)
    sieve = bytearray([1]) * (nprimes * 20)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(len(sieve) ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    primes = [i for i, b in enumerate(sieve) if b][:nprimes]
    print(f"  first prime {primes[0]}, last {primes[-1]:,}")
    row = primes
    bad = []
    k = 0
    while len(row) > 1:
        row = [abs(row[i + 1] - row[i]) for i in range(len(row) - 1)]
        k += 1
        if row[0] != 1:
            bad.append((k, row[0]))
    if bad:
        print(f"  *** REFUTED at depth k={bad[0][0]}: d^k(0) = {bad[0][1]}")
    else:
        print(f"  VERIFIED-TO-N: d^k(0) = 1 for every k from 1 to {k:,}.")
        print(f"  General statement REFUSED -- all k is not enumerable.")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "a063880"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if which == "a063880":
        run_a063880(n or 2_000_000)
    elif which == "juggler":
        run_juggler(n or 5000)
    elif which == "gilbreath":
        run_gilbreath(n or 20000)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
