#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""compare_explore — the breadth half of the solving mode.

`solve` commits: it recovers one rule, puts it to the gate, and stops. Two
questions it cannot answer are what *else* would have fit, and how two
surfaces stand relative to each other. That is `explore` and `compare`.

Neither computes a new verdict. `cross_examine` already manufactures
reasonable doubt by hunting a rival generator that describes the same evidence
within a few bits of the winner, and `collapse` already stamps or refuses.
These compose them, because a second search beside a working adversarial court
is exactly the duplicate this repository keeps unpicking.

WHAT EXPLORE IS FOR

A single VERIFIED result reads as settled. Often it is, and the honest way to
show that is to display what was searched and found wanting. When a rival
*does* survive at MDL parity, the injunction is the finding — the conclusion
cannot stand on uniqueness it does not have.

WHAT COMPARE REFUSES TO DO

It will not rank two surfaces on a single number. Two recovered rules are
comparable on stated axes — whether each verified, model class, parameter
count, compression — and a caller who wants a winner gets the axes and the
disagreements, not a score that hides which axis decided. Where the two do
not differ on any stated axis, that is reported as indistinguishable rather
than broken arbitrarily.

    python3 Chiron/compare_explore.py explore 1 1 2 3 5 8 13 21
    python3 Chiron/compare_explore.py compare "1 2 4 8 16" "1 1 2 3 5 8"
    python3 Chiron/compare_explore.py selftest
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

EXPLORE_SCHEMA = "chiron.explore/1"
COMPARE_SCHEMA = "chiron.compare/1"


def _collapse(surface):
    """The canonical recovery path. Chiron carries no second copy of it."""
    try:
        from primus.engine import collapse
    except ImportError:
        seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
        if seed not in sys.path:
            sys.path.insert(0, seed)
        from primus.engine import collapse
    return collapse(surface)


def _as_terms(surface) -> List[int]:
    import re
    if isinstance(surface, (list, tuple)):
        return [int(x) for x in surface]
    return [int(x) for x in re.findall(r"-?\d+", str(surface))]


def explore(surface) -> Dict[str, Any]:
    """Enumerate what fits, and what was searched and rejected.

    Returns the recovered rule together with `cross_examine`'s defence: the
    rival hypotheses it tried, whether any survived at MDL parity, and whether
    an injunction blocks finality. A conclusion that survived cross-examination
    is reported as surviving, never as unique — nothing here searched the whole
    space, and saying otherwise would be a claim no engine made.
    """
    import cross_examine as ce

    terms = _as_terms(surface)
    defence = ce.cross_examine(terms)
    winner = defence.get("winner") or {}

    rivals = []
    for search in defence.get("searches") or []:
        if isinstance(search, Mapping):
            rivals.append({k: search.get(k) for k in
                           ("avenue", "found", "detail", "peer", "model_class")
                           if k in search})

    doubt = bool(defence.get("reasonable_doubt"))
    injunction = (defence.get("injunction") or {}).get("active", False)

    return {
        "schema": EXPLORE_SCHEMA,
        "terms": terms,
        "recovered": {"model_class": winner.get("model_class"),
                      "verified": bool(winner.get("verified"))},
        "rivals_searched": rivals,
        "reasonable_doubt": doubt,
        "doubt_reasons": list(defence.get("doubt_reasons") or []),
        "injunction_active": bool(injunction),
        "evidence_hash": defence.get("evidence_hash"),
        "verdict": defence.get("verdict"),
        "disposition": (
            "BLOCKED — a rival describes this evidence as well" if injunction
            else "SURVIVED — no admissible rival was found in the searched space"
            if winner.get("verified")
            else "NO CASE — nothing verified, so there is nothing to defend"),
        "note": (
            "Surviving cross-examination is not uniqueness. The search space "
            "is the one cross_examine admits, not the space of all rules."
        ),
    }


# The axes a comparison is allowed to speak on. Named here so a caller can see
# what decided an answer, and so a new axis is an edit rather than a surprise.
AXES = ("verified", "model_class", "parameter_count", "compression_ratio")


def _profile(surface) -> Dict[str, Any]:
    terms = _as_terms(surface)
    inv = _collapse(terms)
    record = inv.to_dict() if hasattr(inv, "to_dict") else dict(inv)
    params = record.get("params") or record.get("parameters") or {}
    if isinstance(params, Mapping):
        count = sum(len(v) if isinstance(v, (list, tuple)) else 1
                    for v in params.values())
    else:
        count = len(params) if isinstance(params, (list, tuple)) else None
    return {
        "terms": terms,
        "verified": bool(getattr(inv, "verified", record.get("verified"))),
        "model_class": record.get("model_class"),
        "parameter_count": count,
        "compression_ratio": record.get("compression_ratio")
                             or record.get("ratio"),
    }


