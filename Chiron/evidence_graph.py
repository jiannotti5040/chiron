#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""evidence_graph — join the records the vault already produces into lineage.

The pieces existed and nothing connected them. `source_provenance` registers a
file and hashes it. `attest` says which supplied input produced each span.
`certify` returns a verdict per claim. Each is a good record on its own, and
together they were a pile: no way to ask *which source is this conclusion
standing on*, or *what contradicts it*.

This builds the graph. It computes nothing new and re-verifies nothing — every
node carries a verdict some engine already reached, and this module would
rather drop an edge than invent one.

    Source ──derived_from── Claim ──supports/contradicts── Evidence
       │                      │
       └──consumes── EngineRun ──produces── Candidate
                              └──certifies── Certificate

The record vocabulary is deliberately the one already defined in
`foundry_boundary`: RecordKind, RelationKind, CanonicalRecord, RecordLink.
Those types are vendor-neutral despite their module's name — the contract is
`chiron.external-ontology/1` and carries no platform-specific type — and
defining a second, parallel vocabulary here is exactly the duplication this
repository keeps having to unpick. The dependency direction is the one wart:
a core module importing from an integration boundary. Both should move to a
neutral module together if either ever does; splitting them is what would do
damage.

WHAT AN EDGE MEANS

`supports` and `contradicts` are asserted only from an engine's own verdict.
A VERIFIED claim gets a `supports` edge from the evidence it was checked
against; a REFUTED one gets `contradicts`. A REFUSED claim gets **neither** —
refusal means no exact checker applied, which is not weak support, and drawing
a faint edge for it would be the graph telling a lie the engines refused to.

    python3 Chiron/evidence_graph.py --demo
    python3 Chiron/evidence_graph.py selftest
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from foundry_boundary import (  # noqa: E402  (path bootstrap must precede)
    CanonicalRecord,
    ClaimVerdict,
    ContractError,
    RecordKind,
    RecordLink,
    RelationKind,
)

SCHEMA = "chiron.evidence_graph/1"


class EvidenceGraph:
    """A typed, append-only record graph with no verdict authority of its own."""

    def __init__(self) -> None:
        self._records: Dict[str, CanonicalRecord] = {}
        self._order: List[str] = []

    # -- construction ------------------------------------------------------

    def add(self, record: CanonicalRecord) -> str:
        if not isinstance(record, CanonicalRecord):
            raise ContractError("add() takes a CanonicalRecord")
        if record.record_id in self._records:
            raise ContractError("duplicate record id: %s" % record.record_id)
        self._records[record.record_id] = record
        self._order.append(record.record_id)
        return record.record_id

    def link(self, source_id: str, relationship: RelationKind,
             target_id: str) -> None:
        """Attach a typed edge, refusing to point at a record that is absent.

        A dangling edge is worse than a missing one: it reads as lineage and
        resolves to nothing, so it is rejected at the point of creation rather
        than discovered later by whoever trusts the graph.
        """
        if source_id not in self._records:
            raise ContractError("no such source record: %s" % source_id)
        if target_id not in self._records:
            raise ContractError("no such target record: %s" % target_id)
        existing = self._records[source_id]
        edge = RecordLink(relationship=relationship, target_id=target_id)
        if edge in existing.links:
            return
        self._records[source_id] = CanonicalRecord(
            record_type=existing.record_type,
            record_id=existing.record_id,
            attributes=existing.attributes,
            links=existing.links + (edge,),
            disposition=existing.disposition,
        )

    # -- traversal ---------------------------------------------------------

    def get(self, record_id: str) -> Optional[CanonicalRecord]:
        return self._records.get(record_id)

    def of_kind(self, kind: RecordKind) -> List[CanonicalRecord]:
        return [self._records[i] for i in self._order
                if self._records[i].record_type is kind]

    def neighbours(self, record_id: str,
                   relationship: Optional[RelationKind] = None
                   ) -> List[Tuple[RelationKind, CanonicalRecord]]:
        record = self._records.get(record_id)
        if record is None:
            return []
        return [(link.relationship, self._records[link.target_id])
                for link in record.links
                if relationship is None or link.relationship is relationship]

    def lineage(self, record_id: str, _seen: Optional[set] = None
                ) -> List[CanonicalRecord]:
        """Every record reachable from this one, breadth-first, cycles handled.

        Answers "what is this standing on" without the caller writing a walk
        and without a cycle in the data turning into a hang.
        """
        seen = _seen if _seen is not None else set()
        out: List[CanonicalRecord] = []
        queue = [record_id]
        while queue:
            current = queue.pop(0)
            if current in seen or current not in self._records:
                continue
            seen.add(current)
            record = self._records[current]
            if current != record_id:
                out.append(record)
            queue.extend(link.target_id for link in record.links)
        return out

    def contradictions(self) -> List[Dict[str, Any]]:
        """Every claim carrying a contradicting edge, with what contradicts it.

        Surfaced as a first-class query because a contradiction that is only
        discoverable by walking the graph by hand is one nobody will find.
        """
        found = []
        for claim in self.of_kind(RecordKind.CLAIM):
            against = self.neighbours(claim.record_id, RelationKind.CONTRADICTS)
            if against:
                found.append({
                    "claim_id": claim.record_id,
                    "claim": claim.attributes.get("text"),
                    "verdict": claim.attributes.get("verdict"),
                    "contradicted_by": [r.record_id for _, r in against],
                })
        return found

    def unsupported(self) -> List[Dict[str, Any]]:
        """Claims with no supporting edge — including every REFUSED one.

        This is the list that matters most and the one a summary would bury.
        A claim nothing supports is not a small caveat on a result; it is the
        part of the result that is not standing on anything.
        """
        out = []
        for claim in self.of_kind(RecordKind.CLAIM):
            if not self.neighbours(claim.record_id, RelationKind.SUPPORTS):
                out.append({
                    "claim_id": claim.record_id,
                    "claim": claim.attributes.get("text"),
                    "verdict": claim.attributes.get("verdict"),
                    "reason": claim.attributes.get("reason"),
                })
        return out

    # -- output ------------------------------------------------------------

    def as_dict(self) -> Dict[str, Any]:
        records = [self._records[i].as_dict() for i in self._order]
        counts: Dict[str, int] = {}
        for record in records:
            counts[record["kind"]] = counts.get(record["kind"], 0) + 1
        return {
            "schema": SCHEMA,
            "records": records,
            "counts": counts,
            "edge_count": sum(len(r["links"]) for r in records),
            "contradictions": self.contradictions(),
            "unsupported": self.unsupported(),
            "note": (
                "Edges restate verdicts the engines already reached. A REFUSED "
                "claim carries neither a supporting nor a contradicting edge: "
                "refusal means no exact checker applied, which is not weak "
                "support."
            ),
        }


