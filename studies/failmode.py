#!/usr/bin/env python3
"""WHICH model classes produce stamps that don't survive? The risk is not
uniform — if it concentrates in specific families, that is directly
actionable: raise the evidence bar for those families only."""
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
        if len(t)>=30 and not any(abs(v)>10**60 for v in t[:20]) and len(set(t[:14]))>=3:
            SEQS.append((p[0],t))
        if len(SEQS)>=6000: break
SHOW=14
by=collections.defaultdict(lambda:[0,0])   # class -> [survived, failed]
examples=collections.defaultdict(list)
for anum,t in SEQS:
    shown=t[:SHOW]; hold=t[SHOW:]
    if len(hold)<8: continue
    try: inv=collapse(list(shown))
    except Exception: continue
    if not inv.verified: continue
    try: full=[int(x) for x in inv.predict(len(t))]
    except Exception: continue
    if full[:SHOW]!=shown: continue
    mc=inv.model_class
    if full[SHOW:len(t)]==hold: by[mc][0]+=1
    else:
        by[mc][1]+=1
        k=next(i for i in range(len(hold)) if full[SHOW+i]!=hold[i])
        if len(examples[mc])<2:
            examples[mc].append((anum,SHOW+k+1,full[SHOW+k],hold[k]))
print(f"corpus {len(SEQS):,} | shown {SHOW} terms each\n")
print(f"{'model class':32s} {'ok':>6} {'fail':>6} {'survival':>9}")
print("-"*58)
rows=sorted(by.items(),key=lambda kv:-(kv[1][0]+kv[1][1]))
for mc,(s,f) in rows:
    tot=s+f
    if tot<4: continue
    print(f"{mc:32s} {s:>6} {f:>6} {s/tot:>8.1%}")
print("\n-- where the risk concentrates (survival < 70%, n>=8) --")
for mc,(s,f) in rows:
    tot=s+f
    if tot>=8 and s/tot<0.70:
        print(f"  {mc}: {s}/{tot} = {s/tot:.0%}")
        for e in examples[mc]:
            print(f"     {e[0]} diverges at term {e[1]}: predicted {e[2]} vs actual {e[3]}")
json.dump({k:v for k,v in by.items()},open("failmode.json","w"),indent=1)
