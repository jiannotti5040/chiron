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
    # Found by A181477, whose name reads "a(n) has generating function
    # 1/((1-x)^k*(1-x^2)^(k*(k-1)/2)) for k=5." The G.f. patterns below all
    # require the literal abbreviation; spelled out, it sailed through as a
    # false survivor. Same failure shape as the original A279538 bug.
    r"\bgenerating function\b",
    r"\bexponential generating function\b",
    r"\brecurrence\b",
    r"\bclosed form\b",
    # UNANCHORED on purpose. OEIS names routinely read "Powers of 2: a(n) = 2^n"
    # or "Triangular numbers: a(n) = binomial(n+1,2)" -- a descriptive phrase,
    # a colon, then the rule. An anchored ^a(n)= misses every one of those, and
    # they are unambiguously documented. Widening this direction risks calling
    # something documented that is not, which is why CONTROLS_UNDOCUMENTED
    # gained cases that mention a(n) WITHOUT defining it.
    r"\ba\s*\(\s*n\s*\)\s*=\s*\S",
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


# Base-dependent classes OEIS does not always keyword `base`. A286508 --
# "Binary representation of the diagonal ... cellular automaton Rule 190" --
# is keyworded only `nonn,easy`, so the keyword gate never saw it. Its terms
# are binary strings read as decimal integers; any recovered "rule" is an
# artifact of the writing, not a fact about the automaton.
BASE_NAME_RE = re.compile(
    r"^\s*(Binary|Decimal|Ternary|Hexadecimal|Base-?\d+)\s+(representation|expansion)\b"
    r"|\bwritten in base\b|\bin base \d+\b|\bdigits? of\b", re.I)

# "Row 4 of array in A265080", "Row sums of the triangular array at A249057".
# For these the mathematics lives in the PARENT entry, which the detector was
# never reading. Four of six survivors were this class.
PARENT_RE = re.compile(
    r"\b(?:Row|Column|Diagonal|Antidiagonal)s?\b[^.]{0,40}?\bA(\d{6})\b"
    r"|\bRow sums? of\b[^.]{0,40}?\bA(\d{6})\b"
    r"|\b(?:array|triangle|table)\b[^.]{0,20}?\b(?:in|at|of)\s+A(\d{6})\b", re.I)


def _lines(entry, key):
    v = entry.get(key)
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def parent_of(entry):
    """A-number of the array/triangle this entry is a row of, or None."""
    m = PARENT_RE.search(entry.get("name", "") or "")
    if not m:
        return None
    g = next((x for x in m.groups() if x), None)
    return int(g) if g else None


def documented(entry, follow_parent=True):
    """Return (is_documented, reason). Ambiguity resolves to documented."""
    # A base-representation sequence is an encoding artifact, not mathematics.
    if BASE_NAME_RE.search(entry.get("name", "") or ""):
        return True, f"base-representation artifact: {(entry.get('name') or '')[:70]}"

    # A row of a documented array is documented BY that array. Follow it once
    # (never recursively -- one hop is the real pattern and it cannot loop).
    if follow_parent:
        p = parent_of(entry)
        if p is not None and p != entry.get("number"):
            pe = entry_by_number(p)
            if pe is not None:
                ok, why = documented(pe, follow_parent=False)
                if ok:
                    return True, f"parent A{p:06d} documents it -> {why[:60]}"
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


def entry_by_number(anum):
    """entry() by A-number, tolerating fetch failure (used for parent lookup)."""
    try:
        return entry(anum)
    except Exception:
        return None


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
    # Real cases found during the run: descriptive phrase, colon, then the rule.
    # An anchored ^a(n)= misses all of these.
    (79,     "name: 'Powers of 2: a(n) = 2^n' -- rule after a colon"),
    (244,    "name: 'Powers of 3: a(n) = 3^n'"),
    (290,    "name: 'The squares: a(n) = n^2'"),
    (217,    "name: 'Triangular numbers: a(n) = binomial(n+1,2) = n*(n+1)/2'"),
]


# Filter 0 above only proves the detector has no FALSE NEGATIVES. A detector
# that called everything documented would pass it perfectly and then report
# zero survivors -- a vacuous zero. These are the opposite control: entries
# with no rule stated anywhere, which the detector must call UNDOCUMENTED.
# Without this, a null result from this search would mean nothing.
CONTROLS_UNDOCUMENTED = [
    ("bare definitional name, nothing else",
     {"name": "Number of ways to place n nonattacking queens on an n X n board.",
      "keyword": "nonn,hard"}),
    ("prose comment, no rule",
     {"name": "Primes p such that p+2 is also prime.",
      "comment": ["These are the lesser of twin primes. - _Some Author_"],
      "keyword": "nonn"}),
    ("xref that is only a Cf. list",
     {"name": "Number of distinct prime factors of n!.",
      "xref": ["Cf. A000142, A001221."], "keyword": "nonn"}),
    ("program that is a brute-force search, no closed form",
     {"name": "Numbers whose digits sum to a perfect square.",
      "program": ['(PARI) for(n=1,100, if(issquare(sumdigits(n)), print1(n", ")))'],
      "keyword": "nonn"}),
    ("example showing terms, not a formula",
     {"name": "Number of partitions of n into distinct parts.",
      "example": ["a(5) = 3 because 5 = 4+1 = 3+2."], "keyword": "nonn"}),
    ("link with no recurrence index",
     {"name": "Number of self-avoiding walks on a square lattice.",
      "link": ['A. Author, <a href="/A001411/b001411.txt">Table of n, a(n)</a>'],
      "keyword": "nonn,walk"}),
    # These three exist because NAME_PATTERNS was unanchored to catch names of
    # the form "Powers of 2: a(n) = 2^n". Unanchoring risks matching a name
    # that MENTIONS a(n) without defining it. It must not.
    ("name mentions a(n) as a condition, does not define it",
     {"name": "Numbers n such that a(n) is prime.", "keyword": "nonn"}),
    ("name refers to another sequence's a(n)",
     {"name": "Indices n for which A000045(n) is a perfect square.",
      "keyword": "nonn"}),
    ("name poses a question about a(n)",
     {"name": "Smallest k such that a(k) exceeds n.", "keyword": "nonn"}),
]


