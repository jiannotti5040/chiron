#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
test_mcp_server.py — full MCP handshake against the real server process.

Spawns `python -m primus.mcp_server` as a subprocess and drives the actual
stdio protocol: initialize → initialized → tools/list → tools/call for both
tools (true/false/refusable cases) → unknown tool → ping. Gates on the same
discipline the server sells: exact expected fields, no tolerance.

    python3 test_mcp_server.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, PYTHONPATH=os.path.join(HERE, "src"))

FAILS = 0


def gate(name, cond):
    global FAILS
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    FAILS += 0 if cond else 1


def run_session(messages):
    """Feed newline-delimited JSON-RPC messages; return responses by id."""
    proc = subprocess.run(
        [sys.executable, "-m", "primus.mcp_server"],
        input="\n".join(json.dumps(m) for m in messages) + "\n",
        capture_output=True, text=True, timeout=60, env=ENV, cwd=HERE)
    out = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)          # every stdout line must be protocol JSON
        if "id" in msg:
            out[msg["id"]] = msg
    return out


def main():
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "handshake-test", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "certify",
                    "arguments": {"text": "2+2=5. The sequence 1 1 2 3 5 8 13 "
                                          "continues as 21, 34. Trust me."}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "collapse", "arguments": {"surface": "1 1 2 3 5 8 13 21"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "collapse",
                    "arguments": {"surface": [7, 2, 9, 4, 4, 8, 3, 1, 6, 5]}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "no_such_tool", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 7, "method": "ping"},
    ]
    r = run_session(msgs)

    init = r.get(1, {}).get("result", {})
    gate("initialize returns serverInfo.name == primus",
         init.get("serverInfo", {}).get("name") == "primus")
    gate("initialize echoes protocol version",
         init.get("protocolVersion") == "2025-06-18")

    tools = {t["name"] for t in r.get(2, {}).get("result", {}).get("tools", [])}
    gate("tools/list exposes exactly {certify, collapse}",
         tools == {"certify", "collapse"})

    cert = r.get(3, {}).get("result", {}).get("structuredContent", {})
    counts = cert.get("counts", {})
    gate("certify: false arithmetic refuted", counts.get("refuted") == 1)
    gate("certify: true continuation verified", counts.get("verified") == 1)
    gate("certify: free text honestly unverifiable",
         cert.get("unverifiable_remainder") is True)
    gate("certify: not flagged as tool error",
         r.get(3, {}).get("result", {}).get("isError") is False)

    fib = r.get(4, {}).get("result", {}).get("structuredContent", {})
    gate("collapse: fibonacci verified via string surface",
         fib.get("verified") is True and "recurrence" in str(fib.get("model_class")))

    rnd = r.get(5, {}).get("result", {}).get("structuredContent", {})
    gate("collapse: random array honestly not verified",
         rnd.get("verified") is False)

    gate("unknown tool -> JSON-RPC invalid-params error",
         r.get(6, {}).get("error", {}).get("code") == -32602)
    gate("ping answered", r.get(7, {}).get("result") == {})

    print(f"\n  {10 - FAILS}/10 MCP handshake gates passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
