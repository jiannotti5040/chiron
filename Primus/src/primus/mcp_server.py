#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
primus.mcp_server — the verifier-that-refuses as an MCP server.

Exposes the two Primus operations as Model Context Protocol tools over
stdio, so any MCP-speaking agent (Claude Code, Claude Desktop, Cowork,
Cursor, ...) can gate its own output through the exact engine:

  certify   — feed it text (typically a model's answer); every checkable
              claim comes back VERIFIED, REFUTED, or REFUSED, the free-text
              remainder is honestly unverifiable, and the certificate is
              returned as structured content.
  collapse  — recover the minimal generator beneath a codified surface
              (integer sequence or string) with held-out proof or refusal.

Design notes:
  * Dependency-free by design: this is a minimal, correct implementation of
    the MCP surface these two tools need (initialize / initialized / ping /
    tools/list / tools/call), speaking newline-delimited JSON-RPC 2.0 over
    stdio per the MCP stdio transport. No SDK required — in keeping with
    the vault's rule that the core runs on bare Python.
  * stdout carries protocol messages ONLY; diagnostics go to stderr.
  * A refuted claim is a RESULT, not a tool error: `isError` is reserved
    for genuine execution failures. Agents gate on the certificate counts.

Run directly:            primus-mcp
Register (Claude Code):  claude mcp add primus -- primus-mcp
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, Optional

PROTOCOL_DEFAULT = "2025-06-18"

TOOLS = [
    {
        "name": "certify",
        "description": (
            "Certify the checkable claims in text (typically an LLM/agent "
            "answer). Each claim is exactly checked: VERIFIED (holds), "
            "REFUTED (exactly false), or REFUSED (no exact proof either "
            "way); free text is reported as unverifiable, never blessed. "
            "Gate on counts.refuted == 0, treat the unverifiable remainder "
            "as unverified, and read `coverage` — a pass means only that "
            "nothing checkable was refuted. Checkable kinds: integer/"
            "rational arithmetic incl. powers, percentages, primality, "
            "binomial coefficients, gcd/lcm, modular arithmetic, date "
            "arithmetic, sums/averages of listed numbers, integer-sequence "
            "continuations, integer runs. Contract: SCHEMA.md "
            "(primus.certificate/2)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string",
                         "description": "The text whose claims to certify."}
            },
            "required": ["text"],
        },
    },
    {
        "name": "conjecture",
        "description": (
            "Guess-and-prove closed-form recovery for an integer sequence. "
            "The exact engine goes first; if it abstains, a genetic-"
            "programming proposer (gplearn, optional dependency) suggests "
            "closed forms and each is checked in exact rational arithmetic "
            "against EVERY term, including a holdout suffix the search "
            "never saw. VERIFIED means exact reproduction of the given "
            "data (never a claim about the true generator — the "
            "certificate's caveat says so); REFUSED means no candidate "
            "survived, or gplearn is not installed. The stochastic "
            "proposer never stamps; only the exact verifier does."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "terms": {
                    "description": "Integer sequence (array or whitespace/"
                                   "comma-separated string).",
                    "anyOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "integer"}},
                    ],
                },
                "seed": {"type": "integer", "description": "RNG seed (default 0)."},
            },
            "required": ["terms"],
        },
    },
    {
        "name": "collapse",
        "description": (
            "Recover the minimal generator beneath a codified surface under "
            "an exact MDL criterion. 'verified' is true only when the "
            "recovered rule exactly predicted held-out data it never saw; "
            "otherwise the engine abstains rather than guess. Accepts an "
            "integer sequence (array or whitespace/comma-separated string) "
            "or an arbitrary string surface (ciphers, encodings)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "surface": {
                    "description": "Integer array, numeric string like "
                                   "'1 1 2 3 5 8', or any string surface.",
                    "anyOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "number"}},
                    ],
                }
            },
            "required": ["surface"],
        },
    },
]


