#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
conjecture_triage.py — run Chiron's verify-or-refuse contract over an external
corpus of formalized open conjectures.

Author: Jacob Iannotti. Apache-2.0.

TARGET: google-deepmind/formal-conjectures — 1,024 Lean files, ~3,343 tagged
theorems spanning Erdos problems, Hilbert problems, Millennium problems, OEIS
conjectures, and more.

WHAT THIS IS. Not a theorem prover. Chiron cannot prove a Lean statement and
does not try. This is the triage layer the engine is actually for:

    external claim arrives
      -> identify the finite / exact obligations inside it
      -> discharge the ones that are exactly checkable
      -> emit machine-readable evidence
      -> explicitly bound the conclusion
      -> REFUSE everything beyond it, with a stated reason

The refusals are the product. A verifier that says "I cannot check this" for
the overwhelming majority of open conjectures, and is RIGHT about which
minority it can, is the useful artifact. A tool that claimed otherwise would
be lying.

PRE-REGISTERED EXPECTATION. The overwhelming majority of obligations will be
REFUSED. Open conjectures are open precisely because they are infinitary.
Anything above a few percent discharged would itself be evidence of a bug in
the classifier, not of capability.

THE CLASSIFIER IS VALIDATED BEFORE IT IS TRUSTED. Same discipline as
the OEIS novelty protocol: a hand-labeled control set of statements whose
correct classification is known must come back correct, in BOTH directions,
or the run is abandoned. Defaulting to REFUSED is safe for soundness but
would make a low discharge rate meaningless, so over-refusal is gated too.

Usage:
    python3 eval/conjecture_triage.py validate        # required first
    python3 eval/conjecture_triage.py triage <repo>   # full corpus
\nThis is the PUBLIC build: classification only, no engine required, so
anyone can reproduce the corpus numbers with nothing but a Python 3
interpreter and a clone of the target repo. The deeper pass -- checking
OEIS-referencing obligations against live oeis.org data with the licensed
engine -- is not included here.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

FINITE = "FINITE-CHECKABLE"      # bounded concrete claim; Chiron has an obligation
INFINITARY = "REFUSED-INFINITARY"     # unbounded quantifier / asymptotic
SEMANTICS = "REFUSED-NEEDS-LEAN"      # depends on defs Chiron cannot evaluate
UNKNOWN_ANS = "REFUSED-NO-ANSWER"     # the corpus itself marks the answer unknown

# Unbounded quantification, asymptotics, and infinite objects. Any of these
# and the statement is not a finite obligation, full stop.
INFINITARY_MARKERS = [
    r"∀\s*[^,]*:\s*ℕ\b(?![^,]*<)",   # forall over all naturals, no bound
    r"∀\s*[^,]*:\s*ℤ\b(?![^,]*<)",
    r"∀\s*[^,]*:\s*ℝ\b",
    r"∀\s*[^,]*:\s*ℚ\b",
    r"\{.*\}\.Infinite", r"Set\.Infinite", r"\.Infinite\b",
    r"Filter\.atTop", r"Tendsto", r"⨆", r"⨅", r"limsup", r"liminf",
    r"∑'", r"∏'",                      # infinite sum / product
    r"\bAsymptotic", r"IsBigO", r"IsLittleO", r"~\[",
    r"Irrational\b", r"Transcendental\b",
    r"∃\s*[^,]*:\s*ℝ\b",
]

# A bounded, concrete claim. These are the ones that MIGHT be dischargeable.
FINITE_MARKERS = [
    r"^\s*\w+\s+\d+\s*=\s*-?\d+\s*$",      # a 5 = 12
    r"=\s*-?\d+\s*$",                       # ... = 42
    r"∀\s*\w+\s*<\s*\d+",                   # forall n < 100
    r"∀\s*\w+\s*≤\s*\d+",
    r"∈\s*Finset\.range\s*\d+",
    r"Nat\.decEq", r"\bdecide\b",
]

# Statements whose truth depends on a Lean definition Chiron cannot evaluate.
SEMANTICS_MARKERS = [
    r"^\s*[A-Z]\w*\s+\d+\s*$",              # `A 2` -- predicate application
    r"\bIsGreatest\b", r"\bIsLeast\b", r"\bSupremum\b",
    r"\bMeasurable\b", r"\bContinuous\b", r"\bDifferentiable\b",
]


def classify(stmt: str, has_sorry_answer: bool = False):
    """
    Return (verdict, reason). Order matters: infinitary dominates everything,
    because a bounded-looking fragment inside an unbounded statement does not
    make the statement finite.
    """
    s = " ".join(stmt.split())

    for pat in INFINITARY_MARKERS:
        if re.search(pat, s):
            return INFINITARY, f"unbounded/asymptotic: matches {pat!r}"

    if has_sorry_answer:
        return UNKNOWN_ANS, "corpus marks the answer itself unknown: answer(sorry)"

    for pat in SEMANTICS_MARKERS:
        if re.search(pat, s):
            return SEMANTICS, f"needs Lean semantics: matches {pat!r}"

    for pat in FINITE_MARKERS:
        if re.search(pat, s):
            return FINITE, f"bounded concrete claim: matches {pat!r}"

    return SEMANTICS, "no bounded concrete obligation identified"


# ---------------------------------------------------------------------------
# VALIDATION -- the classifier must be right in both directions first
# ---------------------------------------------------------------------------

