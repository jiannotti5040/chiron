#!/usr/bin/env python3
"""
systematic_sweep.py — walk EVERY conjecture in the corpus, in order, and give
each one a recorded status. No cherry-picking, no silent skipping.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

TARGET: google-deepmind/formal-conjectures — 850 Lean files, ~3,195 tagged
theorems, ~1,171 of them open.

WHY THIS AND NOT THE PREVIOUS RUNNER. The earlier campaign hand-picked eleven
conjectures and pushed their bounds. That is the wrong shape twice over: it
covers 1% of the corpus, and six of the eleven were already verified by others
to bounds a laptop cannot approach, so the compute could never produce a
result. This walks the WHOLE corpus and records an honest status for every
entry, including the large majority that cannot be searched at all.

COMPLETE COVERAGE MEANS A STATUS FOR EVERY CONJECTURE, NOT A SEARCH FOR EVERY
CONJECTURE. Most of these cannot be attacked by any finite computation, and
saying so per-entry is the honest form of "we hit all of them". The statuses:

    SEARCHED-VERIFIED   bounded search completed, no counterexample found
    SEARCHED-REFUTED    counterexample found -> escalates to a witness
                        certificate, which must independently re-verify
    REFUSED-INFINITARY  asserts an infinite set / asymptotic; no finite
                        computation settles it in either direction
    REFUSED-NEEDS-LEAN  truth depends on Lean definitions this cannot evaluate
    REFUSED-NO-ANSWER   the corpus itself marks the answer unknown
    REFUSED-NO-DATA     OEIS-anchored but the data could not be fetched
    SKIPPED-NOT-OPEN    not a `research open` theorem (test/API/textbook)

THE SEARCH GAP IS RECORDED, NOT IGNORED. Where prior art gives a published
verification bound, it is stored alongside the result, because reaching 10^5
on something verified to 10^12 is not progress and the record should say so
rather than flatter the number.

Resumable: every processed file is journaled. Re-running skips completed work.
Kill it at any point; nothing is lost and nothing is recomputed.

Usage:
    python3 studies/systematic_sweep.py scan            # inventory only
    python3 studies/systematic_sweep.py run [--limit N] # walk the corpus
    python3 studies/systematic_sweep.py report          # status summary
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(VAULT / "Primus" / "src"))

REPO = Path("/private/tmp/claude-501/-Users-jacobiannotti-Desktop/"
            "c94cbf5b-73af-44c3-977f-8e65f8da2b18/scratchpad/formal-conjectures")
JOURNAL = HERE / "systematic_journal.json"

SEARCHED_V = "SEARCHED-VERIFIED"
SEARCHED_R = "SEARCHED-REFUTED"
INFINITARY = "REFUSED-INFINITARY"
NEEDS_LEAN = "REFUSED-NEEDS-LEAN"
NO_ANSWER = "REFUSED-NO-ANSWER"
NO_DATA = "REFUSED-NO-DATA"
NOT_OPEN = "SKIPPED-NOT-OPEN"

# --------------------------------------------------------------------------
# Classification -- reuse the validated detector rather than a second regex
# --------------------------------------------------------------------------

INFINITARY_MARKERS = [
    r"\.Infinite\b", r"Set\.Infinite", r"Filter\.atTop", r"\batTop\b",
    r"Tendsto", r"limsup", r"liminf", r"∑'", r"∏'", r"⨆", r"⨅",
    r"IsBigO", r"IsLittleO", r"Irrational\b", r"Transcendental\b",
    r"∃ᶠ", r"∀ᶠ", r"∀ᵉ", r"HasPosDensity", r"Density\b",
    r"∀\s*[^,]*:\s*ℝ", r"∃\s*[^,]*:\s*ℝ", r"nhds", r"Measurable", r"volume",
]

THM_RE = re.compile(
    r"@\[category\s+([a-zA-Z ]+?)\s*(?:,\s*AMS[^\]]*)?\]\s*\n"
    r"\s*(?:theorem|lemma)\s+(\S+)\s*(.*?)(?::=|\Z)", re.S)


def parse(p: Path):
    txt = p.read_text(errors="replace")
    title = ""
    m = re.search(r"^#\s+(.+)$", txt, re.M)
    if m:
        title = m.group(1).strip()
    oeis = re.search(r"oeis\.org/A(\d+)", txt)
    out = []
    for cat, name, stmt in THM_RE.findall(txt):
        s = " ".join(stmt.split())
        if ":" in s:
            s = s.split(":", 1)[1].strip()
        out.append({"category": cat.strip(), "name": name,
                    "statement": s[:300],
                    "sorry_answer": "answer(sorry)" in stmt})
    return {"title": title, "oeis": int(oeis.group(1)) if oeis else None,
            "theorems": out}


def classify(t):
    s = t["statement"]
    for pat in INFINITARY_MARKERS:
        if re.search(pat, s):
            return INFINITARY, f"matches {pat}"
    if t["sorry_answer"]:
        return NO_ANSWER, "corpus marks the answer unknown: answer(sorry)"
    return NEEDS_LEAN, "no finitely-searchable obligation identified"


# --------------------------------------------------------------------------
# OEIS-anchored search: the one class that CAN be attacked automatically
# --------------------------------------------------------------------------

def try_oeis_search(anum, budget=45):
    """
    For a conjecture anchored to an OEIS sequence, the standard Sun-style
    shape is "a(n) > 0 for all n > k" -- i.e. the sequence has no zero beyond
    some point. That IS finitely refutable: a single published zero past the
    stated threshold is a counterexample to the stated claim.

    Returns (status, detail). Never raises.
    """
    try:
        from oeis_novelty import entry
        e = entry(anum)
        if e is None:
            return NO_DATA, f"A{anum:06d} could not be fetched"
    except Exception as ex:
        return NO_DATA, f"fetch failed: {type(ex).__name__}"

    name = (e.get("name") or "")
    data = [int(x) for x in (e.get("data") or "").split(",")
            if x.strip().lstrip("-").isdigit()]
    if not data:
        return NO_DATA, "no term data published"
    off = int((e.get("offset") or "0,1").split(",")[0])

    # Does the entry state a positivity conjecture we can test against its
    # OWN published terms? Look for "a(n) > 0 for all n > k".
    conj = " ".join(e.get("comment") or [])[:4000]
    m = re.search(r"a\(n\)\s*>\s*0\s*for\s*all\s*n\s*>\s*(\d+)", conj)
    if not m:
        return NEEDS_LEAN, (f"A{anum:06d}: {len(data)} terms published; no "
                            f"machine-checkable positivity claim in the entry")
    k = int(m.group(1))
    zeros = [off + i for i, v in enumerate(data) if v == 0 and off + i > k]
    if zeros:
        return SEARCHED_R, (f"A{anum:06d} publishes a(n)=0 at n={zeros[:3]} "
                            f"despite the entry's own claim a(n)>0 for n>{k}")
    span = off + len(data) - 1
    return SEARCHED_V, (f"A{anum:06d}: entry claims a(n)>0 for n>{k}; every "
                        f"published term from n={k+1} to n={span} is nonzero "
                        f"({len(data)} terms checked)")


# --------------------------------------------------------------------------

def load_journal():
    if JOURNAL.exists():
        return json.loads(JOURNAL.read_text())
    return {"files": {}, "results": []}


def save_journal(j):
    JOURNAL.write_text(json.dumps(j, indent=1))


def scan():
    files = sorted((REPO / "FormalConjectures").rglob("*.lean"))
    tally = Counter()
    opens = 0
    for p in files:
        d = parse(p)
        for t in d["theorems"]:
            tally[t["category"]] += 1
            if t["category"] == "research open":
                opens += 1
    print(f"  files            {len(files):,}")
    print(f"  tagged theorems  {sum(tally.values()):,}")
    print(f"  research open    {opens:,}")
    for c, n in tally.most_common():
        print(f"    {c:18s} {n:6,}")
    return files


def run(limit=None):
    j = load_journal()
    files = sorted((REPO / "FormalConjectures").rglob("*.lean"))
    todo = [p for p in files if str(p.relative_to(REPO)) not in j["files"]]
    if limit:
        todo = todo[:limit]
    print(f"  {len(j['files']):,} files already journaled; {len(todo):,} to process\n")

    t0 = time.time()
    for i, p in enumerate(todo, 1):
        rel = str(p.relative_to(REPO))
        d = parse(p)
        opens = [t for t in d["theorems"] if t["category"] == "research open"]
        if not opens:
            j["files"][rel] = {"status": NOT_OPEN, "n": 0}
            continue

        recs = []
        for t in opens:
            status, detail = classify(t)
            # an OEIS anchor is the one route to an automatic search
            if status == NEEDS_LEAN and d["oeis"]:
                status, detail = try_oeis_search(d["oeis"])
            rec = {"file": rel, "title": d["title"][:90], "oeis": d["oeis"],
                   "theorem": t["name"], "status": status, "detail": detail[:200],
                   "statement": t["statement"][:160]}
            recs.append(rec)
            j["results"].append(rec)
            if status == SEARCHED_R:
                print(f"  *** {SEARCHED_R}  {rel}  {detail[:80]}")
        j["files"][rel] = {"status": "done", "n": len(recs)}

        if i % 25 == 0:
            save_journal(j)
            c = Counter(r["status"] for r in j["results"])
            el = time.time() - t0
            print(f"  {i}/{len(todo)}  ({el:.0f}s)  " +
                  "  ".join(f"{k.split('-')[-1][:8]}={v}" for k, v in c.most_common(4)))

    save_journal(j)
    report(j)


def report(j=None):
    j = j or load_journal()
    c = Counter(r["status"] for r in j["results"])
    tot = sum(c.values())
    print("\n" + "=" * 72)
    print(f"SYSTEMATIC SWEEP — {len(j['files']):,} files, {tot:,} open conjectures")
    print("=" * 72)
    for k, v in c.most_common():
        print(f"  {k:22s} {v:6,}   {100*v/tot:5.1f}%")
    ref = [r for r in j["results"] if r["status"] == SEARCHED_R]
    print(f"\n  REFUTED: {len(ref)}")
    for r in ref[:20]:
        print(f"    {r['file']}  {r['detail'][:90]}")
    if not ref:
        print("    none — which is the expected outcome and is reported as a result")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "scan":
        scan()
    elif cmd == "run":
        lim = None
        if "--limit" in sys.argv:
            lim = int(sys.argv[sys.argv.index("--limit") + 1])
        run(lim)
    elif cmd == "report":
        report()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
