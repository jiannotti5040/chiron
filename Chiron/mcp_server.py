#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. Apache-2.0 — use, modification, distribution,
# and commercial use permitted with attribution. See LICENSE.
"""chiron.mcp_server — the whole vault as tools an agent can call on itself.

Primus already serves `certify` and `collapse` over MCP. This serves Chiron:
the language workbench, the provenance layer, the courts, and — the reason
this file exists — `attest`, which is the only tool here aimed at the agent's
OWN output.

THE POINT

An agent that can call `certify` can check its arithmetic. An agent that can
call `attest` can answer a harder question: of the words I just wrote, which
ones came from the documents I was given, and which ones did I supply? That
question is answerable exactly, and it is answered against the sources the
caller names. It is not a detector. It reports no probability that text is
machine-written, because that number does not exist.

FILES ARE FIRST-CLASS

Every tool that takes text also takes `path` (or `paths`). Reading a file and
attributing an answer to it is the ordinary case, not an extension:

    attest(output=<what the agent wrote>, input_paths=[<what it read>])

WHAT COMES BACK

Chiron's contract, unchanged: VERIFIED, REFUTED, or REFUSED per claim or span,
K / U / Omega at decision scale. A REFUSED span is not a gap in the analysis —
it is the analysis, and it is handed back to the human intact.

Design notes, inherited from primus.mcp_server:
  * Dependency-free. Newline-delimited JSON-RPC 2.0 over stdio, implementing
    exactly the MCP surface these tools need.
  * stdout carries protocol messages ONLY; diagnostics go to stderr.
  * A REFUTED claim or a REFUSED span is a RESULT, not a tool error.
    `isError` is reserved for genuine execution failures.

Run directly:            python3 Chiron/mcp_server.py
Register (Claude Code):  claude mcp add chiron -- python3 /abs/path/Chiron/mcp_server.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

PROTOCOL_DEFAULT = "2025-06-18"
# Version two deliberately replaces the former arbitrary ``call`` dispatch
# with a small, reviewed capability surface.  Tool names are API, so the
# version is exposed in initialize rather than silently changing the meaning
# of an existing name.
SCHEMA = "chiron.mcp/2"
TOOL_METADATA_SCHEMA = "chiron.mcp.tool/1"

# Bounds. A tool that reads whatever it is pointed at needs stated limits, and
# truncation must be visible in the result rather than silent.
MAX_FILE_BYTES = 2_000_000
MAX_TEXT_CHARS = 400_000
MAX_INPUTS = 32
# Collapse and trace can have superlinear work for some surfaces.  Unlike
# general prose analysis, truncating a surface would alter the object being
# proven, so these tools reject over-limit inputs rather than silently trim.
MAX_SURFACE_CHARS = 20_000
MAX_SURFACE_TERMS = 1_024

# This is an intentionally static review boundary.  It is repeated in the
# ``analyze`` schema and validated before it reaches full_stack.run().
ALLOWED_ANALYZE_LAYERS = (
    "language", "provenance", "verification", "candor", "recovery",
    "adjudication", "record",
)


# --------------------------------------------------------------------------
# reading text, from an argument or from disk

class ToolError(Exception):
    """A caller error worth reporting as a tool result, not a crash."""


def _read_path(path: str) -> Dict[str, Any]:
    p = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(p):
        raise ToolError("no such file: %s" % path)
    if os.path.isdir(p):
        raise ToolError("%s is a directory; pass a file, or use paths=[...]" % path)
    size = os.path.getsize(p)
    with open(p, "rb") as fh:
        raw = fh.read(MAX_FILE_BYTES)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", "replace")
    return {"name": os.path.basename(p), "path": p, "text": text,
            "bytes": size, "truncated": size > MAX_FILE_BYTES}


def _text_from(args: Dict[str, Any], key: str = "text",
               path_key: str = "path") -> Dict[str, Any]:
    """Resolve text from either an inline argument or a file path."""
    if args.get(key) is not None and args.get(path_key) is not None:
        raise ToolError("pass %s or %s, not both" % (key, path_key))
    if args.get(path_key) is not None:
        rec = _read_path(str(args[path_key]))
        src = {"from": "file", "path": rec["path"], "bytes": rec["bytes"],
               "truncated": rec["truncated"]}
        return {"text": rec["text"][:MAX_TEXT_CHARS], "source": src}
    if args.get(key) is None:
        raise ToolError("missing argument: %s (or %s)" % (key, path_key))
    text = str(args[key])
    return {"text": text[:MAX_TEXT_CHARS],
            "source": {"from": "argument", "chars": len(text),
                       "truncated": len(text) > MAX_TEXT_CHARS}}


def _candidate_inputs(args: Dict[str, Any]) -> Dict[str, str]:
    """Build attest's candidate map from inline text and/or file paths."""
    inputs: Dict[str, str] = {}
    inline = args.get("inputs") or {}
    if not isinstance(inline, dict):
        raise ToolError("inputs must be an object of name -> text")
    for name, text in inline.items():
        inputs[str(name)] = str(text)[:MAX_TEXT_CHARS]
    for path in (args.get("input_paths") or []):
        rec = _read_path(str(path))
        name = rec["name"]
        n = 2
        while name in inputs:              # two files may share a basename
            name = "%s#%d" % (rec["name"], n)
            n += 1
        inputs[name] = rec["text"][:MAX_TEXT_CHARS]
    if len(inputs) > MAX_INPUTS:
        raise ToolError("too many candidate inputs: %d (max %d)"
                        % (len(inputs), MAX_INPUTS))
    return inputs


# --------------------------------------------------------------------------
# reviewed tool declarations

