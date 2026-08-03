#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
A261303 / A261304 — testing the conjecture the entries ACTUALLY make.

A text search for "a(n) > 0" flagged these, and a(89)=0 looked like a
counterexample. It is not: zeros are normal here, present in the published
data at n = 2, 5, 23. The entries never claim positivity. What they claim is:

  A261303:  a(n+1) = |a(n) - gcd(a(n), 3n+2)|, a(1) = 1.
            "It is conjectured that a(n) = 0 implies that 3n+2 = a(n+1) is
             prime, for all n > 2."   (cf. A186255)

  A261304:  a(n+1) = |a(n) - gcd(a(n), 4n+3)|, a(1) = 1.
            "It is conjectured that a(n) = 0 implies that 4n+3 = a(n+1) is
             prime."                  (cf. A186256)

That is a genuine open conjecture and it is finitely refutable: find an n with
a(n) = 0 whose corresponding 3n+2 (or 4n+3) is COMPOSITE. Only ~80 terms are
published, so almost the entire claim is unswept.

This is a Rowland-type prime-generating recurrence. Rowland (2008) proved the
analogous a(n+1) = a(n) + gcd(n, a(n)) always yields primes; these variants
are conjectured, not proved.
"""
import sys, time
from math import gcd, isqrt
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from oeis_novelty import entry, bfile

def isprime(m):
    if m < 2: return False
    if m % 2 == 0: return m == 2
    d = 3
    while d*d <= m:
        if m % d == 0: return False
        d += 2
    return True

def run(anum, mult, add, label, budget=300):
    e = entry(anum)
    data=[int(x) for x in e['data'].split(',') if x.strip().lstrip('-').isdigit()]
    bt,st = bfile(anum, len(data))
    print(f"\n{'='*74}\n{label}  (A{anum:06d})\n{'='*74}")
    print(f"  claim: a(n) = 0  =>  {mult}n+{add} is PRIME")
    print(f"  published terms: {len(bt)}")

    # validate the recurrence against every published term
    seq=[1]
    for n in range(1, len(bt)):
        seq.append(abs(seq[-1] - gcd(seq[-1], mult*n+add)))
    ok = seq == bt
    print(f"  encoder reproduces ALL {len(bt)} published terms: {ok}")
    if not ok:
        bad=[(i+1,seq[i],bt[i]) for i in range(len(bt)) if seq[i]!=bt[i]]
        print(f"    mismatches: {bad[:5]}"); print("  INVALID — refusing."); return

    # confirm the claim holds on the PUBLISHED range first (a sanity check:
    # if it failed here the conjecture would already be known false)
    pub_zeros=[i+1 for i,v in enumerate(bt) if v==0 and i+1>2]
    pub_bad=[n for n in pub_zeros if not isprime(mult*n+add)]
    print(f"  zeros in the published range: n={pub_zeros}")
    print(f"  of those, {mult}n+{add} composite: {pub_bad if pub_bad else 'none'}")

    print(f"\n  EXTENDING beyond n={len(bt)} ...")
    t0=time.time(); a=1; n=1; zeros=0; viol=[]
    while time.time()-t0 < budget:
        a = abs(a - gcd(a, mult*n+add))
        n += 1
        if a == 0 and n > 2:
            zeros += 1
            v = mult*n+add
            if not isprime(v):
                viol.append((n, v))
                print(f"  *** a({n}) = 0 but {mult}*{n}+{add} = {v:,} is COMPOSITE")
                break
        if n % 2_000_000 == 0:
            print(f"    n={n:,}  zeros seen {zeros:,}  ({time.time()-t0:.0f}s)", flush=True)
    print(f"\n  reached n = {n:,}   zeros encountered: {zeros:,}   "
          f"({time.time()-t0:.0f}s)")
    print(f"  violations: {viol if viol else 'NONE'}")
    if not viol:
        print(f"  every zero up to n={n:,} produced a PRIME — "
              f"{n-len(bt):,} values beyond the published range.")

if __name__ == "__main__":
    run(261303, 3, 2, "A261303  a(n)=0 => 3n+2 prime")
    run(261304, 4, 3, "A261304  a(n)=0 => 4n+3 prime")
