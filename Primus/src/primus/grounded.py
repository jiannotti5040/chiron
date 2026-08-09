# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""primus.grounded — check a claim against facts the caller supplies.

THE PROBLEM THIS SOLVES

Every existing claim kind checks a claim whose truth is *internal to the
sentence*: "the sum of 2 and 2 is 4" carries its own proof. Real operational
prose does not. "Readiness fell to 74%" is not vague and not unfalsifiable —
it is simply a statement about a fact that lives in a table the engine has
never seen. So the gate refused it, and refused everything like it. Measured
on an operational paragraph and a financial paragraph, coverage was 0.0%.

A gate that refuses everything is honest and useless. This closes the gap the
only way that preserves the engine's law: **let the caller supply the facts,
and check against them exactly.** A lookup-and-compare is as exact as
arithmetic. Nothing here estimates, infers, or scores.

THE RULES THAT KEEP ZERO FALSE VERIFICATIONS

1. A claim is VERIFIED only when its subject resolves to exactly one supplied
   fact **and** the asserted value equals that fact exactly, compared as
   rationals so 74, 74.0, and 74.00 agree and 74.1 does not.
2. A claim is REFUTED only when the subject resolves to exactly one fact and
   the values differ exactly.
3. Everything else is REFUSED: subject absent, subject ambiguous between two
   facts, units disagreeing, or a value the engine will not parse.
4. Units must match when both sides state one. "74%" against a fact recorded
   as "74 vehicles" is REFUSED, not VERIFIED — agreeing digits are not
   agreeing facts.
5. Subject matching is exact after normalisation (case, whitespace,
   punctuation, and a small set of possessive/plural suffixes). There is no
   fuzzy matching, no stemming beyond that, and no embedding similarity. A
   near-miss refuses, because a subject the caller did not name is a subject
   the engine cannot claim to have checked.

WHAT THIS IS NOT

It is not retrieval and it is not search. It does not go and find facts; it
checks against facts already handed to it. Where those facts come from — a
CSV, a Foundry Ontology object, a database row — is the caller's problem and
their provenance to record.
"""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA = "primus.grounded/1"

# A subject longer than this is prose, not a key.
MAX_SUBJECT_CHARS = 80
MAX_FACTS = 5_000

_WORD = re.compile(r"[a-z0-9]+")
# Only a trailing plural/possessive `s`. An `es` rule folds "vehicles" to
# "vehicl" while "vehicle" stays whole, so the two stop matching — and worse,
# it folds more aggressively in general. Over-folding is the dangerous
# direction here: it makes the engine claim to have checked a subject the
# caller never wrote. Under-folding merely refuses.
_PLURAL = ("'s", "s'", "s")


def normalise_subject(subject: str) -> str:
    """Fold a subject to its comparison key.

    Deliberately shallow: lowercase, strip punctuation, collapse whitespace,
    and remove one trailing plural/possessive `s`. Anything cleverer would
    start matching subjects the caller never wrote, which is the failure mode
    this whole module exists to avoid.

    Leading articles are dropped for the same reason, and that one is safe in
    both directions: no two distinct subjects differ only by "the".

    Folding need not be linguistically correct, only *consistent*: "readiness"
    folds to "readines" on both sides, so it still matches itself. What must
    never happen is two different subjects folding together.
    """
    words = _WORD.findall(str(subject).lower())
    # A leading article is not part of a subject. "The 2nd Brigade" and
    # "2nd Brigade" are the same thing, and refusing over one is the kind of
    # uselessness that makes an honest gate look broken. Safe to strip: it
    # cannot merge two subjects that were otherwise distinct.
    while words and words[0] in ("the", "a", "an"):
        words = words[1:]
    out = []
    for word in words:
        for suffix in _PLURAL:
            if len(word) > 3 and word.endswith(suffix):
                word = word[: -len(suffix)]
                break
        out.append(word)
    return " ".join(out)


def _as_number(value: Any) -> Optional[Fraction]:
    """Exact numeric value, or None if it is not a number we will compare.

    Fraction over float throughout: 0.1 + 0.2 must not decide a verdict.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        # A float that is not exactly representable is still exact *as given*;
        # the caller supplied it and we compare what they supplied.
        return Fraction(str(value))
    text = str(value).strip().replace(",", "")
    match = re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return Fraction(text)


_UNIT_ALIASES = {
    "%": "percent", "percent": "percent", "pct": "percent",
    "usd": "usd", "$": "usd", "dollars": "usd", "dollar": "usd",
    "m": "million", "million": "million", "mm": "million",
    "k": "thousand", "thousand": "thousand",
    "b": "billion", "billion": "billion", "bn": "billion",
}