# MCP's standard annotations make the operational posture visible to clients.
# ``_meta.chiron`` is the stable, machine-readable policy record for clients
# that need the fuller authority/provenance statement. Keep every callable in
# this file declared here and in _IMPL below; do not reintroduce generic
# module/function dispatch.


def _tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    *,
    contract: str,
    authority: str,
    side_effects: str,
    provenance: Dict[str, str],
) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": input_schema,
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "_meta": {
            "chiron": {
                "schema": TOOL_METADATA_SCHEMA,
                "contract": contract,
                "authority": authority,
                "side_effects": side_effects,
                "provenance": provenance,
            },
        },
    }


_TEXT_OR_PATH = {
    "text": {"type": "string", "description": "The text to analyse."},
    "path": {"type": "string",
             "description": "Path to a local file to read instead of `text`. "
                            "Absolute, or ~-relative."},
}

_SURFACE_OR_PATH = {
    "type": "object",
    "properties": {
        "surface": {
            "description": "An integer sequence (JSON integer array or whitespace/"
                           "comma-separated string), or an arbitrary string surface.",
            "oneOf": [
                {"type": "string", "maxLength": MAX_SURFACE_CHARS},
                {"type": "array", "maxItems": MAX_SURFACE_TERMS,
                 "items": {"type": "integer"}},
            ],
        },
        "path": _TEXT_OR_PATH["path"],
    },
    # Exactly one alternate is accepted. The implementation repeats this check
    # so malformed clients receive a clear tool error even without schema validation.
    "oneOf": [{"required": ["surface"]}, {"required": ["path"]}],
}