def compare(left, right) -> Dict[str, Any]:
    """Put two surfaces side by side on stated axes, with no composite score.

    A single number would hide which axis decided, so there is none. The
    caller gets each axis, the axes that differ, and — only where one side
    verified and the other did not — a statement of which is better supported.
    """
    a, b = _profile(left), _profile(right)

    differences = []
    for axis in AXES:
        if a.get(axis) != b.get(axis):
            differences.append({"axis": axis, "left": a.get(axis),
                                "right": b.get(axis)})

    if a["verified"] and not b["verified"]:
        supported = "left"
    elif b["verified"] and not a["verified"]:
        supported = "right"
    else:
        supported = None

    return {
        "schema": COMPARE_SCHEMA,
        "axes": list(AXES),
        "left": a,
        "right": b,
        "differences": differences,
        "better_supported": supported,
        "indistinguishable": not differences,
        "note": (
            "No composite score is produced. `better_supported` is set only "
            "when exactly one side verified; equal verification on different "
            "model classes is a difference, not a ranking."
        ),
    }


def render_explore(rec: Mapping[str, Any]) -> str:
    lines = ["[explore] %s · %s" % (rec["schema"], rec["disposition"])]
    got = rec.get("recovered") or {}
    lines.append("  recovered: %s (verified=%s)"
                 % (got.get("model_class"), got.get("verified")))
    lines.append("  rivals searched: %d" % len(rec.get("rivals_searched") or []))
    for reason in rec.get("doubt_reasons") or []:
        lines.append("    doubt: %s" % str(reason)[:70])
    return "\n".join(lines)


def render_compare(rec: Mapping[str, Any]) -> str:
    lines = ["[compare] %s" % rec["schema"]]
    for axis in rec["axes"]:
        lines.append("  %-18s left=%-28s right=%s"
                     % (axis, str(rec["left"].get(axis))[:28],
                        str(rec["right"].get(axis))[:28]))
    if rec["indistinguishable"]:
        lines.append("  indistinguishable on every stated axis")
    else:
        lines.append("  differs on: %s"
                     % ", ".join(d["axis"] for d in rec["differences"]))
    lines.append("  better supported: %s" % (rec["better_supported"] or
                                             "neither — see the axes"))
    return "\n".join(lines)


def _selftest() -> int:
    failures, ran = [], []

    def gate(name, condition):
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    fib = explore([1, 1, 2, 3, 5, 8, 13, 21])
    gate("explore recovers and defends a real rule",
         fib["recovered"]["verified"] is True
         and "recurrence" in str(fib["recovered"]["model_class"]))
    gate("explore reports a disposition rather than a bare boolean",
         fib["disposition"].startswith(("SURVIVED", "BLOCKED", "NO CASE")))
    gate("explore never claims uniqueness",
         "uniqueness" in fib["note"] and "not uniqueness" in fib["note"])

    noise = explore([17, 4, 91, 3, 55, 8])
    gate("explore on unstructured input yields NO CASE, not a rule",
         noise["recovered"]["verified"] is False
         and noise["disposition"].startswith("NO CASE"))

    same = compare([1, 1, 2, 3, 5, 8], [1, 1, 2, 3, 5, 8])
    gate("comparing a surface with itself is indistinguishable",
         same["indistinguishable"] is True and same["better_supported"] is None)

    mixed = compare([1, 1, 2, 3, 5, 8, 13, 21], [17, 4, 91, 3, 55, 8])
    gate("compare names the better-supported side only when one verified",
         mixed["better_supported"] == "left")
    gate("compare produces no composite score",
         "score" not in mixed and "rank" not in mixed
         and "No composite score" in mixed["note"])
    gate("compare reports which axes differ",
         any(d["axis"] == "verified" for d in mixed["differences"]))

    both = compare([1, 2, 4, 8, 16, 32], [1, 1, 2, 3, 5, 8, 13, 21])
    gate("two verified surfaces are a difference, never a ranking",
         both["better_supported"] is None
         and any(d["axis"] == "model_class" for d in both["differences"]))

    print("\n  compare_explore self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]

    if not argv or argv[0] in ("selftest", "--selftest"):
        return _selftest() if argv else (print(__doc__.strip().splitlines()[0]) or 0)

    verb, rest = argv[0], argv[1:]
    if verb == "explore":
        if not rest:
            print("usage: compare_explore.py explore <surface>"); return 2
        rec = explore(" ".join(rest))
        print(json.dumps(rec, indent=2) if as_json else render_explore(rec))
        return 0
    if verb == "compare":
        if len(rest) < 2:
            print("usage: compare_explore.py compare <surface-a> <surface-b>")
            return 2
        rec = compare(rest[0], rest[1])
        print(json.dumps(rec, indent=2) if as_json else render_compare(rec))
        return 0
    print("unknown verb: %s (explore | compare | selftest)" % verb)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
