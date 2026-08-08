#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
primus.engine_server — the verifier-that-refuses as a minimal HTTP endpoint.

Request in, certificate out. The engine's source is never serialized: every
response is certificate/verdict JSON assembled from engine output plus fixed
strings, exceptions surface as a REFUSED envelope carrying the exception
TYPE NAME only (no messages, no tracebacks), and routing is a CLOSED table
with no catch-all and no file serving. Everything hostile meets a refusal,
not a crash:

  * closed route table: a path that is not a key is 404, a valid path with
    the wrong method is 405 + `Allow:` — nothing else is reachable
  * body cap 128 KiB (fits certify's MAX_TEXT_CHARS with JSON overhead;
    larger bodies are REFUSED with 413 before parsing)
  * malformed / adversarial JSON (including deeply nested arrays that would
    blow the decoder's recursion limit) is a bounded 400, never a dropped
    connection
  * sequence caps reuse the certify/conjecture bounds (MAX_SEQ_TERMS = 256)
  * per-IP and global rate limits (sliding minute window; 429 + REFUSED)
  * bounded concurrency (excess concurrent requests get 429 immediately)
    with a conservative `Retry-After` hint (60 seconds for rate limits,
    1 second for a saturated concurrency gate)
  * optional static bearer auth: set CHIRON_API_TOKEN and every POST requires
    it. This is a local/development control, not production authentication.
  * CORS is disabled by default. A single exact browser origin may be opted in
    with CHIRON_CORS_ORIGIN; native clients do not need CORS.

No-leak rule, on EVERY path: no response body ever carries a traceback, a
file path, a source snippet, a module name, a raw exception message, or an
echo of the caller's request text. The stdlib's HTML error page (which does
echo the offending method back) is replaced by fixed-string JSON, and any
unexpected exception becomes a generic 500 with the detail logged
server-side only.

Endpoints (all request/response bodies are JSON):

  GET  /                                short banner: routes + limits
  GET  /health                          liveness + engine version
  POST /collapse   {"surface": ...}     exact recovery with held-out proof,
                                        or honest refusal
  POST /certify    {"text": ...}        every checkable claim VERIFIED /
                                        REFUTED / REFUSED
  POST /conjecture {"terms": ..., "seed": 0}
                                        guess-and-prove behind the exact gate

  GET  /v1/capabilities                 versioned local contract index
  POST /v1/collapse {"surface": ...}   strict inline request -> wrapped result
  POST /v1/certify  {"text": ...}      strict inline request -> wrapped result

`/v1` deliberately exposes only the deterministic canonical operations. Its
responses use `chiron.local_api/1` with a server-generated request id and
wrap the existing engine-server result. It accepts no paths, dynamic tool
names, or unknown request fields. The contract is implemented and HTTP-tested
locally; it is not a public deployment or an authentication system.

Access log: one structured line per request — client IP, method, normalized
path (query string never logged), status, and the input LENGTH plus a short
input hash. The caller's input is never logged verbatim. `/health` is not
access-logged by default, so a platform health checker polling once a second
cannot bury the human traffic the log exists to show (set CHIRON_LOG_HEALTH=1
to log it anyway).

Environment:
  CHIRON_API_TOKEN            require `Authorization: Bearer <token>` (default: off)
  CHIRON_RATE_PER_MIN         per-IP requests/minute        (default 30)
  CHIRON_RATE_GLOBAL_PER_MIN  total requests/minute         (default 240)
  CHIRON_MAX_CONCURRENCY      simultaneous engine calls     (default 4)
  CHIRON_LOG_HEALTH           "1" to access-log /health too  (default: off)
  CHIRON_CORS_ORIGIN          one exact http(s) browser origin; CORS is off
                              unless this is configured (default: off)
  CHIRON_TRUST_FORWARDED      "1" to take the client IP from the first
                              X-Forwarded-For hop — set ONLY behind a proxy
                              that overwrites that header

Run:    PYTHONPATH=src python3 -m primus.engine_server --host 127.0.0.1 --port 8790
Boundary: see DEPLOY_ENDPOINT.md for the local-only deployment posture.

Status: implemented-and-tested locally (test_engine_server.py drives a real
server process over real HTTP). The server wraps the engine; it changes
nothing on any stamping path. A public deployment still needs an
authenticated gateway, TLS termination, short-lived scoped credentials,
rotation/revocation, and abuse controls outside this process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
import traceback
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

MAX_BODY_BYTES = 128 * 1024  # certify MAX_TEXT_CHARS (100k) + JSON overhead
SCHEMA = "primus.engine_server/1"
LOCAL_API_SCHEMA = "chiron.local_api/1"
RATE_LIMIT_RETRY_AFTER_SECONDS = 60
BUSY_RETRY_AFTER_SECONDS = 1


def _refused(reason: str, error: str = "refused") -> Dict[str, Any]:
    return {"schema": SCHEMA, "status": "REFUSED", "error": error, "reason": reason}


def _local_api_engine_metadata() -> Dict[str, str]:
    """Import canonical version/schema values only when a v1 response needs them."""
    import primus
    from primus.certify import SCHEMA as certificate_schema

    return {"primus_version": primus.__version__,
            "certificate_schema": certificate_schema}


def _local_api_envelope(operation: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Stable, server-authored v1 envelope around a bounded engine result.

    The request id is deliberately generated here, never accepted from the
    caller. It is useful for a client log or a future gateway correlation
    layer, but carries no ambient authority and no caller-controlled text.
    """
    return {"schema": LOCAL_API_SCHEMA,
            "request_id": secrets.token_hex(16),
            "operation": operation,
            "engine": _local_api_engine_metadata(),
            "result": result}


# ------------------------------------------------------------- rate limiting
class Limiter:
    """Sliding one-minute windows, per key and global. Thread-safe."""

    def __init__(self, per_ip: int, global_: int):
        self.per_ip = per_ip
        self.global_ = global_
        self._ip: Dict[str, deque] = defaultdict(deque)
        self._all: deque = deque()
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            for dq in (self._ip[key], self._all):
                while dq and now - dq[0] > 60.0:
                    dq.popleft()
            if len(self._ip[key]) >= self.per_ip or len(self._all) >= self.global_:
                return False
            self._ip[key].append(now)
            self._all.append(now)
            # keep the per-IP table bounded against address churn
            if len(self._ip) > 4096:
                for k in [k for k, dq in self._ip.items() if not dq][:2048]:
                    del self._ip[k]
            return True


# ---------------------------------------------------------------- tool calls
def _parse_int_terms(raw: Any, cap: int) -> Optional[list]:
    if isinstance(raw, list):
        if len(raw) > cap:
            return None
        out = []
        for x in raw:
            if isinstance(x, bool) or not isinstance(x, int):
                return None  # exact contract: integers only
            out.append(x)
        return out
    ints = re.findall(r"-?\d+", str(raw))
    if len(ints) > cap:
        return None
    return [int(x) for x in ints]


def _do_collapse(body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    from primus.certify import MAX_SEQ_TERMS, MAX_TEXT_CHARS
    from primus.engine import collapse

    raw = body["surface"]
    if isinstance(raw, list):
        terms = _parse_int_terms(raw, MAX_SEQ_TERMS)
        if terms is None:
            return 413, _refused(
                f"over budget: integer surfaces are capped at {MAX_SEQ_TERMS} "
                "terms (the certify bound), and terms must be integers",
                "over budget")
        surface: Any = terms
    else:
        raw = str(raw)
        if len(raw) > MAX_TEXT_CHARS:
            return 413, _refused(
                f"over budget: string surfaces are capped at {MAX_TEXT_CHARS} chars",
                "over budget")
        ints = re.findall(r"-?\d+", raw)
        leftover = re.sub(r"[-\d\s,]+", "", raw)
        if ints and not leftover:
            if len(ints) > MAX_SEQ_TERMS:
                return 413, _refused(
                    f"over budget: integer surfaces are capped at {MAX_SEQ_TERMS} terms",
                    "over budget")
            surface = [int(x) for x in ints]
        else:
            surface = raw
    inv = collapse(surface)
    payload = inv.to_dict()
    payload["verified"] = inv.verified
    return 200, {"schema": SCHEMA, "tool": "collapse", "certificate": payload}


def _do_certify(body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    from primus.certify import certify

    # certify enforces its own MAX_TEXT_CHARS internally (truncates + records)
    cert = certify(str(body["text"]))
    return 200, {"schema": SCHEMA, "tool": "certify", "certificate": cert}


def _do_conjecture(body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    from primus.conjecture import MAX_SEQ_TERMS, conjecture

    terms = _parse_int_terms(body["terms"], MAX_SEQ_TERMS)
    if terms is None:
        return 413, _refused(
            f"over budget: conjecture inputs are capped at {MAX_SEQ_TERMS} "
            "integer terms", "over budget")
    seed = body.get("seed", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        return 400, _refused("seed must be an integer", "bad request")
    cert = conjecture(terms, seed=seed)
    return 200, {"schema": SCHEMA, "tool": "conjecture", "certificate": cert}


_TOOLS = {"/collapse": ("surface", _do_collapse),
          "/certify": ("text", _do_certify),
          "/conjecture": ("terms", _do_conjecture)}

# The legacy routes above retain their permissive historical request shape.
# The versioned boundary is intentionally smaller and strict: local clients
# can submit only inline data for the two deterministic canonical operations.
# In particular, conjecture is not a v1 operation. Its optional proposer may
# use stochastic search, so exposing it would blur the compact, exact
# collapse/certify contract this boundary is meant to stabilize.
_LOCAL_API_TOOLS = {
    "/v1/collapse": ("collapse", "surface", _do_collapse),
    "/v1/certify": ("certify", "text", _do_certify),
}


def _validate_local_api_body(operation: str, required: str,
                          body: Any) -> Optional[Dict[str, Any]]:
    """Reject v1 schema drift before it reaches the canonical implementation.

    The check intentionally does not reimplement the engine's budgets or
    semantics. `_do_collapse` and `_do_certify` remain the only execution
    path; this function merely fixes the wire shape and prevents an accidental
    future field from silently acquiring behavior.
    """
    if not isinstance(body, dict):
        return _refused("body must be a JSON object", "bad request")
    if set(body) != {required}:
        return _refused(
            f"body must contain exactly the {required!r} field", "bad request")

    value = body[required]
    if operation == "collapse":
        if isinstance(value, str):
            return None
        if isinstance(value, list):
            if any(isinstance(item, bool) or not isinstance(item, int)
                   for item in value):
                return _refused(
                    "surface arrays must contain only JSON integers",
                    "bad request")
            return None
        return _refused("surface must be a string or an array of integers",
                        "bad request")

    # `certify` is intentionally text-only at this boundary; `_do_certify`
    # still owns the canonical 100k-character truncation-and-record behavior.
    if isinstance(value, str):
        return None
    return _refused("text must be a string", "bad request")


def _is_local_api_path(path: str) -> bool:
    """Whether a path is in the versioned namespace, including bad routes."""
    return path == "/v1" or path.startswith("/v1/")


def _local_api_operation(path: str) -> str:
    if path == "/v1/capabilities":
        return "capabilities"
    spec = _LOCAL_API_TOOLS.get(path)
    return spec[0] if spec else "unknown"

# ------------------------------------------------------------- route table
# CLOSED table. There is no catch-all, no prefix match, no file serving: a
# path that is not a key here is 404 and never reaches the engine. The tuple
# is the set of methods that path *means* — it becomes the `Allow:` header
# verbatim on a 405. (OPTIONS is answered on every routed path as the CORS
# preflight, and HEAD mirrors GET with no body; neither is advertised as a
# semantic method.)
ROUTES: Dict[str, Tuple[str, ...]] = {
    "/": ("GET",),
    "/health": ("GET",),
    "/collapse": ("POST",),
    "/certify": ("POST",),
    "/conjecture": ("POST",),
    "/v1/capabilities": ("GET",),
    "/v1/collapse": ("POST",),
    "/v1/certify": ("POST",),
}
VALID_ROUTES = [f"{m} {p}" for p in sorted(ROUTES) for m in ROUTES[p]]

# Fixed strings for the stdlib's error paths. Nothing here is derived from
# the request, so nothing here can echo the caller back at themselves.
_ERROR_TEXT = {
    400: "bad request",
    404: "not found",
    405: "method not allowed",
    408: "request timeout",
    411: "length required",
    413: "payload too large",
    414: "uri too long",
    415: "unsupported media type",
    431: "request headers too large",
    500: "internal error",
    501: "method not allowed",
    505: "http version not supported",
}

# The client IP is attacker-influenced when X-Forwarded-For is trusted; keep
# it to address characters so it can never forge a line in the access log.
_IP_SCRUB = re.compile(r"[^0-9A-Fa-f:.\[\]]")


# -------------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    server_version = "chiron-engine-endpoint"
    sys_version = ""  # no Python version banner
    limiter: Limiter = Limiter(30, 240)
    gate: threading.BoundedSemaphore = threading.BoundedSemaphore(4)
    token: Optional[str] = None
    trust_forwarded: bool = False
    log_health: bool = False
    cors_origin: Optional[str] = None

    # -- plumbing -----------------------------------------------------------
    def _client_key(self) -> str:
        raw = ""
        headers = getattr(self, "headers", None)
        if self.trust_forwarded and headers is not None:
            fwd = headers.get("X-Forwarded-For")
            if fwd:
                raw = fwd.split(",")[0].strip()[:64]
        if not raw:
            try:
                raw = str(self.client_address[0])
            except Exception:
                raw = "?"
        return _IP_SCRUB.sub("", raw) or "?"

    def _route_path(self) -> str:
        """Request path with query string and fragment stripped.

        Stripping the query is what makes the table closed rather than
        accidentally strict: `/health?probe=1` is the /health route, not an
        unroutable string. No other normalization happens — `/collapse/` is
        not `/collapse`, and the 404 body names the routes that do exist.
        """
        p = (getattr(self, "path", None) or "/").split("#", 1)[0].split("?", 1)[0]
        return p or "/"

    def _cors_allowed(self) -> bool:
        """Only an operator-configured exact browser origin receives CORS.

        CORS is not authentication, and native clients do not use it. Keeping
        it opt-in prevents an arbitrary web page from driving a local endpoint
        that happens to be running with a development bearer token.
        """
        try:
            origin = self.headers.get("Origin")
        except Exception:
            origin = None
        return bool(self.cors_origin and origin == self.cors_origin)

    def _cors(self) -> None:
        if not self._cors_allowed():
            return
        self.send_header("Access-Control-Allow-Origin", self.cors_origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Vary", "Origin")

    def _send(self, code: int, obj: Dict[str, Any], extra: Tuple = (),
              with_body: bool = True) -> None:
        data = json.dumps(obj, separators=(",", ":"), default=str).encode()
        self.responded = True
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in extra:
            self.send_header(k, v)
        self._cors()
        self.end_headers()
        if with_body:
            self.wfile.write(data)
        self._access(code)

    def _send_local_api(self, code: int, operation: str, result: Dict[str, Any],
                     extra: Tuple = (), with_body: bool = True) -> None:
        """Send a versioned response while keeping `_send` as the sole I/O path."""
        self._send(code, _local_api_envelope(operation, result), extra=extra,
                   with_body=with_body)

    # -- logging ------------------------------------------------------------
    def log_request(self, code="-", size="-"):
        # Silenced: the raw request line carries the query string. We emit our
        # own structured line from _access() instead.
        pass

    def log_message(self, fmt, *args):
        sys.stderr.write("engine_server: " + (fmt % args) + "\n")

    def _access(self, code: int) -> None:
        """One structured line per request. Never the caller's input."""
        try:
            path = self._route_path()
            if path == "/health" and not self.log_health:
                return  # a 1/sec platform probe must not bury human traffic
            fields = [f"ip={self._client_key()}",
                      f"method={getattr(self, 'command', None) or '-'}",
                      f"path={path}",
                      f"status={code}"]
            n = getattr(self, "in_bytes", None)
            if n is not None:
                fields.append(f"in_bytes={n}")
                fields.append(f"in_sha256={getattr(self, 'in_sha', '-')}")
            sys.stderr.write("engine_server: " + " ".join(fields) + "\n")
        except Exception:
            pass  # logging must never be able to fail a request

    # -- refusals (fixed strings only) --------------------------------------
    def _not_found(self, path: str) -> None:
        result = {"schema": SCHEMA, "status": "REFUSED",
                  "error": "not found",
                  "valid_routes": list(VALID_ROUTES),
                  "reason": "no such endpoint"}
        if _is_local_api_path(path):
            self._send_local_api(404, "unknown", result)
        else:
            self._send(404, result)

    def _method_not_allowed(self, allow: Tuple[str, ...], path: str) -> None:
        result = {"schema": SCHEMA, "status": "REFUSED",
                  "error": "method not allowed",
                  "allow": list(allow),
                  "reason": "this path answers a different method"}
        extra = (("Allow", ", ".join(allow)),)
        if _is_local_api_path(path):
            self._send_local_api(405, _local_api_operation(path), result, extra=extra)
        else:
            self._send(405, result, extra=extra)

    def _internal_error(self) -> None:
        # Detail goes to the operator's stderr and nowhere else.
        try:
            sys.stderr.write("engine_server: UNHANDLED on %s %s\n%s" % (
                self.command, self._route_path(), traceback.format_exc()))
        except Exception:
            pass
        if getattr(self, "responded", False):
            self.close_connection = True
            return
        self.close_connection = True
        result = {"schema": SCHEMA, "status": "REFUSED",
                  "error": "internal error", "reason": "internal error"}
        path = self._route_path()
        if _is_local_api_path(path):
            self._send_local_api(500, _local_api_operation(path), result)
        else:
            self._send(500, result)

    def send_error(self, code, message=None, explain=None):
        # The stdlib default renders an HTML page that echoes the offending
        # request text back to the caller ("Unsupported method ('PUT')").
        # Nothing echoes: fixed strings, JSON, and the same no-leak rule as
        # every other path.
        self.close_connection = True
        try:
            code = int(code)
        except Exception:
            code = 500
        if getattr(self, "responded", False):
            return
        result = {"schema": SCHEMA, "status": "REFUSED",
                  "error": _ERROR_TEXT.get(code, "request refused"),
                  "reason": _ERROR_TEXT.get(code, "request refused")}
        path = self._route_path()
        if _is_local_api_path(path):
            self._send_local_api(code, _local_api_operation(path), result)
        else:
            self._send(code, result)

    # -- dispatch -----------------------------------------------------------
    def _dispatch(self, method: str) -> None:
        self.responded = False
        self.in_bytes = None
        self.in_sha = None
        try:
            path = self._route_path()
            allowed = ROUTES.get(path)
            if allowed is None:
                self._not_found(path)
                return
            if method == "OPTIONS":
                self._preflight(path)
                return
            if method == "HEAD" and "GET" in allowed:
                self._get(path, with_body=False)
                return
            if method not in allowed:
                self._method_not_allowed(allowed, path)
                return
            if method == "GET":
                self._get(path)
                return
            self._post(path)
        except Exception:
            self._internal_error()

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_TRACE(self):
        self._dispatch("TRACE")  # never echo the request back

    def do_OPTIONS(self):
        self._dispatch("OPTIONS")

    # -- routes -------------------------------------------------------------
    def _preflight(self, path: str) -> None:
        # CORS preflight — a browser mechanism, so it is exempt from auth and
        # rate limits (it carries no body and performs no work). An Origin
        # that was not explicitly configured receives a fixed refusal rather
        # than a wildcard grant. A bare OPTIONS (no Origin) stays harmless.
        origin = self.headers.get("Origin")
        if origin and not self._cors_allowed():
            result = _refused("CORS origin not allowed", "forbidden")
            if _is_local_api_path(path):
                self._send_local_api(403, _local_api_operation(path), result)
            else:
                self._send(403, result)
            return
        self.responded = True
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()
        self._access(204)

    def _get(self, path: str, with_body: bool = True) -> None:
        import primus

        tools = sorted(t.lstrip("/") for t in _TOOLS)
        if path == "/v1/capabilities":
            from primus.certify import MAX_SEQ_TERMS, MAX_TEXT_CHARS

            self._send_local_api(200, "capabilities", {
                "operations": [
                    {"operation": "collapse", "method": "POST",
                     "path": "/v1/collapse",
                     "body": {"required": ["surface"],
                              "surface": "string or array of JSON integers"}},
                    {"operation": "certify", "method": "POST",
                     "path": "/v1/certify",
                     "body": {"required": ["text"], "text": "string"}},
                ],
                "limits": {"body_bytes": MAX_BODY_BYTES,
                           "surface_terms": MAX_SEQ_TERMS,
                           "certify_chars": MAX_TEXT_CHARS},
                "retry_after_seconds": {
                    "rate_limited": RATE_LIMIT_RETRY_AFTER_SECONDS,
                    "busy": BUSY_RETRY_AFTER_SECONDS},
                "content_type": "application/json",
                "request_fields": "unknown fields are refused",
                "authentication": {"post_bearer": "optional_static",
                                   "configured": bool(self.token)},
            }, with_body=with_body)
            return
        if path == "/health":
            self._send(200, {"schema": SCHEMA, "ok": True,
                             "engine": primus.__version__,
                             "tools": tools}, with_body=with_body)
            return
        # "/" — a short banner. Routes and budgets, nothing about the box.
        self._send(200, {"schema": SCHEMA,
                         "service": "chiron-engine",
                         "engine": primus.__version__,
                         "what": "request in, certificate out — "
                                 "the verifier that refuses",
                         "tools": tools,
                         "routes": list(VALID_ROUTES),
                         "limits": {"body_bytes": MAX_BODY_BYTES,
                                    "rate_per_min": self.limiter.per_ip},
                         "license": "Apache-2.0"},
                   with_body=with_body)

    def _post(self, path: str) -> None:
        local_api_spec = _LOCAL_API_TOOLS.get(path)
        if local_api_spec is None:
            required, impl = _TOOLS[path]
            operation = None
        else:
            operation, required, impl = local_api_spec

        def respond(code: int, obj: Dict[str, Any], extra: Tuple = ()) -> None:
            if operation is None:
                self._send(code, obj, extra=extra)
            else:
                self._send_local_api(code, operation, obj, extra=extra)

        if self.token:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {self.token}":
                respond(401, _refused("missing or wrong bearer token",
                                      "unauthorized"))
                return
        if not self.limiter.allow(self._client_key()):
            respond(429, _refused(
                "rate limit: this endpoint budgets requests per minute; "
                "wait and retry", "rate limited"),
                extra=(("Retry-After", str(RATE_LIMIT_RETRY_AFTER_SECONDS)),))
            return
        if operation is not None:
            media_type = self.headers.get("Content-Type", "").split(";", 1)[0]
            if media_type.strip().lower() != "application/json":
                respond(415, _refused("Content-Type must be application/json",
                                      "unsupported media type"))
                return
        try:
            length = int(self.headers.get("Content-Length", -1))
        except ValueError:
            length = -1
        if length < 0:
            self.close_connection = True  # nothing framed the body; hang up
            respond(411, _refused("Content-Length required",
                                  "length required"))
            return
        if length > MAX_BODY_BYTES:
            # Refused BEFORE reading: the oversized body is never pulled into
            # memory, so the socket is closed rather than drained.
            self.close_connection = True
            respond(413, _refused(
                f"over budget: request bodies are capped at {MAX_BODY_BYTES} bytes",
                "payload too large"))
            return
        raw = self.rfile.read(length)
        self.in_bytes = len(raw)
        self.in_sha = hashlib.sha256(raw).hexdigest()[:16]
        try:
            body = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            # JSONDecodeError, RecursionError from pathological nesting,
            # anything else the decoder can raise: one bounded refusal.
            respond(400, _refused("body must be valid JSON", "bad request"))
            return
        if operation is not None:
            invalid = _validate_local_api_body(operation, required, body)
            if invalid is not None:
                respond(400, invalid)
                return
        elif not isinstance(body, dict) or required not in body:
            respond(400, _refused(
                f"JSON object with a {required!r} field required", "bad request"))
            return
        if not self.gate.acquire(blocking=False):
            respond(429, _refused("busy: concurrency budget exhausted; retry",
                                  "busy"),
                    extra=(("Retry-After", str(BUSY_RETRY_AFTER_SECONDS)),))
            return
        try:
            code, obj = impl(body)
        except Exception as exc:
            # engine exceptions are refusals; only the TYPE name leaves the box
            code, obj = 200, _refused(
                f"engine refused this input ({type(exc).__name__})")
        finally:
            self.gate.release()
        respond(code, obj)


def _configured_cors_origin(raw: Optional[str]) -> Optional[str]:
    """Validate the one explicit browser origin an operator may opt into.

    A CORS allow-list of one exact origin is intentionally small. Paths,
    credentials, query strings, fragments, and `*` are not Origins and are
    rejected at startup rather than accidentally becoming an echo policy.
    """
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        # Accessing .port also catches malformed values such as :abc.
        parsed.port
    except (TypeError, ValueError):
        raise ValueError("CHIRON_CORS_ORIGIN must be one exact http(s) origin")
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc or
            parsed.username is not None or parsed.password is not None or
            parsed.path or parsed.query or parsed.fragment or
            raw != f"{parsed.scheme}://{parsed.netloc}"):
        raise ValueError("CHIRON_CORS_ORIGIN must be one exact http(s) origin")
    return raw


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Chiron engine endpoint (certificates out, source never)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8790)
    args = ap.parse_args(argv)

    Handler.limiter = Limiter(
        per_ip=int(os.environ.get("CHIRON_RATE_PER_MIN", "30")),
        global_=int(os.environ.get("CHIRON_RATE_GLOBAL_PER_MIN", "240")))
    Handler.gate = threading.BoundedSemaphore(
        int(os.environ.get("CHIRON_MAX_CONCURRENCY", "4")))
    Handler.token = os.environ.get("CHIRON_API_TOKEN") or None
    Handler.trust_forwarded = os.environ.get("CHIRON_TRUST_FORWARDED") == "1"
    Handler.log_health = os.environ.get("CHIRON_LOG_HEALTH") == "1"
    try:
        Handler.cors_origin = _configured_cors_origin(
            os.environ.get("CHIRON_CORS_ORIGIN"))
    except ValueError as exc:
        ap.error(str(exc))

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"engine_server: serving collapse+certify+conjecture plus v1 on "
          f"http://{args.host}:{args.port}  (auth: {'on' if Handler.token else 'off'}; "
          f"cors: {'exact origin' if Handler.cors_origin else 'off'})",
          file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