_SCALE = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}


def _unit_of(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    token = str(raw).strip().lower()
    if not token:
        return None
    return _UNIT_ALIASES.get(token, token)


class Fact:
    """One supplied ground-truth fact: a subject, a value, and maybe a unit."""

    __slots__ = ("subject", "key", "value", "unit", "source")

    def __init__(self, subject: str, value: Any, unit: Any = None,
                 source: Optional[str] = None) -> None:
        self.subject = str(subject)[:MAX_SUBJECT_CHARS]
        self.key = normalise_subject(self.subject)
        self.value = _as_number(value)
        self.unit = _unit_of(unit)
        self.source = source

    def as_dict(self) -> Dict[str, Any]:
        return {"subject": self.subject, "key": self.key,
                "value": None if self.value is None else str(self.value),
                "unit": self.unit, "source": self.source}


def build_facts(facts: Any) -> Tuple[Dict[str, List[Fact]], List[str]]:
    """Accept the shapes a caller actually has, and report what was rejected.

    Supported: a mapping of subject -> value, a mapping of subject -> {value,
    unit, source}, or a sequence of those dicts with an explicit `subject`.
    """
    table: Dict[str, List[Fact]] = {}
    rejected: List[str] = []

    def place(subject: Any, value: Any, unit: Any = None, source: Any = None):
        if len(table) >= MAX_FACTS:
            return
        fact = Fact(subject, value, unit, source)
        if fact.value is None:
            rejected.append("%s (value is not an exact number)" % subject)
            return
        if not fact.key:
            rejected.append("%s (subject normalises to nothing)" % subject)
            return
        table.setdefault(fact.key, []).append(fact)

    if isinstance(facts, Mapping):
        for subject, value in facts.items():
            if isinstance(value, Mapping):
                place(subject, value.get("value"), value.get("unit"),
                      value.get("source"))
            else:
                place(subject, value)
    elif isinstance(facts, Sequence) and not isinstance(facts, (str, bytes)):
        for entry in facts:
            if not isinstance(entry, Mapping):
                rejected.append("%r (not an object)" % (entry,))
                continue
            subject = entry.get("subject") or entry.get("key") or entry.get("name")
            if subject is None:
                rejected.append("%r (no subject)" % (entry,))
                continue
            place(subject, entry.get("value"), entry.get("unit"),
                  entry.get("source"))
    elif facts is not None:
        rejected.append("facts must be a mapping or a sequence of objects")
    return table, rejected


# "<subject> is/was/fell to/rose to <number><unit?>" — the shapes operational
# prose actually uses. Deliberately narrow: a sentence this does not match is
# not extracted at all, which is a refusal to guess rather than a miss.
_ASSERTION = re.compile(
    r"(?P<subject>[A-Za-z][A-Za-z0-9 _/'\-]{1," + str(MAX_SUBJECT_CHARS) + r"}?)\s+"
    r"(?:is|was|are|were|=|:|fell to|rose to|dropped to|increased to|"
    r"decreased to|reached|stands at|stood at|totall?ed|reported as)\s+"
    r"(?P<value>[-+]?\$?\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<unit>%|percent|pct|usd|dollars?|million|billion|thousand|m|bn|k)?"
    r"(?=\W|$)",
    re.I,
)


def _scaled(value: Fraction, unit: Optional[str]) -> Tuple[Fraction, Optional[str]]:
    """Fold a magnitude suffix into the number, keeping the real unit.

    "$4.2M" and a fact of 4200000 usd must agree; "4.2" and "4200000" must not.
    """
    if unit in _SCALE:
        return value * _SCALE[unit], None
    return value, unit


def check_text(text: str, facts: Any) -> Dict[str, Any]:
    """Extract subject/value assertions and check each against supplied facts."""
    table, rejected = build_facts(facts)
    results: List[Dict[str, Any]] = []

    for match in _ASSERTION.finditer(text or ""):
        raw_subject = match.group("subject").strip()
        key = normalise_subject(raw_subject)
        asserted = _as_number(match.group("value").replace("$", ""))
        unit = _unit_of(match.group("unit"))
        if asserted is None or not key:
            continue

        entry = {
            "kind": "grounded_fact",
            "text": match.group(0).strip()[:100],
            "span": list(match.span()),
            "subject": raw_subject,
            "subject_key": key,
            "asserted": str(asserted),
            "asserted_unit": unit,
        }

        candidates = table.get(key)
        if not candidates:
            entry.update(status="REFUSED",
                         reason="no supplied fact names this subject")
            results.append(entry)
            continue
        if len(candidates) > 1:
            # Two facts under one key is the caller's ambiguity, not ours to
            # resolve by picking.
            entry.update(status="REFUSED",
                         reason="the supplied facts name this subject %d times"
                                % len(candidates))
            results.append(entry)
            continue

        fact = candidates[0]
        entry["fact"] = fact.as_dict()

        a_value, a_unit = _scaled(asserted, unit)
        f_value, f_unit = _scaled(fact.value, fact.unit)

        if a_unit and f_unit and a_unit != f_unit:
            entry.update(status="REFUSED",
                         reason="units differ: claim in %r, fact in %r"
                                % (a_unit, f_unit))
            results.append(entry)
            continue

        entry.update(status="VERIFIED" if a_value == f_value else "REFUTED",
                     reason=("exact match against the supplied fact"
                             if a_value == f_value else
                             "supplied fact is %s, claim says %s"
                             % (f_value, a_value)))
        results.append(entry)

    counts = {
        "checked": len(results),
        "verified": sum(r["status"] == "VERIFIED" for r in results),
        "refuted": sum(r["status"] == "REFUTED" for r in results),
        "refused": sum(r["status"] == "REFUSED" for r in results),
    }
    return {
        "schema": SCHEMA,
        "claims": results,
        "counts": counts,
        "facts_supplied": sum(len(v) for v in table.values()),
        "facts_rejected": rejected,
        "note": ("A claim is verified only where exactly one supplied fact "
                 "names its subject and the values match exactly. Absent, "
                 "ambiguous, or unit-mismatched subjects are refused, never "
                 "guessed."),
    }


def _selftest() -> int:
    failures, ran = [], []

    def gate(name, condition):
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    def statuses(text, facts):
        return [c["status"] for c in check_text(text, facts)["claims"]]

    facts = {"readiness": {"value": 74, "unit": "percent"},
             "serviceable vehicles": 412,
             "revenue": {"value": 4_200_000, "unit": "usd"}}

    gate("a claim matching a supplied fact verifies",
         statuses("Readiness fell to 74%.", facts) == ["VERIFIED"])
    gate("a claim contradicting a supplied fact is refuted",
         statuses("Readiness fell to 71%.", facts) == ["REFUTED"])
    gate("a subject nobody supplied is refused, not refuted",
         statuses("Morale rose to 88%.", facts) == ["REFUSED"])
    gate("the refusal says the subject was not supplied",
         "no supplied fact" in check_text("Morale rose to 88%.", facts)
         ["claims"][0]["reason"])

    gate("magnitude suffixes fold into the number",
         statuses("Revenue was $4.2M.", facts) == ["VERIFIED"])
    gate("a wrong magnitude is refuted, not excused",
         statuses("Revenue was $4.3M.", facts) == ["REFUTED"])
    gate("trailing zeros do not change a value",
         statuses("Readiness was 74.00%.", facts) == ["VERIFIED"])
    gate("a tenth of a percent is a different number",
         statuses("Readiness was 74.1%.", facts) == ["REFUTED"])

    gate("agreeing digits with disagreeing units are refused",
         statuses("Serviceable vehicles was 412%.",
                  {"serviceable vehicles": {"value": 412, "unit": "vehicles"}})
         == ["REFUSED"])

    gate("an ambiguous subject is refused rather than picked",
         statuses("Readiness was 74%.",
                  [{"subject": "readiness", "value": 74},
                   {"subject": "Readiness", "value": 71}]) == ["REFUSED"])

    gate("plural and possessive fold to the same key",
         normalise_subject("Vehicles'") == normalise_subject("vehicle"))
    gate("a leading article does not prevent a match",
         normalise_subject("The 2nd Brigade") == normalise_subject("2nd Brigade"))
    gate("a near-miss subject does not match",
         statuses("Vehicle readiness was 74%.", facts) == ["REFUSED"])

    gate("a fact whose value is not a number is rejected and reported",
         check_text("x is 1.", {"x": "not a number"})["facts_rejected"])
    gate("no facts supplied means everything refuses",
         statuses("Readiness fell to 74%.", {}) == ["REFUSED"])

    # The invariant: nothing verifies without an exact supplied match.
    big = check_text(
        "Readiness fell to 74%. Revenue was $4.2M. Morale rose to 88%. "
        "Serviceable vehicles was 412.", facts)
    gate("a mixed paragraph verifies only what was supplied",
         big["counts"]["verified"] == 3 and big["counts"]["refused"] == 1
         and big["counts"]["refuted"] == 0)
    gate("coverage is now non-zero on operational prose",
         big["counts"]["checked"] == 4)

    print("\n  grounded self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