def filter0b():
    """The detector must also be able to say NO, or a zero result is vacuous."""
    print("\n" + "=" * 74)
    print("FILTER 0b -- the detector must DISCRIMINATE, not just say 'documented'")
    print("=" * 74)
    bad = []
    for why, e in CONTROLS_UNDOCUMENTED:
        ok, reason = documented(e)
        print(f"  [{'FAIL' if ok else 'PASS'}  ] {why}")
        if ok:
            print(f"           wrongly documented via: {reason[:70]}")
            bad.append(why)
    print()
    if bad:
        print(f"FILTER 0b FAILED -- {len(bad)} false positives. The detector is")
        print("over-broad, so a zero result would be VACUOUS. ABANDONING.")
        return False
    print(f"FILTER 0b PASSED -- {len(CONTROLS_UNDOCUMENTED)}/"
          f"{len(CONTROLS_UNDOCUMENTED)} correctly NOT-documented.")
    print("The detector discriminates both ways; a zero result is meaningful.")
    return True


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
    return filter0b()


# ---------------------------------------------------------------------------
# Candidate evaluation, six filters in order
# ---------------------------------------------------------------------------

def evaluate(anum, verbose=True):
    """
    Return (verdict, detail). 'SURVIVOR' means it passed every filter.

    Filters run cheapest-first ON PURPOSE. Everything derivable from the entry
    JSON (keywords, growth, documentation) is applied before the b-file is
    fetched, because the b-file is a second network round trip and the
    documentation check kills most candidates for free. Order does not affect
    which sequences survive -- a survivor must pass all of them regardless --
    it only affects how many requests OEIS is asked to serve.
    """
    e = entry(anum)
    if e is None:
        return "no-entry", "could not fetch"

    kw = set((e.get("keyword") or "").split(","))
    name = (e.get("name") or "")[:70]

    # Filter 3 -- structurally trivial classes (free)
    bad = kw & EXCLUDED_KEYWORDS
    if bad:
        return "excluded-keyword", f"{','.join(sorted(bad))} | {name}"

    data = [int(x) for x in (e.get("data") or "").split(",")
            if x.strip().lstrip("-").isdigit()]
    if len(data) < MIN_DATA_TERMS:
        return "too-short", f"{len(data)} terms in data | {name}"

    # Filter 4 -- require growth (free)
    g = growth_ratio(data)
    if g < MIN_GROWTH_RATIO:
        return "flat", f"growth {g:.1f} < {MIN_GROWTH_RATIO} | {name}"

    # Filter 5 -- already documented? (free, and kills most candidates)
    doc, reason = documented(e)
    if doc:
        return "documented", f"{reason[:70]}"

    # Filter 2 -- a REAL b-file, not one OEIS synthesized from `data` (1 request)
    terms, status = bfile(anum, len(data))
    if status != "real":
        return f"bfile-{status}", f"{len(terms)} terms vs {len(data)} in data | {name}"

    # The engine must reproduce every single b-file term
    inv, why = recovers_exactly(terms)
    if inv is None:
        return "no-exact-recovery", f"{why} | {name}"

    return "SURVIVOR", (f"{inv.model_class} | {why} | bfile={len(terms)} "
                        f"data={len(data)} growth={g:.0f} | {name}")


def run(anums, label):
    print("=" * 74)
    print(f"RUN: {label}  ({len(anums)} candidates)")
    print("=" * 74)
    sys.stdout.reconfigure(line_buffering=True)

    # Resumable: a 3,000-candidate run at OEIS's politeness delay takes hours,
    # and losing it to a transient network error would be pure waste.
    ledger = CACHE / "sweep_ledger.tsv"
    done = {}
    if ledger.exists():
        for ln in ledger.read_text().splitlines():
            p = ln.split("\t")
            if len(p) >= 3:
                done[int(p[0])] = (p[1], p[2])
        print(f"  resuming: {len(done)} already evaluated\n")

    tally, survivors = {}, []
    with ledger.open("a") as log:
        for i, a in enumerate(anums, 1):
            if a in done:
                verdict, detail = done[a]
            else:
                try:
                    verdict, detail = evaluate(a)
                except Exception as ex:          # never lose the run to one entry
                    verdict, detail = "error", f"{type(ex).__name__}: {ex}"[:90]
                log.write(f"{a}\t{verdict}\t{detail}\n")
                log.flush()
            tally[verdict] = tally.get(verdict, 0) + 1
            if verdict == "SURVIVOR":
                survivors.append((a, detail))
                print(f"  *** SURVIVOR  A{a:06d}  {detail}")
            if i % 100 == 0:
                top = sorted(tally.items(), key=lambda x: -x[1])[:3]
                print(f"      {i}/{len(anums)}  survivors={len(survivors)}  "
                      + "  ".join(f"{k}={v}" for k, v in top))

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