# --------------------------------------------------------------------------
# building a graph from records the vault actually emits


def _claim_id(index: int) -> str:
    return "claim:%d" % index


def from_certificate(certificate: Mapping[str, Any], *,
                     source: Optional[Mapping[str, Any]] = None,
                     graph: Optional[EvidenceGraph] = None) -> EvidenceGraph:
    """Build lineage from a `primus.certificate/2` record.

    The certificate already says, per claim, what was checked and how it came
    out. This turns that into Source → Claim → Evidence with the verdict
    driving the edge kind, and adds an EngineRun and a Certificate so a result
    can be traced back to the run that produced it.
    """
    graph = graph or EvidenceGraph()

    source_id = "source:input"
    attributes: Dict[str, Any] = {"origin": "inline text"}
    if source:
        attributes = {k: v for k, v in source.items()
                      if isinstance(v, (str, int, float, bool)) or v is None}
        source_id = "source:%s" % (source.get("source_id")
                                   or source.get("name") or "input")
    graph.add(CanonicalRecord(record_type=RecordKind.SOURCE,
                              record_id=source_id, attributes=attributes))

    run_id = "run:certify"
    graph.add(CanonicalRecord(
        record_type=RecordKind.ENGINE_RUN, record_id=run_id,
        attributes={"engine": "primus.certify",
                    "contract": certificate.get("schema", "primus.certificate/2")}))
    graph.link(run_id, RelationKind.CONSUMES, source_id)

    certificate_id = "certificate:1"
    graph.add(CanonicalRecord(
        record_type=RecordKind.CERTIFICATE, record_id=certificate_id,
        attributes={k: certificate.get(k) for k in
                    ("schema", "counts", "coverage", "attestation_sha256")
                    if k in certificate}))
    graph.link(run_id, RelationKind.PRODUCES, certificate_id)

    for index, claim in enumerate(certificate.get("claims") or []):
        if not isinstance(claim, Mapping):
            continue
        verdict = str(claim.get("verdict") or claim.get("status") or "").upper()
        cid = _claim_id(index)
        graph.add(CanonicalRecord(
            record_type=RecordKind.CLAIM, record_id=cid,
            attributes={"text": claim.get("text") or claim.get("claim"),
                        "kind": claim.get("kind"),
                        "verdict": verdict,
                        "reason": claim.get("detail") or claim.get("reason")}))
        graph.link(cid, RelationKind.DERIVED_FROM, source_id)
        graph.link(certificate_id, RelationKind.CERTIFIES, cid)

        # The engine's own verdict decides the edge. REFUSED gets no edge at
        # all — see the module docstring.
        if verdict not in (ClaimVerdict.VERIFIED.value, ClaimVerdict.REFUTED.value):
            continue
        eid = "evidence:%d" % index
        graph.add(CanonicalRecord(
            record_type=RecordKind.EVIDENCE, record_id=eid,
            attributes={"basis": "exact check by primus.certify",
                        "kind": claim.get("kind"),
                        "detail": claim.get("detail")}))
        graph.link(eid, RelationKind.DERIVED_FROM, run_id)
        relationship = (RelationKind.SUPPORTS
                        if verdict == ClaimVerdict.VERIFIED.value
                        else RelationKind.CONTRADICTS)
        graph.link(cid, relationship, eid)

    return graph


