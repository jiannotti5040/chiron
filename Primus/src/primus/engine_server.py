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
  * optional bearer auth: set CHIRON_API_TOKEN and every POST requires it
  * permissive CORS (Allow-Origin *) so a browser can call it directly — safe
    because the API is read-only, cookieless, and carries no ambient authority

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
  CHIRON_TRUST_FORWARDED      "1" to take the client IP from the first
                              X-Forwarded-For hop — set ONLY behind a proxy
                              that overwrites that header (Fly/Render do)

Run:    PYTHONPATH=src python3 -m primus.engine_server --host 127.0.0.1 --port 8790
Deploy: see DEPLOY_ENDPOINT.md (Fly.io / Render notes).

Status: implemented-and-tested (test_engine_server.py drives a real server
process over real HTTP). The server wraps the engine; it changes nothing on
any stamping path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
import traceback
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

MAX_BODY_BYTES = 128 * 1024  # certify MAX_TEXT_CHARS (100k) + JSON overhead
SCHEMA = "primus.engine_server/1"


def _refused(reason: str, error: str = "refused") -> Dict[str, Any]:
    return {"schema": SCHEMA, "status": "REFUSED", "error": error, "reason": reason}


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

    def _cors(self) -> None:
        # A public read-only compute API with no cookies and no ambient
        # authority: a permissive CORS policy lets a browser (the playground)
        # call it directly, and grants no capability a curl couldn't already.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

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
    def _not_found(self) -> None:
        self._send(404, {"schema": SCHEMA, "status": "REFUSED",
                         "error": "not found",
                         "valid_routes": list(VALID_ROUTES),
                         "reason": "no such endpoint"})

    def _method_not_allowed(self, allow: Tuple[str, ...]) -> None:
        self._send(405, {"schema": SCHEMA, "status": "REFUSED",
                         "error": "method not allowed",
                         "allow": list(allow),
                         "reason": "this path answers a different method"},
                   extra=(("Allow", ", ".join(allow)),))

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
        self._send(500, {"schema": SCHEMA, "status": "REFUSED",
                         "error": "internal error",
                         "reason": "internal error"})

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
        self._send(code, {"schema": SCHEMA, "status": "REFUSED",
                          "error": _ERROR_TEXT.get(code, "request refused"),
                          "reason": _ERROR_TEXT.get(code, "request refused")})

    # -- dispatch -----------------------------------------------------------
    def _dispatch(self, method: str) -> None:
        self.responded = False
        self.in_bytes = None
        self.in_sha = None
        try:
            path = self._route_path()
            allowed = ROUTES.get(path)
            if allowed is None:
                self._not_found()
                return
            if method == "OPTIONS":
                self._preflight()
                return
            if method == "HEAD" and "GET" in allowed:
                self._get(path, with_body=False)
                return
            if method not in allowed:
                self._method_not_allowed(allowed)
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
    def _preflight(self) -> None:
        # CORS preflight — a browser mechanism, so it is exempt from auth and
        # rate limits (it carries no body and performs no work).
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
        required, impl = _TOOLS[path]
        if self.token:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {self.token}":
                self._send(401, _refused("missing or wrong bearer token",
                                         "unauthorized"))
                return
        if not self.limiter.allow(self._client_key()):
            self._send(429, _refused(
                "rate limit: this endpoint budgets requests per minute; "
                "wait and retry", "rate limited"))
            return
        try:
            length = int(self.headers.get("Content-Length", -1))
        except ValueError:
            length = -1
        if length < 0:
            self.close_connection = True  # nothing framed the body; hang up
            self._send(411, _refused("Content-Length required",
                                     "length required"))
            return
        if length > MAX_BODY_BYTES:
            # Refused BEFORE reading: the oversized body is never pulled into
            # memory, so the socket is closed rather than drained.
            self.close_connection = True
            self._send(413, _refused(
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
            self._send(400, _refused("body must be valid JSON", "bad request"))
            return
        if not isinstance(body, dict) or required not in body:
            self._send(400, _refused(
                f"JSON object with a {required!r} field required", "bad request"))
            return
        if not self.gate.acquire(blocking=False):
            self._send(429, _refused("busy: concurrency budget exhausted; retry",
                                     "busy"))
            return
        try:
            code, obj = impl(body)
        except Exception as exc:
            # engine exceptions are refusals; only the TYPE name leaves the box
            code, obj = 200, _refused(
                f"engine refused this input ({type(exc).__name__})")
        finally:
            self.gate.release()
        self._send(code, obj)


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

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"engine_server: serving collapse+certify+conjecture on "
          f"http://{args.host}:{args.port}  (auth: {'on' if Handler.token else 'off'})",
          file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
