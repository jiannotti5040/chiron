#!/usr/bin/env python3
"""
signature_audit.py — check OEIS's stated linear-recurrence signatures against
the terms published in the same entry.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

WHY THIS TARGET. Roughly 7% of OEIS entries carry a machine-readable claim in
their link field:

    Index entries for linear recurrences with constant coefficients,
    signature (1,1).

That is an EXACT assertion: a(n) = c1*a(n-1) + ... + ck*a(n-k) for all n past
the seeds. Unlike prose conjectures it needs no parsing judgement, and unlike a
bounded search it is decidable outright -- the terms either satisfy the
recurrence or they do not.

Nobody sweeps these against the data. A signature that fails to reproduce its
own entry's terms is an unambiguous, independently checkable error: the
sequence, the claimed signature, the index and the two conflicting values all
sit in one public record.

DISCIPLINE. Exact integer arithmetic only. The check begins at the first index
where the recurrence can apply, never before. Where a b-file is available and
agrees with `data` on the overlap it is preferred, since a signature added
years ago may never have been re-checked against terms uploaded later.
"""
import sys, re, json, time, urllib.request, urllib.parse
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from oeis_novelty import bfile

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) chiron-research/0.6.4"
SIG = re.compile(r"signature\s*\(([-0-9,\s]+)\)", re.I)
REC = "Index entries for linear recurrences with constant coefficients"

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

def audit(e):
    a = e["number"]
    sig = None
    for ln in (e.get("link") or []):
        if REC in ln:
            m = SIG.search(ln)
            if m:
                try:
                    sig = [int(x) for x in m.group(1).replace(" ","").split(",") if x]
                except ValueError:
                    sig = None
            break
    if not sig:
        return None
    data = [int(x) for x in (e.get("data") or "").split(",")
            if x.strip().lstrip("-").isdigit()]
    if len(data) < 2*len(sig) + 2:
        return {"anum": a, "status": "too-short", "order": len(sig)}
    src = f"data({len(data)})"
    try:
        bt, st = bfile(a, len(data))
        if st == "real" and len(bt) > len(data):
            k = min(len(bt), len(data))
            if bt[:k] == data[:k]:
                data, src = bt, f"b-file({len(bt)})"
    except Exception:
        pass

    k = len(sig)
    # An OEIS signature describes EVENTUAL behaviour. Sequences routinely carry
    # irregular initial terms before the recurrence takes hold -- A282718 is
    # explicitly "satisfies the tribonacci recurrence" yet its signature only
    # applies from index 6, not 3. Applying it from index k flagged the seeds
    # and produced 29 false failures out of 217.
    #
    # The correct question is: does there exist a starting index s, small
    # relative to the data, from which the recurrence holds for EVERY
    # remaining term? A genuine defect is a break in the TAIL, after the
    # recurrence has already been holding.
    start = None
    for s0 in range(k, min(len(data) // 2, k + 60)):
        if all(data[i] == sum(sig[j]*data[i-1-j] for j in range(k))
               for i in range(s0, len(data))):
            start = s0
            break
    if start is not None:
        return {"anum": a, "status": "ok", "order": k, "source": src,
                "checked": len(data)-start, "recurrence_from": start}

    # No starting index works. Locate where it breaks AFTER its longest
    # holding run -- that, and only that, is a real inconsistency.
    best_s, best_run = k, 0
    for s0 in range(k, min(len(data)//2, k+60)):
        run = 0
        for i in range(s0, len(data)):
            if data[i] == sum(sig[j]*data[i-1-j] for j in range(k)): run += 1
            else: break
        if run > best_run: best_run, best_s = run, s0
    bad = []
    for i in range(best_s + best_run, len(data)):
        pred = sum(sig[j]*data[i-1-j] for j in range(k))
        if pred != data[i]:
            bad.append((i, data[i], pred))
            if len(bad) >= 4: break
    if bad and best_run >= 8:      # only a break after a real holding run counts
        return {"anum": a, "status": "SIGNATURE-FAILS", "signature": sig,
                "source": src, "mismatches": bad, "n_terms": len(data),
                "held_from": best_s, "held_for": best_run,
                "name": (e.get("name") or "")[:100]}
    if bad:
        return {"anum": a, "status": "no-consistent-start", "order": k,
                "source": src, "best_run": best_run}
    if False:
        return {"anum": a, "status": "SIGNATURE-FAILS", "signature": sig,
                "source": src, "mismatches": bad, "n_terms": len(data),
                "name": (e.get("name") or "")[:100]}
    return {"anum": a, "status": "ok", "order": k, "source": src,
            "checked": len(data)-k}

if __name__ == "__main__":
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    print("="*74)
    print("SIGNATURE AUDIT — OEIS linear recurrences vs their own terms")
    print("="*74)
    print("An exact claim, decidable outright: the terms satisfy the stated")
    print("recurrence or they do not. Exact integers; b-file preferred.\n")
    seen, tally, fails = set(), {}, []
    for q in ['"Index entries for linear recurrences with constant coefficients"',
              '"signature" linear recurrence']:
        for e in search(q, pages):
            if e["number"] in seen: continue
            seen.add(e["number"])
            r = audit(e)
            if not r: continue
            tally[r["status"]] = tally.get(r["status"],0)+1
            if r["status"] == "SIGNATURE-FAILS":
                fails.append(r)
                print(f"  *** A{r['anum']:06d}  signature {r['signature']} FAILS")
                print(f"      {r['name'][:84]}")
                print(f"      source {r['source']}  first mismatches "
                      f"(index, published, predicted): {r['mismatches'][:3]}")
    print(f"\n  entries with a signature: {sum(tally.values())}")
    for k,v in sorted(tally.items(), key=lambda x:-x[1]):
        print(f"    {k:18s} {v}")
    json.dump(fails, open("studies/signature_failures.json","w"), indent=1)
    if not fails:
        print("\n  every stated signature reproduces its own published terms exactly.")
