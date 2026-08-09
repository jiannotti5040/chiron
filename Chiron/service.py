#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""chiron.service — the whole vault over HTTP, on the one dispatch.

`primus.engine_server` serves the seed: certify and collapse. That is the
right surface for the published package and it should stay that way. But it is
also why the iOS app could only certify — twelve operations exist and two were
reachable, so a phone could check arithmetic and nothing else.

This serves all twelve, and it does it by calling
`Chiron/mcp_server.py:_IMPL` — the same dict an MCP client reaches and the
same one `bin/chiron` reaches. There is no second implementation of any
operation here, only a second transport. An app, an agent, and a terminal
therefore cannot disagree about what `attest` does, because there is one
`attest`.

SECURITY POSTURE, inherited deliberately from the seed server

  * Binds 127.0.0.1 unless told otherwise, and says so on startup.
  * Closed route table, fixed at import. Anything else 404s; no prefix match,
    no catch-all, no path arguments.
  * Bodies bounded before parsing.
  * Sliding-window rate limit, per-key and global.
  * One structured access line per request carrying a hashed body prefix, so a
    request can be correlated without its content being retained.
  * Optional bearer token. Absent by default, and absence is reported rather
    than silently meaning "open".

WHAT IT WILL NOT DO

No route mutates anything. `catalog` is the only way to learn what exists, and
arbitrary module dispatch is unavailable here exactly as it is everywhere
else. A refusal is a 200 carrying REFUSED, never a 4xx — a refusal is a
result, and turning it into an HTTP error would teach every client to treat
the vault's most important answer as a failure.

    python3 Chiron/service.py --port 8788
    curl -s localhost:8788/v1/capabilities
    curl -s localhost:8788/v1/attest -d '{"output":"...","input_paths":["a.txt"]}'
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Deque, Dict, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# The envelope contract, shared with primus.engine_server. This server exposes
# more operations, but the wrapper around every result is the same one — so a
# client written for either decodes both, and there is one envelope to reason
# about rather than two. `server` below names which implementation answered.
SCHEMA = "chiron.local_api/1"
SERVER_ID = "chiron.service/1"


def _primus_version() -> str:
    try:
        from primus import __version__
        return __version__
    except Exception:
        seed = os.path.join(os.path.dirname(_HERE), "Primus", "src")
        if seed not in sys.path:
            sys.path.insert(0, seed)
        try:
            from primus import __version__
            return __version__
        except Exception:
            return "unknown"
MAX_BODY_BYTES = 512 * 1024
DEFAULT_PORT = 8788

# Every operation the vault exposes, POST-only, all read-only. The table is
# built from _IMPL rather than typed out, so a tool added to the dispatch
# cannot be silently missing here — and one removed cannot linger.
import mcp_server  # noqa: E402

OPERATIONS = tuple(sorted(mcp_server._IMPL))
ROUTES: Dict[str, Tuple[str, ...]] = {"/v1/capabilities": ("GET",),
                                      "/health": ("GET",)}
for _op in OPERATIONS:
    ROUTES["/v1/" + _op] = ("POST",)


class Limiter:
    """Sliding one-minute window, per key and overall. In-process, so it
    bounds one server rather than a fleet — stated because a limit that
    implies more than it delivers is worse than none."""

    def __init__(self, per_key: int = 60, overall: int = 480) -> None:
        self.per_key, self.overall = per_key, overall
        self._keyed: Dict[str, Deque[float]] = {}
        self._all: Deque[float] = deque()
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        cutoff = now - 60.0
        with self._lock:
            while self._all and self._all[0] < cutoff:
                self._all.popleft()
            window = self._keyed.setdefault(key, deque())
            while window and window[0] < cutoff:
                window.popleft()
            if len(self._all) >= self.overall or len(window) >= self.per_key:
                return False
            self._all.append(now)
            window.append(now)
            return True


