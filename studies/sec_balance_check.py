"""The identity every balance sheet MUST satisfy:
   Assets == LiabilitiesAndStockholdersEquity
Same accession AND same end-date. Exact integers. Refuse otherwise."""
import json, urllib.request
UA={"User-Agent":"Chiron exact-reconciliation research jiannotti1@gmail.com"}
def get(u):
    r=urllib.request.Request(u,headers=UA)
    with urllib.request.urlopen(r,timeout=90) as f: return json.loads(f.read().decode())
tot=chk=exact=off=refused=0; findings=[]
for P in ["CY2024Q4I","CY2024Q3I","CY2024Q2I"]:
    try:
        A={r["cik"]:r for r in get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/USD/{P}.json")["data"]}
        B={r["cik"]:r for r in get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/LiabilitiesAndStockholdersEquity/USD/{P}.json")["data"]}
    except Exception as e:
        print(P,"fetch failed",e); continue
    p_chk=p_off=0
    for cik,a in A.items():
        b=B.get(cik)
        if not b: refused+=1; continue
        # BOTH must come from the same filing AND cover the same instant
        if a["accn"]!=b["accn"] or a["end"]!=b["end"]: refused+=1; continue
        chk+=1; p_chk+=1
        gap=int(a["val"])-int(b["val"])
        if gap==0: exact+=1
        else:
            off+=1; p_off+=1
            findings.append({"period":P,"cik":cik,"name":a["entityName"],"accn":a["accn"],
                "end":a["end"],"assets":int(a["val"]),"L_plus_E":int(b["val"]),
                "gap":gap,"rel":abs(gap)/int(a["val"])})
    print(f"{P}: checked {p_chk:5d}  not-tying {p_off}")
print(f"\nTOTAL CHECKED {chk}   EXACT {exact}   VIOLATIONS {off}   REFUSED {refused}")
print(f"exact-identity rate: {exact/chk:.3%}")
findings.sort(key=lambda f:-abs(f["gap"]))
print(f"\n=== FILINGS WHERE THE BALANCE SHEET DOES NOT BALANCE ===")
for f in findings[:20]:
    print(f"  {f['name'][:34]:34s} {f['end']}  gap ${f['gap']:>14,} ({f['rel']:.2%})  {f['accn']}")
json.dump(findings,open("sec_identity_violations.json","w"),indent=1)
print(f"\n{len(findings)} violations -> sec_identity_violations.json")
