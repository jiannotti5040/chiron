#!/usr/bin/env python3
"""
A179210 with a SEGMENTED sieve — how far can validation actually reach?

The flat bytearray sieve capped at 2e8 and validation failed: the witness for
n=31 sits at 217,795,247, just past the limit, and the witness for n=52 at
18,553,663,237. Reporting the unfound ones as counterexamples would have been
eight false claims at once.

A segmented sieve removes the memory wall (it holds only sqrt(N) base primes
plus one window at a time), so the question becomes how far COMPUTE reaches,
not how far RAM does.
"""
import sys, time
from math import isqrt
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from oeis_novelty import entry, bfile

def base_primes(n):
    s=bytearray([1])*(n+1); s[0:2]=b"\x00\x00"
    for i in range(2,isqrt(n)+1):
        if s[i]: s[i*i::i]=bytearray(len(s[i*i::i]))
    return [i for i,b in enumerate(s) if b]

def segmented_triples(N, seg=1<<22):
    """Yield consecutive primes up to N using O(sqrt N) memory."""
    bp = base_primes(isqrt(N)+1)
    lo = 2
    while lo <= N:
        hi = min(lo+seg-1, N)
        size = hi-lo+1
        blk = bytearray([1])*size
        for p in bp:
            if p*p > hi: break
            start = max(p*p, ((lo+p-1)//p)*p)
            blk[start-lo::p] = bytearray(len(blk[start-lo::p]))
        if lo == 2: blk[0]=1
        for i in range(size):
            if blk[i]:
                v = lo+i
                if v >= 2: yield v
        lo = hi+1

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv)>1 else 2_000_000_000
    e=entry(179210)
    data=[int(x) for x in e['data'].split(',') if x.strip().lstrip('-').isdigit()]
    bt,st=bfile(179210,len(data))
    print("="*74)
    print(f"A179210 — segmented sieve to {N:,}")
    print("="*74)
    print(f"  published terms: {len(bt)};  largest published witness: {max(bt):,}")
    print(f"  this sieve reaches {N:,} -> can validate terms whose witness is below that\n")

    t0=time.time(); best={}; prev=cur=None; cnt=0
    for v in segmented_triples(N):
        if prev is not None:
            g1=cur-prev; g2=v-cur
            if g1 and g2 % g1 == 0:
                n=g2//g1
                if n>=1 and n not in best: best[n]=cur
        prev,cur=cur,v; cnt+=1
        if cnt % 50_000_000 == 0:
            print(f"    {cnt:,} primes  ({time.time()-t0:.0f}s)", flush=True)
    print(f"  swept {cnt:,} primes in {time.time()-t0:.0f}s\n")

    reach=[i for i,p in enumerate(bt,1) if p<=N]
    got=[i for i in reach if best.get(i,0)==bt[i-1]]
    print(f"  published terms whose witness is within reach: {len(reach)} of {len(bt)}")
    print(f"  of those, reproduced EXACTLY: {len(got)}")
    bad=[i for i in reach if best.get(i,0)!=bt[i-1]]
    if bad:
        print(f"  MISMATCHES: {[(i,best.get(i,0),bt[i-1]) for i in bad[:6]]}")
    else:
        print(f"  every in-reach published term reproduced exactly.")
    print(f"\n  terms still OUT of reach (witness > {N:,}): "
          f"{[i for i in range(1,len(bt)+1) if bt[i-1]>N]}")
    print("  Those cannot be validated at this bound, so nothing is claimed")
    print("  about n > 69 — the encoder is only trusted where it is checkable.")