TOOLS = [
    _tool(
        "attest",
        (
            "Attribute generated text to the inputs that produced it, span by "
            "span. THIS IS THE TOOL TO USE ON YOUR OWN OUTPUT: pass what you "
            "wrote as `output` and the documents you read as `input_paths` "
            "(and/or `inputs`), and each span comes back VERIFIED, REFUTED, or "
            "REFUSED, with the closest input named and the words that trace to "
            "nothing listed as novel. Attribution is relative to the candidate "
            "inputs you supply; with none, every span is REFUSED and that is "
            "the honest answer. This is NOT an AI detector and reports no "
            "probability that text is machine-written — that measurement does "
            "not exist. Contract: chiron.attestation/1."
        ),
        {
            "type": "object",
            "properties": {
                "output": {"type": "string",
                           "description": "The generated text to attribute."},
                "output_path": {"type": "string",
                                "description": "Read `output` from this file instead."},
                "inputs": {"type": "object",
                           "description": "Candidate sources as name -> text.",
                           "additionalProperties": {"type": "string"}},
                "input_paths": {"type": "array", "items": {"type": "string"},
                                "description": "Candidate source files. Each is "
                                               "named by its basename."},
            },
        },
        contract="chiron.attestation/1",
        authority=("inline output and candidate text, plus only caller-named "
                   "local files bounded by MAX_FILE_BYTES"),
        side_effects="none; reads caller-authorized local files only",
        provenance={"implementation": "Chiron/attest.py:attest",
                    "source_of_truth": "Chiron/attest.py"},
    ),
    _tool(
        "analyze",
        (
            "Run every applicable Chiron stage over one text or file — "
            "structure, register, readability, outlier sentences, provenance, "
            "extractable claims, exact certification, candour, and (when the "
            "text carries at least four integers) the recovery and "
            "adjudication layers. Returns one record with a per-stage status: "
            "a stage that cannot apply says SKIPPED and why, a stage that "
            "raised says ERROR. Neither is reported as a pass. Contract: "
            "chiron.full_stack/1."
        ),
        {
            "type": "object",
            "properties": dict(_TEXT_OR_PATH, **{
                "layers": {"type": "array", "items": {"type": "string",
                                                            "enum": list(ALLOWED_ANALYZE_LAYERS)},
                           "description": "Restrict to reviewed layers: language, "
                                          "provenance, verification, candor, "
                                          "recovery, adjudication, record."},
            }),
        },
        contract="chiron.full_stack/1",
        authority=("inline text or one caller-named local file bounded by "
                   "MAX_FILE_BYTES; only the reviewed full_stack stage list"),
        side_effects="none; in-process deterministic analysis only",
        provenance={"implementation": "Chiron/full_stack.py:run",
                    "source_of_truth": "Chiron/full_stack.py"},
    ),
    _tool(
        "certify",
        (
            "Supply `facts` (an object of subject -> value, or a list of "
            "{subject, value, unit}) to make claims about the world checkable: "
            "without them, a statement like 'readiness fell to 74%' is REFUSED "
            "because the fact lives in a table this engine has never seen, and "
            "on real operational prose that is every claim. With them it is "
            "checked exactly against exactly one named fact. "
            "Certify the exactly checkable claims in text or a file. Each claim "
            "returns VERIFIED, REFUTED, or REFUSED; the free-text remainder is "
            "reported as unverifiable and is never blessed. Gate on "
            "counts.refuted == 0 and read `coverage` — a pass means only that "
            "nothing checkable was refuted, not that the text is true. "
            "Contract: primus.certificate/2."
        ),
        {"type": "object", "properties": dict(
            _TEXT_OR_PATH,
            facts={"description": "Ground truth: an object of subject -> value, "
                                  "or a list of {subject, value, unit} objects."},
            facts_path={"type": "string",
                        "description": "Read `facts` from a local JSON file instead."})},
        contract="primus.certificate/2",
        authority=("inline text or one caller-named local file bounded by "
                   "MAX_FILE_BYTES"),
        side_effects="none; exact local verification only",
        provenance={"implementation": "Primus/src/primus/certify.py:certify",
                    "source_of_truth": "Primus/src/primus/certify.py"},
    ),
    _tool(
        "collapse",
        (
            "Recover the best compression model for a numeric integer sequence "
            "or a string surface. VERIFIED is returned only when Primus's "
            "canonical held-out exact check succeeds; otherwise read the result "
            "as a candidate or honest refusal. This tool delegates directly to "
            "the canonical Primus collapse engine."
        ),
        _SURFACE_OR_PATH,
        contract="chiron.mcp.collapse/1",
        authority=("one caller-supplied surface, or one caller-named local file; "
                   "integer arrays are preserved exactly and inputs are bounded"),
        side_effects="none; exact local analysis only",
        provenance={"implementation": "Primus/src/primus/engine.py:collapse",
                    "source_of_truth": "Primus/src/primus/engine.py"},
    ),
    _tool(
        "trace",
        (
            "Return the canonical Chiron diagnostic trace for one numeric "
            "surface or string: candidate models/decodings, winner, and its "
            "held-out re-test. This explains a result; it does not create a new "
            "verification stamp."
        ),
        _SURFACE_OR_PATH,
        contract="chiron.trace/1",
        authority=("one caller-supplied surface, or one caller-named local file; "
                   "integer arrays are preserved exactly and inputs are bounded"),
        side_effects="none; deterministic local diagnostic only",
        provenance={"implementation": "Chiron/trace.py:_trace_sequence,_trace_string",
                    "source_of_truth": "Chiron/trace.py"},
    ),
    _tool(
        "solve",
        (
            "Run a goal-directed campaign over a numeric or string surface: "
            "observe, recover a candidate rule, put it to the exact gate, "
            "record what survived, and escalate anything irreversible instead "
            "of doing it. Returns the full step trace and the campaign's "
            "disposition. A step that cannot be verified HALTS the campaign "
            "rather than advancing on an unproven premise, and ESCALATED means "
            "the plan reached a step that leaves the reversible sandbox and "
            "declined to take it — both are successful outcomes, not errors. "
            "Epistemic status: prototype. Contract: chiron.solve/1."
        ),
        {
            "type": "object",
            "properties": {
                "surface": {"description": "A sequence of integers, or a string containing them."},
                "path": {"type": "string", "description": "Read the surface from a local file instead."},
                "intent": {"type": "string", "description": "What the campaign is for."},
                "budget": {"type": "integer", "minimum": 1, "maximum": 64,
                           "description": "Maximum plan steps. Exhaustion is reported, never exceeded."},
            },
        },
        contract="chiron.solve/1",
        authority="composes reviewed engines only; performs no irreversible step",
        side_effects="none; campaign state is local and discarded with the call",
        provenance={"implementation": "Chiron/mcp_server.py:_tool_solve -> planner.run_campaign",
                    "epistemic_status": "prototype"},
    ),
    _tool(
        "lineage",
        (
            "Return the evidence graph behind a text rather than its verdicts: "
            "which source each claim derives from, what supports or contradicts "
            "it, and which claims stand on nothing. Composed over the same "
            "certificate `certify` produces. A REFUSED claim appears under "
            "`unsupported` and carries no supporting edge — refusal means no "
            "exact checker applied, which is not weak support. Contract: "
            "chiron.evidence_graph/1."
        ),
        {"type": "object", "properties": dict(_TEXT_OR_PATH)},
        contract="chiron.evidence_graph/1",
        authority="joins records other engines produced; reaches no verdict of its own",
        side_effects="none; the graph is built in memory and returned",
        provenance={"implementation": "Chiron/mcp_server.py:_tool_lineage -> evidence_graph.from_certificate"},
    ),
    _tool(
        "explore",
        (
            "Recover a rule and then attack it: return the rival hypotheses "
            "searched, whether any survived at MDL parity, and whether an "
            "injunction blocks finality. Surviving cross-examination is "
            "reported as surviving, never as uniqueness — the searched space "
            "is the one the adversarial court admits, not all rules. "
            "Contract: chiron.explore/1."
        ),
        dict(_SURFACE_OR_PATH),
        contract="chiron.explore/1",
        authority="composes the adversarial court; reaches no verdict of its own",
        side_effects="none",
        provenance={"implementation": "Chiron/mcp_server.py:_tool_explore -> compare_explore.explore"},
    ),
    _tool(
        "compare",
        (
            "Put two surfaces side by side on stated axes — verified, model "
            "class, parameter count, compression — and report which axes "
            "differ. Deliberately produces no composite score: a single number "
            "would hide which axis decided. `better_supported` is set only "
            "when exactly one side verified. Contract: chiron.compare/1."
        ),
        {
            "type": "object",
            "properties": {
                "left": {"description": "First surface: integers, or a string containing them."},
                "right": {"description": "Second surface."},
                "left_path": {"type": "string",
                              "description": "Read the first surface from a local file instead of `left`."},
                "right_path": {"type": "string",
                               "description": "Read the second surface from a local file instead of `right`."},
            },
        },
        contract="chiron.compare/1",
        authority="reports stated axes only; produces no ranking score",
        side_effects="none",
        provenance={"implementation": "Chiron/mcp_server.py:_tool_compare -> compare_explore.compare"},
    ),
    _tool(
        "falsifiers",
        (
            "What would overturn this. For a verified rule, the exact next "
            "value it predicts — any other observation refutes it. For a "
            "REFUSED claim, the specific evidence nobody supplied, which "
            "turns a dead end into a task. A REFUTED claim gets neither, "
            "because inventing a falsifier for it would be theatre. "
            "Contract: chiron.falsifiers/1."
        ),
        {"type": "object", "properties": dict(
            _TEXT_OR_PATH, surface={"description": "A sequence, if checking a rule rather than text."},
            facts={"description": "Ground truth, as for certify."})},
        contract="chiron.falsifiers/1",
        authority="derives refuters from verdicts other engines reached; reaches none itself",
        side_effects="none",
        provenance={"implementation": "Chiron/mcp_server.py:_tool_falsifiers -> falsify"},
    ),
    _tool(
        "propose_experiment",
        (
            "The cheapest single thing to go do next, ranked by an ordinal "
            "cost class (lookup < single_observation < series) and never by "
            "an invented likelihood of being informative. Returns nothing "
            "when nothing is actionable, rather than proposing busywork. "
            "Contract: chiron.falsifiers/1."
        ),
        {"type": "object", "properties": dict(
            _TEXT_OR_PATH, surface={"description": "A sequence, if planning around a rule."},
            facts={"description": "Ground truth, as for certify."})},
        contract="chiron.falsifiers/1",
        authority="ranks by stated cost class only; proposes no action it cannot state exactly",
        side_effects="none",
        provenance={"implementation": "Chiron/mcp_server.py:_tool_propose_experiment -> falsify"},
    ),
    _tool(
        "relate",
        (
            "Recover an exact law across COLUMNS of a table — y = f(x1..xk) — "
            "solved in exact rational arithmetic and confirmed on rows the "
            "solver never saw. This is the engine applied to real data rather "
            "than to one sequence. VERIFIED means every held-out row matched "
            "exactly; there is no tolerance and no residual. PARTIAL names the "
            "exact rows that break an otherwise-holding law, which is anomaly "
            "localisation and is explicitly NOT a weaker verification. "
            "Contract: primus.relation/1."
        ),
        {"type": "object",
         "properties": {"rows": {"type": "array", "items": {"type": "object"}, "description": "Rows as objects with named columns."},
                        "target": {"type": "string"},
                        "inputs": {"type": "array", "items": {"type": "string"}}},
         "required": ["rows", "target"]},
        contract="primus.relation/1",
        authority="exact rational solve with held-out proof; never approximates",
        side_effects="none",
        provenance={"implementation": "primus/relate.py:relate"},
    ),
    _tool(
        "solve_for",
        (
            "Run a recovered law backwards: given a target value and all but "
            "one input, solve exactly for the missing one. Offered ONLY for a "
            "law that VERIFIED — inverting an unproven rule would turn it into "
            "a confident number. Irrational roots are REFUSED rather than "
            "rounded. Contract: primus.inverse/1."
        ),
        {"type": "object",
         "properties": {"rows": {"type": "array", "items": {"type": "object"}, "description": "Rows as objects with named columns."},
                        "target": {"type": "string"},
                        "inputs": {"type": "array", "items": {"type": "string"}},
                        "unknown": {"type": "string"},
                        "known": {"type": "object"},
                        "target_value": {"description": "Desired value of the target."}},
         "required": ["rows", "target", "unknown", "target_value"]},
        contract="primus.inverse/1",
        authority="inverts only VERIFIED laws; refuses irrational roots",
        side_effects="none",
        provenance={"implementation": "primus/invert.py:solve_for"},
    ),
    _tool(
        "discover_map",
        (
            "Recover the exact per-column map carrying one table to another — "
            "which column became which, under what law. Each mapping carries "
            "its own held-out proof. A column with no exact law is reported as "
            "unmapped rather than paired with its closest fit. "
            "Contract: primus.transformation/1."
        ),
        {"type": "object",
         "properties": {"source": {"type": "array", "items": {"type": "object"}, "description": "Rows as objects with named columns."},
                        "destination": {"type": "array", "items": {"type": "object"}, "description": "Rows as objects with named columns."}},
         "required": ["source", "destination"]},
        contract="primus.transformation/1",
        authority="per-column exact laws only; never pairs by best guess",
        side_effects="none",
        provenance={"implementation": "primus/invert.py:discover_map"},
    ),
    _tool(
        "catalog",
        (
            "List the reviewed static Chiron MCP capability allowlist and each "
            "tool's input schema, authority, side-effect posture, and canonical "
            "implementation. It does not enumerate or invoke arbitrary vault "
            "modules."
        ),
        {
            "type": "object",
            "properties": {
                "filter": {"type": "string",
                           "description": "Only reviewed MCP tools matching this substring."},
            },
        },
        contract="chiron.catalog/2",
        authority="static capability declarations in this MCP server",
        side_effects="none",
        provenance={"implementation": "Chiron/mcp_server.py:_catalog",
                    "source_of_truth": "Chiron/mcp_server.py:TOOLS"},
    ),
]