def from_attestation(attestation: Mapping[str, Any], *,
                     graph: Optional[EvidenceGraph] = None) -> EvidenceGraph:
    """Add span-level attribution from a `chiron.attestation/1` record.

    Attribution and checkability are independent, and this keeps them so: a
    span links to the input it traces to regardless of its verdict, and words
    that trace to nothing are recorded as an explicit attribute rather than
    left as a silent absence.
    """
    graph = graph or EvidenceGraph()

    for index, span in enumerate(attestation.get("spans") or []):
        if not isinstance(span, Mapping):
            continue
        cid = "span:%d" % index
        novel = [t.get("text") for t in (span.get("tokens") or [])
                 if isinstance(t, Mapping) and t.get("novel")]
        graph.add(CanonicalRecord(
            record_type=RecordKind.CLAIM, record_id=cid,
            attributes={"text": span.get("text"),
                        "verdict": str(span.get("verdict") or "").upper(),
                        "reason": span.get("reason"),
                        "novel_words": novel,
                        "traces_to_nothing": not span.get("origin")}))

        origin = span.get("origin")
        if not origin:
            continue
        sid = "source:%s" % origin
        if graph.get(sid) is None:
            graph.add(CanonicalRecord(
                record_type=RecordKind.SOURCE, record_id=sid,
                attributes={"name": origin}))
        graph.link(cid, RelationKind.DERIVED_FROM, sid)

        # Attribution strength is evidence about origin, never about truth.
        cosine = span.get("origin_cosine")
        if isinstance(cosine, (int, float)) and cosine >= 1.0:
            eid = "evidence:verbatim:%d" % index
            graph.add(CanonicalRecord(
                record_type=RecordKind.EVIDENCE, record_id=eid,
                attributes={"basis": "verbatim match against a supplied input",
                            "origin": origin, "origin_cosine": cosine,
                            "about": "origin, not truth"}))
            graph.link(cid, RelationKind.SUPPORTS, eid)

    return graph


def render(graph: EvidenceGraph) -> str:
    doc = graph.as_dict()
    lines = ["[evidence_graph] %s · %d records · %d edges"
             % (doc["schema"], len(doc["records"]), doc["edge_count"])]
    lines.append("  " + " · ".join("%d %s" % (n, k)
                                   for k, n in sorted(doc["counts"].items())))
    if doc["contradictions"]:
        lines.append("  contradictions (%d):" % len(doc["contradictions"]))
        for item in doc["contradictions"]:
            lines.append("    %s  %s" % (item["verdict"],
                                         str(item["claim"])[:64]))
    if doc["unsupported"]:
        lines.append("  standing on nothing (%d):" % len(doc["unsupported"]))
        for item in doc["unsupported"]:
            lines.append("    %s  %s" % (item["verdict"] or "—",
                                         str(item["claim"])[:64]))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# gates


