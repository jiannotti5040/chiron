#!/usr/bin/env python3
"""
oeis_novelty.py — does Chiron recover an exact rule OEIS does not already state?

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

PRE-REGISTERED, written before any run (see docs/OEIS_NOVELTY_PROTOCOL.md):

  HYPOTHESIS  There exist OEIS sequences for which the engine recovers an exact
              rule that (a) reproduces EVERY term of a real b-file and (b) is
              not documented anywhere in the entry.

  EXPECTATION ZERO. OEIS has been curated by thousands of contributors for 60
              years. A 14-term recovery finding something genuinely new is a
              low-probability event. A zero result is reported as a zero result.

  FALSIFIED   by any survivor turning out, on human read, to be documented or
              trivial.

This script exists because the previous attempt produced a FALSE FINDING. Its
novelty detector read only the `formula` field. A279538's *name* is
"a(n) = -n^3 + 70*n^2 - 939*n + 2393" and it has no `formula` field at all, so
a fully documented entry was reported as undocumented. Filter 0 below exists
solely to make that specific failure impossible to repeat: the detector must
first re-classify a control set of KNOWN-DOCUMENTED entries correctly, or the
run is abandoned.

Two traps this script is built around, both measured rather than assumed:

  1. SYNTHESIZED B-FILES. OEIS serves HTTP 200 for /A######/b######.txt even
     when no b-file was ever uploaded -- it generates one from the entry's own
     `data` field. 45% of sampled b-files are synthetic and carry ZERO terms
     beyond `data`. Verifying against one of those is verifying against the
     same ~40 terms the engine was fit on, while believing you checked 1000.
     Detected two ways: the header comment, and line count vs `data` length.

  2. FORMULAS OUTSIDE `formula`. The field is absent on ~51% of the database.
     Formulas live in `name` (the biggest leak), `link` (machine-readable
     linear-recurrence signatures), `mathematica` (LinearRecurrence[...]),
     `comment`, `xref`, `example`, `maple`, `program`.

Usage:
    python3 studies/oeis_novelty.py filter0     # REQUIRED before any run
    python3 studies/oeis_novelty.py unkn        # the 31 keyword:unkn entries
    python3 studies/oeis_novelty.py sweep FILE  # broad sweep over A-numbers
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Primus" / "src"))
from primus.engine import collapse_numeric  # noqa: E402

# oeis.org returns 403 to urllib's default User-Agent.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) chiron-research/0.6.3"
POLITE_DELAY = 2.0  # seconds between requests; OEIS asks for this

CACHE = Path(__file__).resolve().parent / ".oeis_cache"
CACHE.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Pre-registered constants. Set BEFORE the run, never tuned after seeing output.
# ---------------------------------------------------------------------------

SHOWN_TERMS = 14          # how many terms the engine is allowed to see
MIN_BFILE_GAIN = 20       # b-file must carry >= this many terms beyond `data`
MIN_GROWTH_RATIO = 10     # |last| / max(1,|a_10|); flat sequences are refused
MIN_DATA_TERMS = 25       # below this, no defensible recovery claim

# Structurally trivial classes. A recovered "rule" over any of these is an
# artifact of the encoding, not a fact about a sequence.
EXCLUDED_KEYWORDS = {
    "cons",   # decimal expansion of a constant -- terms are DIGITS
    "cofr",   # continued fraction expansion -- same problem
    "base",   # base-dependent digit property -- artifact of base 10
    "fini",   # finite; extrapolation undefined
    "full",   # the listed terms ARE the whole sequence; fitting is unfalsifiable
    "dead",   # erroneous or duplicated entry -- the DATA is wrong
    "bref",   # too short to analyze (OEIS's own words)
    "dumb",   # editor-marked unimportant
    "obsc",   # definition itself is unclear
    "uned",   # unedited; OEIS docs say formulas may be MISFILED here, so
              # field-position detection is invalid by construction
    "frac",   # numerator/denominator half of a pair
    "tabl",   # triangle read by rows -- a 1-D rule over a linearized 2-D
    "tabf",   #   object is an artifact of the reading order
    "word",   # depends on words in some language
}

# ---------------------------------------------------------------------------
# Documentation detector -- biased HARD toward "documented".
# A false negative here becomes a false public claim, so every ambiguous case
# resolves to documented.
# ---------------------------------------------------------------------------

REC_LINK = "Index entries for linear recurrences with constant coefficients"

MMA_MARKERS = ("LinearRecurrence[", "PadRight[{}", "CoefficientList[Series[",
               "RecurrenceTable[", "DifferenceRoot[")

NAME_PATTERNS = [
    r"^\s*a\s*\(\s*n\s*\)\s*=",
    r"^\s*Expansion of",
    r"G\.f\.\s*[:=]", r"\bG\.f\.\s+is\b",
    r"E\.g\.f\.\s*[:=]", r"\bE\.g\.f\.\s+is\b",
    r"D\.g\.f\.\s*[:=]",
    r"^\s*Decimal expansion of",
    r"^\s*Continued fraction",
    r"a\s*\(\s*n\s*-\s*\d+\s*\)",      # any recurrence reference
    r"a\s*\(\s*n\s*\+\s*\d+\s*\)",
    r"^\s*Numbers of the form",
    r"^\s*Partial sums of",
    r"^\s*Binomial transform of",
]

BODY_PATTERNS = [
    r"a\s*\(\s*n\s*\)\s*=\s*\S",
    r"G\.f\.\s*[:=]", r"E\.g\.f\.\s*[:=]", r"D\.g\.f\.\s*[:=]",
    r"a\s*\(\s*n\s*-\s*\d+\s*\)",
    r"Sum_\{", r"Product_\{",
    r"\bsatisfies the recurrence\b",
]

CONJ_PREFIX = re.compile(r"^\s*(Conjecture|Conjectural|Empirical)", re.I)


def _lines(entry, key):
    v = entry.get(key)
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def documented(entry):
    """Return (is_documented, reason). Ambiguity resolves to documented."""
    # 1. Highest precision: OEIS's own machine-readable recurrence index link.
    for ln in _lines(entry, "link"):
        if REC_LINK in ln:
            sig = re.search(r"signature\s*\(([^)]*)\)", ln)
            return True, f"link: documented linear recurrence signature ({sig.group(1) if sig else '?'})"

    # 2. Mathematica encodes the rule directly.
    for ln in _lines(entry, "mathematica"):
        for m in MMA_MARKERS:
            if m in ln:
                return True, f"mathematica: {m}"

    # 3. THE A279538 FIX -- the name is very often the formula.
    name = entry.get("name", "") or ""
    for pat in NAME_PATTERNS:
        if re.search(pat, name, re.I):
            return True, f"name states the rule: {name[:90]}"

    # 4. A non-empty formula field. Flag conjecture-only, but still documented.
    fl = _lines(entry, "formula")
    if fl:
        if all(CONJ_PREFIX.match(x) for x in fl):
            return True, "formula field (CONJECTURAL only)"
        return True, "formula field"

    # 5. Everything else that can carry a rule.
    for key in ("comment", "xref", "example", "maple", "program"):
        for ln in _lines(entry, key):
            for pat in BODY_PATTERNS:
                if re.search(pat, ln, re.I):
                    return True, f"{key}: {ln[:80]}"

    return False, "no rule found in name/formula/link/mathematica/comment/xref/example/maple/program"


# ---------------------------------------------------------------------------
# OEIS access
# ---------------------------------------------------------------------------

def _get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    return raw if binary else raw.decode("utf-8", "replace")


def entry(anum, use_cache=True):
    """Fetch one OEIS entry as a dict, or None."""
    p = CACHE / f"A{anum:06d}.json"
    if use_cache and p.exists():
        return json.loads(p.read_text())
    try:
        txt = _get(f"https://oeis.org/search?q=id:A{anum:06d}&fmt=json")
    except urllib.error.HTTPError:
        return None
    time.sleep(POLITE_DELAY)
    data = json.loads(txt)
    if isinstance(data, dict):
        data = data.get("results") or []
    if not data:
        return None
    p.write_text(json.dumps(data[0]))
    return data[0]


def bfile(anum, data_terms, use_cache=True):
    """
    Return (terms, status). status is one of:
      'real'         -- a genuinely uploaded b-file with real extra terms
      'synthesized'  -- OEIS generated it from `data`; ZERO information gain
      'thin'         -- real but fewer than MIN_BFILE_GAIN extra terms
      'absent'       -- 404
    """
    p = CACHE / f"b{anum:06d}.txt"
    if use_cache and p.exists():
        txt = p.read_text()
    else:
        try:
            txt = _get(f"https://oeis.org/A{anum:06d}/b{anum:06d}.txt")
        except urllib.error.HTTPError:
            return [], "absent"
        time.sleep(POLITE_DELAY)
        p.write_text(txt)

    head = txt[:400]
    terms = []
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                terms.append(int(parts[1]))
            except ValueError:
                continue

    if "synthesized from sequence entry" in head:
        return terms, "synthesized"
    # Belt and braces: a "real" b-file that adds nothing is synthetic in effect.
    if len(terms) <= data_terms:
        return terms, "synthesized"
    if len(terms) - data_terms < MIN_BFILE_GAIN:
        return terms, "thin"
    return terms, "real"


# ---------------------------------------------------------------------------
# The engine step
# ---------------------------------------------------------------------------

def recovers_exactly(terms):
    """
    Show the engine SHOWN_TERMS terms; demand it reproduce EVERY b-file term.

    predict(n) returns the FIRST n terms (not the next n). Comparing the whole
    prefix is both correct and stronger than slicing -- and it is the specific
    misuse that produced a false '29/30 wrong' result previously.
    """
    shown = terms[:SHOWN_TERMS]
    if len(shown) < SHOWN_TERMS:
        return None, "too few terms to show"
    try:
        inv = collapse_numeric(shown)
    except Exception as e:
        return None, f"engine raised {type(e).__name__}"
    if not getattr(inv, "verified", False):
        return None, "engine refused (unstamped)"
    try:
        pred = inv.predict(len(terms))
    except Exception as e:
        return None, f"predict raised {type(e).__name__}"
    if len(pred) != len(terms):
        return None, f"predict returned {len(pred)} of {len(terms)}"
    for i, (a, b) in enumerate(zip(pred, terms)):
        if a != b:
            return None, f"diverges at index {i}: predicted {a}, actual {b}"
    return inv, f"exact on all {len(terms)} b-file terms"


def growth_ratio(terms):
    if len(terms) < 12:
        return 0.0
    base = max(1, abs(terms[10]))
    return abs(terms[-1]) / base


# ---------------------------------------------------------------------------
# FILTER 0 -- the gate that makes the previous failure impossible to repeat
# ---------------------------------------------------------------------------

# Every one of these is DOCUMENTED, and every one is invisible to a
# formula-field-only check. If the detector misses any, the run is abandoned.
CONTROLS_DOCUMENTED = [
    (279538, "formula is the NAME; no formula field -- the exact case that failed"),
    (24100,  "name: a(n) = 8^n - n^12; no formula field"),
    (173652, "name carries a full rational g.f.; no formula field"),
    (162539, "name: G.f. is the polynomial ..."),
    (193549, "name: E.g.f.: Sum_{n>=0} ..."),
    (103487, "name states a 4-term recurrence with seeds"),
    (353961, "name: a(n) = Sum_{d|n} ..."),
    (335167, "mathematica PadRight encodes the period-5 rule"),
    (292202, "comment: a(n) == n*2^n (mod 9)"),
    (91253,  "xref: a(n) = A007088(A091252(n))"),
    (45,     "Fibonacci -- documented in name, formula, comment, programs"),
    (108,    "Catalan -- documented via generating function"),
    (195,    "name has the proven closed form; formula field is CONJECTURAL only"),
]


def filter0():
    print("=" * 74)
    print("FILTER 0 -- validate the detector against KNOWN-DOCUMENTED entries")
    print("=" * 74)
    print("Every entry below IS documented. The detector must say so for all of")
    print("them. Any miss means the filter is broken and NO run happens.\n")

    misses = []
    for anum, why in CONTROLS_DOCUMENTED:
        e = entry(anum)
        if e is None:
            print(f"  [ERROR ] A{anum:06d}  could not fetch")
            misses.append((anum, "fetch failed"))
            continue
        ok, reason = documented(e)
        has_formula = bool(_lines(e, "formula"))
        tag = "PASS" if ok else "MISS"
        print(f"  [{tag}  ] A{anum:06d}  formula_field={str(has_formula):5s}  {reason[:78]}")
        if not ok:
            print(f"           EXPECTED DOCUMENTED: {why}")
            misses.append((anum, why))

    print()
    if misses:
        print(f"FILTER 0 FAILED -- {len(misses)} documented entries reported as undocumented.")
        print("The detector is broken. ABANDONING the run, exactly as pre-registered.")
        return False
    print(f"FILTER 0 PASSED -- {len(CONTROLS_DOCUMENTED)}/{len(CONTROLS_DOCUMENTED)} "
          "documented entries correctly classified.")
    print("The detector may now be trusted for a real run.")
    return True


# ---------------------------------------------------------------------------
# Candidate evaluation, six filters in order
# ---------------------------------------------------------------------------

def evaluate(anum, verbose=True):
    """Return (verdict, detail). verdict 'SURVIVOR' means it passed every filter."""
    e = entry(anum)
    if e is None:
        return "no-entry", "could not fetch"

    kw = set((e.get("keyword") or "").split(","))
    name = (e.get("name") or "")[:70]

    # Filter 3 -- structurally trivial classes
    bad = kw & EXCLUDED_KEYWORDS
    if bad:
        return "excluded-keyword", f"{','.join(sorted(bad))} | {name}"

    data = [int(x) for x in (e.get("data") or "").split(",") if x.strip().lstrip("-").isdigit()]
    if len(data) < MIN_DATA_TERMS:
        return "too-short", f"{len(data)} terms in data | {name}"

    # Filter 4 -- require growth
    g = growth_ratio(data)
    if g < MIN_GROWTH_RATIO:
        return "flat", f"growth {g:.1f} < {MIN_GROWTH_RATIO} | {name}"

    # Filter 2 -- a REAL b-file, not a synthesized one
    terms, status = bfile(anum, len(data))
    if status != "real":
        return f"bfile-{status}", f"{len(terms)} terms vs {len(data)} in data | {name}"

    # The engine must reproduce every single b-file term
    inv, why = recovers_exactly(terms)
    if inv is None:
        return "no-exact-recovery", f"{why} | {name}"

    # Filter 5 -- is it already documented?
    doc, reason = documented(e)
    if doc:
        return "documented", f"{reason[:70]}"

    return "SURVIVOR", (f"{inv.model_class} | {why} | bfile={len(terms)} "
                        f"data={len(data)} growth={g:.0f} | {name}")


def run(anums, label):
    print("=" * 74)
    print(f"RUN: {label}  ({len(anums)} candidates)")
    print("=" * 74)
    tally, survivors = {}, []
    for i, a in enumerate(anums, 1):
        verdict, detail = evaluate(a)
        tally[verdict] = tally.get(verdict, 0) + 1
        if verdict == "SURVIVOR":
            survivors.append((a, detail))
            print(f"  *** SURVIVOR  A{a:06d}  {detail}")
        else:
            print(f"  [{verdict:18s}] A{a:06d}  {detail[:66]}")
        if i % 25 == 0:
            print(f"      -- {i}/{len(anums)} --")

    print("\n" + "-" * 74)
    for k in sorted(tally, key=lambda x: -tally[x]):
        print(f"  {k:20s} {tally[k]:5d}")
    print("-" * 74)
    print(f"\nSURVIVORS: {len(survivors)}")
    if not survivors:
        print("\nZERO. This is the pre-registered expected outcome and is reported")
        print("as a result, not as a failure. Every candidate was either")
        print("structurally trivial, unverifiable against a real b-file, not")
        print("exactly recoverable, or already documented in the entry.")
    else:
        print("\nNOT A FINDING YET. Filter 6 is a human read by the owner.")
        print("Nothing is published and nothing is submitted to OEIS until then.")
        for a, d in survivors:
            print(f"  https://oeis.org/A{a:06d}   {d}")
    return survivors


def unkn_list():
    """The keyword:unkn set -- OEIS editors' own 'no formula known' marker."""
    out, start = [], 0
    while True:
        txt = _get(f"https://oeis.org/search?q=keyword:unkn&fmt=json&start={start}")
        time.sleep(POLITE_DELAY)
        d = json.loads(txt)
        if isinstance(d, dict):
            d = d.get("results") or []
        if not d:
            break
        for e in d:
            out.append(e["number"])
            (CACHE / f"A{e['number']:06d}.json").write_text(json.dumps(e))
        if len(d) < 10:
            break
        start += 10
    return sorted(set(out))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "filter0"

    if cmd == "filter0":
        sys.exit(0 if filter0() else 1)

    if not filter0():
        print("\nRefusing to run: Filter 0 did not pass.")
        sys.exit(1)
    print()

    if cmd == "unkn":
        ids = unkn_list()
        print(f"keyword:unkn returned {len(ids)} sequences\n")
        run(ids, "keyword:unkn -- OEIS editors say no formula is known")
    elif cmd == "sweep":
        src = Path(sys.argv[2])
        ids = [int(x) for x in re.findall(r"A?(\d{6})", src.read_text())]
        run(sorted(set(ids)), f"sweep over {src.name}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