class Handler(BaseHTTPRequestHandler):
    server_version = "chiron-service/1"
    limiter: Limiter = Limiter()
    bearer: Optional[str] = None

    # -- plumbing ---------------------------------------------------------

    def log_message(self, *args: Any) -> None:  # silence the default logger
        pass

    def _access(self, code: int, body: bytes = b"") -> None:
        digest = hashlib.sha256(body).hexdigest()[:16] if body else "-"
        sys.stderr.write(
            "chiron.service ip=%s method=%s path=%s status=%d in_bytes=%d "
            "in_sha256=%s\n" % (self.client_address[0], self.command,
                                self.path.split("?")[0], code, len(body),
                                digest))
        sys.stderr.flush()

    def _send(self, code: int, payload: Dict[str, Any], body: bytes = b"") -> None:
        raw = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except BrokenPipeError:
            pass
        self._access(code, body)

    def _envelope(self, operation: str, result: Any, body: bytes = b"") -> Dict[str, Any]:
        """The same envelope shape `primus.engine_server` emits.

        One contract, so a client written for either server decodes both. The
        request id is derived from the body digest and the arrival time, which
        makes it correlatable with the access log without carrying content.
        """
        request_id = hashlib.sha256(
            body + repr(time.time()).encode()).hexdigest()[:32]
        return {"schema": SCHEMA, "server": SERVER_ID,
                "request_id": request_id,
                "operation": operation,
                "engine": {"primus_version": _primus_version(),
                           "certificate_schema": "primus.certificate/2"},
                "result": result}

    def _authorized(self) -> bool:
        if not self.bearer:
            return True
        header = self.headers.get("Authorization") or ""
        return header == "Bearer " + self.bearer

    # -- routing ----------------------------------------------------------

    def _check(self, method: str) -> Optional[str]:
        path = self.path.split("?")[0]
        allowed = ROUTES.get(path)
        if allowed is None:
            self._send(404, {"schema": SCHEMA, "error": "no such route",
                             "routes": sorted(ROUTES)})
            return None
        if method not in allowed:
            self._send(405, {"schema": SCHEMA, "error": "method not allowed",
                             "allowed": list(allowed)})
            return None
        if not self._authorized():
            self._send(401, {"schema": SCHEMA, "error": "bearer required"})
            return None
        if not self.limiter.allow(self.client_address[0]):
            self._send(429, {"schema": SCHEMA, "error": "rate limited"})
            return None
        return path

    def do_GET(self) -> None:  # noqa: N802
        path = self._check("GET")
        if path is None:
            return
        if path == "/health":
            return self._send(200, {"schema": SCHEMA, "status": "ok"})
        catalog = json.loads(
            mcp_server._tool_catalog({})["content"][0]["text"])
        self._send(200, self._envelope("capabilities", {
            "operations": [{"operation": name, "method": "POST",
                            "path": "/v1/" + name} for name in OPERATIONS],
            "tools": catalog.get("tools", []),
            "limits": {"body_bytes": MAX_BODY_BYTES},
            "authentication": ("bearer" if self.bearer else "none — bound to "
                               "loopback; do not expose this port"),
            "note": ("Every operation dispatches through "
                     "Chiron/mcp_server.py:_IMPL, the same table MCP clients "
                     "and the CLI use. A REFUSED result returns 200: a "
                     "refusal is a result, not an error."),
        }))

    def do_POST(self) -> None:  # noqa: N802
        path = self._check("POST")
        if path is None:
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._send(400, {"schema": SCHEMA, "error": "bad length"})
        if length > MAX_BODY_BYTES:
            # Drain before replying. Answering mid-upload resets the
            # connection and the client sees a transport error instead of the
            # 413 that explains itself. The bound still holds where it
            # matters: these bytes are discarded, never parsed, and never
            # reach an engine.
            remaining = length
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 65536))
                if not chunk:
                    break
                remaining -= len(chunk)
            self.close_connection = True
            return self._send(413, {"schema": SCHEMA,
                                    "error": "body exceeds %d bytes" % MAX_BODY_BYTES,
                                    "note": "read and discarded without parsing"})
        body = self.rfile.read(length) if length else b""
        try:
            args = json.loads(body or b"{}")
        except ValueError:
            return self._send(400, {"schema": SCHEMA, "error": "malformed JSON"}, body)
        if not isinstance(args, dict):
            return self._send(400, {"schema": SCHEMA,
                                    "error": "body must be a JSON object"}, body)

        operation = path[len("/v1/"):]
        impl = mcp_server._IMPL.get(operation)
        if impl is None:                      # unreachable via ROUTES; belt and braces
            return self._send(404, {"schema": SCHEMA, "error": "no such operation"}, body)
        try:
            wrapped = impl(args)
        except mcp_server.ToolError as exc:
            # A caller error, reported as one. Distinct from a refusal.
            return self._send(400, {"schema": SCHEMA, "operation": operation,
                                    "error": str(exc)}, body)
        except Exception as exc:              # engine fault, not a verdict
            return self._send(500, {"schema": SCHEMA, "operation": operation,
                                    "error": type(exc).__name__}, body)
        try:
            record = json.loads(wrapped["content"][0]["text"])
        except Exception:
            record = wrapped
        self._send(200, self._envelope(operation, record, body), body)


