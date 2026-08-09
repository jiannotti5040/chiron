#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""falsify — what would have to be true for this to be wrong.

Everything else in this vault answers "is it supported?". This answers the
question that actually moves an investigation forward: **what observation
would overturn it, and what is the cheapest one to go get?**

That is the difference between a gate and an instrument. A gate sorts what it
is handed. An instrument tells you where to look next.

THREE DISPOSITIONS, THREE DIFFERENT QUESTIONS

A **VERIFIED** claim needs a *refuter*: a specific, checkable observation that
would make the verdict flip. For a recovered rule that is exact — the rule
predicts term n+1, so any other value at n+1 refutes it, and the prediction is
stated rather than described. For a grounded fact it is the supplied value
changing.

A **REFUSED** claim needs *missing evidence*: not "this is unknowable" but
"here is the specific thing nobody supplied". A refusal that names what it
needs is a task; a refusal that does not is a dead end. This is the case the
rest of the system was weakest on.

A **REFUTED** claim needs neither. It is already overturned, and inventing a
falsifier for it would be theatre.

WHAT THIS WILL NOT DO

It proposes no experiment it cannot state exactly, ranks nothing by a
confidence it does not have, and never implies that surviving a falsifier
makes a claim true — surviving one observation is surviving one observation.
Cost is reported as an ordinal class (`lookup` < `single_observation` <
`series`), never a fabricated number of hours or dollars.

    python3 Chiron/falsify.py "1 1 2 3 5 8 13 21"
    python3 Chiron/falsify.py selftest
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

SCHEMA = "chiron.falsifiers/1"

# Ordinal, not numeric. A number here would be invented.
COST_LOOKUP = "lookup"                    # consult a table you already have
COST_SINGLE = "single_observation"        # observe one more value
COST_SERIES = "series"                    # observe several, or re-run a process
_COST_ORDER = {COST_LOOKUP: 0, COST_SINGLE: 1, COST_SERIES: 2}


def _collapse(surface):
    try:
        from primus.engine import collapse
    except ImportError:
        seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
        if seed not in sys.path:
            sys.path.insert(0, seed)
        from primus.engine import collapse
    return collapse(surface)


def _terms(surface) -> List[int]:
    import re
    if isinstance(surface, (list, tuple)):
        return [int(x) for x in surface]
    return [int(x) for x in re.findall(r"-?\d+", str(surface))]


def falsifiers_for_surface(surface) -> Dict[str, Any]:
    """Exact refuters for a recovered rule.

    A rule that predicts is a rule that can be wrong, and the prediction is
    the falsifier. This states the predicted continuation and says plainly
    that any other observed value at that index overturns the recovery.
    """
    terms = _terms(surface)
    inv = _collapse(terms)
    verified = bool(getattr(inv, "verified", False))
    model_class = getattr(inv, "model_class", None)

    if not verified:
        return {
            "schema": SCHEMA,
            "subject": "surface",
            "disposition": "REFUSED",
            "model_class": model_class,
            "falsifiers": [],
            "missing_evidence": [{
                "what": "more terms of the same series",
                "why": ("no rule was recovered, so there is nothing to refute "
                        "yet; additional terms are what would let a rule be "
                        "recovered or rule one out"),
                "cost": COST_SERIES,
            }],
            "note": ("A refusal is not a claim that no rule exists. It is a "
                     "statement that none was provable from these terms."),
        }

    try:
        predicted = [int(x) for x in inv.predict(len(terms) + 3)][len(terms):]
    except Exception:
        predicted = []

    falsifiers = []
    for offset, value in enumerate(predicted):
        index = len(terms) + offset
        falsifiers.append({
            "observation": "the value at index %d" % index,
            "predicted": value,
            "refutes_if": "the observed value is anything other than %d" % value,
            "cost": COST_SINGLE if offset == 0 else COST_SERIES,
            "exact": True,
        })

    return {
        "schema": SCHEMA,
        "subject": "surface",
        "disposition": "VERIFIED",
        "model_class": model_class,
        "falsifiers": falsifiers,
        "missing_evidence": [],
        "note": ("Surviving these observations is surviving these "
                 "observations. It does not make the rule true, and the "
                 "search space is bounded by what the engine admits."),
    }


