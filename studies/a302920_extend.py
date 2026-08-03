#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
A302920 — extend past its published range.

Conjecture (Zhi-Wei Sun): for any prime p there are nonnegative integers
x, y, z with  x^2 + 2*y^2 + 3*2^z = p^2.

WHY THIS ONE. The entry records that the property FAILS for the composite
m = 5884015571 = 7*17*49445509. So it is not a general fact about integers --
it is a delicate claim that holds specifically on the primes. A claim with a
known nearby failure is a better hunting ground than one that holds everywhere.

The b-file covers 6,000 primes (up to prime(6000) = 59359). Past that, unswept.

METHOD. For each prime p set N = p^2 and try z = 0,1,2,... For each z the
residue R = N - 3*2^z must be representable as x^2 + 2y^2. Classical criterion
for the form of discriminant -8: R is representable iff every prime q = 5 or 7
(mod 8) divides R to an EVEN power. Verified against brute force before use.
Exact integers only.
"""
import sys, time
from math import isqrt
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

def primes_upto(n):
    s=bytearray([1])*(n+1); s[0:2]=b"\x00\x00"
    for i in range(2,isqrt(n)+1):
        if s[i]: s[i*i::i]=bytearray(len(s[i*i::i]))
    return [i for i,b in enumerate(s) if b]

def repr_x2_2y2(R):
    """R = x^2 + 2y^2 solvable in nonnegative integers? Classical criterion."""
    if R < 0: return False
    if R == 0: return True
    m = R
    for q in (2,):
        while m % q == 0: m //= q
    d = 3
    while d*d <= m:
        if m % d == 0:
            e = 0
            while m % d == 0: m //= d; e += 1
            if d % 8 in (5,7) and e % 2: return False
        d += 2
    if m > 1 and m % 8 in (5,7): return False
    return True

def brute_x2_2y2(R):
    for y in range(isqrt(R//2)+1):
        if isqrt(R-2*y*y)**2 == R-2*y*y: return True
    return False

def works(p):
    N = p*p; z = 0
    while 3*(1 << z) <= N:
        if repr_x2_2y2(N - 3*(1 << z)): return True, z
        z += 1
    return False, None

if __name__ == "__main__":
    print("="*74); print("A302920 — extending past the published 6,000 primes")
    print("="*74)
    print("  validating the x^2+2y^2 criterion against brute force, R = 0..4000:")
    bad=[R for R in range(4001) if repr_x2_2y2(R) != brute_x2_2y2(R)]
    print(f"    criterion agrees with brute force: {not bad}"
          + (f"  MISMATCH at {bad[:5]}" if bad else ""))
    if bad: sys.exit(1)

    from oeis_novelty import entry, bfile
    e=entry(302920)
    data=[int(x) for x in e['data'].split(',') if x.strip().lstrip('-').isdigit()]
    bt,st=bfile(302920,len(data))
    print(f"\n  b-file: {st}, {len(bt)} terms -> covers the first {len(bt)} primes")

    P = primes_upto(4_000_000)
    print(f"  sieved {len(P):,} primes (up to {P[-1]:,})")
    print(f"  published range ends at prime({len(bt)}) = {P[len(bt)-1]:,}\n")

    print("  VALIDATION — recomputed vs published, first 40 primes:")
    okc = all(works(P[i])[0] == (bt[i] > 0) for i in range(40))
    print(f"    positivity matches published terms: {okc}")
    if not okc: print("    ENCODER INVALID"); sys.exit(1)

    start=len(bt)
    print(f"\n  EXTENDING from prime index {start} (p = {P[start]:,}) ...")
    t0=time.time(); fails=[]
    i=start
    while i < len(P) and time.time()-t0 < 900:
        ok,z = works(P[i])
        if not ok:
            fails.append(P[i])
            print(f"  *** p = {P[i]:,} has NO representation — CANDIDATE COUNTEREXAMPLE")
            break
        if i % 2000 == 0:
            print(f"    prime index {i:,}  p={P[i]:,}  ({time.time()-t0:.0f}s)", flush=True)
        i+=1
    print(f"\n  extended to prime index {i:,}  (p = {P[min(i,len(P)-1)]:,})  "
          f"({time.time()-t0:.0f}s)")
    print(f"  counterexamples: {fails if fails else 'NONE'}")
    if not fails:
        print(f"  every prime from index {start} to {i:,} has a representation —")
        print(f"  {i-start:,} primes beyond the published b-file.")