# --------------------------------------------------------------------------
# implementations

def _wrap(payload: Dict[str, Any]) -> Dict[str, Any]:
    """MCP result: readable text plus the structured record."""
    return {
        "content": [{"type": "text",
                     "text": json.dumps(payload, indent=2, default=str)[:60000]}],
        "structuredContent": payload,
    }


def _tool_attest(args: Dict[str, Any]) -> Dict[str, Any]:
    import attest as attest_mod

    if args.get("output_path") is not None:
        got = _text_from(args, key="__none__", path_key="output_path")
    else:
        if args.get("output") is None:
            raise ToolError("missing argument: output (or output_path)")
        got = {"text": str(args["output"])[:MAX_TEXT_CHARS],
               "source": {"from": "argument"}}
    inputs = _candidate_inputs(args)
    rec = attest_mod.attest(got["text"], inputs=inputs or None)
    rec["source"] = got["source"]
    if not inputs:
        rec["note"] = ("No candidate inputs were supplied, so every span is "
                       "REFUSED. That is the contract, not a failure: "
                       "attribution is always relative to inputs you name.")
    return _wrap(rec)


def _tool_analyze(args: Dict[str, Any]) -> Dict[str, Any]:
    import full_stack

    got = _text_from(args)
    layers = args.get("layers") or None
    if layers is not None and not isinstance(layers, list):
        raise ToolError("layers must be an array of strings")
    if layers is not None:
        unknown = [layer for layer in layers
                   if not isinstance(layer, str) or layer not in ALLOWED_ANALYZE_LAYERS]
        if unknown:
            raise ToolError("layers must be drawn from the reviewed allowlist: %s"
                            % ", ".join(ALLOWED_ANALYZE_LAYERS))
    rec = full_stack.run(got["text"], only_layers=layers)
    rec["source"] = got["source"]
    return _wrap(rec)