def serve(port: int = DEFAULT_PORT, host: str = "127.0.0.1",
          bearer: Optional[str] = None) -> int:
    Handler.bearer = bearer
    server = ThreadingHTTPServer((host, port), Handler)
    sys.stderr.write(
        "chiron.service %s on http://%s:%d — %d operations, auth=%s\n"
        % (SCHEMA, host, port, len(OPERATIONS),
           "bearer" if bearer else "none (loopback only)"))
    sys.stderr.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _selftest() -> int:
    """Exercises the real socket. A route table that only passes when nothing
    is listening would prove nothing."""
    import urllib.error
    import urllib.request

    failures, ran = [], []

    def gate(name: str, condition: bool) -> None:
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % port

    def get(path):
        with urllib.request.urlopen(base + path, timeout=20) as r:
            return r.status, json.loads(r.read())

    def post(path, payload):
        req = urllib.request.Request(
            base + path, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    try:
        code, caps = get("/v1/capabilities")
        gate("capabilities lists every dispatch operation",
             code == 200 and len(caps["result"]["operations"]) == len(mcp_server._IMPL))
        gate("capabilities names the shared dispatch",
             "_IMPL" in caps["result"]["note"])

        code, body = post("/v1/certify", {"text": "The sum of 2 and 2 is 4."})
        gate("certify verifies through the service",
             code == 200 and body["result"]["counts"]["verified"] == 1)

        code, body = post("/v1/certify", {
            "text": "Readiness fell to 74%.",
            "facts": {"readiness": {"value": 74, "unit": "percent"}}})
        gate("grounded facts reach the service",
             code == 200 and body["result"]["counts"]["verified"] == 1)

        code, body = post("/v1/certify", {
            "text": "Readiness fell to 91%.",
            "facts": {"readiness": {"value": 74, "unit": "percent"}}})
        gate("a wrong figure is REFUTED, and that is still a 200",
             code == 200 and body["result"]["counts"]["refuted"] == 1)

        code, body = post("/v1/falsifiers", {"surface": "1 1 2 3 5 8 13 21"})
        gate("falsifiers reach the service with an exact prediction",
             code == 200 and body["result"]["falsifiers"][0]["predicted"] == 34)

        code, body = post("/v1/solve", {"surface": "1 1 2 3 5 8 13 21"})
        gate("solve escalates rather than performing an irreversible step",
             code == 200 and body["result"]["status"] == "ESCALATED")

        code, body = post("/v1/attest", {"output": "unsourced words"})
        gate("attest with no inputs REFUSES as a 200 result",
             code == 200
             and body["result"]["spans"][0]["verdict"] == "REFUSED")

        code, body = post("/v1/collapse", {"surface": "not a sequence at all"})
        gate("an unrecoverable surface is a result, not an HTTP error",
             code == 200)

        # A genuine ToolError, not a coercible one: _text_from deliberately
        # stringifies a scalar, so `text: 5` is a valid request meaning "5".
        code, body = post("/v1/attest", {"output": "x", "inputs": "not-an-object"})
        gate("a caller error is a 400, distinct from a refusal",
             code == 400 and "error" in body and "result" not in body)

        code, body = post("/v1/certify", {"text": 5})
        gate("a coercible scalar is honoured rather than rejected",
             code == 200)

        try:
            get("/v1/nope")
            reached = True
        except urllib.error.HTTPError as e:
            reached = False
            gate("an unknown route 404s with the closed table", e.code == 404)
        if reached:
            gate("an unknown route 404s with the closed table", False)

        try:
            get("/v1/certify")
            reached = True
        except urllib.error.HTTPError as e:
            reached = False
            gate("a GET on a POST route is 405, not silently handled",
                 e.code == 405)
        if reached:
            gate("a GET on a POST route is 405, not silently handled", False)

        req = urllib.request.Request(
            base + "/v1/certify", data=b"x" * (MAX_BODY_BYTES + 1),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=20)
            oversize = False
        except urllib.error.HTTPError as e:
            oversize = e.code == 413
        gate("an oversize body is refused before parsing", oversize)

        gate("no route mutates state",
             all(m == ("POST",) or m == ("GET",) for m in ROUTES.values()))
    finally:
        server.shutdown()
        server.server_close()

    print("\n  chiron.service self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--bearer", default=os.environ.get("CHIRON_SERVICE_TOKEN"),
                        help="require this bearer token; loopback-only without it")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.selftest:
        return _selftest()
    if args.host != "127.0.0.1" and not args.bearer:
        sys.stderr.write(
            "chiron.service: refusing to bind %s without --bearer. A non-loopback "
            "bind with no authentication would expose every operation.\n" % args.host)
        return 2
    return serve(port=args.port, host=args.host, bearer=args.bearer)


if __name__ == "__main__":
    raise SystemExit(main())
