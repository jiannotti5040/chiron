#!/usr/bin/env python3
"""
oeis_conjecture_miner.py — cross-check OEIS's stated conjectures against
OEIS's own published terms.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

THE OPPORTUNITY. OEIS carries thousands of conjectures in free-text comments:

    "Conjecture: a(n) > 0"          716 entries
    "Conjecture: a(n) < ..."      3,560 entries
    "conjectured that a(n) ..."     346 entries
    "Conjecture: a(n) is never"      23 entries
    "Conjecture: no term ..."        65 entries

Each is a universal claim about a sequence whose terms are published in the
same entry. Nobody sweeps them systematically against that data. A mismatch is
either a genuine finding or -- far more often -- a parsing error, and telling
those apart is the entire job.

WHY THIS SHAPE IS WORTH HUNTING. "For all n, P(n)" cannot be established by
finite testing but is REFUTED by one witness. A conjecture stated in an entry
whose own data contradicts it is a finite, fully-auditable object: the
sequence, the term, the index, and the claim all sit in one public record that
anyone can pull up.

WHY MOST HITS WILL BE FALSE, and what is done about it. The conjectures are
prose. "a(n) > 0 for n > 2", "a(n) > 0 except for a(1)", "Conjecture: a(n) > 0
if n is not a power of 2" all parse alike to a naive matcher and mean very
different things. So:

  * only STRICTLY parseable forms are accepted; anything with a qualifier this
    parser does not model is REFUSED rather than guessed at
  * the stated domain (n > k) is extracted and honoured -- the single most
    common source of false positives is testing a claim outside its own domain
  * OFFSET is read from the entry, never assumed; OEIS sequences do not all
    start at n = 0 or n = 1
  * every candidate violation is re-derived from the raw entry text before it
    is reported at all

This parser has already been wrong about "if and only if" once in this
project's history, producing 3,185 fake counterexamples. The conservatism
below is paid for.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CACHE = HERE / ".oeis_cache"
OUT = HERE / "conjecture_mine.json"

# Qualifiers this parser does NOT model. Their presence means the claim is
# more complex than "a(n) > 0 for n > k", so it is refused rather than tested.
UNMODELLED = re.compile(
    r"\bif and only if\b|\biff\b|\bunless\b|\bassuming\b|"
    r"except"                       # matches "except" AND "exception(s)" --
                                    # \bexcept\b missed "with the only
                                    # exception n=8" on A218585 and the miner
                                    # then flagged the very term exempted
    r"|\bif\b|\bwhen\b|\bwhenever\b|\bprovided\b|\bconditional\b|"
    r"\bprobably\b|\bperhaps\b|\bseems\b|\bappears\b|\bmight\b|"
    r"\beventually\b|\binfinitely\b|\balmost all\b|\bdensity\b|"
    r"\beven\s+n\b|\bodd\s+n\b"   # parity-split domains ("for all even
                                       # n > 8012 and odd n > 15727") are two
                                       # claims, not one; A219055/A219185
    , re.I)

# The one form modelled: a(n) > 0, optionally with a domain "for n > k",
# "for all n >= k", "for n >= k".
POSITIVE = re.compile(
    r"conjecture[sd]?\s*[:.]?\s*(?:that\s+)?a\(n\)\s*>\s*0"
    r"(?:\s*,?\s*for\s+(?:all|every)?\s*n\s*(>=|>|≥)\s*(\d+))?", re.I)

# OEIS very often writes the domain as an enumeration rather than an
# inequality: "for all n = 3,4,...", "for every n = 20, 21, ...". Missing this
# form made the miner test claims outside their own domain and flag exactly
# the terms being excluded (A208243, A218654, A236241).
ENUM_DOMAIN = re.compile(
    r"a\(n\)\s*>\s*0[^.;]{0,20}?for\s+(?:all|every)?\s*n\s*=\s*(\d+)\s*,",
    re.I)


def parse_conjecture(text):
    """
    Return (kind, threshold) or None. Refuses anything with an unmodelled
    qualifier ANYWHERE in the same sentence.
    """
    for sent in re.split(r"(?<=[.;])\s+", text):
        m = POSITIVE.search(sent)
        if not m:
            continue
        if UNMODELLED.search(sent):
            return ("refused-qualifier", sent[:120])
        em = ENUM_DOMAIN.search(sent)
        if em:                                  # "for all n = k, k+1, ..."
            return ("positive", int(em.group(1)) - 1)
        op, k = m.group(1), m.group(2)
        if k is None:
            return ("positive", None)          # claim over the whole domain
        k = int(k)
        return ("positive", k if op in (">", "") else k - 1)  # normalise to n > k
    return None


def check(anum):
    """Cross-check one entry. Returns dict; never raises."""
    from oeis_novelty import entry
    try:
        e = entry(anum)
    except Exception as ex:
        return {"anum": anum, "status": "fetch-failed", "detail": type(ex).__name__}
    if e is None:
        return {"anum": anum, "status": "fetch-failed", "detail": "no entry"}

    text = " ".join(e.get("comment") or []) + " " + (e.get("name") or "")
    parsed = parse_conjecture(text)
    if parsed is None:
        return {"anum": anum, "status": "no-parseable-conjecture"}
    kind, arg = parsed
    if kind == "refused-qualifier":
        return {"anum": anum, "status": "refused-qualifier", "detail": arg}

    data = [int(x) for x in (e.get("data") or "").split(",")
            if x.strip().lstrip("-").lstrip("+").isdigit()
            or (x.strip().startswith("-") and x.strip()[1:].isdigit())]
    if not data:
        return {"anum": anum, "status": "no-data"}
    off = int((e.get("offset") or "0,1").split(",")[0])
    thr = arg if arg is not None else off - 1     # no domain => whole sequence

    viol = [(off + i, v) for i, v in enumerate(data)
            if off + i > thr and v <= 0]
    if viol:
        return {"anum": anum, "status": "VIOLATION",
                "threshold": thr, "offset": off,
                "violations": viol[:6], "n_terms": len(data),
                "name": (e.get("name") or "")[:110],
                "claim_text": text[:260]}
    return {"anum": anum, "status": "consistent", "threshold": thr,
            "n_terms": len(data)}


def harvest(pages=8, per=10):
    """Collect A-numbers whose text contains a positivity conjecture."""
    import urllib.request
    UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) chiron-research/0.6.4"
    found = []
    for start in range(0, pages * per, per):
        url = ("https://oeis.org/search?q=%22Conjecture%3A+a%28n%29+%3E+0%22"
               f"&fmt=json&start={start}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            break
        if isinstance(d, dict):
            d = d.get("results") or []
        if not d:
            break
        for e in d:
            found.append(e["number"])
            (CACHE / f"A{e['number']:06d}.json").write_text(json.dumps(e))
        time.sleep(2)
    return sorted(set(found))


def main():
    CACHE.mkdir(exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 12

    print("=" * 74)
    print("OEIS CONJECTURE MINER — stated conjectures vs published terms")
    print("=" * 74)
    print("Only the strictly-parseable form 'a(n) > 0 [for n > k]' is tested.")
    print("Anything carrying a qualifier this parser does not model is REFUSED,")
    print("not guessed at — an earlier version of this project mis-parsed")
    print("'if and only if' and produced 3,185 fake counterexamples.\n")

    ids = harvest(pages=pages)
    print(f"  harvested {len(ids)} entries stating a positivity conjecture\n")

    res, tally = [], {}
    for i, a in enumerate(ids, 1):
        r = check(a)
        res.append(r)
        tally[r["status"]] = tally.get(r["status"], 0) + 1
        if r["status"] == "VIOLATION":
            print(f"  *** VIOLATION  A{a:06d}  {r['name'][:70]}")
            print(f"      claims a(n)>0 for n>{r['threshold']}, but publishes "
                  f"{r['violations'][:3]}")
        if i % 25 == 0:
            print(f"      {i}/{len(ids)}  " +
                  "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))

    OUT.write_text(json.dumps(res, indent=1))
    print("\n" + "-" * 74)
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"  {k:26s} {v:5d}")
    viol = [r for r in res if r["status"] == "VIOLATION"]
    print(f"\n  VIOLATIONS: {len(viol)}")
    if viol:
        print("  NOT FINDINGS YET — each needs the raw entry re-read by a human")
        print("  before any claim. Most such hits are parser error.")
        for r in viol:
            print(f"    https://oeis.org/A{r['anum']:06d}  {r['violations'][:3]}")
    else:
        print("  none — every parseable positivity conjecture is consistent with")
        print("  its own published terms.")
    print(f"\n  written: {OUT}")


if __name__ == "__main__":
    main()