def falsifiers_for_certificate(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    """Per-claim refuters and, for refusals, the specific missing evidence.

    The refusal branch is the one that matters. `certify` refuses a claim
    whose subject nobody supplied, and that refusal previously ended the
    conversation. Here it becomes an instruction: supply a fact naming this
    subject, and the claim becomes checkable.
    """
    out: List[Dict[str, Any]] = []
    for claim in certificate.get("claims") or []:
        if not isinstance(claim, Mapping):
            continue
        status = str(claim.get("status") or "").upper()
        kind = claim.get("kind")
        text = claim.get("text")
        entry: Dict[str, Any] = {"claim": text, "kind": kind,
                                 "disposition": status}

        if status == "REFUTED":
            entry["falsifiers"] = []
            entry["missing_evidence"] = []
            entry["note"] = ("Already overturned by the engine. Inventing a "
                             "falsifier for a refuted claim would be theatre.")

        elif status == "VERIFIED":
            if kind == "grounded_fact":
                fact = claim.get("fact") or {}
                entry["falsifiers"] = [{
                    "observation": "the authoritative value for %r"
                                   % (fact.get("subject") or claim.get("subject")),
                    "currently": fact.get("value"),
                    "refutes_if": "the authoritative source records any other value",
                    "cost": COST_LOOKUP,
                    "exact": True,
                }]
            else:
                entry["falsifiers"] = [{
                    "observation": "re-derivation of this claim's arithmetic",
                    "refutes_if": "exact re-computation disagrees",
                    "cost": COST_LOOKUP,
                    "exact": True,
                }]
            entry["missing_evidence"] = []

        elif status == "REFUSED":
            entry["falsifiers"] = []
            subject = claim.get("subject")
            reason = str(claim.get("reason") or "")
            if subject and "no supplied fact" in reason:
                entry["missing_evidence"] = [{
                    "what": "a fact naming %r" % subject,
                    "why": ("the claim is checkable in principle; nothing "
                            "supplied names its subject, so the engine has "
                            "nothing to compare against"),
                    "cost": COST_LOOKUP,
                    "actionable": True,
                }]
            elif "units differ" in reason:
                entry["missing_evidence"] = [{
                    "what": "the subject's value in the unit the claim asserts",
                    "why": reason,
                    "cost": COST_LOOKUP,
                    "actionable": True,
                }]
            elif "names this subject" in reason:
                entry["missing_evidence"] = [{
                    "what": "a single authoritative value for %r" % subject,
                    "why": reason + " — the ambiguity is in the supplied facts",
                    "cost": COST_LOOKUP,
                    "actionable": True,
                }]
            else:
                entry["missing_evidence"] = [{
                    "what": "an exact checker covering this claim's domain",
                    "why": reason or "no exact method applies to this claim",
                    "cost": COST_SERIES,
                    # Honest: this one is not a task the operator can just do.
                    "actionable": False,
                }]
        else:
            entry["falsifiers"] = []
            entry["missing_evidence"] = []
        out.append(entry)

    actionable = [m for e in out for m in e["missing_evidence"]
                  if m.get("actionable")]
    return {
        "schema": SCHEMA,
        "subject": "certificate",
        "claims": out,
        "counts": {
            "with_falsifiers": sum(1 for e in out if e["falsifiers"]),
            "needing_evidence": sum(1 for e in out if e["missing_evidence"]),
            "actionable_now": len(actionable),
        },
        "note": ("A refusal that names what it needs is a task. A refusal "
                 "that does not is a boundary, and both are reported as "
                 "themselves."),
    }


def propose_experiment(report: Mapping[str, Any]) -> Dict[str, Any]:
    """The cheapest single thing to go do next, or an honest 'nothing'.

    Ranked only by the ordinal cost class and whether it is actionable — never
    by an invented probability of being informative. Where nothing is
    actionable, that is stated rather than dressed up as a plan.
    """
    candidates: List[Dict[str, Any]] = []

    for entry in report.get("claims") or []:
        for missing in entry.get("missing_evidence") or []:
            if missing.get("actionable"):
                candidates.append({
                    "action": "obtain %s" % missing["what"],
                    "resolves": entry.get("claim"),
                    "from_disposition": entry.get("disposition"),
                    "cost": missing.get("cost", COST_SERIES),
                    "why": missing.get("why"),
                })
        for falsifier in entry.get("falsifiers") or []:
            candidates.append({
                "action": "check %s" % falsifier["observation"],
                "resolves": entry.get("claim"),
                "from_disposition": entry.get("disposition"),
                "cost": falsifier.get("cost", COST_SERIES),
                "why": falsifier.get("refutes_if"),
            })

    for falsifier in report.get("falsifiers") or []:
        candidates.append({
            "action": "observe %s" % falsifier["observation"],
            "resolves": report.get("model_class"),
            "from_disposition": report.get("disposition"),
            "cost": falsifier.get("cost", COST_SERIES),
            "why": falsifier.get("refutes_if"),
        })
    for missing in report.get("missing_evidence") or []:
        candidates.append({
            "action": "obtain %s" % missing["what"],
            "resolves": report.get("model_class") or "the surface",
            "from_disposition": report.get("disposition"),
            "cost": missing.get("cost", COST_SERIES),
            "why": missing.get("why"),
        })

    if not candidates:
        return {
            "schema": SCHEMA,
            "proposed": None,
            "alternatives": [],
            "note": ("Nothing actionable. Every claim is either already "
                     "overturned or needs a capability that does not exist, "
                     "and proposing work that cannot be done would be worse "
                     "than proposing none."),
        }

    candidates.sort(key=lambda c: _COST_ORDER.get(c["cost"], 9))
    return {
        "schema": SCHEMA,
        "proposed": candidates[0],
        "alternatives": candidates[1:6],
        "note": ("Ranked by cost class only. There is no estimate of how "
                 "likely an observation is to be informative, because the "
                 "engine has no basis for one."),
    }


def render(report: Mapping[str, Any]) -> str:
    lines = ["[falsify] %s · %s" % (report.get("schema"),
                                    report.get("subject"))]
    if report.get("claims") is not None:
        counts = report.get("counts", {})
        lines.append("  %d with falsifiers · %d needing evidence · %d actionable now"
                     % (counts.get("with_falsifiers", 0),
                        counts.get("needing_evidence", 0),
                        counts.get("actionable_now", 0)))
        for entry in report["claims"]:
            lines.append("  [%s] %s" % (entry["disposition"],
                                        str(entry.get("claim"))[:56]))
            for f in entry.get("falsifiers") or []:
                lines.append("      refuted if: %s" % f["refutes_if"][:64])
            for m in entry.get("missing_evidence") or []:
                mark = "NEEDS" if m.get("actionable") else "gap  "
                lines.append("      %s: %s [%s]" % (mark, m["what"][:52], m["cost"]))
    else:
        lines.append("  %s · %s" % (report.get("disposition"),
                                    report.get("model_class")))
        for f in report.get("falsifiers") or []:
            lines.append("      %s -> predicted %s; %s"
                         % (f["observation"], f.get("predicted"),
                            f["refutes_if"][:48]))
        for m in report.get("missing_evidence") or []:
            lines.append("      NEEDS: %s [%s]" % (m["what"], m["cost"]))
    return "\n".join(lines)


def _selftest() -> int:
    failures, ran = [], []

    def gate(name, condition):
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    fib = falsifiers_for_surface([1, 1, 2, 3, 5, 8, 13, 21])
    gate("a verified rule yields exact refuters",
         fib["disposition"] == "VERIFIED" and len(fib["falsifiers"]) >= 1)
    gate("the refuter states the prediction rather than describing it",
         fib["falsifiers"][0]["predicted"] == 34
         and fib["falsifiers"][0]["exact"] is True)
    gate("surviving a falsifier is not claimed to prove the rule",
         "does not make the rule true" in fib["note"])

    noise = falsifiers_for_surface([17, 4, 91, 3, 55, 8])
    gate("an unrecovered surface asks for evidence, not refuters",
         noise["disposition"] == "REFUSED" and not noise["falsifiers"]
         and noise["missing_evidence"])
    gate("refusal is not restated as 'no rule exists'",
         "not a claim that no rule exists" in noise["note"])

    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(_HERE), "Primus", "src"))
    from primus.certify import certify

    facts = {"gross_margin": {"value": 74, "unit": "percent"}}
    cert = certify("Gross margin reached 74%. Retention rose to 88%. "
                   "Revenue was 5 percent.", facts=facts)
    report = falsifiers_for_certificate(cert)

    verified = [c for c in report["claims"] if c["disposition"] == "VERIFIED"]
    refused = [c for c in report["claims"] if c["disposition"] == "REFUSED"]
    gate("a verified grounded claim gets a lookup-cost refuter",
         verified and verified[0]["falsifiers"][0]["cost"] == COST_LOOKUP)
    gate("a refused claim names the fact nobody supplied",
         refused and any("naming" in m["what"] for m in refused[0]["missing_evidence"]))
    gate("that missing evidence is marked actionable",
         refused and refused[0]["missing_evidence"][0]["actionable"] is True)
    gate("counts report what can be done now",
         report["counts"]["actionable_now"] >= 1)

    plan = propose_experiment(report)
    gate("an experiment is proposed from the cheapest actionable gap",
         plan["proposed"] is not None
         and plan["proposed"]["cost"] == COST_LOOKUP)
    gate("no likelihood of being informative is invented",
         "no basis for one" in plan["note"])

    empty = propose_experiment({"claims": [
        {"claim": "x", "disposition": "REFUTED",
         "falsifiers": [], "missing_evidence": []}]})
    gate("nothing actionable proposes nothing rather than busywork",
         empty["proposed"] is None and "worse than proposing none" in empty["note"])

    unactionable = falsifiers_for_certificate({"claims": [
        {"status": "REFUSED", "text": "retention improved",
         "reason": "no exact checker supplied for this domain"}]})
    gate("a domain gap is reported as not actionable",
         unactionable["claims"][0]["missing_evidence"][0]["actionable"] is False)

    print("\n  falsify self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if not argv:
        print("usage: python3 Chiron/falsify.py <surface> | selftest")
        return 2
    if argv[0] in ("selftest", "--selftest"):
        return _selftest()
    report = falsifiers_for_surface(" ".join(argv))
    print(json.dumps(report, indent=2) if as_json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