# --------------------------------------------------------------- tool impls
def _parse_surface(raw: Any):
    if isinstance(raw, list):
        vals = [float(x) for x in raw]
        return [int(v) if v.is_integer() else v for v in vals]
    raw = str(raw)
    ints = re.findall(r"-?\d+", raw)
    leftover = re.sub(r"[-\d\s,]+", "", raw)
    if ints and not leftover:
        return [int(x) for x in ints]
    return raw


def _tool_certify(args: Dict[str, Any]) -> Dict[str, Any]:
    from primus.certify import certify, render

    cert = certify(str(args["text"]))
    return {"content": [{"type": "text", "text": render(cert)}],
            "structuredContent": cert,
            "isError": False}


def _tool_collapse(args: Dict[str, Any]) -> Dict[str, Any]:
    from primus.engine import collapse

    inv = collapse(_parse_surface(args["surface"]))
    payload = inv.to_dict()
    payload["verified"] = inv.verified
    return {"content": [{"type": "text", "text": inv.explanation}],
            "structuredContent": payload,
            "isError": False}


def _tool_conjecture(args: Dict[str, Any]) -> Dict[str, Any]:
    from primus.conjecture import conjecture, render

    raw = args["terms"]
    if isinstance(raw, list):
        terms = [int(x) for x in raw]
    else:
        terms = [int(x) for x in re.findall(r"-?\d+", str(raw))]
    cert = conjecture(terms, seed=int(args.get("seed", 0)))
    return {"content": [{"type": "text", "text": render(cert)}],
            "structuredContent": cert,
            "isError": False}


_IMPL = {"certify": _tool_certify, "collapse": _tool_collapse,
         "conjecture": _tool_conjecture}


# ------------------------------------------------------------- JSON-RPC core
def _reply(msg_id: Any, result: Dict[str, Any]) -> None:
    _send({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _reply_error(msg_id: Any, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": msg_id,
           "error": {"code": code, "message": message}})


def _send(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, separators=(",", ":"), default=str) + "\n")
    sys.stdout.flush()


def _handle(msg: Dict[str, Any]) -> None:
    method = msg.get("method")
    msg_id = msg.get("id")
    is_request = "id" in msg

    if method == "initialize":
        import primus

        client_ver = (msg.get("params") or {}).get("protocolVersion")
        _reply(msg_id, {
            "protocolVersion": client_ver or PROTOCOL_DEFAULT,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "primus",
                           "title": "Primus — exact verification with refusal",
                           "version": primus.__version__},
            "instructions": (
                "Two tools, one discipline: never certify what cannot be "
                "exactly verified. Use `certify` to gate generated text "
                "(refuted==0 passes; the unverifiable remainder is exactly "
                "that). Use `collapse` to recover the exact rule beneath a "
                "sequence or string, or receive an honest refusal."),
        })
    elif method in ("notifications/initialized", "notifications/cancelled",
                    "notifications/roots/list_changed"):
        return  # notifications need no reply
    elif method == "ping":
        _reply(msg_id, {})
    elif method == "tools/list":
        _reply(msg_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        impl = _IMPL.get(name)
        if impl is None:
            _reply_error(msg_id, -32602, f"unknown tool: {name!r}")
            return
        try:
            _reply(msg_id, impl(params.get("arguments") or {}))
        except KeyError as exc:
            _reply_error(msg_id, -32602, f"missing argument: {exc}")
        except Exception as exc:  # execution failure -> tool-level error result
            _reply(msg_id, {"content": [{"type": "text",
                                         "text": f"{type(exc).__name__}: {exc}"}],
                            "isError": True})
    elif is_request:
        _reply_error(msg_id, -32601, f"method not found: {method!r}")
    # unknown notifications are ignored


def main(argv: Optional[list] = None) -> int:
    print("primus-mcp: serving certify + collapse over stdio "
          "(newline-delimited JSON-RPC)", file=sys.stderr)
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
        except Exception as exc:  # never crash the transport
            if "id" in msg:
                _reply_error(msg.get("id"), -32603,
                             f"internal error: {type(exc).__name__}")
            print(f"primus-mcp: internal error: {exc!r}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
