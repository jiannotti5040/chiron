#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Chiron MCP transport contract against the real stdio server process.

Run: python3 Chiron/tests/test_mcp_server.py

The server's own selftest exercises implementations in process. This test is
the separate boundary gate: it sends JSON-RPC through real stdin/stdout and
requires every stdout line to remain protocol JSON.
"""
import json
import os
import subprocess
import sys
import tempfile


CHIRON = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.dirname(CHIRON)
SERVER = os.path.join(CHIRON, "mcp_server.py")


def run_session(messages):
    proc = subprocess.run(
        [sys.executable, SERVER],
        input="\n".join(json.dumps(message) for message in messages) + "\n",
        text=True,
        capture_output=True,
        cwd=ROOT,
        timeout=90,
    )
    responses = {}
    for line in proc.stdout.splitlines():
        message = json.loads(line)  # stdout must carry protocol, never logging.
        if "id" in message:
            responses[message["id"]] = message
    return proc, responses


def main():
    checks = []

    def gate(name, condition):
        checks.append((name, bool(condition)))
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "quarterly_report.txt")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write("The quarterly report lists 4200 units shipped and 1400 returned.")

        proc, response = run_session([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "chiron-transport-test", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "analyze", "arguments": {"path": source}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "certify",
                        "arguments": {"text": "The sum of 2 and 3 is 5. 2+2=5."}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
             "params": {"name": "attest", "arguments": {
                 "output": "The report lists 4200 units shipped and 1400 returned.",
                 "input_paths": [source]}}},
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
             "params": {"name": "catalog", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
             "params": {"name": "collapse", "arguments": {
                 "surface": [1, 1, 2, 3, 5, 8, 13, 21]}}},
            {"jsonrpc": "2.0", "id": 8, "method": "tools/call",
             "params": {"name": "trace", "arguments": {
                 "surface": "1 1 2 3 5 8 13 21"}}},
            # This was the former generic dispatcher. It must now fail at the
            # real stdio boundary, not merely be absent from an in-process map.
            {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
             "params": {"name": "call", "arguments": {
                 "module": "language", "function": "readability",
                 "text": "A short sentence. Another follows."}}},
            {"jsonrpc": "2.0", "id": 10, "method": "tools/call",
             "params": {"name": "not_a_tool", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 11, "method": "ping"},
        ])

    gate("server exits cleanly after stdio closes", proc.returncode == 0)
    init = response.get(1, {}).get("result", {})
    gate("initialize identifies Chiron", init.get("serverInfo", {}).get("name") == "chiron")
    gate("initialize echoes the requested protocol", init.get("protocolVersion") == "2025-06-18")
    tools = {tool.get("name") for tool in response.get(2, {}).get("result", {}).get("tools", [])}
    tool_records = response.get(2, {}).get("result", {}).get("tools", [])
    gate("tools/list exposes only the reviewed static Chiron surface",
         tools == {"attest", "analyze", "certify", "collapse", "trace", "catalog"})
    gate("tools/list makes schema, authority, side effects, and provenance explicit",
         all(
             tool.get("annotations") == {
                 "readOnlyHint": True, "destructiveHint": False,
                 "idempotentHint": True, "openWorldHint": False,
             }
             and set(tool.get("_meta", {}).get("chiron", {}))
             >= {"schema", "contract", "authority", "side_effects", "provenance"}
             and tool["_meta"]["chiron"]["schema"] == "chiron.mcp.tool/1"
             for tool in tool_records))

    analyzed = response.get(3, {}).get("result", {}).get("structuredContent", {})
    gate("analyze reads a caller-authorized file with visible source metadata",
         analyzed.get("schema") == "chiron.full_stack/1"
         and analyzed.get("source", {}).get("from") == "file"
         and analyzed.get("stages_run") == len(analyzed.get("results", [])))

    certificate = response.get(4, {}).get("result", {}).get("structuredContent", {})
    counts = certificate.get("counts", {})
    gate("certify returns both an exact verification and refutation",
         counts.get("verified", 0) >= 1 and counts.get("refuted", 0) >= 1)

    attestation = response.get(5, {}).get("result", {}).get("structuredContent", {})
    gate("attest names the supplied candidate rather than claiming global attribution",
         "quarterly_report.txt" in attestation.get("candidate_inputs", []))

    catalog = response.get(6, {}).get("result", {}).get("structuredContent", {})
    gate("catalog records the reviewed static allowlist and its policy metadata",
         catalog.get("schema") == "chiron.catalog/2"
         and catalog.get("reviewed_static_allowlist") is True
         and {tool.get("name") for tool in catalog.get("tools", [])} == tools
         and all("metadata" in tool for tool in catalog.get("tools", [])))

    collapsed = response.get(7, {}).get("result", {}).get("structuredContent", {})
    gate("collapse delegates to the canonical exact engine without float coercion",
         collapsed.get("schema") == "chiron.mcp.collapse/1"
         and collapsed.get("verified") is True
         and "recurrence" in str(collapsed.get("model_class"))
         and collapsed.get("source", {}).get("kind") == "integer-array")

    trace = response.get(8, {}).get("result", {}).get("structuredContent", {})
    gate("trace returns the canonical diagnostic record, not a new stamp",
         trace.get("schema") == "chiron.trace/1"
         and trace.get("engine_verdict") in ("VERIFIED", "ABSTAINED"))

    gate("the former generic call tool is refused at the stdio boundary",
         response.get(9, {}).get("error", {}).get("code") == -32602)
    gate("unknown tools return an MCP invalid-params error",
         response.get(10, {}).get("error", {}).get("code") == -32602)
    gate("ping receives an empty result", response.get(11, {}).get("result") == {})

    passed = sum(1 for _, good in checks if good)
    print("\n  %d/%d Chiron MCP transport gates passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