CONTROLS = [
    # (statement, expected verdict, why)
    ("a 0 = 2", FINITE, "concrete value claim"),
    ("a 12 = 144", FINITE, "concrete value claim"),
    ("∀ n < 100, P n", FINITE, "explicitly bounded quantifier"),
    ("∀ n : ℕ, ∃ p, p.Prime ∧ p > n", INFINITARY,
     "unbounded forall over naturals"),
    ("{n | P n}.Infinite", INFINITARY, "asserts an infinite set"),
    ("Filter.Tendsto f Filter.atTop (nhds 0)", INFINITARY, "asymptotic"),
    ("Irrational (zeta 3)", INFINITARY, "irrationality of a real"),
    ("∑' n, f n = π ^ 2 / 6", INFINITARY, "infinite sum"),
    ("A 2", SEMANTICS, "predicate application, needs the Lean definition"),
    ("IsGreatest {x | P x} 5", SEMANTICS, "needs Lean order semantics"),
]


def validate():
    print("=" * 74)
    print("CLASSIFIER VALIDATION -- required before any triage run")
    print("=" * 74)
    print("The classifier defaults to REFUSED, which is safe for soundness but")
    print("would make a low discharge rate meaningless. So it is checked in")
    print("BOTH directions: finite things must be called finite, and")
    print("infinitary things must be refused.\n")
    bad = []
    for stmt, want, why in CONTROLS:
        got, reason = classify(stmt)
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {stmt[:44]:46s} -> {got}")
        if not ok:
            print(f"         expected {want} ({why}); got {reason[:60]}")
            bad.append(stmt)
    print()
    if bad:
        print(f"VALIDATION FAILED -- {len(bad)}/{len(CONTROLS)} misclassified.")
        print("ABANDONING. A triage run on a broken classifier is worthless.")
        return False
    print(f"VALIDATION PASSED -- {len(CONTROLS)}/{len(CONTROLS)} correct "
          "in both directions.")
    return True


# ---------------------------------------------------------------------------
# Lean parsing -- deliberately shallow
# ---------------------------------------------------------------------------

# Only structurally unambiguous things are extracted: the attribute line, the
# theorem name, and the raw statement text. No attempt is made to interpret
# Lean semantically -- that is exactly what the engine must refuse to do.
THM_RE = re.compile(
    r"@\[category\s+([a-zA-Z ]+?)\s*(?:,\s*AMS[^\]]*)?\]\s*\n"
    r"\s*(?:theorem|lemma)\s+(\S+)\s*(.*?)(?::=|\Z)",
    re.S)


def parse_file(p: Path):
    txt = p.read_text(errors="replace")
    title = ""
    m = re.search(r"^#\s+(.+)$", txt, re.M)
    if m:
        title = m.group(1).strip()
    aref = re.search(r"oeis\.org/A(\d+)", txt)
    out = []
    for cat, name, stmt in THM_RE.findall(txt):
        clean = " ".join(stmt.split())
        # Lean writes `theorem a_0 : a 0 = 2 := by`, so the captured statement
        # carries a leading ':' (and often binders before it). Strip to the
        # proposition itself, or the concrete-value matcher never fires.
        if ":" in clean:
            clean = clean.split(":", 1)[1].strip()
        out.append({
            "category": cat.strip(),
            "name": name,
            "statement": clean[:300],
            "has_sorry_answer": "answer(sorry)" in stmt,
        })
    return {"file": str(p), "title": title,
            "oeis": int(aref.group(1)) if aref else None, "theorems": out}


def triage(repo: Path):
    if not validate():
        sys.exit(1)
    print()
    files = sorted((repo / "FormalConjectures").rglob("*.lean"))
    print("=" * 74)
    print(f"TRIAGE: {len(files)} files from {repo.name}")
    print("=" * 74)

    tally, by_cat, rows = Counter(), Counter(), []
    for p in files:
        d = parse_file(p)
        area = p.relative_to(repo / "FormalConjectures").parts[0]
        for t in d["theorems"]:
            v, reason = classify(t["statement"], t["has_sorry_answer"])
            tally[v] += 1
            by_cat[(t["category"], v)] += 1
            rows.append({"area": area, "file": p.name, "title": d["title"],
                         "oeis": d["oeis"], **t, "verdict": v, "reason": reason})

    total = sum(tally.values())
    print(f"\n  {total} tagged theorems parsed\n")
    for v, c in tally.most_common():
        print(f"    {v:24s} {c:6d}   {100*c/total:5.1f}%")

    print("\n  by the corpus's own category label:")
    cats = sorted({c for c, _ in by_cat})
    print(f"    {'category':18s} " + "".join(f"{v.split('-')[-1][:9]:>11s}"
                                             for v in tally))
    for c in cats:
        print(f"    {c:18s} " + "".join(f"{by_cat[(c,v)]:11d}" for v in tally))

    fin = [r for r in rows if r["verdict"] == FINITE]
    print(f"\n  FINITE-CHECKABLE obligations: {len(fin)} "
          f"({100*len(fin)/total:.1f}% of corpus)")
    print("  Everything else is REFUSED with a stated reason. That is the")
    print("  correct behaviour, not a shortfall: these conjectures are open")
    print("  precisely because they are not finitely checkable.")

    out = HERE / "triage.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))
    print(f"\n  full certificate: {out}")
    return rows



def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if cmd == "validate":
        sys.exit(0 if validate() else 1)
    if cmd == "triage":
        repo = Path(sys.argv[2]).expanduser()
        if not repo.exists():
            print(f"repo not found: {repo}")
            print("  git clone --depth 1 https://github.com/google-deepmind/formal-conjectures")
            sys.exit(1)
        triage(repo)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
