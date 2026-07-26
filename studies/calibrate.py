#!/usr/bin/env python3
"""THE CALIBRATION CURVE: what is a VERIFIED stamp actually worth?

Vary how many terms the engine sees (10..34). For each, measure how often a
stamp survives every remaining term it never saw. Nobody has measured this.
If the curve rises, the engine's evidence rule is sound and the residual risk
is purely a function of evidence supplied.
"""
import sys,json,collections
sys.path.insert(0,"/Users/jacobiannotti/Desktop/Jacob-s-Portfolio-Vault/Primus/src")
from primus.engine import collapse

SEQS=[]
with open("oeis/stripped") as f:
    for line in f:
        if line.startswith("#"): continue
        p=line.strip().split(" ",1)
        if len(p)!=2: continue
        try: t=[int(x) for x in p[1].strip().strip(",").split(",") if x]
        except ValueError: continue
        if len(t)>=46 and not any(abs(v)>10**60 for v in t[:40]) and len(set(t[:14]))>=3:
            SEQS.append((p[0],t))
        if len(SEQS)>=12000: break
print(f"corpus: {len(SEQS):,} OEIS sequences with >=46 terms\n")
print(f"{'shown':>6} {'stamped':>8} {'survived':>9} {'failed':>7} {'survival':>9}  {'refused':>8}")
print("-"*58)
curve=[]
for SHOW in (10,12,14,18,22,26,30,34):
    st=su=fa=rf=0
    for anum,t in SEQS:
        shown=t[:SHOW]; hold=t[SHOW:]
        if len(hold)<8: continue
        try: inv=collapse(list(shown))
        except Exception: rf+=1; continue
        if not inv.verified: rf+=1; continue
        st+=1
        try: full=[int(x) for x in inv.predict(len(t))]
        except Exception: continue
        if full[:SHOW]!=shown: continue
        if full[SHOW:len(t)]==hold: su+=1
        else: fa+=1
    rate=su/st if st else 0
    curve.append({"shown":SHOW,"stamped":st,"survived":su,"failed":fa,
                  "survival_rate":rate,"refused":rf})
    print(f"{SHOW:>6} {st:>8,} {su:>9,} {fa:>7,} {rate:>8.1%}  {rf:>8,}")
json.dump(curve,open("calibration_curve.json","w"),indent=1)
print()
first,last=curve[0],curve[-1]
print(f"survival at {first['shown']} terms shown: {first['survival_rate']:.1%}")
print(f"survival at {last['shown']} terms shown: {last['survival_rate']:.1%}")
