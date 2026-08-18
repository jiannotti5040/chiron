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
4. Units must be equal, and "no unit" is a unit that matches only "no unit".
   "74%" against a fact recorded as "74 vehicles" is REFUSED, and so is "74%"
   against a bare 74 — agreeing digits are not agreeing facts. A magnitude
   ("M", "thousand") scales the number and is not a unit; a currency ("$")
   is a unit and rides on the value, not the suffix.
5. Subject matching is exact after normalisation (case, whitespace,
   punctuation). Nothing is stemmed: no suffix rule is injective over English,
   and the one that was here folded "species" onto "specie". There is no fuzzy
   matching and no embedding similarity. A near-miss refuses and says what the
   nearest supplied subject was, because a subject the caller did not name is
   a subject the engine cannot claim to have checked.

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
# Suffix stripping used to run on the comparison key. It cannot: no
# suffix rule is injective over English. Stripping a trailing `s` folds
# "species" onto "specie" — two different words, one of which a caller may
# genuinely have supplied — and an external audit (issue #3) caught exactly
# that pairing stamping VERIFIED. The rule survives only as a *hint* in the
# refusal message, where it can help a caller without deciding anything.
_PLURAL = ("'s", "s'", "s")


def _plural_hint(key: str) -> str:
    """A near-miss key, for explaining a refusal. Never used to match."""
    out = []
    for word in key.split():
        for suffix in _PLURAL:
            if len(word) > 3 and word.endswith(suffix):
                word = word[: -len(suffix)]
                break
        out.append(word)
    return " ".join(out)


def normalise_subject(subject: str) -> str:
    """Fold a subject to its comparison key.

    Deliberately shallow, and now deliberately **injective**: lowercase,
    strip punctuation, collapse whitespace. Nothing else. Two subjects that
    were written differently stay different.

    Leading articles are dropped, and that one is safe in both directions:
    no two distinct subjects differ only by "the".

    What must never happen is two different subjects folding together — and
    for a while one did. Plural/possessive stripping folded "species" onto
    "specie", so a claim about one verified against a fact about the other.
    The whole point of this module is that it never claims to have checked a
    subject the caller did not write, so the fold is gone. The cost is that
    "vehicle" no longer matches a fact recorded as "vehicles": that is a
    REFUSAL, which is the honest direction to be wrong in, and the refusal
    says so by name.
    """
    words = _WORD.findall(str(subject).lower())
    # A leading article is not part of a subject. "The 2nd Brigade" and
    # "2nd Brigade" are the same thing, and refusing over one is the kind of
    # uselessness that makes an honest gate look broken. Safe to strip: it
    # cannot merge two subjects that were otherwise distinct.
    while words and words[0] in ("the", "a", "an"):
        words = words[1:]
    return " ".join(words)


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


def _measure(value: Fraction, unit: Optional[str],
             currency: Optional[str] = None
             ) -> Tuple[Fraction, Optional[str], bool]:
    """Separate the magnitude from the unit, and keep both.

    A written quantity carries up to two different things after the digits.
    "$4.2M" is *4.2 million* — a magnitude, which scales the number — and
    *dollars* — a semantic unit, which says what the number counts. They are
    not interchangeable and folding them together is precisely how a dollar
    figure came to verify against a vehicle count (issue #3): the magnitude
    was folded in and the unit slot was then blanked, so the comparison had
    nothing left to disagree about.

    Returns `(scaled_value, semantic_unit, conflict)`. `conflict` is True when
    the claim states two different semantic units at once ("$4.2 percent"),
    which is not a thing to adjudicate — it is a thing to refuse.
    """
    if unit in _SCALE:
        value = value * _SCALE[unit]
        semantic = None
    else:
        semantic = unit
    if currency:
        if semantic is not None and semantic != currency:
            return value, semantic, True
        semantic = currency
    return value, semantic, False


def check_text(text: str, facts: Any) -> Dict[str, Any]:
    """Extract subject/value assertions and check each against supplied facts."""
    table, rejected = build_facts(facts)
    results: List[Dict[str, Any]] = []

    for match in _ASSERTION.finditer(text or ""):
        raw_subject = match.group("subject").strip()
        key = normalise_subject(raw_subject)
        raw_value = match.group("value")
        # The currency sits on the *value* ("$4.2M"), not in the unit slot.
        # Dropping it here is what let a dollar claim arrive unitless.
        currency = "usd" if "$" in raw_value else None
        asserted = _as_number(raw_value.replace("$", ""))
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
            # Say whether a plural/possessive near-miss was the reason, so a
            # caller can fix their table. The hint never selects a fact.
            hint = _plural_hint(key)
            near = [k for k in table if k != key and _plural_hint(k) == hint]
            entry.update(
                status="REFUSED",
                reason=("no supplied fact names this subject"
                        + (" (closest supplied: %s — subjects must match "
                           "exactly; singular and plural are different keys)"
                           % ", ".join(sorted(near)[:3]) if near else "")))
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

        a_value, a_unit, a_conflict = _measure(asserted, unit, currency)
        f_value, f_unit, _ = _measure(fact.value, fact.unit)
        entry["asserted_unit"] = a_unit

        if a_conflict:
            entry.update(status="REFUSED",
                         reason="the claim states two different units at once")
            results.append(entry)
            continue

        # Units must be *equal*, and "no unit" is a unit. Requiring both sides
        # to state one before comparing left every one-sided pairing open, and
        # agreeing digits then decided the verdict on their own.
        if a_unit != f_unit:
            if a_unit is None:
                reason = ("the claim states no unit but the fact is recorded "
                          "in %r" % f_unit)
            elif f_unit is None:
                reason = ("the claim is in %r but the fact is recorded with "
                          "no unit" % a_unit)
            else:
                reason = "units differ: claim in %r, fact in %r" % (a_unit,
                                                                    f_unit)
            entry.update(status="REFUSED", reason=reason)
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

    # This gate used to assert the opposite — that "Vehicles'" and "vehicle"
    # fold together. That fold is what let a claim about "Species" verify
    # against a fact about "specie" (issue #3), so the invariant is inverted:
    # subjects the caller wrote differently must stay different.
    gate("distinct subjects never fold together",
         normalise_subject("Species") != normalise_subject("specie"))
    gate("punctuation and case still do not distinguish a subject",
         normalise_subject("Vehicles'") == normalise_subject("vehicles"))
    gate("a singular claim against a plural fact refuses rather than matching",
         statuses("Vehicle was 412.", {"vehicles": 412}) == ["REFUSED"])
    gate("...and the refusal points at the subject the caller did supply",
         "closest supplied" in check_text("Vehicle was 412.",
                                          {"vehicles": 412})["claims"][0]["reason"])
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
