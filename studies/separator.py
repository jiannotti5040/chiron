#!/usr/bin/env python3
"""THE QUESTION: does the engine already compute a signal that predicts
whether its own stamp will survive?

Capture EVERY stamp with its full certificate features, label it by whether
the rule survived every unseen term, and look for a separator. If one exists,
the engine can report calibrated confidence instead of a bare VERIFIED.
"""
import sys,json,collections,statistics
sys.path.insert(0,"/Users/jacobiannotti/Desktop/Jacob-s-Portfolio-Vault/Primus/src")
from primus.engine import collapse
SHOW=14
rows=[]
seen=0
with open("oeis/stripped") as f:
    for line in f:
        if line.startswith("#"): continue
        p=line.strip().split(" ",1)
        if len(p)!=2: continue
        try: t=[int(x) for x in p[1].strip().strip(",").split(",") if x]
        except ValueError: continue
        if len(t)<SHOW+10: continue
        if any(abs(v)>10**60 for v in t[:SHOW]): continue
        if len(set(t[:SHOW]))<3: continue
        seen+=1
        if seen>25000: break
        shown=t[:SHOW]; hold=t[SHOW:]
        try: inv=collapse(list(shown))
        except Exception: continue
        if not inv.verified: continue
        try: full=[int(x) for x in inv.predict(len(t))]
        except Exception: continue
        if full[:SHOW]!=shown: continue
        survived = full[SHOW:len(t)]==hold
        d=inv.to_dict()
        rows.append({
          "anum":p[0],"survived":survived,"model_class":inv.model_class,
          "model_bits":d.get("model_bits"),"surface_bits":d.get("surface_bits"),
          "compression_ratio":d.get("compression_ratio"),
          "fit_score":d.get("fit_score"),"residual_bits":d.get("residual_bits"),
          "n_params":len(str(d.get("params",""))),
          "holdout_len":len(hold),
          "max_abs":max(abs(v) for v in shown),
          "growth": (abs(shown[-1])+1)/(abs(shown[0])+1),
        })
        if len(rows)%200==0: print(f"  collected {len(rows)} stamps (scanned {seen})",flush=True)
print(f"\nTOTAL STAMPS CAPTURED: {len(rows)}")
S=[r for r in rows if r["survived"]]; F=[r for r in rows if not r["survived"]]
print(f"  survived {len(S)}   failed {len(F)}   ({len(S)/len(rows):.1%} survival)\n")
def cmp(field):
    a=[r[field] for r in S if isinstance(r.get(field),(int,float))]
    b=[r[field] for r in F if isinstance(r.get(field),(int,float))]
    if len(a)<10 or len(b)<10: return None
    ma,mb=statistics.median(a),statistics.median(b)
    return (field,ma,mb,(ma-mb))
print(f"{'feature':22s} {'median SURVIVED':>17s} {'median FAILED':>15s} {'separation':>12s}")
print("-"*70)
for fl in ("compression_ratio","model_bits","surface_bits","residual_bits",
           "fit_score","n_params","holdout_len","max_abs","growth"):
    c=cmp(fl)
    if c: print(f"{c[0]:22s} {c[1]:>17.3f} {c[2]:>15.3f} {c[3]:>12.3f}")
json.dump(rows,open("separator_rows.json","w"))
print(f"\nwrote separator_rows.json")
