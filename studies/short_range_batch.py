#!/usr/bin/env python3
"""
short_range_batch.py — conjectures with under ~80 published terms.

The shortest verification ranges in OEIS are the most unswept ground in it.
Each encoder must reproduce every published term before it may extend.
"""
import sys, time
from math import gcd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from oeis_novelty import entry, bfile

def a157409(n):
    """min{k>0 : floor(2^n / 3^k) mod 6 == 3}, else 0."""
    p = 1 << n
    k = 1; d = 3
    while d <= p:
        if (p // d) % 6 == 3: return k
        k += 1; d *= 3
    return 0

def _a261(mult, add, N):
    """a(1)=1, a(n+1) = |a(n) - gcd(a(n), mult*n+add)| ; return list a(1..N)."""
    out = [1]
    for n in range(1, N):
        a = out[-1]
        out.append(abs(a - gcd(a, mult*n + add)))
    return out

def run_seq(label, anum, gen, budget=240):
    """gen(N) -> list of a(offset..offset+N-1)"""
    e = entry(anum)
    data = [int(x) for x in e['data'].split(',') if x.strip().lstrip('-').isdigit()]
    bt, st = bfile(anum, len(data))
    off = int((e.get('offset') or '1,1').split(',')[0])
    print(f"\n{'='*74}\n{label}  (A{anum:06d})\n{'='*74}")
    print(f"  {e.get('name','')[:98]}")
    print(f"  b-file: {st}, {len(bt)} terms")
    got = gen(len(bt))
    ok = got[:len(bt)] == bt
    print(f"  encoder reproduces ALL {len(bt)} published terms: {ok}")
    if not ok:
        bad=[(i+off,got[i],bt[i]) for i in range(min(len(bt),len(got))) if got[i]!=bt[i]]
        print(f"    first mismatches (n, computed, published): {bad[:5]}")
        print("  ENCODER INVALID — refusing to extend."); return
    t0=time.time(); N=len(bt)
    while time.time()-t0 < budget:
        N = int(N*2)
        seq = gen(N)
        z = [i+off for i,v in enumerate(seq) if v == 0 and i >= len(bt)]
        if z:
            print(f"  *** a({z[0]}) = 0 — CANDIDATE COUNTEREXAMPLE (first of {len(z)})")
            return
    print(f"  extended n = {off+len(bt)} .. {off+N-1:,}  ({time.time()-t0:.0f}s)")
    print(f"  counterexamples: NONE   ({N-len(bt):,} values beyond the b-file)")

def run_fn(label, anum, f, budget=240):
    e = entry(anum)
    data=[int(x) for x in e['data'].split(',') if x.strip().lstrip('-').isdigit()]
    bt,st = bfile(anum, len(data))
    off = int((e.get('offset') or '1,1').split(',')[0])
    print(f"\n{'='*74}\n{label}  (A{anum:06d})\n{'='*74}")
    print(f"  {e.get('name','')[:98]}")
    print(f"  b-file: {st}, {len(bt)} terms")
    ok = all(f(off+i)==bt[i] for i in range(len(bt)))
    print(f"  encoder reproduces ALL {len(bt)} published terms: {ok}")
    if not ok:
        bad=[(off+i,f(off+i),bt[i]) for i in range(len(bt)) if f(off+i)!=bt[i]]
        print(f"    mismatches: {bad[:5]}")
        print("  ENCODER INVALID — refusing to extend."); return
    t0=time.time(); n=off+len(bt)
    while time.time()-t0 < budget:
        if f(n)==0:
            print(f"  *** a({n}) = 0 — CANDIDATE COUNTEREXAMPLE"); return
        n+=1
    print(f"  extended n = {off+len(bt)} .. {n:,}  ({time.time()-t0:.0f}s)")
    print(f"  counterexamples: NONE   ({n-off-len(bt):,} values beyond the b-file)")

if __name__ == "__main__":
    run_fn("A157409  floor(2^n/3^k) mod 6 = 3", 157409, a157409, budget=300)
    run_seq("A261303  a(n+1)=|a(n)-gcd(a(n),3n+2)|", 261303,
            lambda N: _a261(3,2,N), budget=200)
    run_seq("A261304  a(n+1)=|a(n)-gcd(a(n),4n+3)|", 261304,
            lambda N: _a261(4,3,N), budget=200)
