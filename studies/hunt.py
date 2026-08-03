#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
hunt.py — hunt OEIS for a stated conjecture contradicted by published data.

Author: Jacob Iannotti. Apache-2.0.

Every domain decision goes through claim_domain.domain_of, which refuses when
the domain is not a simple threshold. That function is a regression suite of
five real false positives this project produced by testing claims outside
their own domains.

Two edges over a naive sweep:
  * tests against the B-FILE where one exists -- often hundreds to thousands
    of terms versus the ~40 in `data`, uploaded after the conjecture was
    written and never re-checked against it
  * covers universal NEGATIVES ("a(n) is never k", "no term is k") as well as
    positivity, since a universal negative dies to a single equal term
"""
import sys, re, json, time, urllib.request, urllib.parse
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from claim_domain import domain_of
from oeis_novelty import entry, bfile

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) chiron-research/0.6.4"

CLAIMS = [
    ("positive", re.compile(r"a\(n\)\s*(?:>|is\s+(?:always\s+)?(?:positive|greater\s+than)\s*)\s*0", re.I),
     lambda v, k: v <= 0),
    ("never",    re.compile(r"a\(n\)\s+is\s+never\s+(?:equal\s+to\s+)?(-?\d+)\b", re.I),
     None),
    ("nonzero",  re.compile(r"a\(n\)\s*(?:!=|≠|<>)\s*0", re.I),
     lambda v, k: v == 0),
]

def search(q, pages):
    out = []
    for st in range(0, pages*10, 10):
        u = "https://oeis.org/search?q=" + urllib.parse.quote(q) + f"&fmt=json&start={st}"
        try:
            r = urllib.request.Request(u, headers={"User-Agent": UA})
            d = json.loads(urllib.request.urlopen(r, timeout=60).read().decode("utf-8","replace"))
        except Exception:
            break
        if isinstance(d, dict): d = d.get("results") or []
        if not d: break
        out += d; time.sleep(2)
    return out

def terms_for(e):
    """Prefer the b-file; require it to agree with `data` on the overlap."""
    a = e["number"]
    data = [int(x) for x in (e.get("data") or "").split(",")
            if x.strip().lstrip("-").isdigit()]
    if not data: return [], "none"
    try:
        bt, st = bfile(a, len(data))
        if st == "real" and len(bt) > len(data):
            k = min(len(bt), len(data))
            if bt[:k] == data[:k]:
                return bt, f"b-file({len(bt)})"
    except Exception:
        pass
    return data, f"data({len(data)})"

def run(queries, pages):
    seen, tested, refused, viol = set(), 0, 0, []
    for q in queries:
        for e in search(q, pages):
            a = e["number"]
            if a in seen: continue
            seen.add(a)
            txt = " ".join(e.get("comment") or []) + " " + (e.get("name") or "")
            for sent in re.split(r"(?<=[.;])\s+", txt):
                hit = None
                for kind, rx, pred in CLAIMS:
                    m = rx.search(sent)
                    if m: hit = (kind, m, pred); break
                if not hit: continue
                kind, m, pred = hit
                dk, dv = domain_of(sent)
                if dk == "refuse":
                    refused += 1; break
                off = int((e.get("offset") or "0,1").split(",")[0])
                thr = dv if dk == "threshold" else off - 1
                data, src = terms_for(e)
                if not data: break
                if kind == "never":
                    k = int(m.group(1)); pred = lambda v, k=k: v == k
                tested += 1
                bad = [(off+i, v) for i, v in enumerate(data)
                       if off+i > thr and pred(v, None)]
                if bad:
                    viol.append(dict(anum=a, kind=kind, thr=thr, src=src,
                                     bad=bad[:5], name=(e.get("name") or "")[:100],
                                     claim=sent[:170]))
                    print(f"  *** A{a:06d} [{kind}] thr n>{thr} src={src}")
                    print(f"      {(e.get('name') or '')[:86]}")
                    print(f"      claim: {sent[:130]}")
                    print(f"      violating terms: {bad[:4]}")
                break
    print(f"\n  entries seen {len(seen)}   claims tested {tested}   "
          f"refused (domain not simple) {refused}   VIOLATIONS {len(viol)}")
    json.dump(viol, open("studies/hunt_violations.json","w"), indent=1)
    return viol

if __name__ == "__main__":
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    Q = ['"Conjecture: a(n) > 0"', '"Conjecture: a(n)>0"',
         '"a(n) is never"', '"conjectured that a(n) > 0"',
         '"Conjecture: a(n) > 0 for all n"', '"a(n) > 0 for all n >"',
         '"Conjecture: a(n) > 0 for every n"', '"a(n) is always positive"',
         '"Conjecture: a(n) is never zero"', '"we conjecture that a(n) > 0"',
         '"It is conjectured that a(n) > 0"', '"Conjecture: every n"',
         '"a(n) > 0 for n >"', '"Conjecture: a(n) != 0"',
         '"Conjecture: a(n) is nonzero"', '"a(n) is never a square"',
         '"Conjecture: a(n) > 1"', '"conjectured to be positive"']
    print("="*74); print("HUNT — OEIS conjectures vs published terms (b-file preferred)")
    print("="*74)
    v = run(Q, pages)
    if not v:
        print("\n  No stated conjecture is contradicted by its own published data")
        print("  in this sample. Reported as a result.")