def _selftest() -> int:
    failures = []
    ran = []

    def gate(name, condition, detail=""):
        # The total is counted, never written down. A hardcoded denominator is
        # a number that goes stale the first time a gate is added.
        ran.append(name)
        status = "PASS" if condition else "FAIL"
        if not condition:
            failures.append(name)
        print("  [%s] %s%s" % (status, name, (" — " + detail) if detail and not condition else ""))

    certificate = {
        "schema": "primus.certificate/2",
        "counts": {"verified": 1, "refuted": 1, "refused": 1},
        "claims": [
            {"text": "The sum of 2 and 2 is 4", "kind": "arithmetic", "verdict": "VERIFIED"},
            {"text": "The product of 6 and 7 is 41", "kind": "arithmetic", "verdict": "REFUTED"},
            {"text": "Morale improved in the third quarter", "verdict": "REFUSED",
             "detail": "no exact checker supplied for this domain"},
        ],
    }
    graph = from_certificate(certificate)
    doc = graph.as_dict()

    gate("a certificate becomes a graph", doc["counts"].get("Claim") == 3)
    gate("a VERIFIED claim gains a supporting edge",
         any(r for _, r in graph.neighbours("claim:0", RelationKind.SUPPORTS)))
    gate("a REFUTED claim gains a contradicting edge",
         any(r for _, r in graph.neighbours("claim:1", RelationKind.CONTRADICTS)))
    gate("a REFUSED claim gains neither edge",
         not graph.neighbours("claim:2", RelationKind.SUPPORTS)
         and not graph.neighbours("claim:2", RelationKind.CONTRADICTS))
    gate("refusal is reported as standing on nothing, not as weak support",
         any(u["claim_id"] == "claim:2" for u in doc["unsupported"]))
    gate("contradictions are a first-class query",
         len(doc["contradictions"]) == 1
         and doc["contradictions"][0]["claim_id"] == "claim:1")
    gate("lineage reaches the source through the claim",
         any(r.record_id == "source:input" for r in graph.lineage("claim:0")))
    gate("a certificate certifies every claim it covers",
         len(graph.neighbours("certificate:1", RelationKind.CERTIFIES)) == 3)
    gate("the engine run consumes the source and produces the certificate",
         any(r.record_id == "source:input"
             for _, r in graph.neighbours("run:certify", RelationKind.CONSUMES))
         and any(r.record_id == "certificate:1"
                 for _, r in graph.neighbours("run:certify", RelationKind.PRODUCES)))

    # A dangling edge reads as lineage and resolves to nothing.
    try:
        graph.link("claim:0", RelationKind.SUPPORTS, "evidence:does-not-exist")
        gate("an edge to a missing record is refused", False)
    except ContractError:
        gate("an edge to a missing record is refused", True)

    try:
        graph.add(CanonicalRecord(record_type=RecordKind.CLAIM,
                                  record_id="claim:0", attributes={}))
        gate("a duplicate record id is refused", False)
    except ContractError:
        gate("a duplicate record id is refused", True)

    attestation = {
        "schema": "chiron.attestation/1",
        "spans": [
            {"text": "The product of 6 and 7 is 42.", "verdict": "REFUSED",
             "origin": "src.txt", "origin_cosine": 1.0,
             "tokens": [{"text": "The", "novel": False}]},
            {"text": "Churn fell because of onboarding.", "verdict": "REFUSED",
             "origin": None,
             "tokens": [{"text": "Churn", "novel": True},
                        {"text": "onboarding", "novel": True}]},
        ],
    }
    att = from_attestation(attestation)
    gate("a verbatim span links to the input it traces to",
         any(r.record_id == "source:src.txt"
             for _, r in att.neighbours("span:0", RelationKind.DERIVED_FROM)))
    gate("attribution evidence is labelled as being about origin, not truth",
         any(r.attributes.get("about") == "origin, not truth"
             for _, r in att.neighbours("span:0", RelationKind.SUPPORTS)))
    gate("a span tracing to nothing is recorded as such",
         att.get("span:1").attributes["traces_to_nothing"] is True
         and att.get("span:1").attributes["novel_words"] == ["Churn", "onboarding"])

    # A cycle must not hang the walk.
    cyc = EvidenceGraph()
    cyc.add(CanonicalRecord(record_type=RecordKind.CLAIM, record_id="a", attributes={}))
    cyc.add(CanonicalRecord(record_type=RecordKind.CLAIM, record_id="b", attributes={}))
    cyc.link("a", RelationKind.DERIVED_FROM, "b")
    cyc.link("b", RelationKind.DERIVED_FROM, "a")
    gate("a cycle terminates rather than hanging", len(cyc.lineage("a")) == 1)

    print("\n  evidence_graph self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "selftest" in argv or "--selftest" in argv:
        return _selftest()
    if "--demo" in argv:
        certificate = {
            "schema": "primus.certificate/2",
            "claims": [
                {"text": "The sum of 2 and 2 is 4", "kind": "arithmetic", "verdict": "VERIFIED"},
                {"text": "The product of 6 and 7 is 41", "kind": "arithmetic", "verdict": "REFUTED"},
                {"text": "Morale improved", "verdict": "REFUSED",
                 "detail": "no exact checker supplied for this domain"},
            ],
        }
        graph = from_certificate(certificate)
        if "--json" in argv:
            print(json.dumps(graph.as_dict(), indent=2))
        else:
            print(render(graph))
        return 0
    print(__doc__.strip().splitlines()[0])
    print("usage: python3 Chiron/evidence_graph.py [--demo [--json] | selftest]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
