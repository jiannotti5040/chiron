"""EVERY SEC balance sheet, 2009 -> 2025, exact identity check.
   Assets == LiabilitiesAndStockholdersEquity, same accession, same instant.
   Exact integers. Refuse rather than guess. Polite to data.sec.gov."""
import json, urllib.request, time, sys
UA={"User-Agent":"Chiron exact-reconciliation research jiannotti1@gmail.com"}
def get(u):
    for attempt in range(3):
        try:
            r=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(r,timeout=60) as f:
                return json.loads(f.read().decode())
        except urllib.error.HTTPError as e:
            if e.code==404: return None
            time.sleep(2)
        except Exception: time.sleep(2)
    return None

periods=[f"CY{y}Q{q}I" for y in range(2009,2026) for q in (1,2,3,4)]
tot_chk=tot_exact=tot_ref=0; viol=[]; per_period=[]
for i,P in enumerate(periods):
    A=get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/USD/{P}.json")
    time.sleep(0.35)
    B=get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/LiabilitiesAndStockholdersEquity/USD/{P}.json")
    time.sleep(0.35)
    if not A or not B: continue
    Ad={r["cik"]:r for r in A["data"]}; Bd={r["cik"]:r for r in B["data"]}
    c=e=rf=0
    for cik,a in Ad.items():
        b=Bd.get(cik)
        if not b or a["accn"]!=b["accn"] or a["end"]!=b["end"]: rf+=1; continue
        c+=1
        gap=int(a["val"])-int(b["val"])
        if gap==0: e+=1
        else:
            viol.append({"period":P,"cik":cik,"name":a["entityName"],"accn":a["accn"],
                "end":a["end"],"assets":int(a["val"]),"L_plus_E":int(b["val"]),
                "gap":gap,"rel":abs(gap)/int(a["val"]) if int(a["val"]) else None})
    tot_chk+=c; tot_exact+=e; tot_ref+=rf
    per_period.append({"period":P,"checked":c,"exact":e,"violations":c-e,"refused":rf})
    print(f"  {P}: checked {c:5d}  violations {c-e:3d}  refused {rf:5d}", flush=True)

print(f"\n{'='*66}")
print(f"TOTAL CHECKED   {tot_chk:,}")
print(f"TIE EXACTLY     {tot_exact:,}")
print(f"VIOLATIONS      {len(viol):,}")
print(f"REFUSED         {tot_ref:,}")
print(f"exact rate      {tot_exact/tot_chk:.4%}")
viol.sort(key=lambda v:-abs(v["gap"]))
print(f"\nTOP 25 BY ABSOLUTE GAP:")
for v in viol[:25]:
    print(f"  {v['end']}  {v['name'][:34]:34s} ${v['gap']:>16,}  {v['rel']:.2%}")
json.dump({"checked":tot_chk,"exact":tot_exact,"refused":tot_ref,
           "per_period":per_period,"violations":viol},
          open("sec_full_history.json","w"),indent=1)
print(f"\nwrote sec_full_history.json")
