#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
A300362 — extend a Zhi-Wei Sun conjecture BEYOND its published range.

Conjecture (OEIS A300362): a(n) > 0 for all n = 0,1,2,...
  a(n) = #{(x,y,z,w) >= 0 : n^2 = x^2+y^2+z^2+w^2,
                            x + 2y is a square,
                            (z + 2w)/3 is a square,
                            w is even}

WHY THIS TARGET. The b-file stops at n = 1000. A published conjecture is
checked as far as its author computed and no further; everything past that
bound is unswept. Published data never contradicts a published claim -- the
author checks that before submitting -- so a counterexample, if one exists,
lives beyond where they stopped.

METHOD. Meet in the middle, exact integers.
  Left  : x + 2y = s^2  =>  x = s^2 - 2y.  Enumerate (s,y), store x^2+y^2.
  Right : z + 2w = 3t^2 =>  z = 3t^2 - 2w, w even. Enumerate (t,w), store z^2+w^2.
  a(n) > 0  iff  some right value B has (n^2 - B) among the left values.
Bounds: x,z <= n so s^2 <= 3n and 3t^2 <= 3n, giving s <= sqrt(3n), t <= sqrt(n).
"""
import sys, time
from math import isqrt

def is_sq(v):
    if v < 0: return False
    r = isqrt(v); return r*r == v

def left_values(N, n):
    """A = x^2+y^2 with x = s^2-2y >= 0, A <= N."""
    vals = set()
    smax = isqrt(3*n) + 2
    for s in range(smax+1):
        ss = s*s
        for y in range(ss//2 + 1):
            x = ss - 2*y
            A = x*x + y*y
            if A <= N: vals.add(A)
    return vals

def a_positive(n):
    """True iff a(n) > 0. Also returns a witness."""
    N = n*n
    L = left_values(N, n)
    tmax = isqrt(n) + 2
    for t in range(tmax+1):
        tt = 3*t*t
        for w in range(0, tt//2 + 1, 2):        # w even
            z = tt - 2*w
            B = z*z + w*w
            if B > N: continue
            if (N - B) in L:
                return True, (t, w, z, N-B)
    return False, None

def a_count(n):
    """Full count, for validating against published terms."""
    N = n*n; c = 0
    smax = isqrt(3*n)+2; tmax = isqrt(n)+2
    left = {}
    for s in range(smax+1):
        ss=s*s
        for y in range(ss//2+1):
            x=ss-2*y; A=x*x+y*y
            if A<=N: left[(x,y)]=A
    for t in range(tmax+1):
        tt=3*t*t
        for w in range(0,tt//2+1,2):
            z=tt-2*w; B=z*z+w*w
            if B>N: continue
            for (x,y),A in left.items():
                if A+B==N: c+=1
    return c

if __name__ == "__main__":
    sys.path.insert(0,'studies')
    from oeis_novelty import entry, bfile
    e=entry(300362)
    data=[int(x) for x in e['data'].split(',') if x.strip().lstrip('-').isdigit()]
    bt,st=bfile(300362,len(data))
    print("="*74); print("A300362 — extending a Sun conjecture past its published range")
    print("="*74)
    print(f"  b-file: {st}, {len(bt)} terms (n = 0..{len(bt)-1})")
    print(f"  minimum published value: {min(bt)}  -> conjecture holds on the published range\n")

    print("  VALIDATION — recomputed counts vs published terms:")
    ok=True
    for n in range(0,26):
        c=a_count(n)
        m = c==bt[n]
        ok &= m
        if n<12 or not m:
            print(f"    n={n:3d}  computed {c:4d}   published {bt[n]:4d}   {'ok' if m else 'MISMATCH'}")
    print(f"  encoder reproduces published terms n=0..25: {ok}")
    if not ok:
        print("  ENCODER INVALID — refusing to extend."); sys.exit(1)

    start=len(bt)
    print(f"\n  EXTENDING beyond the published range, from n={start} ...")
    t0=time.time(); zeros=[]
    n=start
    while time.time()-t0 < 900:
        pos,wit=a_positive(n)
        if not pos:
            zeros.append(n)
            print(f"  *** a({n}) = 0  — CANDIDATE COUNTEREXAMPLE")
            break
        if n % 250 == 0:
            print(f"    n={n:,}  ({time.time()-t0:.0f}s)  still positive", flush=True)
        n+=1
    print(f"\n  extended to n = {n:,}  ({time.time()-t0:.0f}s)")
    print(f"  counterexamples found: {zeros if zeros else 'NONE'}")
    if not zeros:
        print(f"  a(n) > 0 confirmed for every n from {start} to {n:,},")
        print(f"  territory the published b-file does not cover.")
