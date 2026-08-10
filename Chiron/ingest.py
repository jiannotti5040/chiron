#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""ingest — hand it anything, get back the certified law underneath it.

Every other entry point asks the caller to already know what they have. Is
this a sequence? A table? Prose with checkable claims? Pick the right verb,
shape the argument, then get an answer. That is a reasonable API and a bad
product: the person with the file is exactly the person who does not yet know
what is in it.

This reads text or a file, works out what mathematical structure is actually
present, routes it to the engine that can certify that structure, and returns
the recovered invariant together with **what you can now do with it**.

WHAT IT LOOKS FOR, in order

  1. A **table** — CSV, TSV, or JSON records. Routed to `primus.relate`, which
     recovers an exact law across columns and names the rows that break it.
  2. A **sequence** — enough integers in order to be a series. Routed to
     `primus.engine.collapse`, which recovers the generator and proves it on
     held-out terms.
  3. **Claims in prose** — routed to `primus.certify`.

Detection is structural, never statistical. Four integers in a sentence are
not a series just because they are four integers, so a sequence is only
proposed when the numbers are the dominant content rather than incidental to
it. Getting this wrong in the permissive direction would mean confidently
"recovering" a law from a phone number.

THE PART THAT MATTERS: WHAT COMES NEXT

A recovered invariant is not the end of the interaction, it is the start of
one. Every result carries `next` — the operations that are meaningful *for
that specific invariant*, with the arguments already filled in. A verified
sequence can be extended and falsified. A verified relation can be solved
backwards. A refusal names what evidence would resolve it. Nothing offers an
operation that would not work.

    python3 Chiron/ingest.py data.csv
    python3 Chiron/ingest.py "2 4 8 16 32 64"
    python3 Chiron/ingest.py selftest
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

SCHEMA = "chiron.ingest/1"
MAX_BYTES = 8 * 1024 * 1024
# Below this, "a run of integers" is a coincidence rather than a series.
MIN_SEQUENCE_TERMS = 5
# A sequence must be most of what the text is. Prose that mentions six numbers
# is prose; refusing to treat it as a series is the whole point.
SEQUENCE_DENSITY = 0.6


def _ensure_primus() -> None:
    try:
        import primus  # noqa: F401
    except ImportError:
        seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
        if seed not in sys.path:
            sys.path.insert(0, seed)


def _read(source: str) -> Dict[str, Any]:
    """Text, or the contents of a path. A path that exists wins; everything
    else is treated as the text itself."""
    expanded = os.path.abspath(os.path.expanduser(source)) if len(source) < 4096 else ""
    if expanded and os.path.isfile(expanded):
        size = os.path.getsize(expanded)
        if size > MAX_BYTES:
            raise ValueError("file is %d bytes; the bound is %d" % (size, MAX_BYTES))
        with open(expanded, "rb") as fh:
            raw = fh.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Strict, for the same reason source_provenance is strict: a lossy
            # decode changes byte lengths and every span after it.
            raise ValueError("file is not valid UTF-8; no lossy decode is "
                             "attempted because it would corrupt every offset")
        return {"text": text, "origin": {"from": "file", "path": expanded,
                                         "bytes": size}}
    return {"text": source, "origin": {"from": "argument",
                                       "chars": len(source)}}


# ------------------------------------------------------------------ detect

def _try_json_records(text: str) -> Optional[List[Dict[str, Any]]]:
    stripped = text.strip()
    if not stripped.startswith("["):
        return None
    try:
        parsed = json.loads(stripped)
    except ValueError:
        return None
    if isinstance(parsed, list) and len(parsed) >= 5 and \
            all(isinstance(row, dict) for row in parsed):
        return parsed
    return None


