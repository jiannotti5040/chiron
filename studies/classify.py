"""Taxonomy of HOW a filed balance sheet fails to balance.
Exact ratio tests only — no fuzzy matching, no judgment calls."""
import json, collections
from decimal import Decimal
d=json.load(open("sec_full_history.json"))
V=d["violations"]
def cls(v):
    a=Decimal(v["assets"]); b=Decimal(v["L_plus_E"]); g=Decimal(v["gap"])
    if b==0: return "counterparty_zero"          # L+E tagged as 0
    if a==0: return "assets_zero"
    r=a/b
    if b==-a: return "sign_flip"                 # L+E is exactly -Assets
    for p,name in [(10,"scale_10x"),(100,"scale_100x"),(1000,"scale_1000x"),
                   (1000000,"scale_1e6")]:
        if r==p or r==Decimal(1)/p: return name
    if abs(g)<=2: return "rounding_1_2_dollars"
    if abs(g)<=1000: return "small_le_1k"
    return "other_material"
buckets=collections.Counter(cls(v) for v in V)
print(f"655 violations, classified by exact ratio test:\n")
tot=len(V)
for k,c in buckets.most_common():
    print(f"  {k:24s} {c:4d}  {c/tot:6.1%}")
print(f"\n=== SIGN FLIPS (L+E == exactly -Assets) — unambiguous tagging defect ===")
sf=[v for v in V if cls(v)=="sign_flip"]
sf.sort(key=lambda v:-abs(v["gap"]))
for v in sf[:10]:
    print(f"  {v['end']}  {v['name'][:36]:36s} ${v['gap']:>15,}")
print(f"  ...{len(sf)} total")
print(f"\n=== SCALE ERRORS (exact power-of-ten ratio) ===")
sc=[v for v in V if cls(v).startswith("scale")]
sc.sort(key=lambda v:-abs(v["gap"]))
for v in sc[:8]:
    print(f"  {v['end']}  {v['name'][:36]:36s} ${v['gap']:>15,}  {cls(v)}")
print(f"  ...{len(sc)} total")
print(f"\n=== MATERIAL, UNEXPLAINED (>$1k, no clean pattern) ===")
mat=[v for v in V if cls(v)=="other_material"]
mat.sort(key=lambda v:-abs(v["gap"]))
for v in mat[:12]:
    print(f"  {v['end']}  {v['name'][:36]:36s} ${v['gap']:>15,}  {v['rel']:.1%}")
print(f"  ...{len(mat)} total")
# repeat offenders
rep=collections.Counter(v["name"] for v in V)
print(f"\n=== REPEAT OFFENDERS (same filer, multiple periods) ===")
for n,c in rep.most_common(10):
    if c>1: print(f"  {c:2d}x  {n[:52]}")
json.dump({"buckets":dict(buckets),
           "sign_flips":sf,"scale_errors":sc,"material":mat},
          open("sec_taxonomy.json","w"),indent=1,default=str)
print("\nwrote sec_taxonomy.json")
