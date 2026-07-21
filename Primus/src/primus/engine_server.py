#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
primus.engine_server — the verifier-that-refuses as a minimal HTTP endpoint.

Request in, certificate out. The engine's source is never serialized: every
response is certificate/verdict JSON assembled from engine output plus fixed
strings, exceptions surface as a REFUSED envelope carrying the exception
TYPE NAME only (no messages, no tracebacks), and the only GET route is
/health. Everything hostile meets a refusal, not a crash:

  * body cap 128 KiB (fits certify's MAX_TEXT_CHARS with JSON overhead;
    larger bodies are REFUSED with 413 before parsing)
  * sequence caps reuse the certify/conjecture bounds (MAX_SEQ_TERMS = 256)
  * per-IP and global rate limits (sliding minute window; 429 + REFUSED)
  * bounded concurrency (excess concurrent requests get 429 immediately)
  * optional bearer auth: set CHIRON_API_TOKEN and every POST requires it
  * permissive CORS (Allow-Origin *) so a browser can call it directly — safe
    because the API is read-only, cookieless, and carries no ambient authority

Endpoints (all request/response bodies are JSON):

  GET  /health                          liveness + engine version
  POST /collapse   {"surface": ...}     exact recovery with held-out proof,
                                        or honest refusal
  POST /certify    {"text": ...}        every checkable claim VERIFIED /
                                        REFUTED / REFUSED
  POST /conjecture {"terms": ..., "seed": 0}
                                        guess-and-prove behind the exact gate

Environment:
  CHIRON_API_TOKEN            require `Authorization: Bearer <token>` (default: off)
  CHIRON_RATE_PER_MIN         per-IP requests/minute        (default 30)
  CHIRON_RATE_GLOBAL_PER_MIN  total requests/minute         (default 240)
  CHIRON_MAX_CONCURRENCY      simultaneous engine calls     (default 4)
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
import json
import os
import re
import sys
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

MAX_BODY_BYTES = 128 * 1024  # certify MAX_TEXT_CHARS (100k) + JSON overhead
SCHEMA = "primus.engine_server/1"


def _refused(reason: str) -> Dict[str, Any]:
    return {"schema": SCHEMA, "status": "REFUSED", "reason": reason}


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
                "terms (the certify bound), and terms must be integers")
        surface: Any = terms
    else:
        raw = str(raw)
        if len(raw) > MAX_TEXT_CHARS:
            return 413, _refused(
                f"over budget: string surfaces are capped at {MAX_TEXT_CHARS} chars")
        ints = re.findall(r"-?\d+", raw)
        leftover = re.sub(r"[-\d\s,]+", "", raw)
        if ints and not leftover:
            if len(ints) > MAX_SEQ_TERMS:
                return 413, _refused(
                    f"over budget: integer surfaces are capped at {MAX_SEQ_TERMS} terms")
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
            "integer terms")
    seed = body.get("seed", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        return 400, _refused("seed must be an integer")
    cert = conjecture(terms, seed=seed)
    return 200, {"schema": SCHEMA, "tool": "conjecture", "certificate": cert}


_TOOLS = {"/collapse": ("surface", _do_collapse),
          "/certify": ("text", _do_certify),
          "/conjecture": ("terms", _do_conjecture)}


# -------------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    server_version = "chiron-engine-endpoint"
    sys_version = ""  # no Python version banner
    limiter: Limiter
    gate: threading.BoundedSemaphore
    token: Optional[str]
    trust_forwarded: bool

    # -- plumbing -----------------------------------------------------------
    def _client_key(self) -> str:
        if self.trust_forwarded:
            fwd = self.headers.get("X-Forwarded-For")
            if fwd:
                return fwd.split(",")[0].strip()
        return self.client_address[0]

    def _cors(self) -> None:
        # A public read-only compute API with no cookies and no ambient
        # authority: a permissive CORS policy lets a browser (the playground)
        # call it directly, and grants no capability a curl couldn't already.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send(self, code: int, obj: Dict[str, Any]) -> None:
        data = json.dumps(obj, separators=(",", ":"), default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # stderr, no bodies, no query strings
        sys.stderr.write("engine_server: %s %s\n" %
                         (self._client_key(), fmt % args))

    # -- routes -------------------------------------------------------------
    def do_OPTIONS(self):
        # CORS preflight — a browser mechanism, so it is exempt from auth and
        # rate limits (it carries no body and performs no work).
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            import primus
            self._send(200, {"schema": SCHEMA, "ok": True,
                             "engine": primus.__version__,
                             "tools": sorted(t.lstrip("/") for t in _TOOLS)})
        elif self.path in _TOOLS:
            self._send(405, _refused("POST a JSON body to this endpoint"))
        else:
            self._send(404, _refused("no such endpoint"))

    def do_POST(self):
        route = _TOOLS.get(self.path)
        if route is None:
            self._send(404, _refused("no such endpoint"))
            return
        if self.token:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {self.token}":
                self._send(401, _refused("missing or wrong bearer token"))
                return
        if not self.limiter.allow(self._client_key()):
            self._send(429, _refused(
                "rate limit: this endpoint budgets requests per minute; "
                "wait and retry"))
            return
        try:
            length = int(self.headers.get("Content-Length", -1))
        except ValueError:
            length = -1
        if length < 0:
            self._send(411, _refused("Content-Length required"))
            return
        if length > MAX_BODY_BYTES:
            self._send(413, _refused(
                f"over budget: request bodies are capped at {MAX_BODY_BYTES} bytes"))
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8", "replace"))
        except json.JSONDecodeError:
            self._send(400, _refused("body must be valid JSON"))
            return
        required, impl = route
        if not isinstance(body, dict) or required not in body:
            self._send(400, _refused(f"JSON object with a {required!r} field required"))
            return
        if not self.gate.acquire(blocking=False):
            self._send(429, _refused("busy: concurrency budget exhausted; retry"))
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
