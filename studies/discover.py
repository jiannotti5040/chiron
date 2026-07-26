#!/usr/bin/env python3
"""Run Chiron's exact rule-recovery across ALL of OEIS and find sequences
where it recovers a rule that then predicts terms it never saw.

Protocol per sequence (the engine's own discipline, applied at scale):
  1. show the engine only the FIRST 14 terms
  2. if it refuses -> refuse. No guessing, no second chances.
  3. if it VERIFIES, take the recovered rule and predict every remaining
     term OEIS has, and compare EXACTLY
  4. a hit = the rule reproduces ALL held-out terms exactly

Step 4 is the whole point: the engine saw 14 terms; the b-file may hold
hundreds. A rule surviving that many unseen terms is not a curve fit.
"""
import sys, json, os
sys.path.insert(0,"/Users/jacobiannotti/Desktop/Jacob-s-Portfolio-Vault/Primus/src")
from primus.engine import collapse

SHOW=14
lo,hi=int(sys.argv[1]),int(sys.argv[2])
out=[]; seen=0; verified=0; held=0; refused=0
with open("oeis/stripped") as f:
    for line in f:
        if line.startswith("#"): continue
        parts=line.strip().split(" ",1)
        if len(parts)!=2: continue
        anum=parts[0]
        try: n=int(anum[1:])
        except ValueError: continue
        if not (lo<=n<hi): continue
        try:
            terms=[int(x) for x in parts[1].strip().strip(",").split(",") if x]
        except ValueError: continue
        seen+=1
        if len(terms)<SHOW+8: continue          # need real holdout
        if any(abs(t)>10**60 for t in terms[:SHOW]): continue
        shown=terms[:SHOW]; hold=terms[SHOW:]
        if len(set(shown))<3: continue          # skip constant/trivial
        try:
            inv=collapse(list(shown))
        except Exception:
            refused+=1; continue
        if not inv.verified:
            refused+=1; continue
        verified+=1
        try:
            full=[int(x) for x in inv.predict(len(terms))]
        except Exception:
            continue
        if full[:SHOW]!=shown:                  # must reproduce what it saw
            continue
        pred=full[SHOW:len(terms)]
        if pred==hold and len(hold)>=8:
            held+=1
            out.append({"anum":anum,"model_class":inv.model_class,
                        "shown":SHOW,"heldout_confirmed":len(hold),
                        "params":str(inv.params)[:220],
                        "first_terms":shown[:8]})
        if seen%2000==0:
            print(f"  {anum} | scanned {seen} verified {verified} HOLDOUT-CONFIRMED {held}",flush=True)
print(f"\nRANGE {lo}-{hi}: scanned {seen}  engine-verified {verified}  "
      f"HOLDOUT-CONFIRMED {held}  refused {refused}")
json.dump(out,open(f"discovered_{lo}_{hi}.json","w"),indent=1)
