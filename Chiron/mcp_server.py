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

import importlib
import inspect
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

PROTOCOL_DEFAULT = "2025-06-18"
SCHEMA = "chiron.mcp/1"

# Bounds. A tool that reads whatever it is pointed at needs stated limits, and
# truncation must be visible in the result rather than silent.
MAX_FILE_BYTES = 2_000_000
MAX_TEXT_CHARS = 400_000
MAX_INPUTS = 32


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
# tool declarations

_TEXT_OR_PATH = {
    "text": {"type": "string", "description": "The text to analyse."},
    "path": {"type": "string",
             "description": "Path to a local file to read instead of `text`. "
                            "Absolute, or ~-relative."},
}

TOOLS = [
    {
        "name": "attest",
        "description": (
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
        "inputSchema": {
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
    },
    {
        "name": "analyze",
        "description": (
            "Run every applicable Chiron stage over one text or file — "
            "structure, register, readability, outlier sentences, provenance, "
            "extractable claims, exact certification, candour, and (when the "
            "text carries at least four integers) the recovery and "
            "adjudication layers. Returns one record with a per-stage status: "
            "a stage that cannot apply says SKIPPED and why, a stage that "
            "raised says ERROR. Neither is reported as a pass. Contract: "
            "chiron.full_stack/1."
        ),
        "inputSchema": {
            "type": "object",
            "properties": dict(_TEXT_OR_PATH, **{
                "layers": {"type": "array", "items": {"type": "string"},
                           "description": "Restrict to these layers: language, "
                                          "provenance, verification, candor, "
                                          "recovery, adjudication, record."},
            }),
        },
    },
    {
        "name": "certify",
        "description": (
            "Certify the exactly checkable claims in text or a file. Each claim "
            "returns VERIFIED, REFUTED, or REFUSED; the free-text remainder is "
            "reported as unverifiable and is never blessed. Gate on "
            "counts.refuted == 0 and read `coverage` — a pass means only that "
            "nothing checkable was refuted, not that the text is true. "
            "Contract: primus.certificate/2."
        ),
        "inputSchema": {"type": "object", "properties": dict(_TEXT_OR_PATH)},
    },
    {
        "name": "catalog",
        "description": (
            "List every module in the vault with its entrypoints, discovered by "
            "introspection rather than from a hardcoded list. Use this to find "
            "which module answers a question before calling `call`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {"type": "string",
                           "description": "Only modules or functions matching "
                                          "this substring."},
            },
        },
    },
    {
        "name": "call",
        "description": (
            "Invoke one entrypoint of one module by name, on text or on the "
            "integers found in it. Dispatch only: the result is exactly what "
            "the module returned, or the exception type it raised — never a "
            "substitute value. Use `catalog` first to find the name."
        ),
        "inputSchema": {
            "type": "object",
            "properties": dict(_TEXT_OR_PATH, **{
                "module": {"type": "string", "description": "Module name, e.g. 'language'."},
                "function": {"type": "string", "description": "Entrypoint name, e.g. 'stylometry'."},
            }),
            "required": ["module", "function"],
        },
    },
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
    rec = full_stack.run(got["text"], only_layers=layers)
    rec["source"] = got["source"]
    return _wrap(rec)


def _tool_certify(args: Dict[str, Any]) -> Dict[str, Any]:
    got = _text_from(args)
    # The seed engine's certify is the source of truth for the certificate;
    # Chiron does not carry a second copy of it.
    try:
        from primus.certify import certify
    except ImportError:
        seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
        if seed not in sys.path:
            sys.path.insert(0, seed)
        from primus.certify import certify
    rec = certify(got["text"])
    rec["source"] = got["source"]
    return _wrap(rec)


_TEXT_HINTS = ("text", "output", "s", "string", "prose", "passage", "content",
               "sentence", "doc", "body", "claim", "message")
_SEQ_HINTS = ("surface", "seq", "sequence", "values", "terms", "nums",
              "numbers", "data", "series", "xs")


def _kind_of(param) -> str:
    name = param.name.lower()
    ann = getattr(param.annotation, "__name__", str(param.annotation)).lower()
    if name in _SEQ_HINTS or "list" in ann or "sequence" in ann or "iterable" in ann:
        return "surface"
    if name in _TEXT_HINTS or "str" in ann:
        return "text"
    return "unknown"


def _catalog(filter_: Optional[str] = None) -> Dict[str, Any]:
    mods = sorted(f[:-3] for f in os.listdir(_HERE) if f.endswith(".py"))
    out: List[Dict[str, Any]] = []
    for name in mods:
        entry: Dict[str, Any] = {"name": name, "functions": []}
        try:
            mod = importlib.import_module(name)
        except BaseException as exc:                       # noqa: BLE001
            entry.update(status="FAILED",
                         error="%s: %s" % (type(exc).__name__, exc))
            out.append(entry)
            continue
        entry["status"] = "OK"
        entry["doc"] = ((mod.__doc__ or "").strip().splitlines() or [""])[0][:200]
        for fname, obj in vars(mod).items():
            if fname.startswith("_") or not inspect.isfunction(obj):
                continue
            if getattr(obj, "__module__", None) != name:
                continue
            try:
                sig = inspect.signature(obj)
            except (ValueError, TypeError):
                continue
            params = list(sig.parameters.values())
            positional = [p for p in params
                          if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            required = [p for p in positional if p.default is p.empty]
            entry["functions"].append({
                "name": fname,
                "doc": ((obj.__doc__ or "").strip().splitlines() or [""])[0][:160],
                "params": [p.name for p in params],
                "required_arity": len(required),
                "first_arg_kind": _kind_of(positional[0]) if positional else "unknown",
            })
        entry["functions"].sort(key=lambda f: f["name"])
        out.append(entry)

    if filter_:
        q = filter_.lower()
        out = [m for m in out
               if q in m["name"].lower()
               or any(q in f["name"].lower() for f in m["functions"])]
    return {
        "schema": "chiron.catalog/1",
        "modules": out,
        "module_count": len(out),
        "imported": sum(1 for m in out if m["status"] == "OK"),
        "entrypoints": sum(len(m["functions"]) for m in out),
    }


def _tool_catalog(args: Dict[str, Any]) -> Dict[str, Any]:
    return _wrap(_catalog(args.get("filter")))


def _numbers(text: str) -> List[int]:
    import re
    out = []
    for tok in re.findall(r"\b\d[\d,]*\b", text or ""):
        try:
            out.append(int(tok.replace(",", "")))
        except ValueError:
            pass
    return out


def _tool_call(args: Dict[str, Any]) -> Dict[str, Any]:
    module = args.get("module")
    function = args.get("function")
    if not module or not function:
        raise ToolError("module and function are both required")
    got = _text_from(args)
    rec: Dict[str, Any] = {"schema": "chiron.call/1",
                           "module": module, "function": function,
                           "source": got["source"]}
    t0 = time.time()
    try:
        mod = importlib.import_module(str(module))
    except ImportError as exc:
        raise ToolError("no such module: %s (%s)" % (module, exc))
    fn = getattr(mod, str(function), None)
    if fn is None or not callable(fn):
        raise ToolError("%s has no callable %s" % (module, function))
    try:
        sig = inspect.signature(fn)
        positional = [p for p in sig.parameters.values()
                      if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        kind = _kind_of(positional[0]) if positional else "unknown"
        if kind == "surface":
            arg: Any = _numbers(got["text"])
        elif kind == "text":
            arg = got["text"]
        else:
            raise ToolError(
                "%s.%s takes %r, which is neither text nor a numeric surface; "
                "this tool can only drive one-argument text or surface "
                "entrypoints" % (module, function,
                                 positional[0].name if positional else None))
        rec["arg_kind"] = kind
        rec["result"] = fn(arg)
        rec["status"] = "OK"
    except ToolError:
        raise
    except BaseException as exc:                           # noqa: BLE001
        rec["status"] = "ERROR"
        rec["error"] = ("%s: %s" % (type(exc).__name__, exc))[:400]
    rec["ms"] = round((time.time() - t0) * 1000, 1)
    return _wrap(rec)


_IMPL = {
    "attest": _tool_attest,
    "analyze": _tool_analyze,
    "certify": _tool_certify,
    "catalog": _tool_catalog,
    "call": _tool_call,
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
    "the remainder stays unverified), and `catalog` then `call` to reach any "
    "individual module. Every tool accepts a local file path. Report REFUSED "
    "spans to the user as unattributed rather than dropping them, and never "
    "describe any output here as a probability that text is machine-written."
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
    print("chiron-mcp: serving attest + analyze + certify + catalog + call "
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

    # catalog discovers the vault
    cat = body(_tool_catalog({}))
    check("catalog: every module imports",
          cat["imported"] == cat["module_count"] and cat["module_count"] > 50,
          "%d/%d" % (cat["imported"], cat["module_count"]))
    check("catalog: filter narrows", len(body(_tool_catalog(
        {"filter": "attest"}))["modules"]) < cat["module_count"])

    # call dispatches, and refuses what it cannot drive
    r = body(_tool_call({"module": "language", "function": "readability",
                         "text": "Short sentence. Another one here."}))
    check("call: dispatches a text entrypoint", r["status"] == "OK",
          str(r.get("error")))
    r = body(_tool_call({"module": "aesthetics", "function": "aesthetic",
                         "text": "1, 4, 9, 16, 25"}))
    check("call: dispatches a surface entrypoint",
          r["status"] == "OK" and r["arg_kind"] == "surface", str(r.get("error")))
    try:
        _tool_call({"module": "language", "function": "does_not_exist",
                    "text": "x"})
        check("call: unknown function rejected", False)
    except ToolError:
        check("call: unknown function rejected", True)

    # protocol surface
    check("tools: all declared tools have an implementation",
          {t["name"] for t in TOOLS} == set(_IMPL))
    check("tools: every tool documents a file path",
          all("path" in json.dumps(t["inputSchema"]) for t in TOOLS
              if t["name"] != "catalog"))

    print("\n  chiron-mcp gates: %d/%d passed." % (passed, passed + failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
