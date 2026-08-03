#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
bfile_consistency.py — do OEIS b-files agree with the `data` field of the
same entry?

Author: Jacob Iannotti. Apache-2.0.

An entry publishes its first terms twice: in the `data` field, and again as
the opening lines of its b-file. These are maintained separately, often years
apart and by different contributors. If they DISAGREE, one of them is wrong
and it is an unambiguous, independently checkable data error -- no parsing
judgement, no domain to misread, no conjecture to misinterpret.

This is the cleanest possible target: two published records of the same object
that must be identical.

Synthesized b-files are excluded. OEIS generates those from `data` on demand,
so they agree trivially and prove nothing.
"""
import sys, json, time, urllib.request, urllib.parse
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from oeis_novelty import bfile
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) chiron-research/0.6.4"

def search(q, pages):
    out=[]
    for st in range(0,pages*10,10):
        u="https://oeis.org/search?q="+urllib.parse.quote(q)+f"&fmt=json&start={st}"
        try:
            r=urllib.request.Request(u,headers={"User-Agent":UA})
            d=json.loads(urllib.request.urlopen(r,timeout=60).read().decode("utf-8","replace"))
        except Exception: break
        if isinstance(d,dict): d=d.get("results") or []
        if not d: break
        out+=d; time.sleep(2)
    return out

if __name__=="__main__":
    pages=int(sys.argv[1]) if len(sys.argv)>1 else 25
    print("="*74); print("B-FILE CONSISTENCY — b-file vs `data`, same entry")
    print("="*74)
    print("Two published records of the same terms, maintained separately.")
    print("A disagreement is an unambiguous data error.\n")
    seen=set(); checked=0; synth=0; mism=[]
    for q in ['"Table of n, a(n)"','keyword:nice','keyword:core','"b-file"']:
        for e in search(q,pages):
            a=e["number"]
            if a in seen: continue
            seen.add(a)
            data=[int(x) for x in (e.get("data") or "").split(",")
                  if x.strip().lstrip("-").isdigit()]
            if len(data)<10: continue
            try: bt,st=bfile(a,len(data))
            except Exception: continue
            if st!="real": synth+=1; continue
            k=min(len(bt),len(data)); checked+=1
            bad=[(i,data[i],bt[i]) for i in range(k) if data[i]!=bt[i]]
            if bad:
                mism.append(dict(anum=a,name=(e.get("name") or "")[:96],
                                 n_data=len(data),n_bfile=len(bt),diffs=bad[:5]))
                print(f"  *** A{a:06d}  data and b-file DISAGREE")
                print(f"      {(e.get('name') or '')[:86]}")
                print(f"      (index, data, b-file): {bad[:4]}")
    print(f"\n  entries seen {len(seen)}   real b-files compared {checked}   "
          f"synthesized skipped {synth}   MISMATCHES {len(mism)}")
    json.dump(mism, open("studies/bfile_mismatches.json","w"), indent=1)
    if not mism:
        print("  every real b-file agrees with its entry's data field exactly.")