def _tool_certify(args: Dict[str, Any]) -> Dict[str, Any]:
    got = _text_from(args)
    facts = args.get("facts")
    if facts is not None and not isinstance(facts, (dict, list)):
        raise ToolError("facts must be an object of subject -> value, or a "
                        "list of {subject, value, unit} objects")
    if args.get("facts_path") is not None:
        if facts is not None:
            raise ToolError("pass facts or facts_path, not both")
        import json as _json
        facts = _json.loads(_read_path(str(args["facts_path"]))["text"])
    # The seed engine's certify is the source of truth for the certificate;
    # Chiron does not carry a second copy of it.
    try:
        from primus.certify import certify
    except ImportError:
        seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
        if seed not in sys.path:
            sys.path.insert(0, seed)
        from primus.certify import certify
    rec = certify(got["text"], facts=facts)
    rec["source"] = got["source"]
    return _wrap(rec)


_INTEGER_SEQUENCE = re.compile(r"[+-]?\d+(?:[\s,]+[+-]?\d+)*")


def _surface_from(args: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a bounded surface without coercing caller integers through float.

    This is deliberately distinct from _text_from(): a surface is the evidence
    for a collapse proof, so truncating or lossy conversion would change its
    meaning.  The only numeric array accepted is JSON integers; callers with a
    non-integer surface can submit it as a string and receive the canonical
    string-surface analysis instead of an accidental exactness claim.
    """
    has_surface = args.get("surface") is not None
    has_path = args.get("path") is not None
    if has_surface == has_path:
        raise ToolError("pass surface or path, exactly one")

    if has_path:
        got = _text_from(args, key="__surface__", path_key="path")
        if got["source"].get("truncated"):
            raise ToolError("surface file exceeds MAX_FILE_BYTES; refusing to truncate evidence")
        raw: Any = got["text"]
        source = got["source"]
    else:
        raw = args["surface"]
        source = {"from": "argument"}

    if isinstance(raw, list):
        if len(raw) > MAX_SURFACE_TERMS:
            raise ToolError("surface has too many terms: %d (max %d)"
                            % (len(raw), MAX_SURFACE_TERMS))
        if any(isinstance(value, bool) or not isinstance(value, int) for value in raw):
            raise ToolError("numeric surface arrays must contain JSON integers only")
        source.update(kind="integer-array", terms=len(raw), truncated=False)
        return {"surface": list(raw), "source": source}

    if not isinstance(raw, str):
        raise ToolError("surface must be a string or an array of JSON integers")
    if len(raw) > MAX_SURFACE_CHARS:
        raise ToolError("string surface exceeds %d characters; refusing to truncate evidence"
                        % MAX_SURFACE_CHARS)
    if _INTEGER_SEQUENCE.fullmatch(raw.strip()):
        parts = re.split(r"[\s,]+", raw.strip())
        if len(parts) > MAX_SURFACE_TERMS:
            raise ToolError("surface has too many terms: %d (max %d)"
                            % (len(parts), MAX_SURFACE_TERMS))
        source.update(kind="integer-sequence", terms=len(parts), truncated=False)
        return {"surface": [int(part) for part in parts], "source": source}
    source.update(kind="string", chars=len(raw), truncated=False)
    return {"surface": raw, "source": source}


def _tool_collapse(args: Dict[str, Any]) -> Dict[str, Any]:
    got = _surface_from(args)
    try:
        from primus.engine import collapse
    except ImportError:
        seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
        if seed not in sys.path:
            sys.path.insert(0, seed)
        from primus.engine import collapse
    inv = collapse(got["surface"])
    rec = inv.to_dict()
    # ``to_dict`` intentionally leaves the convenience property out; preserve
    # the engine's exact held-out verdict rather than reinterpreting it here.
    rec["schema"] = "chiron.mcp.collapse/1"
    rec["verified"] = bool(inv.verified)
    rec["source"] = got["source"]
    return _wrap(rec)


def _tool_trace(args: Dict[str, Any]) -> Dict[str, Any]:
    from trace import _trace_sequence, _trace_string

    got = _surface_from(args)
    surface = got["surface"]
    # The trace module is itself the canonical diagnostic implementation. It
    # does not stamp a result; it reports the engine's own verdict verbatim.
    rec = _trace_sequence(surface) if isinstance(surface, list) else _trace_string(surface)
    rec["schema"] = "chiron.trace/1"
    rec["source"] = got["source"]
    return _wrap(rec)


def _tool_solve(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run a goal-directed campaign and return its full trace.

    This composes rather than computes. `planner.run_campaign` already
    implements the mandate's solving loop — observe, analyze, verify with the
    gate arbitrating, remember, and escalate anything irreversible — and
    `cross_examine` already manufactures reasonable doubt by searching for an
    MDL-parity rival. Writing a second solver beside them would have produced
    exactly the duplicate this repository keeps having to unpick.

    The campaign's disposition is the planner's own, verbatim. Note what
    ESCALATED means here: the plan reached a step that leaves the reversible
    sandbox and refused to take it. That is a successful outcome, not a
    failure, and it is never rewritten into one.
    """
    got = _surface_from(args)
    surface = got["surface"]
    intent = args.get("intent", "recover and prove the rule behind this surface")
    if not isinstance(intent, str):
        raise ToolError("intent must be a string")
    budget = args.get("budget", 8)
    if not isinstance(budget, int) or isinstance(budget, bool) or not 1 <= budget <= 64:
        raise ToolError("budget must be an integer between 1 and 64")

    from planner import Goal, run_campaign

    result = run_campaign(Goal(intent, budget=budget), surface)
    rec = dict(result) if isinstance(result, dict) else {"result": result}
    rec["schema"] = "chiron.solve/1"
    rec["intent"] = intent
    rec["source"] = got["source"]
    rec["epistemic_status"] = "prototype"
    rec["note"] = (
        "Composed from planner.run_campaign. A step that cannot be verified "
        "HALTS the campaign rather than advancing on an unproven premise, and "
        "an irreversible step is ESCALATED rather than performed. Neither is "
        "an error."
    )
    return _wrap(rec)


def _tool_lineage(args: Dict[str, Any]) -> Dict[str, Any]:
    """Certify a text, then return the evidence graph rather than the verdicts.

    Same run, different question. `certify` answers "what came out"; `lineage`
    answers "what is it standing on, and what contradicts it". It composes
    `evidence_graph.from_certificate` over the certificate the canonical gate
    already produced and asserts nothing of its own.

    A REFUSED claim appears under `unsupported` with no supporting edge. That
    is the honest placement: refusal means no exact checker applied, which is
    not weak support.
    """
    got = _text_from(args)
    import evidence_graph
    # Same bootstrap _tool_certify uses; the seed engine's certify is the one
    # source of truth for a certificate and Chiron carries no second copy.
    try:
        from primus.certify import certify
    except ImportError:
        seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
        if seed not in sys.path:
            sys.path.insert(0, seed)
        from primus.certify import certify
    certificate = certify(got["text"])
    graph = evidence_graph.from_certificate(
        certificate, source={"source_id": "input", **got["source"]})
    rec = graph.as_dict()
    rec["source"] = got["source"]
    return _wrap(rec)


def _tool_explore(args: Dict[str, Any]) -> Dict[str, Any]:
    """What else would have fit: the rivals searched, and whether one survived.

    Composes `cross_examine`, the adversarial court that already hunts a rival
    generator describing the same evidence within a few bits. Surviving is
    reported as surviving, never as uniqueness — the searched space is the one
    cross_examine admits, not the space of all rules.
    """
    got = _surface_from(args)
    import compare_explore
    rec = compare_explore.explore(got["surface"])
    rec["source"] = got["source"]
    return _wrap(rec)


def _tool_compare(args: Dict[str, Any]) -> Dict[str, Any]:
    """Two surfaces on stated axes, with no composite score.

    A single number would hide which axis decided the answer, so there is
    none. `better_supported` is set only where exactly one side verified;
    two verified surfaces on different model classes are a difference, not a
    ranking.

    Each side takes a value or a path, like every other tool here. Files are
    first-class in this server, and a comparison tool that could only take
    inline values would be the one place a caller had to read a file itself.
    """
    sides = {}
    for key in ("left", "right"):
        path_key = key + "_path"
        if args.get(key) is not None and args.get(path_key) is not None:
            raise ToolError("pass %s or %s, not both" % (key, path_key))
        if args.get(path_key) is not None:
            sides[key] = _read_path(str(args[path_key]))["text"]
        elif args.get(key) is not None:
            sides[key] = args[key]
        else:
            raise ToolError("compare needs %s or %s" % (key, path_key))
    import compare_explore
    rec = compare_explore.compare(sides["left"], sides["right"])
    rec["source"] = {
        "left": "file" if args.get("left_path") else "argument",
        "right": "file" if args.get("right_path") else "argument",
    }
    return _wrap(rec)


def _tool_falsifiers(args: Dict[str, Any]) -> Dict[str, Any]:
    """What observation would overturn this, and what is missing to check it.

    Answers the question the rest of the vault does not: not "is it
    supported?" but "what would make it wrong, and what is the cheapest thing
    to go get?" A REFUSED claim comes back naming the specific fact nobody
    supplied, which turns a dead end into a task.
    """
    import falsify
    if args.get("text") is not None or args.get("path") is not None:
        got = _text_from(args)
        try:
            from primus.certify import certify
        except ImportError:
            seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
            if seed not in sys.path:
                sys.path.insert(0, seed)
            from primus.certify import certify
        cert = certify(got["text"], facts=args.get("facts"))
        rec = falsify.falsifiers_for_certificate(cert)
        rec["source"] = got["source"]
        return _wrap(rec)
    got = _surface_from(args)
    rec = falsify.falsifiers_for_surface(got["surface"])
    rec["source"] = got["source"]
    return _wrap(rec)


def _tool_propose_experiment(args: Dict[str, Any]) -> Dict[str, Any]:
    """The cheapest next observation, ranked by cost class only."""
    import falsify
    report = _tool_falsifiers(args)
    inner = json.loads(report["content"][0]["text"])
    rec = falsify.propose_experiment(inner)
    rec["from"] = inner.get("schema")
    return _wrap(rec)


def _relate_args(args: Dict[str, Any]):
    rows = args.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ToolError("rows must be a non-empty list of objects")
    target = args.get("target")
    if not isinstance(target, str):
        raise ToolError("target must be a column name")
    inputs = args.get("inputs")
    if inputs is not None and not isinstance(inputs, list):
        raise ToolError("inputs must be a list of column names")
    return rows, target, inputs


def _tool_relate(args: Dict[str, Any]) -> Dict[str, Any]:
    """Recover an exact law across columns, proven on held-out rows.

    The disposition is the result. VERIFIED means the law held on every row
    the solver never saw, in exact rational arithmetic. PARTIAL names the rows
    that break it — an anomaly finding, explicitly not a weaker verification.
    """
    from primus.relate import relate, RelationError as _RE
    rows, target, inputs = _relate_args(args)
    try:
        return _wrap(relate(rows, target, inputs))
    except _RE as exc:
        raise ToolError(str(exc))


def _tool_solve_for(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run a proven law backwards for one unknown input."""
    from primus.relate import relate, RelationError as _RE
    from primus.invert import solve_for
    rows, target, inputs = _relate_args(args)
    unknown = args.get("unknown")
    if not isinstance(unknown, str):
        raise ToolError("unknown must be an input column name")
    if "target_value" not in args:
        raise ToolError("target_value is required")
    try:
        law = relate(rows, target, inputs)
        rec = solve_for(law, args.get("known") or {}, unknown,
                        args["target_value"])
    except _RE as exc:
        raise ToolError(str(exc))
    rec["law_status"] = law.get("status")
    return _wrap(rec)


def _tool_discover_map(args: Dict[str, Any]) -> Dict[str, Any]:
    """Recover the exact per-column map carrying one table to another."""
    from primus.relate import RelationError as _RE
    from primus.invert import discover_map
    source, destination = args.get("source"), args.get("destination")
    if not isinstance(source, list) or not isinstance(destination, list):
        raise ToolError("source and destination must be lists of objects")
    try:
        return _wrap(discover_map(source, destination))
    except _RE as exc:
        raise ToolError(str(exc))


def _catalog(filter_: Optional[str] = None) -> Dict[str, Any]:
    """Return the static tool allowlist without importing arbitrary modules."""
    if filter_ is not None and not isinstance(filter_, str):
        raise ToolError("filter must be a string")
    query = (filter_ or "").lower()
    out: List[Dict[str, Any]] = []
    for tool in TOOLS:
        policy = tool["_meta"]["chiron"]
        haystack = " ".join((tool["name"], tool["description"],
                              policy["contract"], policy["authority"],
                              policy["side_effects"],
                              policy["provenance"]["implementation"]))
        if query and query not in haystack.lower():
            continue
        out.append({
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": tool["inputSchema"],
            "annotations": tool["annotations"],
            "metadata": policy,
        })
    return {
        "schema": "chiron.catalog/2",
        "reviewed_static_allowlist": True,
        "tools": out,
        "tool_count": len(out),
        "scope": ("Only reviewed MCP tools are listed. Arbitrary Chiron "
                  "module/function dispatch is intentionally unavailable."),
    }


def _tool_catalog(args: Dict[str, Any]) -> Dict[str, Any]:
    return _wrap(_catalog(args.get("filter")))


_IMPL = {
    "attest": _tool_attest,
    "analyze": _tool_analyze,
    "certify": _tool_certify,
    "collapse": _tool_collapse,
    "trace": _tool_trace,
    "catalog": _tool_catalog,
    "solve": _tool_solve,
    "lineage": _tool_lineage,
    "explore": _tool_explore,
    "compare": _tool_compare,
    "falsifiers": _tool_falsifiers,
    "propose_experiment": _tool_propose_experiment,
    "relate": _tool_relate,
    "solve_for": _tool_solve_for,
    "discover_map": _tool_discover_map,
}


# --------------------------------------------------------------------------
# transport

def _send(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, separators=(",", ":"), default=str) + "\n")
    sys.stdout.flush()


def _reply(msg_id: Any, result: Dict[str, Any]) -> None:
    _send({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _reply_error(msg_id: Any, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": msg_id,
           "error": {"code": code, "message": message}})


INSTRUCTIONS = (
    "Chiron never certifies what it cannot exactly prove, and refusal is a "
    "result, not a failure. Use `attest` on your OWN output to see which spans "
    "trace to the sources you were given and which words you supplied — pass "
    "the files you read as input_paths. Use `analyze` for a full reading of a "
    "text or file, `certify` to gate checkable claims (refuted == 0 passes; "
    "the remainder stays unverified), `collapse` for the canonical Primus "
    "invariant result, and `trace` for a diagnostic explanation. `catalog` "
    "lists the reviewed static allowlist and its authority metadata; arbitrary "
    "module dispatch is intentionally unavailable. Report REFUSED spans to the "
    "user as unattributed rather than dropping them, and never describe any "
    "output here as a probability that text is machine-written."
)


def _handle(msg: Dict[str, Any]) -> None:
    method = msg.get("method")
    msg_id = msg.get("id")
    is_request = "id" in msg

    if method == "initialize":
        client_ver = (msg.get("params") or {}).get("protocolVersion")
        _reply(msg_id, {
            "protocolVersion": client_ver or PROTOCOL_DEFAULT,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "chiron",
                           "title": "Chiron — provenance, analysis, and refusal",
                           "version": SCHEMA},
            "instructions": INSTRUCTIONS,
        })
    elif method in ("notifications/initialized", "notifications/cancelled",
                    "notifications/roots/list_changed"):
        return
    elif method == "ping":
        _reply(msg_id, {})
    elif method == "tools/list":
        _reply(msg_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        impl = _IMPL.get(name)
        if impl is None:
            _reply_error(msg_id, -32602, "unknown tool: %r" % (name,))
            return
        try:
            _reply(msg_id, impl(params.get("arguments") or {}))
        except ToolError as exc:
            # A caller mistake is a tool-level error result, not a crash.
            _reply(msg_id, {"content": [{"type": "text", "text": str(exc)}],
                            "isError": True})
        except Exception as exc:                           # noqa: BLE001
            _reply(msg_id, {"content": [{"type": "text",
                                         "text": "%s: %s" % (type(exc).__name__, exc)}],
                            "isError": True})
    elif is_request:
        _reply_error(msg_id, -32601, "method not found: %r" % (method,))


def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "selftest":
        return _selftest()
    print("chiron-mcp: serving attest + analyze + certify + collapse + trace + catalog "
          "over stdio (newline-delimited JSON-RPC)", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _send({"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32700, "message": "parse error"}})
            continue
        try:
            _handle(msg)
        except Exception as exc:                           # noqa: BLE001
            if "id" in msg:
                _reply_error(msg.get("id"), -32603,
                             "internal error: %s" % type(exc).__name__)
            print("chiron-mcp: internal error: %r" % (exc,), file=sys.stderr)
    return 0


def _selftest() -> int:
    """In-process gates over the tool implementations."""
    import tempfile

    passed = failed = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
            print("  [PASS] %s" % name)
        else:
            failed += 1
            print("  [FAIL] %s %s" % (name, detail))

    def body(res):
        return res["structuredContent"]

    # attest with no candidates must refuse every span
    r = body(_tool_attest({"output": "A sentence with no candidates at all."}))
    check("attest: no candidates -> every span REFUSED",
          r["spans"] and all(s["verdict"] == "REFUSED" for s in r["spans"]))
    check("attest: refusal is explained, not silent", "note" in r)

    # attest against a real file
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "source_note.txt")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("The quarterly report lists 4200 units shipped and "
                     "1400 returned during the period.")
        r = body(_tool_attest({
            "output": "The report lists 4200 units shipped and 1400 returned.",
            "input_paths": [src]}))
        check("attest: file candidate is named by basename",
              "source_note.txt" in (r.get("candidate_inputs") or []),
              str(r.get("candidate_inputs")))
        check("attest: verdicts stay in the vocabulary",
              all(s["verdict"] in ("VERIFIED", "REFUTED", "REFUSED")
                  for s in r["spans"]))

        # analyze from a path
        r = body(_tool_analyze({"path": src}))
        check("analyze: reads a file and reports its source",
              r["schema"] == "chiron.full_stack/1"
              and r["source"]["from"] == "file")
        check("analyze: no stage is silently dropped",
              r["stages_run"] == len(r["results"]))

        # certify from a path
        with open(os.path.join(tmp, "claims.txt"), "w", encoding="utf-8") as fh:
            fh.write("The sum of 2 and 2 is 4. The product of 3 and 4 is 11.")
        r = body(_tool_certify({"path": os.path.join(tmp, "claims.txt")}))
        check("certify: verifies the true claim",
              r["counts"]["verified"] >= 1, json.dumps(r["counts"]))
        check("certify: refutes the false one",
              r["counts"]["refuted"] >= 1, json.dumps(r["counts"]))

    # text and path are mutually exclusive
    try:
        _tool_analyze({"text": "x", "path": "/etc/hosts"})
        check("analyze: text+path rejected", False)
    except ToolError:
        check("analyze: text+path rejected", True)

    # a missing file is a caller error, not a crash
    try:
        _tool_analyze({"path": "/nonexistent/nowhere.txt"})
        check("analyze: missing file rejected", False)
    except ToolError:
        check("analyze: missing file rejected", True)

    # Catalog is now a reviewed static capability record, never a dynamic
    # importer/dispatcher over the rest of the vault.
    cat = body(_tool_catalog({}))
    check("catalog: returns the reviewed static allowlist",
          cat["schema"] == "chiron.catalog/2"
          and cat["reviewed_static_allowlist"] is True
          and cat["tool_count"] == len(TOOLS))
    check("catalog: filter narrows", len(body(_tool_catalog(
        {"filter": "attest"}))["tools"]) < cat["tool_count"])

    # Narrow typed tools delegate to their canonical cores.
    r = body(_tool_collapse({"surface": [1, 1, 2, 3, 5, 8, 13, 21]}))
    check("collapse: canonical exact held-out result is preserved",
          r.get("verified") is True and "recurrence" in str(r.get("model_class")))
    r = body(_tool_trace({"surface": "1 1 2 3 5 8 13 21"}))
    check("trace: canonical diagnostic keeps its non-stamping contract",
          r.get("schema") == "chiron.trace/1"
          and r.get("engine_verdict") in ("VERIFIED", "ABSTAINED"))

    try:
        _tool_collapse({"surface": [1, 1.5, 2]})
        check("collapse: non-integer numeric arrays rejected", False)
    except ToolError:
        check("collapse: non-integer numeric arrays rejected", True)
    try:
        _tool_analyze({"text": "x", "layers": ["not-reviewed"]})
        check("analyze: unreviewed layer rejected", False)
    except ToolError:
        check("analyze: unreviewed layer rejected", True)

    # protocol surface
    check("tools: all declared tools have an implementation",
          {t["name"] for t in TOOLS} == set(_IMPL))
    check("tools: no generic arbitrary module dispatcher remains",
          "call" not in _IMPL and "call" not in {t["name"] for t in TOOLS})
    check("tools: every declaration carries reviewed authority metadata",
          all(
              t.get("annotations") == {
                  "readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": False,
              }
              and set(t.get("_meta", {}).get("chiron", {}))
              >= {"schema", "contract", "authority", "side_effects", "provenance"}
              and t["_meta"]["chiron"]["schema"] == TOOL_METADATA_SCHEMA
              for t in TOOLS))
    check("tools: every tool documents a file path",
          all("path" in json.dumps(t["inputSchema"]) for t in TOOLS
              if t["name"] != "catalog"))

    print("\n  chiron-mcp gates: %d/%d passed." % (passed, passed + failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