def _try_delimited(text: str) -> Optional[List[Dict[str, Any]]]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 6:                      # header + five rows
        return None
    sample = "\n".join(lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return None
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    if len(rows) < 5:
        return None
    # Every column must be present in every row; a ragged file is not a table
    # this engine will reason about.
    header = set(rows[0])
    if not header or any(set(r) != header or None in r for r in rows):
        return None
    typed: List[Dict[str, Any]] = []
    for row in rows:
        converted: Dict[str, Any] = {}
        for key, value in row.items():
            value = (value or "").strip()
            try:
                converted[key] = int(value)
            except ValueError:
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = value
        typed.append(converted)
    numeric_columns = [c for c in header
                       if all(isinstance(r[c], (int, float)) for r in typed)]
    return typed if len(numeric_columns) >= 2 else None


def _try_sequence(text: str) -> Optional[List[int]]:
    integers = re.findall(r"-?\d+", text)
    if len(integers) < MIN_SEQUENCE_TERMS:
        return None
    digits_and_seps = sum(len(m) for m in integers) + text.count(",") + text.count(" ")
    if len(text.strip()) and digits_and_seps / len(text.strip()) < SEQUENCE_DENSITY:
        return None
    try:
        return [int(x) for x in integers]
    except ValueError:
        return None


# ------------------------------------------------------------------- route

def ingest(source: str, target: Optional[str] = None) -> Dict[str, Any]:
    """Detect the structure in `source`, certify it, and say what to do next."""
    _ensure_primus()
    got = _read(source)
    text = got["text"]
    origin = got["origin"]

    records = _try_json_records(text) or _try_delimited(text)
    if records is not None:
        from primus.relate import relate
        columns = [k for k in records[0]
                   if all(isinstance(r.get(k), (int, float)) for r in records)]
        chosen = target if target in columns else (columns[-1] if columns else None)
        if chosen is None or len(columns) < 2:
            return {"schema": SCHEMA, "origin": origin, "detected": "table",
                    "status": "REFUSED",
                    "reason": "the table has fewer than two fully numeric "
                              "columns, so there is no relation to recover",
                    "columns": list(records[0]), "next": []}
        inputs = [c for c in columns if c != chosen]
        result = relate(records, chosen, inputs)
        return {"schema": SCHEMA, "origin": origin, "detected": "table",
                "rows": len(records), "columns": list(records[0]),
                "target": chosen, "inputs": inputs,
                "status": result["status"], "law": result.get("law"),
                "result": result,
                "next": _next_for_relation(result, records, chosen, inputs)}

    sequence = _try_sequence(text)
    if sequence is not None:
        from primus.engine import collapse
        invariant = collapse(sequence)
        verified = bool(getattr(invariant, "verified", False))
        record = invariant.to_dict()
        record["verified"] = verified
        return {"schema": SCHEMA, "origin": origin, "detected": "sequence",
                "terms": len(sequence),
                "status": "VERIFIED" if verified else "REFUSED",
                "law": getattr(invariant, "model_class", None),
                "result": record,
                "next": _next_for_sequence(verified, sequence)}

    from primus.certify import certify
    certificate = certify(text)
    counts = certificate["counts"]
    status = ("REFUTED" if counts["refuted"] else
              "VERIFIED" if counts["verified"] else "REFUSED")
    return {"schema": SCHEMA, "origin": origin, "detected": "prose",
            "status": status, "coverage": certificate.get("coverage"),
            "result": certificate,
            "next": _next_for_prose(certificate)}


# --------------------------------------------------------------- next steps

def _next_for_sequence(verified: bool, sequence: List[int]) -> List[Dict[str, Any]]:
    surface = " ".join(str(x) for x in sequence)
    if verified:
        return [
            {"operation": "falsifiers",
             "why": "the exact next value the law predicts — any other "
                    "observation overturns it",
             "arguments": {"surface": surface}},
            {"operation": "explore",
             "why": "what other rules would have fitted these terms",
             "arguments": {"surface": surface}},
            {"operation": "trace",
             "why": "why this rule and not another",
             "arguments": {"surface": surface}},
        ]
    return [
        {"operation": "falsifiers",
         "why": "no rule was recovered; this says what further evidence would "
                "let one be recovered or ruled out",
         "arguments": {"surface": surface}},
        {"operation": "explore",
         "why": "the rules that were tried and why each failed",
         "arguments": {"surface": surface}},
    ]


def _next_for_relation(result: Dict[str, Any], rows: List[Dict[str, Any]],
                       target: str, inputs: List[str]) -> List[Dict[str, Any]]:
    base = {"rows": rows, "target": target, "inputs": inputs}
    if result["status"] == "VERIFIED":
        return [
            {"operation": "solve_for",
             "why": "run the proven law backwards to recover a missing value",
             "arguments": dict(base, unknown=inputs[0], known={}, target_value=0)},
            {"operation": "falsifiers",
             "why": "what observation would overturn this law",
             "arguments": {"text": result.get("law") or ""}},
        ]
    if result["status"] == "PARTIAL":
        return [
            {"operation": "inspect_rows",
             "why": "the rows inconsistent with the law governing the rest",
             "arguments": {"rows": result.get("anomalous_rows", [])}},
            {"operation": "solve_for",
             "why": "not offered — a law that is not VERIFIED must not be "
                    "inverted, because that would turn an unproven rule into a "
                    "confident number",
             "arguments": None},
        ]
    return [
        {"operation": "relate",
         "why": "try a different target column; the law may run the other way",
         "arguments": dict(base, target=inputs[0] if inputs else target)},
    ]


def _next_for_prose(certificate: Dict[str, Any]) -> List[Dict[str, Any]]:
    refused_subjects = [c.get("subject") for c in certificate.get("claims", [])
                        if c.get("status") == "REFUSED" and c.get("subject")]
    steps: List[Dict[str, Any]] = []
    if refused_subjects:
        steps.append({
            "operation": "certify",
            "why": "supply ground truth for %s and these claims become "
                   "checkable" % ", ".join(sorted(set(refused_subjects))[:4]),
            "arguments": {"facts": {s: {"value": None, "unit": None}
                                    for s in sorted(set(refused_subjects))[:4]}},
        })
    steps.append({"operation": "attest",
                  "why": "which supplied source produced each span of this text",
                  "arguments": {"input_paths": []}})
    steps.append({"operation": "propose_experiment",
                  "why": "the cheapest next thing to go check",
                  "arguments": {}})
    return steps


def _selftest() -> int:
    failures, ran = [], []

    def gate(name, condition):
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    r = ingest("1 1 2 3 5 8 13 21 34")
    gate("a bare sequence is detected and certified",
         r["detected"] == "sequence" and r["status"] == "VERIFIED")
    gate("the sequence result offers falsifiers as a next step",
         any(n["operation"] == "falsifiers" for n in r["next"]))

    prose = ("The committee met on 14 March. Three of the 27 members voted "
             "against, and the motion carried by a margin of 9 votes.")
    r = ingest(prose)
    gate("prose with incidental numbers is NOT treated as a series",
         r["detected"] == "prose")

    csv_text = ("units,ship,total\n3,10,85\n4,11,111\n5,12,137\n6,10,160\n"
                "7,11,186\n8,12,212\n9,10,235\n10,11,261\n")
    r = ingest(csv_text)
    gate("a CSV table is detected", r["detected"] == "table")
    gate("the relation across its columns is recovered",
         r["status"] == "VERIFIED" and "total" in (r.get("law") or ""))
    gate("a verified relation offers to be solved backwards",
         any(n["operation"] == "solve_for" and n["arguments"] for n in r["next"]))

    broken = csv_text + "11,12,999\n12,10,310\n"
    r = ingest(broken)
    gate("a broken row makes it PARTIAL rather than VERIFIED",
         r["status"] == "PARTIAL")
    gate("PARTIAL explicitly refuses to offer inversion",
         any(n["operation"] == "solve_for" and n["arguments"] is None
             for n in r["next"]))

    r = ingest('[{"a":1,"b":2},{"a":2,"b":4},{"a":3,"b":6},{"a":4,"b":8},'
               '{"a":5,"b":10},{"a":6,"b":12},{"a":7,"b":14}]')
    gate("JSON records are detected as a table", r["detected"] == "table")

    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
        fh.write(csv_text)
        path = fh.name
    try:
        r = ingest(path)
        gate("a file path is read and routed the same way",
             r["detected"] == "table" and r["origin"]["from"] == "file")
    finally:
        os.unlink(path)

    r = ingest("the quick brown fox jumps over the lazy dog")
    gate("text with no mathematics REFUSES rather than inventing structure",
         r["detected"] == "prose" and r["status"] == "REFUSED")

    print("\n  chiron.ingest self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python3 Chiron/ingest.py <file|text> | selftest")
        return 2
    if argv[0] in ("selftest", "--selftest"):
        return _selftest()
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    record = ingest(" ".join(argv))
    if as_json:
        print(json.dumps(record, indent=2, default=str))
        return 0
    print("[ingest] detected %s · %s" % (record["detected"], record["status"]))
    if record.get("law"):
        print("  law: %s" % record["law"])
    for step in record["next"]:
        mark = "  next:" if step["arguments"] is not None else "  not offered:"
        print("%s %s — %s" % (mark, step["operation"], step["why"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
